"""Upload edge cases against the public RAV18 v1.1 API and SQL store."""

import pytest

from backend.config import get_settings
from backend.services.errors import IncidentIngestionError
from backend.services.video import VideoProbeResult, VideoService


@pytest.fixture(autouse=True)
def fake_ffprobe(monkeypatch):
    monkeypatch.setattr(VideoService, "probe", lambda self, path: VideoProbeResult(20, 30, 1280, 720))


def video_file(content=b"video-bytes"):
    return ("incident.mp4", content, "video/mp4")


@pytest.mark.asyncio
async def test_upload_mp4_and_canonical_csv_returns_incident_id(db_client):
    response = await db_client.post(
        "/api/v1/incidents/upload",
        files={
            "video": video_file(),
            "log": ("telemetry.csv", b"sec_from_incident,sim_time_s\n-1,9\n0,10\n1,11\n", "text/csv"),
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["incident_id"].startswith("INC-")
    assert payload["processing_status"] == "READY"
    assert "package_id" not in payload
    detail = (await db_client.get(f"/api/v1/incidents/{payload['incident_id']}")).json()
    assert detail["telemetry_metadata"]["time_column"] == "sec_from_incident"
    assert detail["telemetry_metadata"]["start_s"] == -1
    assert detail["telemetry_metadata"]["end_s"] == 1
    assert detail["telemetry_uri"].startswith(payload["incident_id"] + "/")


@pytest.mark.asyncio
async def test_upload_without_log_leaves_telemetry_absent(db_client):
    response = await db_client.post("/api/v1/incidents/upload", files={"video": video_file()})
    assert response.status_code == 201
    detail = (await db_client.get(f"/api/v1/incidents/{response.json()['incident_id']}")).json()
    assert detail["telemetry_uri"] is None
    assert detail["telemetry_metadata"] is None


@pytest.mark.asyncio
async def test_missing_or_unsupported_video_uses_error_envelope(db_client):
    missing = await db_client.post("/api/v1/incidents/upload")
    unsupported = await db_client.post(
        "/api/v1/incidents/upload", files={"video": ("incident.mov", b"video", "video/quicktime")}
    )
    for response in (missing, unsupported):
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_VIDEO"
    assert (await db_client.get("/api/v1/incidents")).json()["total"] == 0


@pytest.mark.asyncio
async def test_corrupt_video_is_rejected_without_persisting_incident(db_client, monkeypatch):
    def reject(self, path):
        raise IncidentIngestionError("video_invalid", "The video is corrupt.", field="video")

    monkeypatch.setattr(VideoService, "probe", reject)
    response = await db_client.post("/api/v1/incidents/upload", files={"video": video_file(b"invalid")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_VIDEO"
    assert (await db_client.get("/api/v1/incidents")).json()["total"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("csv", [b"speed\n12\n", b"sec_from_incident,speed\n0,12\n0,13\n"])
async def test_noncanonical_or_nonmonotonic_log_is_rejected(db_client, csv):
    response = await db_client.post(
        "/api/v1/incidents/upload",
        files={"video": video_file(), "log": ("telemetry.csv", csv, "text/csv")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_LOG"
    assert (await db_client.get("/api/v1/incidents")).json()["total"] == 0


@pytest.mark.asyncio
async def test_video_size_limit_returns_413(db_client, monkeypatch):
    monkeypatch.setenv("MAX_VIDEO_SIZE_MB", "1")
    get_settings.cache_clear()
    response = await db_client.post("/api/v1/incidents/upload", files={"video": video_file(b"x" * (1024 * 1024 + 1))})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "VIDEO_TOO_LARGE"
    assert (await db_client.get("/api/v1/incidents")).json()["total"] == 0
