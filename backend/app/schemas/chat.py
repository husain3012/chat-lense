from datetime import datetime
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field

Platform = Literal["whatsapp", "telegram", "instagram", "imessage"]
MessageType = Literal[
    "text", "image", "video", "audio", "file", "sticker", "call", "system", "other"
]


def uid() -> str:
    return str(uuid4())


class Participant(BaseModel):
    id: str = Field(default_factory=uid)
    conversation_id: str = ""
    display_name: str
    platform_identifier: str | None = None
    is_current_user: bool = False


class Message(BaseModel):
    id: str = Field(default_factory=uid)
    conversation_id: str = ""
    platform_message_id: str | None = None
    timestamp: datetime
    sequence: int = 0
    sender_id: str | None = None
    sender_name: str | None = None
    message_type: MessageType = "text"
    text: str | None = None
    reply_to_id: str | None = None
    mentions: list[str] = Field(default_factory=list)
    reactions: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ParsedConversation(BaseModel):
    id: str = Field(default_factory=uid)
    platform: Platform
    external_id: str | None = None
    title: str
    conversation_type: Literal["direct", "group"] = "direct"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    message_count: int = 0
    participants: list[Participant] = Field(default_factory=list)
    messages: list[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def finalize(self):
        self.messages.sort(key=lambda m: m.timestamp)
        by_name = {p.display_name: p for p in self.participants}
        for sequence, m in enumerate(self.messages):
            m.sequence = sequence
            m.conversation_id = self.id
            if m.sender_name and m.sender_name not in by_name:
                p = Participant(display_name=m.sender_name)
                self.participants.append(p)
                by_name[m.sender_name] = p
            if m.sender_name and not m.sender_id:
                m.sender_id = by_name[m.sender_name].id
        for p in self.participants:
            p.conversation_id = self.id
        self.message_count = len(self.messages)
        if self.messages:
            self.started_at, self.ended_at = (
                self.messages[0].timestamp,
                self.messages[-1].timestamp,
            )
        if len(self.participants) > 2:
            self.conversation_type = "group"
        return self
