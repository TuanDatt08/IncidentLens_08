import base64
import hashlib
import hmac
import importlib
import json
import secrets
import time

import pytest

from backend.config import get_settings
from backend.errors import ApiError


def signed_identity(key, *, subject="engineer", roles=None, scopes=None, expires=None):
    payload = {"sub": subject, "roles": roles or ["Engineer"], "recordings": scopes or ["rec"], "exp": expires or int(time.time()) + 300, "iss": "local-v2", "aud": "incidentlens-v2"}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + signature


@pytest.fixture
def identity_key(monkeypatch):
    key = secrets.token_urlsafe(48)
    monkeypatch.setenv("V2_IDENTITY_SECRET", key)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


def test_signed_identity_role_and_scope_are_server_validated(identity_key):
    module = importlib.import_module("backend.services.identity")
    principal = module.authenticate("Bearer " + signed_identity(identity_key))
    module.authorize(principal, "rec", "Engineer")
    with pytest.raises(ApiError) as exc:
        module.authorize(principal, "other", "Engineer")
    assert exc.value.status_code == 404
    with pytest.raises(ApiError) as exc:
        module.authorize(principal, "rec", "Reviewer")
    assert exc.value.status_code == 403


@pytest.mark.parametrize("kind", ["missing", "unsigned", "expired", "tampered"])
def test_missing_invalid_or_expired_identity_is_401(identity_key, kind):
    module = importlib.import_module("backend.services.identity")
    token = signed_identity(identity_key, expires=int(time.time()) - 1 if kind == "expired" else None)
    if kind == "missing":
        token = None
    elif kind == "unsigned":
        token = token.split(".")[0]
    elif kind == "tampered":
        token += "0"
    with pytest.raises(ApiError) as exc:
        module.authenticate("Bearer " + token if token else None)
    assert exc.value.status_code == 401


def test_local_signing_fixture_cannot_enable_production(identity_key, monkeypatch):
    module = importlib.import_module("backend.services.identity")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    with pytest.raises(ApiError) as exc:
        module.authenticate("Bearer " + signed_identity(identity_key))
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_cookie_identity_requires_csrf_header_for_mutations(db_client, identity_key):
    db_client.cookies.set("incidentlens_v2_identity", signed_identity(identity_key))
    response = await db_client.post("/api/v2/uploads", json={"recording_id": "rec", "filename": "video.mp4", "bytes": 2048, "media_type": "video/mp4", "sha256": "0" * 64})
    assert response.status_code == 403
    response = await db_client.post("/api/v2/uploads", json={"recording_id": "rec", "filename": "video.mp4", "bytes": 2048, "media_type": "video/mp4", "sha256": "0" * 64}, headers={"X-Requested-With": "IncidentLens"})
    assert response.status_code == 201
