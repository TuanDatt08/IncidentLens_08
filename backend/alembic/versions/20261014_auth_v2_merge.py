"""Merge internal auth and existing V2 migration histories."""
revision = "20261014_auth_v2"
down_revision = ("20261010_auth", "20261003_jobs")
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
