import httpx
import pytest

from backend.config import Settings


def test_ollama_uses_local_vision_model_without_llama_launch(monkeypatch):
    from backend.services.qwen_local import create_local_provider, ensure_ollama_runtime

    settings = Settings(_env_file=None, qwen_runtime="ollama", qwen_endpoint="http://127.0.0.1:11434/v1/chat/completions")
    provider = create_local_provider(settings)
    assert provider.config.model == "qwen2.5vl:7b"
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"capabilities": ["vision"], "details": {"parameter_size": "7.6B"}})))
    monkeypatch.setattr("backend.services.qwen_local.httpx.Client", lambda **kw: client)
    ensure_ollama_runtime(settings)


def test_text_only_model_is_rejected(monkeypatch):
    from backend.services.qwen_local import ensure_ollama_runtime

    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"capabilities": ["completion"], "details": {"parameter_size": "7B"}})))
    monkeypatch.setattr("backend.services.qwen_local.httpx.Client", lambda **kw: client)
    with pytest.raises(ValueError, match="vision"):
        ensure_ollama_runtime(Settings(_env_file=None, qwen_endpoint="http://127.0.0.1:11434/v1/chat/completions"))


def test_compact_context_preserves_all_rows_fields_and_numeric_precision():
    from backend.services.vlm_provider import compact_records

    rows = [{"time_s": 1.123456789, "brake": 0.8}, {"time_s": 2.0, "speed": 8.888888888}]
    encoded = compact_records(rows)
    decoded = [{key: value for key, value in zip(encoded["columns"], values, strict=True) if value is not None} for values in encoded["rows"]]
    assert decoded == rows


def test_ollama_schema_rejects_no_detection_with_claims():
    jsonschema = pytest.importorskip("jsonschema")
    from backend.services.vlm_provider import detection_output_schema

    schema = detection_output_schema()
    value = {"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Unknown coverage", "timeline": [], "factors": [], "unknowns": [], "review_status": "DRAFT"}
    jsonschema.validate(value, schema)
    value["timeline"] = [{"time_s": 0.0, "observation": "Driving", "evidence_ids": ["EVD-1"], "source": "VIDEO", "certainty": "OBSERVED"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, schema)
