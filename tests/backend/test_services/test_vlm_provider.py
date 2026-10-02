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
