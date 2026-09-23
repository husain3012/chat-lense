"""Initial normalized conversation schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    j = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String()),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("conversation_type", sa.String(10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("metadata", j, nullable=False),
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("platform_identifier", sa.String()),
        sa.Column("is_current_user", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_participants_conversation_id", "participants", ["conversation_id"]
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform_message_id", sa.String()),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "sender_id",
            sa.String(36),
            sa.ForeignKey("participants.id", ondelete="CASCADE"),
        ),
        sa.Column("sender_name", sa.String()),
        sa.Column("message_type", sa.String(16), nullable=False),
        sa.Column("text", sa.String()),
        sa.Column("reply_to_id", sa.String()),
        *[
            sa.Column(k, j, nullable=False)
            for k in ("mentions", "reactions", "attachments", "metadata")
        ],
    )
    for column in ("conversation_id", "timestamp", "sender_id", "message_type"):
        op.create_index("ix_messages_" + column, "messages", [column])
    op.create_index(
        "ix_messages_conversation_timestamp",
        "messages",
        ["conversation_id", "timestamp", "id"],
    )


def downgrade():
    op.drop_table("messages")
    op.drop_table("participants")
    op.drop_table("conversations")
