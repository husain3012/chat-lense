import json
from collections import defaultdict
from datetime import datetime, timezone
from app.parsers.base import ChatParser, files
from app.schemas.chat import Message, ParsedConversation, Participant
from app.utils.text import normalize_meta_text as norm


class InstagramParser(ChatParser):
    @classmethod
    def detect(cls, input_path):
        for path in files(input_path, ".json"):
            data = json.loads(path.read_text())
            if (
                isinstance(data, dict)
                and "participants" in data
                and "messages" in data
                and any("timestamp_ms" in m for m in data["messages"][:10])
            ):
                return 0.99
        return 0.0

    def parse(self, input_path):
        groups = defaultdict(list)
        for path in files(input_path, ".json"):
            data = json.loads(path.read_text())
            if "participants" in data and "messages" in data:
                groups[str(path.parent)].append(data)
        output = []
        for parts in groups.values():
            first = parts[0]
            c = ParsedConversation(
                platform="instagram",
                title=norm(first.get("title", "Instagram chat")),
                metadata={"reactions_available": True},
            )
            names = dict.fromkeys(
                norm(p["name"]) for part in parts for p in part["participants"]
            )
            c.participants = [Participant(display_name=name) for name in names]
            for part in parts:
                for item in part["messages"]:
                    kind = "text"
                    attachments = []
                    for field, category in [
                        ("photos", "image"),
                        ("videos", "video"),
                        ("audio_files", "audio"),
                        ("files", "file"),
                        ("sticker", "sticker"),
                    ]:
                        if item.get(field):
                            kind = category
                            values = (
                                item[field]
                                if isinstance(item[field], list)
                                else [item[field]]
                            )
                            attachments.extend(
                                {"reference": v.get("uri", ""), "available": False}
                                for v in values
                            )
                    text = norm(item.get("content", ""))
                    if item.get("share"):
                        text += "\n" + item["share"].get("link", "")
                    if item.get("call_duration") is not None:
                        kind = "call"
                    if item.get("is_unsent"):
                        kind, text = "other", "Unsent message"
                    c.messages.append(
                        Message(
                            timestamp=datetime.fromtimestamp(
                                item["timestamp_ms"] / 1000, timezone.utc
                            ),
                            sender_name=norm(item["sender_name"])
                            if item.get("sender_name")
                            else None,
                            text=text or None,
                            message_type=kind,
                            reactions=[
                                {
                                    "emoji": norm(r["reaction"]),
                                    "count": 1,
                                    "actors": [norm(r["actor"])],
                                }
                                for r in item.get("reactions", [])
                            ],
                            attachments=attachments,
                        )
                    )
            output.append(c.finalize())
        return output
