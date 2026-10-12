"""Migration must preserve reviewed data and reject conflicting reimports."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select

from backend.models import tables_v2  # noqa: F401
from backend.models.tables import Base, Incident


def test_reimport_and_conflict_roll_back(tmp_path):
    from backend.migrate_to_postgres import copy_records
    source = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    Base.metadata.create_all(source)
    Base.metadata.create_all(target)
    record = dict(id=uuid4(), incident_id="INC-MIGRATION", processing_status="completed", video_uri="INC-MIGRATION/input/video.mp4", raw_incident_data={"note": "Tiếng Việt", "values": [1, None]}, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    with source.begin() as conn:
        conn.execute(Incident.__table__.insert(), record)
    first = copy_records(source, target)
    assert first['incidents'] == {"source": 1, "inserted": 1, "existing": 0}
    assert copy_records(source, target)['incidents']['existing'] == 1
    with target.begin() as conn:
        conn.execute(Incident.__table__.update().values(scenario="Engineer changed"))
    with source.begin() as conn:
        conn.execute(Incident.__table__.insert(), {**record, "id": uuid4(), "incident_id": "INC-NEW"})
    with pytest.raises(ValueError, match="conflict"):
        copy_records(source, target)
    with target.connect() as conn:
        assert len(conn.execute(select(Incident.__table__)).all()) == 1


def test_active_jobs_are_not_imported(tmp_path):
    from backend.migrate_to_postgres import copy_records
    from backend.models.tables import Job
    source = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    Base.metadata.create_all(source)
    Base.metadata.create_all(target)
    incident = uuid4()
    with source.begin() as conn:
        conn.execute(Incident.__table__.insert(), dict(id=incident, incident_id="INC-ACTIVE", processing_status="processing", video_uri="video.mp4"))
        conn.execute(Job.__table__.insert(), dict(id=uuid4(), job_id="JOB-ACTIVE", incident_id=incident, status="running"))
    with pytest.raises(ValueError, match="active jobs"):
        copy_records(source, target)
    with target.connect() as conn:
        assert not conn.execute(select(Incident.__table__)).all()


def test_cloud_url_preserves_query_and_requires_ssl():
    from backend.config import Settings
    settings = Settings(_env_file=None, database_cloud=True, database_url="postgres://user:p%40ss@db.example.com/db?application_name=first&application_name=second")
    assert settings.database_url.startswith("postgresql+psycopg2://")
    assert 'p%40ss' in settings.database_url
    assert 'application_name=first&application_name=second' in settings.database_url
    assert 'sslmode=require' in settings.database_url
    assert 'connect_timeout=10' in settings.database_url
    with pytest.raises(ValueError, match="SSL"):
        Settings(_env_file=None, database_cloud=True, database_url="postgresql://user:pass@db.example.com/db?sslmode=disable")
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings(_env_file=None, database_cloud=True, database_url="sqlite:///local.db")
