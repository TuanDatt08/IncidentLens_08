"""Separate V2 recording/candidate snapshots; the six V1 tables are untouched."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.tables import Base, JsonValue, now


class RecordingV2(Base):
    __tablename__ = "recordings_v2"
    recording_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    duration_s: Mapped[float] = mapped_column(Float, nullable=False)
    video_uri: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JsonValue, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class CandidateV2(Base):
    __tablename__ = "candidates_v2"
    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recording_id: Mapped[str] = mapped_column(ForeignKey("recordings_v2.recording_id"), index=True, nullable=False)
    window: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    reasons: Mapped[list] = mapped_column(JsonValue, default=list, nullable=False)
    analysis_state: Mapped[str] = mapped_column(String(20), nullable=False)


class ReportV2(Base):
    __tablename__ = "reports_v2"
    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates_v2.candidate_id"), unique=True, nullable=False)
    recording_id: Mapped[str] = mapped_column(ForeignKey("recordings_v2.recording_id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    provenance: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    evidence_registry: Mapped[list] = mapped_column(JsonValue, nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(255))


class SnapshotV2(Base):
    __tablename__ = "report_snapshots_v2"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports_v2.report_id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint("report_id", "version", name="uq_v2_snapshot_version"),)


class UploadV2(Base):
    __tablename__ = "uploads_v2"
    upload_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recording_id: Mapped[str] = mapped_column(String(64), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    part_size: Mapped[int] = mapped_column(Integer, nullable=False)
    parts: Mapped[dict] = mapped_column(JsonValue, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JobV2(Base):
    __tablename__ = "jobs_v2"
    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    recording_id: Mapped[str] = mapped_column(ForeignKey("recordings_v2.recording_id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_profile: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoints: Mapped[dict] = mapped_column(JsonValue, default=dict, nullable=False)
    coverage: Mapped[dict] = mapped_column(JsonValue, default=dict, nullable=False)
    budget: Mapped[dict] = mapped_column(JsonValue, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (
        UniqueConstraint("recording_id", "idempotency_key", name="uq_v2_job_idempotency"),
        Index("uq_v2_job_active", "recording_id", unique=True, postgresql_where=text("status IN ('queued', 'running')"), sqlite_where=text("status IN ('queued', 'running')")),
    )
