import json

import httpx
import pytest

from backend.config import Settings
from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.evidence_validation import EvidenceRegistry
from backend.services.two_stage_qwen import FrameThenDecisionProvider
from backend.services.vlm_provider import AnalysisContext, ProviderConfig


def test_each_frame_is_observed_before_one_image_free_decision(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.services.two_stage_qwen.ensure_ollama_runtime', lambda s: None)
    frames = []
    for index in range(2):
        path = tmp_path / f'{index}.jpg'
        path.write_bytes(b'jpeg')
        frames.append(EvidenceAsset(f'E{index}', 'rec', 'candidate', path, file_hash(path), float(index), float(index), 'VIDEO', 'image/jpeg', index))
    seen = []
    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) <= 2:
            result = {'description': 'Người trên đường', 'pedestrians_visible': True, 'pedestrian_positions': ['phía trước xe'], 'other_objects': [], 'contact_evidence': 'UNKNOWN', 'occlusions': []}
        else:
            assert len(json.loads(payload['messages'][0]['content'][0]['text'].rsplit('\n', 1)[1])['frame_observations']) == 2
            result = {'schema_version': '2.0', 'incident_detected': False, 'event_type': 'UNKNOWN', 'time_basis': 'video_seconds', 'window': None, 'summary': 'Cần review', 'timeline': [], 'factors': [], 'unknowns': ['Chưa rõ xung đột'], 'review_status': 'DRAFT'}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(result)}}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
    provider = FrameThenDecisionProvider(ProviderConfig('self_hosted', 'http://localhost:11434/v1/chat/completions', 'qwen2.5vl:7b', 'qwen2.5vl:7b', requests_dir=str(tmp_path/'requests')), Settings(_env_file=None, qwen_runtime='ollama'))
    provider.client = httpx.Client(transport=httpx.MockTransport(respond))
    context = AnalysisContext(EvidenceRegistry('rec', 'candidate', tuple(frames)), 2., tuple(frames), candidate_window=(0., 1., 2.))
    result = provider.analyze(context)
    assert len(seen) == 3
    assert all(sum(item['type'] == 'image_url' for item in call['messages'][0]['content']) == 1 for call in seen[:2])
    assert not any(item['type'] == 'image_url' for item in seen[-1]['messages'][0]['content'])
    assert 'incident_detected' not in seen[0]['response_format']['json_schema']['schema']['properties']
    assert result.provenance['analysis_mode'] == 'frames_then_decision'
    assert result.usage['attempts'] == 3
    assert len(list((tmp_path/'requests').glob('*.response.json'))) == 3
    # A retry reuses valid per-image observations, but obtains a fresh decision.
    def decide_only(request):
        payload = json.loads(request.content)
        assert not any(item['type'] == 'image_url' for item in payload['messages'][0]['content'])
        result = {'schema_version': '2.0', 'incident_detected': False, 'event_type': 'UNKNOWN', 'time_basis': 'video_seconds', 'window': None, 'summary': 'Cần review', 'timeline': [], 'factors': [], 'unknowns': [], 'review_status': 'DRAFT'}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(result)}}]})
    provider.client.close()
    provider.client = httpx.Client(transport=httpx.MockTransport(decide_only))
    assert provider.analyze(context).usage['reused_observations'] == 2
    provider.client.close()


def test_observation_cannot_contain_an_incident_verdict():
    from backend.services.two_stage_qwen import FrameObservation
    with pytest.raises(ValueError):
        FrameObservation.model_validate({'incident_detected': False})
