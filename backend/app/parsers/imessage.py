import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from app.parsers.base import ChatParser
from app.schemas.chat import Message, ParsedConversation, Participant

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def apple_timestamp(value):
    value = float(value or 0)
    return APPLE_EPOCH + timedelta(
        seconds=value / 1_000_000_000 if abs(value) > 1e12 else value
    )


class IMessageParser(ChatParser):
    @classmethod
    def detect(cls, input_path):
        candidates = (
            list(input_path.rglob("*.db")) if input_path.is_dir() else [input_path]
        )
        for path in candidates:
            with path.open("rb") as f:
                if f.read(16) == b"SQLite format 3\x00":
                    return 0.9
        return 0.0

    def parse(self, input_path):
        paths = list(input_path.rglob("*.db")) if input_path.is_dir() else [input_path]
        output = []
        for path in paths:
            db = sqlite3.connect(
                "file:" + quote(str(path.resolve())) + "?mode=ro&immutable=1", uri=True
            )
            db.row_factory = sqlite3.Row
            try:
                db.execute("PRAGMA query_only=ON")
                tables = {
                    r[0]
                    for r in db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                if (
                    not {
                        "chat",
                        "message",
                        "handle",
                        "chat_message_join",
                        "chat_handle_join",
                    }
                    <= tables
                ):
                    raise ValueError(
                        "SQLite file is not a supported macOS Messages chat.db"
                    )
                # Bound work on potentially malicious/corrupt uploaded databases.
                budget = [0]

                def progress():
                    budget[0] += 1
                    return int(budget[0] > 200000)

                db.set_progress_handler(progress, 10000)
                handles = {
                    r["ROWID"]: r["id"]
                    for r in db.execute("SELECT ROWID, id FROM handle")
                }
                for row in db.execute("SELECT ROWID AS chat_rowid, * FROM chat"):
                    chat = dict(row)
                    ids = [
                        r[0]
                        for r in db.execute(
                            "SELECT handle_id FROM chat_handle_join WHERE chat_id=?",
                            (chat["chat_rowid"],),
                        )
                    ]
                    people = {
                        i: Participant(
                            display_name=handles.get(i, "Unknown"),
                            platform_identifier=handles.get(i),
                        )
                        for i in ids
                    }
                    me = Participant(
                        display_name="Me", platform_identifier="local-user"
                    )
                    title = (
                        chat.get("display_name")
                        or chat.get("chat_identifier")
                        or "iMessage chat"
                    )
                    c = ParsedConversation(
                        platform="imessage",
                        external_id=str(chat["chat_rowid"]),
                        title=title,
                        conversation_type="group" if len(ids) > 1 else "direct",
                    )
                    unavailable = 0
                    for mr in db.execute(
                        "SELECT m.ROWID AS message_rowid, m.* FROM message m JOIN chat_message_join j ON j.message_id=m.ROWID WHERE j.chat_id=? ORDER BY m.date",
                        (chat["chat_rowid"],),
                    ):
                        m = dict(mr)
                        sender = (
                            me
                            if m.get("is_from_me")
                            else people.setdefault(
                                m.get("handle_id"),
                                Participant(
                                    display_name=handles.get(
                                        m.get("handle_id"), "Unknown"
                                    ),
                                    platform_identifier=handles.get(m.get("handle_id")),
                                ),
                            )
                        )
                        body = m.get("text")
                        metadata = {}
                        if not body and m.get("attributedBody"):
                            unavailable += 1
                            metadata["body_unavailable"] = True
                        attachments = []
                        if {"attachment", "message_attachment_join"} <= tables:
                            for ar in db.execute(
                                "SELECT a.* FROM attachment a JOIN message_attachment_join j ON a.ROWID=j.attachment_id WHERE j.message_id=?",
                                (m["message_rowid"],),
                            ):
                                a = dict(ar)
                                attachments.append(
                                    {
                                        "reference": a.get("filename"),
                                        "mime_type": a.get("mime_type"),
                                        "size": a.get("total_bytes"),
                                        "available": False,
                                    }
                                )
                        mime = (
                            (attachments[0].get("mime_type") or "")
                            if attachments
                            else ""
                        )
                        kind = (
                            (
                                "image"
                                if mime.startswith("image/")
                                else "video"
                                if mime.startswith("video/")
                                else "audio"
                                if mime.startswith("audio/")
                                else "file"
                            )
                            if attachments
                            else ("text" if body else "other")
                        )
                        c.messages.append(
                            Message(
                                platform_message_id=m.get("guid")
                                or str(m["message_rowid"]),
                                timestamp=apple_timestamp(m.get("date")),
                                sender_id=sender.id,
                                sender_name=sender.display_name,
                                message_type=kind,
                                text=body,
                                attachments=attachments,
                                metadata=metadata,
                            )
                        )
                    c.participants = [me, *people.values()]
                    if unavailable:
                        c.warnings.append(
                            f"{unavailable} attributedBody-only messages have unavailable text; binary typedstream decoding is not supported."
                        )
                    output.append(c.finalize())
            finally:
                db.close()
        return output
