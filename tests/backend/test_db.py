from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.tables import Incident, Job


def test_initial_migration_creates_six_tables_and_rolls_back(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "20260923_rav18")
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


def test_migration_uses_database_url_environment_in_container(tmp_path, monkeypatch):
    target = f"sqlite:///{(tmp_path / 'target.db').as_posix()}"
    wrong = f"sqlite:///{(tmp_path / 'wrong.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", target)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", wrong)
    command.upgrade(config, "head")
    assert "incidents" in inspect(create_engine(target)).get_table_names()
    assert "incidents" not in inspect(create_engine(wrong)).get_table_names()


def test_v2_upgrade_preserves_v1_evidence_and_snapshot_and_sqlite_backup(tmp_path):
    import sqlite3

    from backend.models.tables import AnalysisReport, Evidence, ReportVersion
    path = tmp_path / "preserved.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path.as_posix()}")
    command.upgrade(config, "20260923_rav18")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with Session(engine) as session:
        incident = Incident(incident_id="preserved", processing_status="READY", video_uri="fixture.mp4")
        session.add(incident)
        session.flush()
        report = AnalysisReport(incident_id=incident.id, review_status="APPROVED")
        session.add(report)
        session.flush()
        session.add(Evidence(incident_id=incident.id, evidence_id="preserved-evidence", kind="VIDEO", uri="immutable.mp4", sha256="a" * 64, time_start_s=1.0, time_end_s=2.0))
        session.add(ReportVersion(report_id=report.id, version=1, content={"summary": "immutable old report"}))
        session.commit()
    command.upgrade(config, "head")
    from sqlalchemy import select
    with Session(engine) as session:
        assert session.scalar(select(Evidence)).sha256 == "a" * 64
        assert session.scalar(select(ReportVersion)).content == {"summary": "immutable old report"}
    engine.dispose()
    with sqlite3.connect(path) as source, sqlite3.connect(tmp_path / "restored.db") as restored:
        source.backup(restored)
        assert restored.execute("SELECT content FROM report_versions").fetchone() == source.execute("SELECT content FROM report_versions").fetchone()
