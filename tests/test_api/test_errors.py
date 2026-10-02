import pytest

from src.services.video import VideoService


@pytest.mark.asyncio
async def test_missing_video_and_missing_incident_use_error_envelope(db_client):
    response = await db_client.post("/api/v1/incidents/upload", files={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_VIDEO"
    assert "message" in response.json()["error"]
    assert "details" in response.json()["error"]

    response = await db_client.get("/api/v1/incidents/INC-404")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_bad_video_container_is_rejected(db_client, monkeypatch):
    from src.services.errors import IncidentIngestionError

    def corrupt(self, path):
        raise IncidentIngestionError("video_invalid", "Invalid MP4", field="video")

    monkeypatch.setattr(VideoService, "probe", corrupt)
    response = await db_client.post(
        "/api/v1/incidents/upload", files={"video": ("clip.mp4", b"corrupt", "video/mp4")}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_VIDEO"
