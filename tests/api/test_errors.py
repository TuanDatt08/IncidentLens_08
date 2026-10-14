import pytest

from backend.services.video import VideoService


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
    from backend.services.errors import IncidentIngestionError

    def corrupt(self, path):
        raise IncidentIngestionError("video_invalid", "Invalid MP4", field="video")

    monkeypatch.setattr(VideoService, "probe", corrupt)
    response = await db_client.post(
        "/api/v1/incidents/upload", files={"video": ("clip.mp4", b"corrupt", "video/mp4")}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_VIDEO"


@pytest.mark.asyncio
async def test_http_exception_preserves_status_headers_and_error_envelope():
    import json

    from fastapi import HTTPException, Request

    from api.errors import http_error_handler

    request = Request({"type": "http", "method": "GET", "path": "/missing", "headers": []})
    response = await http_error_handler(request, HTTPException(404, "Resource not found.", headers={"X-Request-ID": "missing-resource"}))
    assert response.status_code == 404
    assert response.headers["x-request-id"] == "missing-resource"
    assert json.loads(response.body) == {"error": {"code": "INVALID_REQUEST", "message": "Resource not found.", "details": None}}


@pytest.mark.asyncio
async def test_rate_limit_error_preserves_retry_after_and_error_envelope():
    import json

    from fastapi import Request

    from api.errors import api_error_handler
    from backend.errors import ApiError

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/auth/login", "headers": []})
    error = ApiError("RATE_LIMITED", "Too many login attempts.", 429, {"retry_after": 42})
    response = await api_error_handler(request, error)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert json.loads(response.body) == {"error": {"code": "RATE_LIMITED", "message": "Too many login attempts.", "details": {"retry_after": 42}}}
