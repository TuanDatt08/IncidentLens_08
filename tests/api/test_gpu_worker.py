from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from backend.gpu_worker import next_local_job
from backend.services.incidents import create_incident
from backend.services.jobs import create_job, get_job
from backend.services.video import VideoProbeResult, VideoService


@pytest.mark.asyncio
async def test_missing_media_keeps_job_queued_without_consuming_attempt(db_client, monkeypatch):
    monkeypatch.setattr(VideoService, 'probe', lambda self, path: VideoProbeResult(10, 30, 320, 240))
    incident = create_incident(UploadFile(file=BytesIO(b'video'), filename='clip.mp4'), principal=db_client.principal)
    job = create_job(incident['incident_id'], principal=db_client.principal)
    assert next_local_job() == job['job_id']
    from pathlib import Path

    from backend.config import get_settings
    video = Path(get_settings().incident_storage_dir) / incident['incident_id'] / 'source/video.mp4'
    video.unlink()
    assert next_local_job() is None
    assert get_job(job['job_id'])['status'] == 'queued'
