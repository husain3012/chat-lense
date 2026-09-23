from datetime import datetime, timedelta, timezone
from app.schemas.chat import Message, ParsedConversation
from app.analytics.overview import calculate


def fixture(group=False):
    c = ParsedConversation(
        platform="telegram",
        title="Test",
        conversation_type="group" if group else "direct",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.messages = [
        Message(
            timestamp=start + timedelta(seconds=s),
            sender_name=name,
            message_type=kind,
            platform_message_id=str(i),
        )
        for i, (s, name, kind) in enumerate(
            [
                (0, None, "system"),
                (60, "Alice", "text"),
                (120, "Alice", "text"),
                (180, "Bob", "text"),
                (14400 + 181, "Bob", "text"),
                (14400 + 241, "Alice", "text"),
            ]
        )
    ]
    return c.finalize()


def test_analytics():
    c = fixture()
    a = calculate(c.messages, c.participants, c.conversation_type, {}, 4)
    assert a["total_messages"] == 6
    assert a["sessions"]["total"] == 2
    assert a["active_days"] == 1
    alice, bob = a["participants"]
    assert alice["message_count"] == 3 and bob["message_count"] == 2
    assert alice["sessions_started"] == 1 and bob["sessions_started"] == 1
    assert bob["response_times"]["median"] == 60
    assert alice["response_times"]["median"] == 60
    assert sum(x["count"] for x in a["activity"]["hourly"]) == 6
    assert a["reactions"] is None


def test_group_replies():
    c = fixture(True)
    a = calculate(c.messages, c.participants, "group", {}, 4)
    assert all(p["response_times"] is None for p in a["participants"])
    c.messages[3].reply_to_id = "1"
    c.messages[3].reactions = [{"emoji": "❤", "count": 1, "actors": ["Alice"]}]
    a = calculate(c.messages, c.participants, "group", {"reactions_available": True}, 4)
    assert a["participants"][1]["response_times"]["median"] == 120
    assert a["interactions"]["matrix"] == [[0, 1], [1, 0]]
    assert a["reactions"]["total"] == 1


def test_session_exact_boundary():
    c = fixture()
    c.messages = c.messages[:2]
    c.messages[1].timestamp = c.messages[0].timestamp + timedelta(hours=4)
    assert (
        calculate(c.messages, c.participants, "direct", {}, 4)["sessions"]["total"] == 1
    )
    c.messages[1].timestamp += timedelta(seconds=1)
    assert (
        calculate(c.messages, c.participants, "direct", {}, 4)["sessions"]["total"] == 2
    )


def test_empty():
    a = calculate([], [], "direct", {}, 4)
    assert a["sessions"]["total"] == 0
    assert a["messages_per_active_day"] == 0
