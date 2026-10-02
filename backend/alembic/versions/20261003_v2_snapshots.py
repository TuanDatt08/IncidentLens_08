"""V2 recording and review snapshots, additive to V1.

Revision ID: 20261003_v2
Revises: 20260923_rav18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261003_v2"
down_revision = "20260923_rav18"
branch_labels = None
depends_on = None
json_type = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade():
    op.create_table("recordings_v2", sa.Column("recording_id", sa.String(64), primary_key=True), sa.Column("duration_s", sa.Float(), nullable=False), sa.Column("video_uri", sa.Text()), sa.Column("metadata_json", json_type, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("candidates_v2", sa.Column("candidate_id", sa.String(64), primary_key=True), sa.Column("recording_id", sa.String(64), sa.ForeignKey("recordings_v2.recording_id"), nullable=False), sa.Column("window", json_type, nullable=False), sa.Column("reasons", json_type, nullable=False), sa.Column("analysis_state", sa.String(20), nullable=False))
    op.create_index("ix_candidates_v2_recording_id", "candidates_v2", ["recording_id"])
    op.create_table("reports_v2", sa.Column("report_id", sa.String(64), primary_key=True), sa.Column("candidate_id", sa.String(64), sa.ForeignKey("candidates_v2.candidate_id"), unique=True, nullable=False), sa.Column("recording_id", sa.String(64), sa.ForeignKey("recordings_v2.recording_id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("analysis", json_type, nullable=False), sa.Column("provenance", json_type, nullable=False), sa.Column("evidence_registry", json_type, nullable=False), sa.Column("submitted_by", sa.String(255)))
    op.create_table("report_snapshots_v2", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("report_id", sa.String(64), sa.ForeignKey("reports_v2.report_id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("content", json_type, nullable=False), sa.Column("actor", sa.String(255), nullable=False), sa.Column("action", sa.String(32), nullable=False), sa.Column("reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("report_id", "version", name="uq_v2_snapshot_version"))


def downgrade():
    op.drop_table("report_snapshots_v2")
    op.drop_table("reports_v2")
    op.drop_table("candidates_v2")
    op.drop_table("recordings_v2")
