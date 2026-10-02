import hashlib
import secrets
import subprocess

import pytest
from test_authorization import signed_identity

from backend.config import get_settings


@pytest.mark.asyncio
async def test_upload_resume_corrupt_part_and_complete_replay(db_client, monkeypatch, tmp_path):
    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("V2_IDENTITY_SECRET", key)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    source = tmp_path / "video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=blue:s=64x64:r=10:d=2", "-c:v", "libx264", str(source)], check=True, capture_output=True, timeout=30)
    data = source.read_bytes()
    engineer = {"Authorization": "Bearer " + signed_identity(key)}
    request = {"recording_id": "rec", "filename": "video.mp4", "bytes": len(data), "media_type": "video/mp4", "sha256": hashlib.sha256(data).hexdigest(), "part_size": 1024}
    initial = await db_client.post("/api/v2/uploads", json=request, headers=engineer)
    assert initial.status_code == 201
    upload_id = initial.json()["upload_id"]
    url = "/api/v2/uploads/" + upload_id
    assert (await db_client.put(url + "/parts/1", content=data[:1024], headers={**engineer, "X-Part-SHA256": "0" * 64})).status_code == 422
    for index, start in enumerate(range(0, len(data), 1024), 1):
        part = data[start:start + 1024]
        response = await db_client.put(url + f"/parts/{index}", content=part, headers={**engineer, "X-Part-SHA256": hashlib.sha256(part).hexdigest()})
        assert response.status_code == 200
    resumed = await db_client.get(url, headers=engineer)
    assert len(resumed.json()["parts"]) == initial.json()["part_count"]
    completed = await db_client.post(url + "/complete", headers=engineer)
    assert completed.status_code == 200
    assert completed.json()["recording_id"] == "rec"
    assert (await db_client.post(url + "/complete", headers=engineer)).json() == completed.json()
    other = {"Authorization": "Bearer " + signed_identity(key, scopes=["other"])}
    assert (await db_client.get(url, headers=other)).status_code == 404


@pytest.mark.asyncio
async def test_upload_size_and_expiry_fail_closed(db_client, monkeypatch):
    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("V2_IDENTITY_SECRET", key)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    headers = {"Authorization": "Bearer " + signed_identity(key)}
    request = {"recording_id": "rec", "filename": "video.mp4", "bytes": 2**50, "media_type": "video/mp4", "sha256": "0" * 64}
    assert (await db_client.post("/api/v2/uploads", json=request, headers=headers)).status_code == 413
    request["bytes"] = 2048
    response = await db_client.post("/api/v2/uploads", json=request, headers=headers)
    assert response.status_code == 201
    import importlib
    from datetime import UTC, datetime, timedelta

    from backend.db import session_scope
    module = importlib.import_module("backend.models.tables_v2")
    with session_scope() as session:
        upload = session.get(module.UploadV2, response.json()["upload_id"])
        upload.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await db_client.get("/api/v2/uploads/" + response.json()["upload_id"], headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_streaming_64_mib_parts_keep_python_memory_bounded(db_client, monkeypatch):
    import tracemalloc

    from backend.models.contracts_v2 import UploadRequestV2
    from backend.services.identity import Principal
    from backend.services.uploads_v2 import init_upload, resume_upload, write_part
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    actor = Principal("engineer", frozenset({"Engineer"}), frozenset({"rec"}))
    chunk = b"x" * 65536
    digest = hashlib.sha256()
    for _ in range(128):
        digest.update(chunk)
    upload = init_upload(UploadRequestV2(recording_id="rec", filename="fixture.mp4", media_type="video/mp4", bytes=64 * 1024**2, sha256="0" * 64, part_size=8 * 1024**2), actor)
    async def chunks():
        for _ in range(128):
            yield chunk
    tracemalloc.start()
    try:
        for part in range(1, 9):
            await write_part(upload["upload_id"], part, digest.hexdigest(), chunks(), actor)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024**2
    assert len(resume_upload(upload["upload_id"], actor)["parts"]) == 8
    # Synthetic bytes test streaming only; real MP4 integrity is covered separately.
