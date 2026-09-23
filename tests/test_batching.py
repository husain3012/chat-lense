import json
from datetime import datetime, timedelta, timezone
from app.schemas.chat import ParsedConversation, Message
from app.insights.engine import build_report
from app.synthesis.packet import build_packet, compact_packet
from app.synthesis.batching import fit_passage


def test_large_worker_batch_is_contiguous_not_legacy_sample():
    chat = ParsedConversation(platform="whatsapp", title="Synthetic batch")
    chat.messages = [
        Message(
            sender_name="A" if i % 2 else "B",
            text=f"नमस्ते 世界 🌷 {i}",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i),
        )
        for i in range(2008)
    ]
    chat.finalize()
    report = build_report(chat.messages, chat.participants, chat)
    packet = build_packet(report, chat.messages, chat.participants, full_passage=True)
    packet["measured_findings"] = {}
    fitted, offset = fit_passage(packet, 0, 8, 234000)
    assert offset == 0
    assert len(fitted["samples"]) > 1200
    assert [m["id"] for m in fitted["samples"]] == [
        m.id for m in chat.messages[: len(fitted["samples"])]
    ]
    assert (
        len(
            json.dumps(
                compact_packet(fitted)[0], ensure_ascii=False, separators=(",", ":")
            ).encode()
        )
        <= 234000
    )


def test_large_overlap_shrinks_without_losing_new_messages():
    samples = [
        {
            "id": str(i),
            "sender_id": "a",
            "timestamp": "2026-01-01",
            "text": "世界" * 1000,
            "type": "text",
            "window": 0,
            "truncated": False,
        }
        for i in range(20)
    ]
    packet = {
        "participants": [{"id": "a", "name": "A"}],
        "measured_findings": {},
        "samples": samples,
        "coverage": {},
        "tone": "fun",
        "timezone": "UTC",
    }
    fitted, offset = fit_passage(packet, 0, 8, 13000)
    assert offset < 9 and offset + len(fitted["samples"]) > 8
    assert "8" in [m["id"] for m in fitted["samples"]]
    assert [int(m["id"]) for m in fitted["samples"]] == list(
        range(offset, offset + len(fitted["samples"]))
    )
