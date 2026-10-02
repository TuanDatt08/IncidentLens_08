"""The six persisted RAV18 entities. Media bytes stay outside the database."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonValue = JSON().with_variant(JSONB, "postgresql")


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False)
    video_uri: Mapped[str] = mapped_column(Text, nullable=False)
    telemetry_uri: Mapped[str | None] = mapped_column(Text)
    video_metadata: Mapped[dict | None] = mapped_column(JsonValue)
    telemetry_metadata: Mapped[dict | None] = mapped_column(JsonValue)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scenario: Mapped[str | None] = mapped_column(String(255))
    template: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[dict | None] = mapped_column(JsonValue)
    collision: Mapped[dict | None] = mapped_column(JsonValue)
    ego: Mapped[dict | None] = mapped_column(JsonValue)
    quality: Mapped[dict | None] = mapped_column(JsonValue)
    raw_incident_data: Mapped[dict | None] = mapped_column(JsonValue)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    pass_number: Mapped[int | None] = mapped_column("pass", SmallInteger)
    progress_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_total: Mapped[int | None] = mapped_column(Integer)
    result_uri: Mapped[str | None] = mapped_column(Text)
    error: Mapped[dict | None] = mapped_column(JsonValue)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "uq_jobs_one_active_per_incident",
            "incident_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    time_start_s: Mapped[float] = mapped_column(Float, nullable=False)
    time_end_s: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str | None] = mapped_column(String(20))
    bytes: Mapped[int | None] = mapped_column(BigInteger)
    media_type: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False)
    incident_detected: Mapped[bool | None]
    incident_type: Mapped[str | None] = mapped_column(String(255))
    start_s: Mapped[float | None] = mapped_column(Float)
    critical_s: Mapped[float | None] = mapped_column(Float)
    end_s: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    timeline: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    key_factors: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    observations: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    unknowns: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    model_metadata: Mapped[dict | None] = mapped_column(JsonValue)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("analysis_reports.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    edited_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

    __table_args__ = (Index("uq_report_versions_report_version", "report_id", "version", unique=True),)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255))
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JsonValue)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

    __table_args__ = (Index("ix_audit_incident_created", "incident_id", "created_at"),)
