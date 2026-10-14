from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.db import session_scope
from backend.errors import ApiError
from backend.models.tables import Job
from backend.services.incidents import create_incident
from backend.services.jobs import claim_job, create_job, fail_job, get_job, heartbeat
from backend.services.video import VideoProbeResult, VideoService


@pytest.mark.asyncio
async def test_slow_vlm_keeps_job_lease_alive(db_client, monkeypatch):
    from io import BytesIO
    from threading import Event, Thread

    from starlette.datastructures import UploadFile

    import backend.services.jobs as jobs
    import backend.worker as worker
    from backend.models.contracts import LocalizationResult
    from backend.worker import run_once

    monkeypatch.setattr(jobs, "LEASE_SECONDS", 0.15)
    # Advance job time only after a real renewal is observed; Windows scheduling
    # cannot reliably guarantee a database heartbeat every 50 milliseconds.
    current = [datetime.now(UTC)]
    class Clock:
        @staticmethod
        def now(tz):
            return current[0]
    monkeypatch.setattr(jobs, "datetime", Clock)
    renewed = Event()
    actual_heartbeat = worker.heartbeat
    def observed_heartbeat(*args, **kwargs):
        actual_heartbeat(*args, **kwargs)
        renewed.set()
    monkeypatch.setattr(worker, "heartbeat", observed_heartbeat)
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))

    def frame(self, video_path, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", frame)
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"), principal=db_client.principal)["incident_id"]
    job_id = create_job(incident_id, principal=db_client.principal)["job_id"]
    started = Event()
    release = Event()

    class SlowVLM:
        def pass1(self, video_path, sampled_frames, metadata):
            started.set()
            release.wait(10)
            return LocalizationResult(incident_detected=False)

        def pass2(self, prepared):
            raise AssertionError("Pass 2 must not run")

    thread = Thread(target=lambda: run_once(vlm=SlowVLM()))
    thread.start()
    try:
        assert started.wait(5)
        for _ in range(4):
            renewed.clear()
            current[0] += timedelta(seconds=0.1)
            assert renewed.wait(3), "No real heartbeat observed while VLM is blocked"
            assert claim_job() is None
        assert get_job(job_id)["status"] == "running"
    finally:
        release.set()
        thread.join(5)
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_claim_is_single_and_failed_job_is_terminal(db_client, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"), principal=db_client.principal)["incident_id"]
    job_id = create_job(incident_id, principal=db_client.principal)["job_id"]
    first = claim_job()
    assert first.job_id == job_id
    assert claim_job() is None
    heartbeat(job_id, pass_number=1, done=1, total=None)
    assert get_job(job_id)["pass"] == 1
    fail_job(job_id, "VLM_FAILED", "Provider timed out")
    assert get_job(job_id)["status"] == "failed"
    assert get_job(job_id)["error"]["code"] == "VLM_FAILED"
    assert claim_job() is None


@pytest.mark.asyncio
async def test_reclaimed_job_rejects_stale_worker_updates(db_client, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"), principal=db_client.principal)["incident_id"]
    job_id = create_job(incident_id, principal=db_client.principal)["job_id"]
    first = claim_job()
    with session_scope() as session:
        job = session.scalar(select(Job).where(Job.job_id == job_id))
        job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    second = claim_job()
    assert second.attempt == first.attempt + 1
    with pytest.raises(ApiError) as exc:
        heartbeat(job_id, pass_number=2, done=1, total=2, expected_attempt=first.attempt)
    assert exc.value.code == "JOB_LEASE_LOST"
    with pytest.raises(ApiError):
        fail_job(job_id, "VLM_FAILED", "Old worker", expected_attempt=first.attempt)
    assert get_job(job_id)["status"] == "running"
    assert claim_job() is None


@pytest.mark.asyncio
async def test_expired_lease_retries_then_fails_after_limit(db_client, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"), principal=db_client.principal)["incident_id"]
    job_id = create_job(incident_id, principal=db_client.principal)["job_id"]
    for attempt in range(1, 4):
        claimed = claim_job()
        assert claimed.job_id == job_id
        assert claimed.attempt == attempt
        with session_scope() as session:
            job = session.scalar(select(Job).where(Job.job_id == job_id))
            job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    assert claim_job() is None
    assert get_job(job_id)["status"] == "failed"


@pytest.mark.asyncio
async def test_v1_default_worker_uses_local_pipeline_without_openai(db_client, monkeypatch):
    monkeypatch.setenv('QWEN_RUNTIME', 'llama_cpp')
    from io import BytesIO

    from starlette.datastructures import UploadFile

    import backend.worker as worker
    from backend.config import get_settings
    from backend.models.analysis_v2 import AIIncidentAnalysisV2
    from backend.services.vlm_provider import ProviderResult
    monkeypatch.setenv("QWEN_V1_LOG_OFFSET_S", "0")
    get_settings.cache_clear()
    monkeypatch.setattr("backend.services.vlm.get_llm", lambda: pytest.fail("external VLM used"))
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(30, 30, 320, 240))
    def output(self, source, at_s, *args):
        destination = args[-1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(str(at_s).encode())
        return destination
    monkeypatch.setattr(VideoService, "extract_frame", output)
    monkeypatch.setattr(VideoService, "extract_clip", output)
    incident = create_incident(UploadFile(file=BytesIO(b"video"), filename="video.mp4"), UploadFile(file=BytesIO(b"sec_from_incident,brake\n0,0\n10,1\n11,0\n20,0\n"), filename="log.csv"), principal=db_client.principal)
    job = create_job(incident["incident_id"], principal=db_client.principal)
    calls = []
    class Local:
        def analyze(self, context):
            calls.append(context)
            return ProviderResult(AIIncidentAnalysisV2.model_validate({"schema_version": "2.0", "incident_detected": False, "event_type": "UNKNOWN", "time_basis": "video_seconds", "window": None, "summary": "Supplied frames only", "timeline": [], "factors": [], "unknowns": ["Not full video coverage"], "review_status": "DRAFT"}), {}, {})
    monkeypatch.setattr(worker, "create_local_provider", lambda settings: Local())
    legacy_settings = get_settings().model_copy(update={'qwen_candidate_min_acceleration': None, 'qwen_inference_frame_limit': None})
    monkeypatch.setattr(worker, 'get_settings', lambda: legacy_settings)
    worker.run_once(job_id=job["job_id"])
    assert get_job(job["job_id"])["status"] == "succeeded"
    assert sum(len(context.frames) for context in calls) == 32
    assert all(context.candidate_window == (5.0, 10.0, 13.0) for context in calls)
