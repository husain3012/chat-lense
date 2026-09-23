"""Correct previously imported WhatsApp GIF placeholders without touching authored text."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    messages = sa.table(
        "messages",
        sa.column("conversation_id"),
        sa.column("message_type"),
        sa.column("text"),
        sa.column(
            "attachments", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
        ),
    )
    conversations = sa.table("conversations", sa.column("id"), sa.column("platform"))
    normalized = sa.func.lower(
        sa.func.trim(
            sa.func.replace(
                sa.func.replace(messages.c.text, "\u200e", ""), "\u200f", ""
            )
        )
    )
    bind.execute(
        messages.update()
        .where(
            messages.c.conversation_id.in_(
                sa.select(conversations.c.id).where(
                    conversations.c.platform == "whatsapp"
                )
            ),
            normalized.in_(["gif omitted", "<gif omitted>"]),
        )
        .values(
            message_type="video",
            text=None,
            attachments=[{"reference": "GIF omitted", "available": False}],
        )
    )


def downgrade():
    # Data correction is intentionally not reversed into incorrect authored text.
    pass
