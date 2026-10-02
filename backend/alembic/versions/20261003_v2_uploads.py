"""Local resumable upload sessions.

Revision ID: 20261003_upload
Revises: 20261003_v2
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261003_upload"
down_revision = "20261003_v2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("uploads_v2", sa.Column("upload_id", sa.String(64), primary_key=True), sa.Column("recording_id", sa.String(64), nullable=False), sa.Column("owner", sa.String(255), nullable=False), sa.Column("byte_count", sa.Integer(), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("part_size", sa.Integer(), nullable=False), sa.Column("parts", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("uploads_v2")
