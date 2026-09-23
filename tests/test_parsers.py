import json
import sqlite3
from pathlib import Path
import pytest
from app.parsers.whatsapp import WhatsAppParser
from app.parsers.telegram import TelegramParser
from app.parsers.instagram import InstagramParser
from app.parsers.imessage import IMessageParser, apple_timestamp
from app.parsers.registry import detect
from app.utils.text import normalize_meta_text

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_whatsapp_examples():
    direct = WhatsAppParser().parse(EXAMPLES / "whatsapp_direct.txt")[0]
    group = WhatsAppParser().parse(EXAMPLES / "whatsapp_group.txt")[0]
    assert direct.conversation_type == "direct"
    assert group.conversation_type == "group"
    assert len(group.participants) == 4
    assert group.messages[0].message_type == "system"
    assert "https://example.com/meet?a=1:b" in direct.messages[2].text
    assert "\n" in direct.messages[2].text
    assert direct.messages[0].timestamp.hour == 19
    assert direct.messages[3].message_type == "image"
    assert "👋" in direct.messages[0].text
    assert detect(EXAMPLES / "whatsapp_direct.txt")["platform"] == "whatsapp"


@pytest.mark.parametrize(
    "header,hour",
    [
        ("12/08/2026, 7:42 pm - ", 19),
        ("12/08/2026, 19:42 - ", 19),
        ("[12/08/2026, 7:42:10 PM] ", 19),
        ("[12/08/26, 12:01 AM] ", 0),
        ("2026/08/12, 19:42 - ", 19),
    ],
)
def test_whatsapp_formats(tmp_path, header, hour):
    path = tmp_path / "chat.txt"
    path.write_text(
        header
        + "Alice: Héllo: a - b, 🌿\nمرحبا\n"
        + header
        + "Sam: https://example.com/a:b"
    )
    c = WhatsAppParser().parse(path)[0]
    assert c.messages[0].timestamp.hour == hour
    assert c.messages[0].text == "Héllo: a - b, 🌿\nمرحبا"
    assert len(c.messages) == 2


def test_whatsapp_order_and_events(tmp_path):
    path = tmp_path / "chat.txt"
    path.write_text(
        "08/25/2026, 09:00 - Sam: Missed voice call\n08/25/2026, 09:01 - Alice: This message was deleted\n08/25/2026, 09:02 - Alice left"
    )
    c = WhatsAppParser().parse(path)[0]
    assert c.started_at.month == 8 and c.started_at.day == 25
    assert [m.message_type for m in c.messages] == ["call", "other", "system"]
    path.write_text("08/12/2026, 09:00 - Alice: hi")
    assert WhatsAppParser("mdy").parse(path)[0].started_at.month == 8
    assert WhatsAppParser("dmy").parse(path)[0].started_at.month == 12


def test_whatsapp_sender_prefixed_system_records_do_not_become_people(tmp_path):
    path = tmp_path / "_chat.txt"
    path.write_text(
        "01/01/2026, 09:00 - Weekend Crew: Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.\n"
        "01/01/2026, 09:01 - Weekend Crew: Alice added you\n"
        "01/01/2026, 09:02 - You: You pinned a message\n"
        "01/01/2026, 09:03 - Alice: hello\n"
        "01/01/2026, 09:04 - Husain: hi"
    )
    chat = WhatsAppParser().parse(path)[0]
    assert chat.title == "Weekend Crew"
    assert [p.display_name for p in chat.participants] == ["Alice", "Husain"]
    assert [m.message_type for m in chat.messages[:3]] == ["system"] * 3
    assert all(m.sender_id is None for m in chat.messages[:3])
    assert chat.messages[2].metadata["export_system_label"] == "You"


def test_telegram():
    c = TelegramParser().parse(EXAMPLES / "telegram_direct.json")[0]
    assert c.messages[1].text == "Hello Alice"
    assert c.messages[1].reply_to_id == "1"
    c = TelegramParser().parse(EXAMPLES / "telegram_group.json")[0]
    assert c.conversation_type == "group"
    assert c.messages[-1].message_type == "image"
    assert c.messages[1].reactions[0]["count"] == 2
    assert c.messages[0].message_type == "system"
    assert detect(EXAMPLES / "telegram_group.json")["platform"] == "telegram"


def test_instagram_multi(tmp_path):
    base = json.loads((EXAMPLES / "instagram_direct.json").read_text())
    for i, m in enumerate(base["messages"]):
        part = {
            **base,
            "participants": base["participants"] + [{"name": "Mia"}],
            "messages": [m],
        }
        (tmp_path / f"message_{i + 1}.json").write_text(json.dumps(part))
    c = InstagramParser().parse(tmp_path)[0]
    assert c.conversation_type == "group"
    assert c.messages[0].timestamp < c.messages[1].timestamp
    assert c.messages[0].message_type == "image"
    assert c.messages[1].reactions[0]["actors"] == ["Alice"]
    assert c.messages[0].timestamp.year == 2026
    assert detect(tmp_path)["platform"] == "instagram"


