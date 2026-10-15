import importlib
import json
from dataclasses import replace

import httpx
import pytest

from backend.services.evidence_extraction import EvidenceAsset, file_hash
from backend.services.evidence_validation import EvidenceRegistry


def context_and_config(tmp_path, kind="external_api"):
    module = importlib.import_module("backend.services.vlm_provider")
    path = tmp_path / "masked.jpg"
    path.write_bytes(b"masked-fixture")
    asset = EvidenceAsset("EVD-1", "rec", "cnd", path, file_hash(path), 2.0, 2.0, "VIDEO", "image/jpeg", 0, "MASKED", "PASSED")
    context = module.AnalysisContext(EvidenceRegistry("rec", "cnd", (asset,)), 10.0, (asset,), ({"time_s": 2.0, "speed": 3.0, "gps": "private"},))
    endpoint = "https://provider.example/v1/chat/completions" if kind == "external_api" else "http://127.0.0.1:8080/v1/chat/completions"
    config = module.ProviderConfig(kind, endpoint, "fixture-model", "fixture-revision", allowed_hosts=("provider.example",), egress_approved=True)
    return module, context, config


def provider_response():
    analysis = {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": 1.0, "critical_s": 2.0, "end_s": 3.0}, "summary": "Braking", "timeline": [{"time_s": 2.0, "observation": "Slowing", "evidence_ids": ["EVD-1"], "source": "VIDEO", "certainty": "OBSERVED"}], "factors": [], "unknowns": [], "review_status": "DRAFT"}
    return {"choices": [{"message": {"content": json.dumps(analysis)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}


def test_trigger_memory_is_transmitted_without_switching_sequence_to_final(tmp_path):
    module, context, config = context_and_config(tmp_path, 'self_hosted')
    memory = {'context_id': 'rec:job:cnd', 'observations': [{'summary': 'Earlier actor approaching', 'frame_times_s': [1.0]}]}
    previous_signature = module.batch_signature(context, config)
    context = replace(context, trigger_memory=memory, decision_scope='SUPPLIED_SEQUENCE', frame_roles=('CORE',))
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=provider_response())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        module.create_provider(config, client=client).analyze(context)
    content = requests[0]['messages'][0]['content']
    payload = json.loads(content[0]['text'].split('\n')[-1])
    assert payload['trigger_memory'] == memory
    assert payload['decision_scope'] == 'SUPPLIED_SEQUENCE'
    assert 't_video_s=2.0 role=CORE' in content[1]['text']
    assert module.batch_signature(context, config) != previous_signature


def test_history_cannot_authorize_evidence_outside_current_candidate(tmp_path):
    module, context, _ = context_and_config(tmp_path)
    alien = replace(context.frames[0], evidence_id='EVD-ALIEN', candidate_id='another')
    context = replace(context, registry=replace(context.registry, assets=(*context.frames, alien)), prior_evidence_ids=('EVD-ALIEN',))
    from backend.services.evidence_validation import validate_analysis
    with pytest.raises(ValueError, match='outside recording/candidate'):
        validate_analysis(provider_response_analysis(), module.batch_registry(context), 10.)


def provider_response_analysis():
    return json.loads(provider_response()['choices'][0]['message']['content'])


def test_new_visual_claim_about_unattached_history_is_rejected(tmp_path):
    module, context, _ = context_and_config(tmp_path)
    old = context.frames[0]
    current = replace(old, evidence_id='EVD-2', time_start_s=3., time_end_s=3.)
    context = replace(context, frames=(current,), registry=replace(context.registry, assets=(old,current)),
                      prior_evidence_ids=(old.evidence_id,), trigger_memory={'observations': [{'timeline': []}]})
    with pytest.raises(ValueError, match='historical'):
        module.validate_context_analysis(provider_response_analysis(), context)
    previous = provider_response_analysis()
    previous['timeline'][0]['observation'] = 'Validated ' * 100
    compacted = {**previous['timeline'][0], 'observation': 'Truncated replacement'}
    context = replace(context, prior_observations=({'timeline': previous['timeline']},),
                      trigger_memory={'observations': [{'timeline': [compacted]}]})
    assert module.validate_context_analysis(previous, context).incident_detected
    changed = {**previous, 'timeline': [compacted]}
    with pytest.raises(ValueError, match='historical'):
        module.validate_context_analysis(changed, context)


def test_temporal_settings_reject_non_six_frame_budget_before_processing():
    from backend.config import Settings
    with pytest.raises(ValueError, match='six'):
        Settings(_env_file=None, qwen_temporal_context=True, qwen_batch_frames=4)


@pytest.mark.parametrize("kind", ["external_api", "self_hosted"])
def test_both_adapters_share_schema_filter_telemetry_and_record_provenance(tmp_path, kind):
    module, context, config = context_and_config(tmp_path, kind)
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(200, json=provider_response())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = module.create_provider(config, client=client).analyze(context)
    assert result.analysis.review_status == "DRAFT"
    assert result.provenance["config_hash"]
    assert result.provenance["input_hashes"] == [context.frames[0].sha256]
    assert result.usage["input_tokens"] == 100
    assert result.usage["cost_usd"] is None
    assert "gps" not in json.dumps(requests)
    assert "private" not in json.dumps(requests)
    assert requests[0]["model"] == "fixture-model"
    if kind == "self_hosted":
        branches = requests[0]["response_format"]["json_schema"]["schema"]["anyOf"]
        absent = next(branch for branch in branches if branch["properties"]["incident_detected"]["const"] is False)
        assert absent["properties"]["window"] == {"type": "null"}
        assert absent["properties"]["timeline"]["maxItems"] == 0
        assert absent["properties"]["factors"]["maxItems"] == 0


@pytest.mark.parametrize("kind", ["external_api", "self_hosted"])
def test_retry_is_bounded_and_invalid_schema_not_retried(tmp_path, kind):
    module, context, config = context_and_config(tmp_path, kind)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="unavailable"):
            module.create_provider(config, client=client).analyze(context)
    assert len(calls) == config.max_attempts
    calls.clear()
    with httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200, json={}))) as client:
        with pytest.raises(ValueError):
            module.create_provider(config, client=client).analyze(context)
    assert len(calls) == 1


