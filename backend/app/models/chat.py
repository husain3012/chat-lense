from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base

Json = JSON().with_variant(JSONB, "postgresql")


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    conversation_type: Mapped[str] = mapped_column(String(10))
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer)
    extra: Mapped[dict] = mapped_column("metadata", Json, default=dict)


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(String)
    platform_identifier: Mapped[str | None] = mapped_column(String)
    is_current_user: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    platform_message_id: Mapped[str | None] = mapped_column(String)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    sender_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    sender_name: Mapped[str | None] = mapped_column(String)
    message_type: Mapped[str] = mapped_column(String(16), index=True)
    text: Mapped[str | None] = mapped_column(String)
    reply_to_id: Mapped[str | None] = mapped_column(String)
    mentions: Mapped[list] = mapped_column(Json, default=list)
    reactions: Mapped[list] = mapped_column(Json, default=list)
    attachments: Mapped[list] = mapped_column(Json, default=list)
    extra: Mapped[dict] = mapped_column("metadata", Json, default=dict)
    __table_args__ = (
        Index(
            "ix_messages_conversation_timestamp",
            "conversation_id",
            "timestamp",
            "sequence",
            "id",
        ),
    )


class SynthesisRun(Base):
    __tablename__ = "synthesis_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    payload: Mapped[dict] = mapped_column(Json)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    available_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    options: Mapped[dict] = mapped_column(Json, default=dict)
    progress: Mapped[dict] = mapped_column(Json, default=dict)
    result: Mapped[dict] = mapped_column(Json, default=dict)
    error: Mapped[str | None] = mapped_column(String)


class AppSetting(Base):
    __tablename__ = "app_settings"
    name: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(Json)
