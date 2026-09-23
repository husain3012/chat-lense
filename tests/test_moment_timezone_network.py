from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.schemas.chat import ParsedConversation, Message
from app.services.import_timezone import apply_timezone
from app.analytics.reply_network import calculate
from app.synthesis import editorial
from app.synthesis.gemini import RetryableError


def whatsapp(timestamp):
    return ParsedConversation(
        platform="whatsapp",
        title="Synthetic",
        messages=[Message(timestamp=timestamp, sender_name="A", text="Hi")],
    ).finalize()


def test_whatsapp_requires_explicit_timezone_and_converts_half_hour_offset():
    c = whatsapp(datetime(2026, 1, 2, 0, 15, tzinfo=timezone.utc))
    with pytest.raises(HTTPException, match="timezone"):
        apply_timezone(c, None, required=True)
    apply_timezone(c, "Asia/Kolkata", required=True)
    assert c.messages[0].timestamp == datetime(2026, 1, 1, 18, 45, tzinfo=timezone.utc)
    assert c.started_at == c.messages[0].timestamp
    assert c.metadata["source_timezone"] == "Asia/Kolkata"


def test_timezone_dst_gap_fold_and_invalid_zone():
    with pytest.raises(HTTPException):
        apply_timezone(whatsapp(datetime(2026, 1, 1)), "Not/AZone", True)
    with pytest.raises(HTTPException, match="clock gap"):
        apply_timezone(whatsapp(datetime(2026, 3, 8, 2, 30)), "America/New_York", True)
    c = whatsapp(datetime(2026, 11, 1, 1, 30))
    apply_timezone(c, "America/New_York", True)
    assert c.messages[0].timestamp.hour == 5
    assert any("repeated" in w for w in c.warnings)


def test_reply_network_counts_only_resolved_cross_person_replies():
    people = [SimpleNamespace(id=i, display_name=i) for i in "ABC"]

    def msg(mid, sender, reply=None, kind="text"):
        return SimpleNamespace(
            id=mid,
            platform_message_id="external-" + mid,
            sender_id=sender,
            reply_to_id=reply,
            message_type=kind,
        )

    rows = [
        msg("1", "A"),
        msg("2", "B", "external-1"),
        msg("3", "A", "2"),
        msg("4", "B", "external-1"),
        msg("5", "A", "1"),
        msg("6", "C", "missing"),
        msg("7", "C", "1", "system"),
    ]
    data = calculate(rows, people)
    assert data["total_replies"] == 3
    assert len(data["edges"]) == 1
    assert data["edges"][0]["weight"] == 3
    assert data["edges"][0]["forward"] == 1
    assert data["edges"][0]["backward"] == 2
    assert calculate([msg("1", "A"), msg("2", "B")], people) is None


def test_editorial_retains_low_score_findings_for_synthesis(monkeypatch):
    moments = [
        {
            "id": "a",
            "title": "Checking in",
            "description": "An ordinary greeting",
            "evidence_ids": ["m1", "m2"],
        },
        {
            "id": "b",
            "title": "Making up",
            "description": "A substantial repair",
            "evidence_ids": ["m3", "m4", "m5"],
        },
    ]
    monkeypatch.setattr(
        editorial,
        "ask",
        lambda *args: {
            "moments": [
                {"id": "a", "kind": "sweet", "score": 2},
                {"id": "b", "kind": "repair", "score": 8},
            ]
        },
    )
    result = editorial.review(moments, {})
    assert len(result) == 2 and result[0]["display_score"] == 2
    assert result[1]["evidence_ids"] == moments[1]["evidence_ids"]
    monkeypatch.setattr(
        editorial,
        "ask",
        lambda *args: {"moments": [{"id": "a", "kind": "sweet", "score": 2}]},
    )
    partial = editorial.review(moments, {})
    assert [m["id"] for m in partial] == ["a"]
    monkeypatch.setattr(
        editorial,
        "ask",
        lambda *args: {"moments": [{"id": "invented", "kind": "romance", "score": 9}]},
    )
    with pytest.raises(RetryableError):
        editorial.review(moments, {})
    monkeypatch.setattr(
        editorial,
        "ask",
        lambda *args: {"moments": [{"id": "a", "kind": ["sweet"], "score": 8}]},
    )
    with pytest.raises(RetryableError):
        editorial.review(moments, {})
