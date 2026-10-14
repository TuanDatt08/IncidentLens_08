from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.main import app


@pytest_asyncio.fixture
async def auth_client(tmp_path, monkeypatch):
    """Real HTTP routes against an Alembic-created isolated SQL database."""
    from alembic import command
    from alembic.config import Config

    from backend.config import get_settings
    from backend.db import get_session_factory

    url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_CLOUD", "false")
    monkeypatch.setenv("INCIDENT_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    get_settings.cache_clear()
    get_session_factory.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    get_session_factory.cache_clear()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_client(auth_client):
    """Existing business tests authenticate real DB accounts, never bypass auth."""
    from backend.services.access import Principal
    from tests.api.test_auth import login, seed_user
    user_id = seed_user()
    seed_user("reviewer@example.com", ["reviewer"])
    await login(auth_client)
    auth_client.principal = Principal(user_id, frozenset({"engineer"}), False)
    yield auth_client


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
