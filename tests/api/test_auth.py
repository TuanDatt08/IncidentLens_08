from datetime import timedelta

import pytest
from sqlalchemy import select

PASSWORD = "correct password for tests"
ORIGIN = "http://localhost:3000"


def seed_user(email="engineer@example.com", roles=None, temporary=False):
    from backend.db import session_scope
    from backend.models.auth import User
    from backend.services.auth import hash_password
    with session_scope() as session:
        user = User(email=email, display_name="Test User", roles=roles or ["engineer"],
                    password_hash=hash_password(PASSWORD), must_change_password=temporary)
        session.add(user)
        session.flush()
        return user.id


async def login(client, email="engineer@example.com", password=PASSWORD):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password}, headers={"Origin": ORIGIN})
    if response.status_code == 200:
        client.headers.update({"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]})
    return response


@pytest.mark.asyncio
async def test_login_me_logout_cookie_and_no_secret_json(auth_client):
    seed_user()
    response = await login(auth_client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    assert "password_hash" not in response.text and "token_hash" not in response.text
    assert response.headers["cache-control"] == "no-store"
    from backend.db import session_scope
    from backend.models.auth import UserSession
    with session_scope() as session:
        row = session.scalar(select(UserSession))
        assert row.token_hash not in response.text
        assert row.token_hash != auth_client.cookies.get("incidentlens_session")
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 200
    assert (await auth_client.post("/api/v1/auth/logout")).status_code == 204
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_origin_and_csrf_are_required(auth_client):
    seed_user()
    assert (await auth_client.post("/api/v1/auth/login", json={"email": "engineer@example.com", "password": PASSWORD})).status_code == 403
    await login(auth_client)
    auth_client.headers.pop("X-CSRF-Token")
    assert (await auth_client.post("/api/v1/auth/logout")).json()["error"]["code"] == "CSRF_FAILED"
    auth_client.headers["Origin"] = "http://localhost:3000.evil.example"
    assert (await auth_client.post("/api/v1/auth/logout")).status_code == 403


@pytest.mark.asyncio
async def test_forced_password_change_revokes_all_sessions(auth_client):
    seed_user(temporary=True)
    await login(auth_client)
    assert (await auth_client.get("/api/v1/incidents")).json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    response = await auth_client.post("/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": "new correct password value"})
    assert response.status_code == 204
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 401
    assert (await login(auth_client, password="new correct password value")).json()["user"]["must_change_password"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["expires_at", "last_seen_at"])
async def test_expiry_is_persistently_revoked(auth_client, field):
    from backend.db import session_scope
    from backend.models.auth import UserSession
    from backend.services.auth import utc_now
    seed_user()
    await login(auth_client)
    with session_scope() as session:
        row = session.scalar(select(UserSession))
        setattr(row, field, utc_now() - timedelta(hours=9))
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 401
    with session_scope() as session:
        assert session.scalar(select(UserSession)).revoked_at is not None


@pytest.mark.asyncio
async def test_shared_login_failure_limit_and_uniform_credentials(auth_client):
    seed_user()
    for _ in range(5):
        response = await login(auth_client, password="wrong password")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    response = await login(auth_client)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    from httpx import ASGITransport, AsyncClient

    from api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second:
        assert (await login(second)).status_code == 429


@pytest.mark.asyncio
async def test_unknown_account_also_limited(auth_client):
    for _ in range(5):
        assert (await login(auth_client, "missing@example.com")).status_code == 401
    assert (await login(auth_client, "missing@example.com")).status_code == 429


@pytest.mark.asyncio
async def test_rate_window_cleanup_and_absolute_timeout_use_controlled_clock(auth_client, monkeypatch):
    import backend.services.auth as auth
    from backend.db import session_scope
    from backend.models.auth import LoginRateLimit, UserSession
    seed_user()
    clock = auth.utc_now()
    monkeypatch.setattr(auth, "utc_now", lambda: clock)
    for _ in range(5):
        assert (await login(auth_client, password="wrong password")).status_code == 401
    assert (await login(auth_client)).status_code == 429
    clock += timedelta(minutes=16)
    assert (await login(auth_client)).status_code == 200
    with session_scope() as session:
        assert all(row.failures == 0 for row in session.scalars(select(LoginRateLimit)))
        row = session.scalar(select(UserSession))
        row.last_seen_at = clock + timedelta(hours=8)
    clock += timedelta(hours=8)
    assert (await auth_client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_ip_budget_and_no_secret_audit_or_logs(auth_client, monkeypatch, caplog):
    from backend.config import get_settings
    from backend.db import session_scope
    from backend.models.auth import AuthEvent
    monkeypatch.setenv("AUTH_IP_FAILURE_LIMIT", "3")
    get_settings.cache_clear()
    for index in range(3):
        assert (await login(auth_client, f"unknown{index}@example.com", "secret password sent in test")).status_code == 401
    assert (await login(auth_client, "another@example.com")).status_code == 429
    with session_scope() as session:
        events = session.scalars(select(AuthEvent)).all()
        assert len(events) == 3 and all(event.outcome == "failure" and event.event_metadata == {} for event in events)
    assert "secret password sent in test" not in caplog.text


@pytest.mark.asyncio
async def test_new_session_tokens_and_password_rehash(auth_client):
    from argon2 import PasswordHasher

    from backend.db import session_scope
    from backend.models.auth import User, UserSession
    from backend.services.auth import password_hasher
    user_id = seed_user()
    with session_scope() as session:
        session.get(User, user_id).password_hash = PasswordHasher(time_cost=1, memory_cost=8192).hash(PASSWORD)
    await login(auth_client)
    token = auth_client.cookies.get("incidentlens_session")
    await login(auth_client)
    assert auth_client.cookies.get("incidentlens_session") != token
    with session_scope() as session:
        assert not password_hasher.check_needs_rehash(session.get(User, user_id).password_hash)
        assert len(session.scalars(select(UserSession)).all()) == 2


@pytest.mark.asyncio
async def test_database_failures_never_log_session_secrets(auth_client, monkeypatch, caplog):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    import backend.services.auth as auth
    from api.main import app
    from backend.db import session_scope
    seed_user()
    with session_scope() as session:
        session.execute(text("CREATE TRIGGER fail_sessions BEFORE INSERT ON user_sessions BEGIN SELECT RAISE(ABORT, 'deliberate failure'); END"))
    raw_token = "session-token-fixture-not-a-real-secret"
    raw_csrf = "csrf-token-fixture-not-a-real-secret"
    values = iter([raw_token, raw_csrf])
    monkeypatch.setattr(auth.secrets, "token_urlsafe", lambda size: next(values))
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await login(client)
    assert response.status_code == 500
    assert raw_token not in caplog.text
    assert raw_csrf not in caplog.text
    assert auth.token_hash(raw_token) not in caplog.text
    assert response.headers.get("cache-control") == "no-store"
