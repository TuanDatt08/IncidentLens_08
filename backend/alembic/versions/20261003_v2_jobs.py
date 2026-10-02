"""V2 durable checkpoints and finite budgets.

Revision ID: 20261003_jobs
Revises: 20261003_upload
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261003_jobs"
down_revision = "20261003_upload"
branch_labels = None
depends_on = None
json_type = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade():
    op.create_table("jobs_v2", sa.Column("job_id", sa.String(64), primary_key=True), sa.Column("recording_id", sa.String(64), sa.ForeignKey("recordings_v2.recording_id"), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("provider_profile", sa.String(20), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("stage", sa.String(32), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("lease_until", sa.DateTime(timezone=True)), sa.Column("checkpoints", json_type, nullable=False), sa.Column("coverage", json_type, nullable=False), sa.Column("budget", json_type, nullable=False), sa.Column("error_code", sa.String(64)), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("recording_id", "idempotency_key", name="uq_v2_job_idempotency"))
    op.create_index("uq_v2_job_active", "jobs_v2", ["recording_id"], unique=True, postgresql_where=sa.text("status IN ('queued', 'running')"), sqlite_where=sa.text("status IN ('queued', 'running')"))


def downgrade():
    op.drop_table("jobs_v2")
