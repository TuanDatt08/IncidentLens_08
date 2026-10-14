import pytest
from pydantic import ValidationError


def test_argon2_password_not_trimmed_and_wrong_password_rejected():
    from backend.services.auth import hash_password, verify_password

    password = "  password with spaces  "
    encoded = hash_password(password)
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, password)
    assert not verify_password(encoded, password.strip())
    assert not verify_password(encoded, "a different password")


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_password_length_rejected(password):
    from backend.services.auth import hash_password

    with pytest.raises(ValueError):
        hash_password(password)


def test_six_character_password_hashes_and_verifies():
    from backend.services.auth import hash_password, verify_password

    encoded = hash_password("aB3!xy")
    assert verify_password(encoded, "aB3!xy")
    assert not verify_password(encoded, "aB3!xz")


@pytest.mark.parametrize("length", [5, 6, 128, 129])
def test_new_password_contract_boundaries(length):
    from backend.models.auth_contracts import ChangePassword, CreateUser, ResetPassword

    password = "x" * length
    payloads = [
        (ChangePassword, {"current_password": "existing password", "new_password": password}),
        (CreateUser, {"email": "person@example.com", "display_name": "Person", "roles": ["engineer"], "temporary_password": password}),
        (ResetPassword, {"temporary_password": password}),
    ]
    for model, payload in payloads:
        if 6 <= length <= 128:
            model(**payload)
        else:
            with pytest.raises(ValidationError):
                model(**payload)


@pytest.mark.parametrize("roles", [[], ["admin", "admin"], ["owner"]])
def test_invalid_roles_rejected(roles):
    from backend.models.auth_contracts import CreateUser

    with pytest.raises(ValidationError):
        CreateUser(email="person@example.com", display_name="Person", roles=roles, temporary_password="a long password value")


def test_email_normalized():
    from backend.models.auth_contracts import CreateUser

    user = CreateUser(email="  PERSON@Example.com ", display_name="Person", roles=["admin"], temporary_password="a long password value")
    assert user.email == "person@example.com"


def test_additive_migration_preserves_existing_incident_and_email_uniqueness(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, select
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from backend.models.auth import User
    from backend.models.tables import Incident
    from backend.services.auth import hash_password
    url = f"sqlite:///{(tmp_path / 'additive.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "20260923_rav18")
    engine = create_engine(url)
    with Session(engine) as session:
        session.add(Incident(incident_id="INC-OLD", processing_status="READY", video_uri="old/video.mp4"))
        session.commit()
    command.upgrade(config, "head")
    with Session(engine) as session:
        assert session.scalar(select(Incident)).incident_id == "INC-OLD"
        encoded = hash_password("password for migration")
        session.add(User(email="Person@Example.com", display_name="First", roles=["admin"], password_hash=encoded))
        session.commit()
        session.add(User(email=" PERSON@example.com ", display_name="Second", roles=["engineer"], password_hash=encoded))
        with pytest.raises(IntegrityError):
            session.commit()
    command.downgrade(config, "20260923_rav18")
    with Session(engine) as session:
        assert session.scalar(select(Incident)).video_uri == "old/video.mp4"


def test_bootstrap_cli_uses_hidden_prompt_and_forces_rotation(tmp_path, monkeypatch, capsys):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select

    import backend.cli.users as cli
    from backend.config import get_settings
    from backend.db import get_session_factory, session_scope
    from backend.models.auth import User
    from backend.services.auth import verify_password
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'cli.db').as_posix()}")
    monkeypatch.setenv("DATABASE_CLOUD", "false")
    get_settings.cache_clear()
    get_session_factory.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    secret = "secret password for CLI test"
    monkeypatch.setattr(cli, "getpass", lambda prompt: secret)
    monkeypatch.setattr("sys.argv", ["users", "create-admin", "--email", "Admin@Example.com", "--name", "Administrator"])
    cli.main()
    assert secret not in capsys.readouterr().out
    with session_scope() as session:
        user = session.scalar(select(User))
        assert user.roles == ["admin"] and user.must_change_password
        assert verify_password(user.password_hash, secret)
    monkeypatch.setenv("DATABASE_CLOUD", "false")
    get_settings.cache_clear()
    get_session_factory.cache_clear()


@pytest.mark.parametrize("origins,secure", [("*", True), ("http://localhost:3000", True), ("https://example.com", False)])
def test_production_refuses_unsafe_auth_configuration(origins, secure):
    from backend.config import Settings
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", cors_origins=origins, auth_cookie_secure=secure)
