import pytest

from src.services.video import VideoProbeResult, VideoService


@pytest.fixture(autouse=True)
def fake_ffprobe(monkeypatch):
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(10, 30, 320, 240))


@pytest.mark.asyncio
async def test_analyze_returns_queued_job_without_running_vlm(db_client):
    upload = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": ("clip.mp4", b"video", "video/mp4")},
    )
    incident_id = upload.json()["incident_id"]
    response = await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert response.status_code == 202
    assert response.json()["incident_id"] == incident_id
    assert response.json()["status"] == "queued"
    job_id = response.json()["job_id"]
    job = (await db_client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "queued"
    assert job["pass"] is None
    assert job["progress"] == {"done": 0, "total": None}
    assert job["result_uri"] is None
    assert job["error"] is None
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}")).json()["processing_status"] == "PROCESSING"
    assert (await db_client.get(f"/api/v1/incidents/{incident_id}/report")).status_code == 404

    duplicate = await db_client.post(f"/api/v1/incidents/{incident_id}/analyze")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ANALYSIS_ALREADY_RUNNING"
    assert (await db_client.get("/api/v1/jobs/does-not-exist")).json()["error"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_analyze_missing_incident_uses_stable_error(db_client):
    response = await db_client.post("/api/v1/incidents/INC-404/analyze")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"
