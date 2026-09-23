"""Optional, conversation-scoped Gemini synthesis cache."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "synthesis_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_synthesis_runs_conversation_id", "synthesis_runs", ["conversation_id"]
    )


def downgrade():
    op.drop_table("synthesis_runs")
