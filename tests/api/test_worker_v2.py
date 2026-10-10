import importlib

import pytest

from backend.db import session_scope
from backend.models.tables_v2 import RecordingV2
from backend.services.identity import Principal
from backend.services.jobs_v2 import create_job, get_job
from backend.services.video import VideoService


@pytest.mark.asyncio
async def test_v2_worker_discovers_multiple_candidates_and_resumes_without_reanalysis(db_client, tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_BATCH_FRAMES", "32")
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
    assert len(calls[0].frames) == 24  # Merged flags at 2/3s, window clipped to [0,6).
    assert len(calls[1].frames) == 32
    assert [frame.time_start_s for frame in calls[1].frames] == [27 + i / 4 for i in range(32)]
    assert calls[0].flags[0]["time_s"] == 2.0
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


@pytest.mark.asyncio
async def test_worker_uses_local_even_when_job_requests_external(db_client, tmp_path, monkeypatch):
    monkeypatch.setenv("QWEN_BATCH_FRAMES", "32")
    from backend.config import get_settings
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.services.vlm_provider import ProviderResult
    root = tmp_path / "storage"
    root.mkdir(exist_ok=True)
    (root / "video.mp4").write_bytes(b"fixture")
    (root / "log.csv").write_text("clock,brake\n0,0\n10,1\n11,0\n20,0\n")
    monkeypatch.setenv("INCIDENT_STORAGE_DIR", str(root))
    get_settings.cache_clear()
    with session_scope() as session:
        session.add(RecordingV2(recording_id="local", duration_s=30.0, video_uri="video.mp4", metadata_json={"duration": 30.0, "fps": 10.0, "telemetry_uri": "log.csv", "log_config": {"timestamp_column": "clock", "time_reference": "recording_relative"}, "anchors": [{"log_s": 0.0, "video_s": 0.0, "source": "fixture"}, {"log_s": 20.0, "video_s": 20.0, "source": "fixture"}]}))
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"local"}))
    job = create_job("local", "external_api", "local-only", actor)
    def output(self, source, start, *args):
        destination = args[-1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(str(start).encode())
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", output)
    monkeypatch.setattr(VideoService, "extract_clip", output)
    module = importlib.import_module("backend.worker_v2")
    calls = []
    class LocalProvider:
        def analyze(self, context):
            calls.append(context)
            assert len(context.frames) == 32 and context.candidate_window == (5.0, 10.0, 13.0)
            analysis = AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Checked supplied frames only", "timeline": [], "factors": [], "unknowns": ["No full-video coverage"], "review_status": "DRAFT"})
            return ProviderResult(analysis, {"provider": "local"}, {"attempts": 1})
    monkeypatch.setattr(module, "create_local_provider", lambda settings: LocalProvider())
    module.run_once(job_id=job["job_id"])
    assert get_job(job["job_id"], actor)["status"] == "succeeded"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_resume_changed_batch_size_reanalyzes_exact_frames(db_client, tmp_path, monkeypatch):
    from backend.config import get_settings
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.services.vlm_provider import ProviderResult
    root = tmp_path / "storage"
    root.mkdir(exist_ok=True)
    (root / "video.mp4").write_bytes(b"fixture")
    (root / "log.csv").write_text("clock,brake\n0,0\n10,1\n11,0\n20,0\n")
    monkeypatch.setenv("INCIDENT_STORAGE_DIR", str(root))
    monkeypatch.setenv("QWEN_BATCH_FRAMES", "8")
    get_settings.cache_clear()
    with session_scope() as session:
        session.add(RecordingV2(recording_id="batch", duration_s=30.0, video_uri="video.mp4", metadata_json={"duration": 30.0, "fps": 10.0, "telemetry_uri": "log.csv", "log_config": {"timestamp_column": "clock", "time_reference": "recording_relative"}, "anchors": [{"log_s": 0.0, "video_s": 0.0, "source": "fixture"}, {"log_s": 20.0, "video_s": 20.0, "source": "fixture"}]}))
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"batch"}))
    job = create_job("batch", "self_hosted", "batch-resume", actor)
    def output(self, source, start, *args):
        destination = args[-1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(str(start).encode())
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", output)
    monkeypatch.setattr(VideoService, "extract_clip", output)
    module = importlib.import_module("backend.worker_v2")
    calls = []
    class Provider:
        def analyze(self, context):
            calls.append(context)
            if len(calls) == 2:
                raise RuntimeError("interrupted batch")
            analysis = AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Checked supplied frames", "timeline": [], "factors": [], "unknowns": ["Limited coverage"], "review_status": "DRAFT"})
            return ProviderResult(analysis, {}, {"attempts": 1})
    provider = Provider()
    module.run_once(provider=provider, job_id=job["job_id"])
    assert get_job(job["job_id"], actor)["status"] == "failed"
    monkeypatch.setenv("QWEN_BATCH_FRAMES", "32")
    get_settings.cache_clear()
    module.resume_failed(job["job_id"], actor)
    module.run_once(provider=provider, job_id=job["job_id"])
    assert get_job(job["job_id"], actor)["status"] == "succeeded"
    assert [len(context.frames) for context in calls] == [8, 8, 32]
    assert calls[-1].frames[0].time_start_s == 5.0 and calls[-1].frames[-1].time_start_s == 12.75
