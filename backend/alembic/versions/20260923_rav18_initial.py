"""Initial RAV18 six-table schema.

Revision ID: 20260923_rav18
Revises:
"""

import sqlalchemy as sa
from alembic import op

from sqlalchemy.dialects.postgresql import JSONB


revision = "20260923_rav18"
down_revision = None
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(JSONB, "postgresql")


def _id():
    return sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True)


def _time(name, nullable=False):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade():
    op.create_table(
        "incidents",
        _id(),
        sa.Column("incident_id", sa.String(64), nullable=False, unique=True),
        sa.Column("processing_status", sa.String(20), nullable=False),
        sa.Column("video_uri", sa.Text(), nullable=False),
        sa.Column("telemetry_uri", sa.Text()),
        sa.Column("video_metadata", json_type),
        sa.Column("telemetry_metadata", json_type),
        _time("recorded_at", True),
        sa.Column("scenario", sa.String(255)),
        sa.Column("template", sa.String(64)),
        sa.Column("source", json_type),
        sa.Column("collision", json_type),
        sa.Column("ego", json_type),
        sa.Column("quality", json_type),
        sa.Column("raw_incident_data", json_type),
        _time("created_at"),
        _time("updated_at"),
    )
    op.create_table(
        "jobs",
        _id(),
        sa.Column("job_id", sa.String(64), nullable=False, unique=True),
        sa.Column("incident_id", sa.Uuid(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("pass", sa.SmallInteger()),
        sa.Column("progress_done", sa.Integer(), nullable=False),
        sa.Column("progress_total", sa.Integer()),
        sa.Column("result_uri", sa.Text()),
        sa.Column("error", json_type),
        sa.Column("attempt", sa.Integer(), nullable=False),
        _time("lease_until", True),
        _time("created_at"),
        _time("started_at", True),
        _time("updated_at"),
        _time("completed_at", True),
    )
    op.create_index(
        "uq_jobs_one_active_per_incident",
        "jobs",
        ["incident_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_table(
        "evidences",
        _id(),
        sa.Column("evidence_id", sa.String(64), nullable=False, unique=True),
        sa.Column("incident_id", sa.Uuid(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("time_start_s", sa.Float(), nullable=False),
        sa.Column("time_end_s", sa.Float(), nullable=False),
        sa.Column("tier", sa.String(20)),
        sa.Column("bytes", sa.BigInteger()),
        sa.Column("media_type", sa.String(128)),
        _time("created_at"),
    )
    op.create_table(
        "analysis_reports",
        _id(),
        sa.Column("incident_id", sa.Uuid(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("incident_detected", sa.Boolean()),
        sa.Column("incident_type", sa.String(255)),
        sa.Column("start_s", sa.Float()),
        sa.Column("critical_s", sa.Float()),
        sa.Column("end_s", sa.Float()),
        sa.Column("summary", sa.Text()),
        sa.Column("timeline", json_type, nullable=False),
        sa.Column("key_factors", json_type, nullable=False),
        sa.Column("observations", json_type, nullable=False),
        sa.Column("unknowns", json_type, nullable=False),
        sa.Column("evidence_ids", json_type, nullable=False),
        sa.Column("model_metadata", json_type),
        sa.Column("review_status", sa.String(20), nullable=False),
        _time("created_at"),
        _time("updated_at"),
    )
    op.create_table(
        "report_versions",
        _id(),
        sa.Column("report_id", sa.Uuid(as_uuid=True), sa.ForeignKey("analysis_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", json_type, nullable=False),
        sa.Column("edited_by", sa.String(255)),
        _time("created_at"),
    )
    op.create_index("uq_report_versions_report_version", "report_versions", ["report_id", "version"], unique=True)
    op.create_table(
        "audit_events",
        _id(),
        sa.Column("incident_id", sa.Uuid(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(255)),
        sa.Column("metadata", json_type),
        _time("created_at"),
    )
    op.create_index("ix_audit_incident_created", "audit_events", ["incident_id", "created_at"])


def downgrade():
    op.drop_table("audit_events")
    op.drop_table("report_versions")
    op.drop_table("analysis_reports")
    op.drop_table("evidences")
    op.drop_table("jobs")
    op.drop_table("incidents")
