import json
from datetime import datetime, timezone
from app.parsers.base import ChatParser, files
from app.schemas.chat import Message, ParsedConversation, Participant


class TelegramParser(ChatParser):
    @classmethod
    def detect(cls, input_path):
        for p in files(input_path, ".json"):
            data = json.loads(p.read_text())
            if isinstance(data, dict) and (
                "chats" in data
                or ("messages" in data and "type" in data and "id" in data)
            ):
                return 0.99
        return 0.0

    def parse(self, input_path):
        output = []
        for path in files(input_path, ".json"):
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                continue
            chats = data.get("chats", {}).get("list", [data])
            for chat in chats:
                if "messages" not in chat:
                    continue
                c = ParsedConversation(
                    platform="telegram",
                    title=chat.get("name") or "Telegram chat",
                    external_id=str(chat.get("id", "")),
                    conversation_type="group"
                    if "group" in chat.get("type", "")
                    else "direct",
                    metadata={"reactions_available": True},
                )
                identities = {}
                for item in chat["messages"]:
                    name = item.get("from") or item.get("actor")
                    external = item.get("from_id") or item.get("actor_id")
                    if name:
                        key = str(external or name)
                        if key not in identities:
                            identities[key] = Participant(
                                display_name=name, platform_identifier=key
                            )
                    fragments = item.get("text", "")
                    text = (
                        fragments
                        if isinstance(fragments, str)
                        else "".join(
                            f if isinstance(f, str) else f.get("text", "")
                            for f in fragments
                        )
                    )
                    mentions = (
                        [
                            f.get("user_id", f.get("text", ""))
                            for f in fragments
                            if isinstance(f, dict)
                            and f.get("type") in ("mention", "mention_name")
                        ]
                        if isinstance(fragments, list)
                        else []
                    )
                    kind = "system" if item.get("type") == "service" else "text"
                    attachments = []
                    if item.get("photo") or item.get("file"):
                        media = item.get("media_type", "")
                        kind = (
                            "image"
                            if item.get("photo")
                            else {
                                "video_file": "video",
                                "animation": "video",
                                "voice_message": "audio",
                                "audio_file": "audio",
                                "sticker": "sticker",
                            }.get(media, "file")
                        )
                        attachments = [
                            {
                                "reference": item.get("photo") or item.get("file"),
                                "available": False,
                            }
                        ]
                    stamp = (
                        datetime.fromtimestamp(
                            float(item["date_unixtime"]), timezone.utc
                        )
                        if item.get("date_unixtime")
                        else datetime.fromisoformat(item["date"])
                    )
                    stamp = (
                        stamp.replace(tzinfo=timezone.utc)
                        if stamp.tzinfo is None
                        else stamp.astimezone(timezone.utc)
                    )
                    reactions = []
                    for r in item.get("reactions", []):
                        recent = r.get("recent", [])
                        reactions.append(
                            {
                                "emoji": r.get("emoji", r.get("type", "?")),
                                "count": r.get("count", len(recent)),
                                "actors": [str(a.get("from_id", "")) for a in recent],
                            }
                        )
                    c.messages.append(
                        Message(
                            platform_message_id=str(item["id"]),
                            timestamp=stamp,
                            sender_name=name,
                            sender_id=identities[str(external or name)].id
                            if name
                            else None,
                            text=text or item.get("action"),
                            message_type=kind,
                            reply_to_id=str(item["reply_to_message_id"])
                            if item.get("reply_to_message_id")
                            else None,
                            mentions=[str(m) for m in mentions],
                            reactions=reactions,
                            attachments=attachments,
                            metadata={
                                k: item[k]
                                for k in ("forwarded_from", "edited", "action")
                                if k in item
                            },
                        )
                    )
                c.participants = list(identities.values())
                output.append(c.finalize())
        return output
