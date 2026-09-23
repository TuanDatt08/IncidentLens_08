from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql

from src.models.tables import Incident, Job


def test_initial_migration_creates_six_tables_and_rolls_back(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) - {"alembic_version"} == {
        "incidents",
        "jobs",
        "evidences",
        "analysis_reports",
        "report_versions",
        "audit_events",
    }
    assert str(Incident.__table__.c.source.type.compile(dialect=postgresql.dialect())) == "JSONB"

    with Session(engine) as session:
        incident = Incident(incident_id="INC-001", processing_status="READY", video_uri="incidents/INC-001/source/video.mp4")
        session.add(incident)
        session.commit()
        session.add_all([Job(job_id=f"JOB-{uuid4().hex}", incident_id=incident.id, status="queued") for _ in range(2)])
        with pytest.raises(IntegrityError):
            session.commit()

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
