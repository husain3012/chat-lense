"""Preserve source ordering for messages sharing a timestamp."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "messages",
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_index("ix_messages_conversation_timestamp", table_name="messages")
    op.create_index(
        "ix_messages_conversation_timestamp",
        "messages",
        ["conversation_id", "timestamp", "sequence", "id"],
    )
    op.alter_column("messages", "sequence", server_default=None)


def downgrade():
    op.drop_index("ix_messages_conversation_timestamp", table_name="messages")
    op.create_index(
        "ix_messages_conversation_timestamp",
        "messages",
        ["conversation_id", "timestamp", "id"],
    )
    op.drop_column("messages", "sequence")