@pytest.mark.parametrize("state,validation", [("RAW", "PASSED"), ("MASKED", "FAILED"), ("MASKED", "NOT_CHECKED")])
def test_external_privacy_failure_blocks_network(tmp_path, state, validation):
    module, context, config = context_and_config(tmp_path)
    frame = replace(context.frames[0], privacy_state=state, privacy_validation=validation)
    context = replace(context, frames=(frame,), registry=replace(context.registry, assets=(frame,)))
    with httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail("egress before privacy"))) as client:
        with pytest.raises(ValueError, match="privacy"):
            module.create_provider(config, client=client).analyze(context)


@pytest.mark.parametrize("change", [{"endpoint": "https://evil.example/v1"}, {"egress_approved": False}, {"endpoint": "http://provider.example/v1"}, {"max_attempts": 0}, {"timeout_s": float("nan")}, {"max_frames": 0}])
def test_endpoint_policy_and_budgets_are_explicit(tmp_path, change):
    module, context, config = context_and_config(tmp_path)
    with pytest.raises(ValueError):
        module.create_provider(replace(config, **change))


def test_self_hosted_rejects_public_endpoint(tmp_path):
    module, context, config = context_and_config(tmp_path, "self_hosted")
    with pytest.raises(ValueError, match="internal"):
        module.create_provider(replace(config, endpoint="https://8.8.8.8/v1"))


def test_candidate_measurements_are_explicit_in_model_context(tmp_path):
    module, context, config = context_and_config(tmp_path, 'self_hosted')
    context = replace(context, candidate_window=(0.,2.,4.), telemetry_rows=(
        {'time_s':1.,'speed':9.,'brake':0.,'acceleration':0.},
        {'time_s':2.,'speed':2.,'brake':.902,'acceleration':-27.043},
        {'time_s':2.5,'speed':0.,'brake':.902,'acceleration':0.}))
    payloads=[]
    def handler(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200,json=provider_response())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        module.create_provider(config,client=client).analyze(context)
    data=json.loads(payloads[0]['messages'][0]['content'][0]['text'].split('\n')[-1])
    assert data['telemetry_findings']['peak_brake']==.902
    assert data['telemetry_findings']['min_acceleration_m_s2']==-27.043
    assert data['telemetry_findings']['speed_drop_m_s']==9.
