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
    import time
    from io import BytesIO
    from threading import Event, Thread

    from starlette.datastructures import UploadFile

    import backend.services.jobs as jobs
    from backend.models.contracts import LocalizationResult
    from backend.worker import run_once

    monkeypatch.setattr(jobs, "LEASE_SECONDS", 0.15)
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))

    def frame(self, video_path, at_s, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return destination

    monkeypatch.setattr(VideoService, "extract_frame", frame)
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"))["incident_id"]
    job_id = create_job(incident_id)["job_id"]
    started = Event()
    release = Event()

    class SlowVLM:
        def pass1(self, video_path, sampled_frames, metadata):
            started.set()
            release.wait(2)
            return LocalizationResult(incident_detected=False)

        def pass2(self, prepared):
            raise AssertionError("Pass 2 must not run")

    thread = Thread(target=lambda: run_once(vlm=SlowVLM()))
    thread.start()
    try:
        assert started.wait(2)
        time.sleep(0.35)
        assert claim_job() is None
        assert get_job(job_id)["status"] == "running"
    finally:
        release.set()
        thread.join(2)
    assert not thread.is_alive()


@pytest.mark.asyncio
async def test_claim_is_single_and_failed_job_is_terminal(db_client, monkeypatch):
    from io import BytesIO

    from starlette.datastructures import UploadFile

    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"))["incident_id"]
    job_id = create_job(incident_id)["job_id"]
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
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"))["incident_id"]
    job_id = create_job(incident_id)["job_id"]
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
    incident_id = create_incident(UploadFile(file=BytesIO(b"video"), filename="clip.mp4"))["incident_id"]
    job_id = create_job(incident_id)["job_id"]
    for attempt in range(1, 4):
        claimed = claim_job()
        assert claimed.job_id == job_id
        assert claimed.attempt == attempt
        with session_scope() as session:
            job = session.scalar(select(Job).where(Job.job_id == job_id))
            job.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    assert claim_job() is None
    assert get_job(job_id)["status"] == "failed"
