import importlib

import pytest

from backend.db import session_scope
from backend.models.tables_v2 import RecordingV2
from backend.services.identity import Principal
from backend.services.jobs_v2 import create_job, get_job
from backend.services.video import VideoService


@pytest.mark.asyncio
async def test_v2_worker_discovers_multiple_candidates_and_resumes_without_reanalysis(db_client, tmp_path, monkeypatch):
    from backend.config import get_settings
    root = tmp_path / "storage"
    root.mkdir(exist_ok=True)
    (root / "video.mp4").write_bytes(b"video")
    (root / "log.csv").write_text("clock,brake,mode\n0,0,AUTO\n2,1,AUTO\n3,0,MANUAL\n30,0,AUTO\n32,1,AUTO\n")
    monkeypatch.setenv("INCIDENT_STORAGE_DIR", str(root))
    get_settings.cache_clear()
    with session_scope() as session:
        session.add(RecordingV2(recording_id="rec", duration_s=60.0, video_uri="video.mp4", metadata_json={"duration": 60.0, "fps": 10.0, "telemetry_uri": "log.csv", "log_config": {"timestamp_column": "clock", "time_reference": "recording_relative"}, "anchors": [{"log_s": 0.0, "video_s": 0.0, "source": "fixture"}, {"log_s": 59.0, "video_s": 59.0, "source": "fixture"}]}))
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"rec"}))
    job = create_job("rec", "self_hosted", "fixture", actor)
    def output(self, source, start, *args):
        destination = args[-1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"fixture-{start}".encode())
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", output)
    monkeypatch.setattr(VideoService, "extract_clip", output)
    module = importlib.import_module("backend.worker_v2")
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.services.vlm_provider import ProviderResult
    calls = []
    class FakeProvider:
        def analyze(self, context):
            assert get_job(job["job_id"], actor)["stage"] == "ANALYSIS"
            calls.append(context)
            if len(calls) == 2:
                raise RuntimeError("simulated crash after first published candidate")
            asset = context.frames[0]
            analysis = {"schema_version": "2.0", "incident_detected": True, "event_type": "HARD_BRAKING", "time_basis": "video_seconds", "window": {"start_s": asset.time_start_s, "critical_s": asset.time_start_s, "end_s": asset.time_start_s + 0.5}, "summary": "Fixture braking", "timeline": [{"time_s": asset.time_start_s, "observation": "Slowing", "evidence_ids": [asset.evidence_id], "source": "VIDEO", "certainty": "OBSERVED"}], "factors": [], "unknowns": [], "review_status": "DRAFT"}
            return ProviderResult(AIIncidentAnalysisV2.model_validate(analysis), {"provider": "fake"}, {"attempts": 1})
    provider = FakeProvider()
    assert module.run_once(provider=provider, job_id=job["job_id"])
    status = get_job(job["job_id"], actor)
    assert status["status"] == "failed"
    assert any(item.get("report_id") for item in status["partial_results"])
    module.resume_failed(job["job_id"], actor)
    assert module.run_once(provider=provider, job_id=job["job_id"])
    status = get_job(job["job_id"], actor)
    assert status["status"] == "succeeded"
    assert len(calls) == 3
    assert "attempt-1" in calls[0].frames[0].path.parts
    assert "attempt-2" in calls[2].frames[0].path.parts
    assert len([item for item in status["partial_results"] if item.get("report_id")]) == 2


@pytest.mark.asyncio
async def test_pending_scan_resumes_and_cancellation_stops_next_frame(db_client, tmp_path, monkeypatch):
    from backend.config import get_settings
    root = tmp_path / "storage"
    root.mkdir()
    (root / "video.mp4").write_bytes(b"fixture")
    monkeypatch.setenv("INCIDENT_STORAGE_DIR", str(root))
    get_settings.cache_clear()
    with session_scope() as session:
        for name in ("resume", "cancel"):
            session.add(RecordingV2(recording_id=name, duration_s=180.0, video_uri="video.mp4", metadata_json={"duration": 180.0, "fps": 10.0}))
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"resume", "cancel"}))
    def output(self, source, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"frame")
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", output)
    module = importlib.import_module("backend.worker_v2")
    job = create_job("resume", "self_hosted", "resume", actor)["job_id"]
    module.run_once(provider=object(), job_id=job)
    assert get_job(job, actor)["error"]["code"] == "SPARSE_SCANNER_NOT_CONFIGURED"
    module.resume_failed(job, actor)
    module.run_once(provider=object(), job_id=job, scanner=lambda path, at_s: False)
    status = get_job(job, actor)
    assert status["status"] == "succeeded"
    assert status["coverage"]["sampled_frames"] == 3
    assert status["partial_results"][0]["scan_pending"] is False
    cancelled = create_job("cancel", "self_hosted", "cancel", actor)["job_id"]
    scanned = []
    def cancel(path, at_s):
        scanned.append(at_s)
        get_job(cancelled, actor, cancel=True)
        return False
    module.run_once(provider=object(), job_id=cancelled, scanner=cancel)
    assert scanned == [0.0]
    assert get_job(cancelled, actor)["status"] == "cancelled"
