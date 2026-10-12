from pathlib import Path

import pytest

from backend.services.prompt_pipeline import prompt_contracts, validate_stage


def test_requested_prompt_contracts_and_required_fields():
    contracts = prompt_contracts(Path('backend/data/promt.txt').read_text(encoding='utf-8'))
    assert contracts['A'][1].model_json_schema()['properties']['schema_version']['const'] == 'incident_detection_v3'
    assert 'causal_analysis' in contracts['B'][1].model_json_schema()['required']
    with pytest.raises(ValueError):
        validate_stage({'schema_version': '2.0'}, contracts['A'][1], {}, 10)


def test_invented_evidence_and_out_of_bounds_times_rejected():
    contracts = prompt_contracts(Path('backend/data/promt.txt').read_text(encoding='utf-8'))
    data = {'schema_version': 'incident_detection_v3', 'time_basis': 'video_seconds', 'review_status': 'DRAFT', 'video_duration_s': 10.0, 'analyzed_intervals': [{'start_s': 0.0, 'end_s': 10.0}], 'overall_status': 'INCONCLUSIVE', 'incidents': [{'incident_id': 'I1', 'status': 'INCONCLUSIVE', 'event_type': 'OTHER', 'onset_s': None, 'critical_s': None, 'end_s': None, 'clip_window': {'start_s': None, 'end_s': None}, 'confidence': 0.1, 'event_summary': 'Chưa đủ bằng chứng', 'evidence': [{'evidence_id': 'FAKE', 'time_s': 1.0, 'source': 'VIDEO_FRAME', 'observation': 'Xe'}], 'unknowns': ['Chưa đủ frame']}], 'coverage_limitations': ['Mẫu thưa']}
    with pytest.raises(ValueError, match='evidence'):
        validate_stage(data, contracts['A'][1], {}, 10)


def test_pipeline_keeps_prompt_raw_response_and_missing_sync(monkeypatch, tmp_path):
    import json

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline
    root = tmp_path / 'incidents'
    source = root / 'INC-TEST' / 'source'
    source.mkdir(parents=True)
    (source / 'video.mp4').write_bytes(b'video')
    (source / 'telemetry.csv').write_text('sec_from_incident,speed_kmh,brake,accel_x\n-1,20,0,0\n0,0,1,-10\n')
    prompt = tmp_path / 'promt.txt'
    prompt.write_text(Path('backend/data/promt.txt').read_text(encoding='utf-8'), encoding='utf-8')
    settings = Settings(qwen_runtime='ollama', qwen_prompt_path=str(prompt), qwen_outputs_path=str(tmp_path/'outputs.txt'))
    requests = []
    response = {'schema_version': 'incident_detection_v3', 'time_basis': 'video_seconds', 'review_status': 'DRAFT', 'video_duration_s': 2.0, 'analyzed_intervals': [{'start_s': 0., 'end_s': 2.}], 'overall_status': 'NO_INCIDENT', 'incidents': [], 'coverage_limitations': ['Mẫu thưa, chưa đủ quan sát toàn bộ.']}
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            import httpx
            requests.append(json)
            return httpx.Response(200, json={'choices': [{'message': {'content': __import__('json').dumps(response)}}], 'usage': {'total_tokens': 1}}, request=httpx.Request('POST', url))
    def extract(self, source, at, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'image')
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    result = pipeline.process_prompt_incident({'incident_id': 'INC-TEST', 'video_uri': 'INC-TEST/source/video.mp4', 'telemetry_uri': 'INC-TEST/source/telemetry.csv', 'video_metadata': {'duration': 2.0, 'fps': 30.}}, storage_root=root, settings=settings, job_id='JOB-TEST')
    assert not result.analysis.incident_detected
    assert result.analysis.model_metadata['draft_v3']['alignment']['quality'] == 'UNKNOWN'
    assert len(requests[0]['messages'][1]['content']) == 5
    context = json.loads(requests[0]['messages'][1]['content'][0]['text'])
    assert context['unsynchronized_log']['rows']
    assert requests[0]['messages'][0]['content'].startswith('## STAGE A')
    output = root/'INC-TEST'/'output'
    assert list((output/'requests').glob('*.response.json'))
    assert (output/'JOB-TEST.draft-v3.json').is_file()


