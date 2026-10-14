"""Online auth migration and cross-connection locking on an isolated PG test DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def postgres_auth_database():
    url = os.environ.get("AUTH_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set AUTH_TEST_POSTGRES_URL to a dedicated disposable auth_test database")
    if make_url(url).database != "auth_test":
        pytest.fail("Refusing auth smoke on any database not named auth_test")
    from alembic import command
    from alembic.config import Config
    from backend.config import get_settings
    from backend.db import get_session_factory
    from backend.models.tables import Incident
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    get_session_factory.cache_clear()
    engine = create_engine(url)
    config = Config("alembic.ini")
    command.upgrade(config, "20260923_rav18")
    with Session(engine) as session:
        session.add(Incident(incident_id="INC-BEFORE-AUTH", processing_status="READY", video_uri="old/source.mp4"))
        session.commit()
    command.upgrade(config, "head")
    yield engine
    get_session_factory.cache_clear()
    get_settings.cache_clear()
    engine.dispose()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous


def test_postgres_additive_migration_preserves_incident(postgres_auth_database):
    from backend.models.tables import Incident
    with Session(postgres_auth_database) as session:
        assert session.scalar(select(Incident)).video_uri == "old/source.mp4"


def test_two_admins_cannot_simultaneously_remove_last_admin(postgres_auth_database):
    from backend.db import session_scope
    from backend.errors import ApiError
    from backend.models.auth import User
    from backend.models.auth_contracts import UpdateUser
    from backend.services.access import Principal
    from backend.services.auth import hash_password
    from backend.services.users import update_user
    encoded = hash_password("postgres test password value")
    with session_scope() as session:
        users = [User(email=f"admin{index}@example.com", display_name="Administrator", roles=["admin"], password_hash=encoded, must_change_password=False) for index in [1, 2]]
        session.add_all(users)
        session.flush()
        ids = [user.id for user in users]
    barrier = Barrier(2)
    def deactivate(user_id):
        barrier.wait(timeout=10)
        try:
            update_user(user_id, UpdateUser(is_active=False), principal=Principal(user_id, frozenset({"admin"}), False))
            return "success"
        except ApiError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(deactivate, ids))
    assert sorted(results) == ["LAST_ADMIN_REQUIRED", "success"]
    with session_scope() as session:
        assert sum(user.is_active and "admin" in user.roles for user in session.scalars(select(User))) == 1


def test_login_budget_shared_across_concurrent_connections(postgres_auth_database):
    from backend.db import session_scope
    from backend.errors import ApiError
    from backend.models.auth import LoginRateLimit
    from backend.services.auth import login_user
    def attempt(index):
        try:
            login_user("missing@example.com", "incorrect password", "shared-ip")
        except ApiError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(8)))
    assert outcomes.count("INVALID_CREDENTIALS") == 5
    assert outcomes.count("RATE_LIMITED") == 3
    with session_scope() as session:
        assert all(row.failures == 5 for row in session.scalars(select(LoginRateLimit)))


def test_logout_and_password_reset_do_not_deadlock(postgres_auth_database):
    from threading import Event, Thread, current_thread
    from sqlalchemy import event
    from backend.db import get_session_factory, session_scope
    from backend.models.auth import User
    from backend.services.access import Principal
    from backend.services.auth import hash_password, login_user, logout, resolve_session
    from backend.services.users import reset_password
    with session_scope() as session:
        user = User(email="logout-target@example.com", display_name="Target", roles=["engineer"], password_hash=hash_password("logout concurrency password"), must_change_password=False)
        session.add(user)
        session.flush()
        user_id = user.id
        admin = next(row for row in session.scalars(select(User)) if row.is_active and "admin" in row.roles)
        principal = Principal(admin.id, frozenset({"admin"}), False)
    _, token, _ = login_user("logout-target@example.com", "logout concurrency password", "logout-ip")
    context = resolve_session(token)
    engine = get_session_factory().kw["bind"]
    logout_updated, reset_locked = Event(), Event()
    def coordinate(connection, cursor, statement, parameters, context, executemany):
        if current_thread().name == "auth-logout" and statement.startswith("UPDATE user_sessions"):
            logout_updated.set()
            reset_locked.wait(0.5)
        if current_thread().name == "auth-reset" and statement.startswith("SELECT users.") and "FOR UPDATE" in statement:
            reset_locked.set()
    errors = []
    def run(operation):
        try:
            operation()
        except Exception as error:
            errors.append(type(error).__name__)
    event.listen(engine, "after_cursor_execute", coordinate)
    first = Thread(name="auth-logout", target=lambda: run(lambda: logout(context)))
    second = Thread(name="auth-reset", target=lambda: run(lambda: reset_password(user_id, "replacement concurrency password", principal=principal)))
    try:
        first.start()
        assert logout_updated.wait(5)
        second.start()
        first.join(10)
        second.join(10)
        assert not first.is_alive() and not second.is_alive()
        assert errors == []
    finally:
        event.remove(engine, "after_cursor_execute", coordinate)
