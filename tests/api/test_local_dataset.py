import json

import httpx
import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_dataset_archives_reference_labels_without_sending_them_to_model(db_client, tmp_path, monkeypatch):
    import backend.worker as worker
    from backend.analyze_local_dataset import analyze_directory
    from backend.config import get_settings
    from backend.db import session_scope
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.models.tables import Incident
    from backend.services.video import VideoProbeResult, VideoService
    from backend.services.vlm_provider import ProviderResult

    source = tmp_path / "dataset"
    source.mkdir()
    (source / "sample.mp4").write_bytes(b"video")
    (source / "sample.csv").write_text("sec_from_incident,brake\n0,0\n10,1\n11,0\n20,0\n")
    (source / "sample.expected.json").write_text('{"label":"REFERENCE_ONLY_POISON","verified_by":null}')
    (source / "README.md").write_text("Reference source information")
    monkeypatch.setenv("QWEN_RUNTIME", "ollama")
    monkeypatch.setenv("QWEN_ARTIFACT_SUBDIR", "output")
    monkeypatch.setenv("QWEN_PROMPT_PATH", "./backend/prompts/ollama_incident.txt")
    get_settings.cache_clear()
    get_settings().qwen_candidate_min_acceleration = None
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(30, 30, 320, 240))

    def extract(self, source, at_s, *args):
        path = args[-1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(str(at_s).encode())
        return path

    monkeypatch.setattr(VideoService, "extract_frame", extract)
    monkeypatch.setattr(VideoService, "extract_clip", extract)
    calls = []

    class Provider:
        def analyze(self, context):
            calls.append(context)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Not confirmed", "timeline": [], "factors": [], "unknowns": ["Coverage limited"], "review_status": "DRAFT"}), {}, {})

    monkeypatch.setattr(worker, "create_local_provider", lambda settings: Provider())
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"models": []})))
    monkeypatch.setattr("backend.analyze_local_dataset.httpx.Client", lambda **kw: client)
    result = analyze_directory(source, 0, "fixture explicit frame/log mapping")
    identity = result[0]["incident_id"]
    assert result[0]["review_status"] == "DRAFT"
    assert all("REFERENCE_ONLY_POISON" not in repr(context) for context in calls)
    with session_scope() as session:
        row = session.scalar(select(Incident).where(Incident.incident_id == identity))
        assert row.source["reference_labels_sent_to_model"] is False
        assert row.raw_incident_data["reference_documents"]["sample.expected.json"]["label"] == "REFERENCE_ONLY_POISON"
        assert len(row.raw_incident_data["archive_files"]) == 4
        assert row.video_uri.startswith(identity + "/input/")
    output = tmp_path / "storage" / identity / "output"
    assert json.loads((output / "draft.json").read_text())["review_status"] == "DRAFT"
    assert (output / "model-metadata.json").is_file()