@pytest.mark.parametrize("text", ["Hello 🌿", "مرحبا", "café", "你好", "plain ASCII"])
def test_unicode(text):
    assert normalize_meta_text(text) == text
    assert normalize_meta_text(text.encode("utf-8").decode("latin-1")) == text


def make_imessage(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """CREATE TABLE chat (display_name TEXT,chat_identifier TEXT); CREATE TABLE handle (id TEXT); CREATE TABLE message (guid TEXT,date INTEGER,handle_id INTEGER,is_from_me INTEGER,text TEXT,attributedBody BLOB); CREATE TABLE chat_handle_join(chat_id INTEGER,handle_id INTEGER); CREATE TABLE chat_message_join(chat_id INTEGER,message_id INTEGER); INSERT INTO handle VALUES ('Alice'),('Sam'); INSERT INTO chat VALUES ('','Alice'),('Weekend Makers','group'); INSERT INTO chat_handle_join VALUES (1,1),(2,1),(2,2); INSERT INTO message VALUES ('m1',100000000000000000,1,0,'Hello',NULL),('m2',100000060000000000,0,1,'Hi',NULL),('m3',100000120000000000,2,0,NULL,X'0102'); INSERT INTO chat_message_join VALUES (1,1),(1,2),(2,1),(2,2),(2,3);"""
        )


def test_imessage(tmp_path):
    path = tmp_path / "chat.db"
    make_imessage(path)
    before = path.read_bytes()
    chats = IMessageParser().parse(path)
    assert path.read_bytes() == before
    assert chats[0].conversation_type == "direct"
    assert [m.sender_name for m in chats[0].messages] == ["Alice", "Me"]
    assert chats[1].conversation_type == "group"
    assert chats[1].title == "Weekend Makers"
    assert chats[1].messages[-1].metadata["body_unavailable"]
    assert apple_timestamp(0).isoformat() == "2001-01-01T00:00:00+00:00"
    assert apple_timestamp(700000000) == apple_timestamp(700000000000000000)


@pytest.mark.parametrize(
    "field,media_type,expected",
    [
        ("file", "video_file", "video"),
        ("file", "voice_message", "audio"),
        ("file", "audio_file", "audio"),
        ("file", "sticker", "sticker"),
        ("file", "unknown", "file"),
    ],
)
def test_telegram_media_and_metadata(tmp_path, field, media_type, expected):
    payload = {
        "id": 8,
        "type": "personal_chat",
        "name": "Test",
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date_unixtime": "1786352400",
                "from": "Alice",
                "from_id": "user1",
                "text": [{"type": "mention_name", "text": "Sam", "user_id": 2}],
                "forwarded_from": "Mia",
                "edited": "2026-08-10T09:10:00",
                field: "media/file",
                "media_type": media_type,
            }
        ],
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(payload))
    c = TelegramParser().parse(path)[0]
    assert c.messages[0].message_type == expected
    assert c.messages[0].mentions == ["2"]
    assert c.messages[0].metadata["forwarded_from"] == "Mia"


def test_instagram_share_unsent_call(tmp_path):
    path = tmp_path / "message_1.json"
    path.write_text(
        json.dumps(
            {
                "title": "Test",
                "participants": [{"name": "Alice"}, {"name": "Sam"}],
                "messages": [
                    {
                        "sender_name": "Alice",
                        "timestamp_ms": 1786352400000,
                        "share": {"link": "https://example.com/post"},
                    },
                    {
                        "sender_name": "Sam",
                        "timestamp_ms": 1786352410000,
                        "is_unsent": True,
                    },
                    {
                        "sender_name": "Alice",
                        "timestamp_ms": 1786352420000,
                        "call_duration": 30,
                    },
                ],
            }
        )
    )
    c = InstagramParser().parse(path)[0]
    assert c.conversation_type == "direct"
    assert "https://example.com/post" in c.messages[0].text
    assert c.messages[1].message_type == "other"
    assert c.messages[2].message_type == "call"


def test_telegram_offset(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            {
                "id": 1,
                "name": "Test",
                "type": "personal_chat",
                "messages": [
                    {
                        "id": 1,
                        "type": "message",
                        "date": "2026-08-10T09:00:00+05:30",
                        "from": "Alice",
                        "text": "hi",
                    }
                ],
            }
        )
    )
    stamp = TelegramParser().parse(path)[0].messages[0].timestamp
    assert stamp.hour == 3 and stamp.minute == 30


def test_whatsapp_title_changes(tmp_path):
    path = tmp_path / "chat.txt"
    path.write_text(
        "12/08/2026, 09:00 - Alice created group “Old title”\n12/08/2026, 09:01 - Alice changed the subject from “Old title” to “New title”\n12/08/2026, 09:02 - Alice: hello\n12/08/2026, 09:03 - Sam: hi"
    )
    c = WhatsAppParser().parse(path)[0]
    assert c.title == "New title"
    assert c.conversation_type == "group"
    assert len(c.participants) == 2
