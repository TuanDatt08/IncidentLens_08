from io import BytesIO

import pytest
from starlette.datastructures import UploadFile


@pytest.mark.asyncio
async def test_ollama_worker_exports_sql_draft_uncertainty_and_scoped_paths(db_client, monkeypatch):
    import json
    from pathlib import Path

    import backend.worker as worker
    from backend.config import get_settings
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.services.incidents import create_incident
    from backend.services.jobs import create_job, get_job
    from backend.services.video import VideoProbeResult, VideoService
    from backend.services.vlm_provider import ProviderResult

    monkeypatch.setenv("QWEN_RUNTIME", "ollama")
    monkeypatch.setenv("QWEN_ARTIFACT_SUBDIR", "output")
    monkeypatch.setenv("QWEN_V1_LOG_OFFSET_S", "0")
    monkeypatch.setenv("QWEN_INFERENCE_FRAME_LIMIT", "8")
    monkeypatch.setenv("QWEN_BATCH_FRAMES", "4")
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
    scoped_settings = []

    class Provider:
        def analyze(self, context):
            calls.append(context)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Uncertain", "timeline": [], "factors": [], "unknowns": ["Missing visual coverage"], "review_status": "DRAFT"}), {}, {})

    def factory(settings):
        scoped_settings.append(settings)
        return Provider()

    monkeypatch.setattr(worker, "create_local_provider", factory)
    incident = create_incident(UploadFile(BytesIO(b"video"), filename="sample.mp4"), UploadFile(BytesIO(b"sec_from_incident,brake\n0,0\n10,1\n11,0\n20,0\n"), filename="sample.csv"), principal=db_client.principal)
    identity = incident["incident_id"]
    job = create_job(identity, principal=db_client.principal)
    assert worker.run_once(job_id=job["job_id"])
    output = Path(get_settings().incident_storage_dir) / identity / "output"
    assert get_job(job["job_id"])["status"] == "succeeded"
    assert json.loads((output / "draft.json").read_text())["review_status"] == "DRAFT"
    rich_draft = json.loads((output / "draft-v2.json").read_text())
    assert rich_draft["summary"] == "Uncertain\nUncertain"
    assert "Missing visual coverage" in rich_draft["unknowns"]
    assert json.loads((output / "review.json").read_text())["approved_by"] is None
    metadata = json.loads((output / "model-metadata.json").read_text())
    assert "Missing visual coverage" in metadata["unknowns"]
    assert metadata["draft_v2"] == rich_draft
    manifest = json.loads((output / "local-analysis.json").read_text())
    assert manifest["visual_coverage"]["extracted_frame_count"] == 32
    assert manifest["visual_coverage"]["model_frame_count"] == 8
    assert not manifest["visual_coverage"]["complete"]
    assert sum(len(context.frames) for context in calls) == 8
    assert Path(scoped_settings[0].qwen_requests_dir) == output.resolve() / "requests"