def test_explicit_offset_supplies_synchronized_log(monkeypatch, tmp_path):
    # Clock correctness is checked independently of any model verdict.
    from backend.services.log_normalization import normalize_log
    from backend.services.synchronization import TimeAnchor, align
    path = tmp_path/'log.csv'
    path.write_text('sec_from_incident,speed_kmh\n-7.967,30\n1.5,0\n')
    mapping = align({'duration': 9.533333}, normalize_log(path), [TimeAnchor(-7.967, 0., 'explicit_upload_offset'), TimeAnchor(1.566333, 9.533333, 'explicit_upload_offset')])
    assert mapping.quality == 'VERIFIED'
    assert mapping.to_video_seconds(-7.967) == pytest.approx(0.)


def test_stage_b_full_fields_are_kept_for_inconclusive_candidate(monkeypatch, tmp_path):
    import json

    from backend.config import Settings
    from backend.services import prompt_pipeline as pipeline

    root = tmp_path/'storage'
    source = root/'INC-T'/'source'
    source.mkdir(parents=True)
    (source/'video.mp4').write_bytes(b'video')
    prompt = Path('backend/data/promt.txt').read_text(encoding='utf-8')
    section_b = prompt.split('## STAGE B')[1]
    schema_b = json.JSONDecoder().raw_decode(section_b[section_b.index('{\n'):])[0]
    def enum_values(value):
        if isinstance(value, dict):
            return {k: enum_values(v) for k,v in value.items()}
        if isinstance(value, list):
            return []
        return value.split(' | ')[0] if isinstance(value, str) else value
    b = enum_values(schema_b)
    b.update(analysis_status='INCONCLUSIVE', summary='Chưa đủ bằng chứng để xác nhận sự cố.', confidence=0.1)
    b['timing'].update(clip_start_s=0., clip_end_s=2.)
    stages = []
    class Client:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            import httpx
            stage = json['response_format']['json_schema']['name'][-1]
            stages.append(stage)
            if stage == 'B':
                result = b
            else:
                context = __import__('json').loads(json['messages'][1]['content'][0]['text'])
                event = {'incident_id':'I1','status':'INCONCLUSIVE','event_type':'OTHER','onset_s':None,'critical_s':None,'end_s':None,'clip_window':{'start_s':None,'end_s':None},'confidence':0.1,'event_summary':'Cần kiểm tra thêm frame.','evidence':[{'evidence_id':context['evidence'][0]['evidence_id'],'time_s':0.,'source':'VIDEO_FRAME','observation':'Xe đang di chuyển.'}],'unknowns':['Chưa đủ quan sát.']}
                result = {'schema_version':'incident_detection_v3','time_basis':'video_seconds','review_status':'DRAFT','video_duration_s':2.,'analyzed_intervals':[{'start_s':0.,'end_s':2.}],'overall_status':'INCONCLUSIVE','incidents':[event],'coverage_limitations':['Frame thưa.']}
            return httpx.Response(200, json={'choices':[{'message':{'content':__import__('json').dumps(result)}}]},request=httpx.Request('POST',url))
    def extract(self, source, at, *args):
        path = args[-1]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'evidence')
        return path
    monkeypatch.setattr(pipeline, 'ensure_ollama_runtime', lambda settings: None)
    monkeypatch.setattr(pipeline.httpx, 'Client', Client)
    monkeypatch.setattr(pipeline.VideoService, 'extract_frame', extract)
    monkeypatch.setattr(pipeline.VideoService, 'extract_clip', extract)
    settings = Settings(qwen_runtime='ollama',qwen_outputs_path=str(tmp_path/'outputs.txt'))
    result = pipeline.process_prompt_incident({'incident_id':'INC-T','video_uri':'INC-T/source/video.mp4','video_metadata':{'duration':2.,'fps':30.}},storage_root=root,settings=settings,job_id='JOB-T')
    assert stages == ['A','B']
    stored = result.analysis.model_metadata['draft_v3']['stage_b'][0]
    assert stored['analysis_status'] == 'INCONCLUSIVE'
    assert set(stored['causal_analysis']) == {'supported_immediate_cause','root_cause','contributing_factors','hypotheses','causal_uncertainty'}
    assert not result.analysis.incident_detected
