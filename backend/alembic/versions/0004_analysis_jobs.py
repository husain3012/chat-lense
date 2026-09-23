"""Durable analysis checkpoints and local server settings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = depends_on = None


def upgrade():
    json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "analysis_jobs",
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("options", json, nullable=False),
        sa.Column("progress", json, nullable=False),
        sa.Column("result", json, nullable=False),
        sa.Column("error", sa.String(), nullable=True),
    )
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_available_at", "analysis_jobs", ["available_at"])
    op.create_table(
        "app_settings",
        sa.Column("name", sa.String(60), primary_key=True),
        sa.Column("value", json, nullable=False),
    )


def downgrade():
    op.drop_table("analysis_jobs")
    op.drop_table("app_settings")
