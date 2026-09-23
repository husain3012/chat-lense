from datetime import datetime, timedelta, timezone
from app.schemas.chat import ParsedConversation, Message
from app.insights.engine import build_report
from app.synthesis.packet import build_packet, compact_packet, partitions, MAX_MESSAGES
from app.synthesis.contracts import Interpretation, EvidenceQuote, SynthesisOutput
from app.synthesis.validation import validate


def multilingual():
    c = ParsedConversation(platform="whatsapp", title="Shared moments")
    texts = [
        ("A", "抱抱你 🫂"),
        ("B", "谢谢你 ❤️"),
        ("A", "मैं यहीं हूँ, आराम से बात करो।"),
        ("B", "تمہارا شکریہ، اب بہتر ہوں"),
        ("A", "ごめんね"),
        ("B", "大丈夫、一緒に話そう"),
    ]
    c.messages = [
        Message(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i),
            sender_name=name,
            text=text,
        )
        for i, (name, text) in enumerate(texts)
    ]
    c.finalize()
    r = build_report(c.messages, c.participants, c)
    return c, r, build_packet(r, c.messages, c.participants)


def test_original_scripts_and_short_quotes_are_preserved():
    c, r, packet = multilingual()
    compact, reverse = compact_packet(packet)
    assert [row[3] for row in compact["messages"]] == [m.text for m in c.messages]
    assert reverse["m0"] == c.messages[0].id
    item = Interpretation(
        family="comfort",
        title="A little hug through the screen",
        description="A offers comfort and B responds with thanks.",
        category="Care",
        moment_kind="sweet",
        evidence_ids=[m.id for m in c.messages[:2]],
        quotes=[EvidenceQuote(message_id=c.messages[0].id, text="抱抱你 🫂")],
        novelty=8,
        caveat="A reading of this exchange.",
    )
    valid, rejected = validate(SynthesisOutput(insights=[item]), packet, r)
    assert rejected == 0 and valid[0].source_quotes[0]["text"] == "抱抱你 🫂"
    assert valid[0].source_quotes[0]["sender_name"] == "A"
    item.quotes[0].text = "我爱你"
    assert validate(SynthesisOutput(insights=[item]), packet, r)[1] == 1


def test_repair_needs_a_sequence_not_an_isolated_apology():
    c, r, packet = multilingual()
    item = Interpretation(
        family="repair",
        title="Talking it through",
        description="They acknowledge the hurt and talk.",
        category="Repair",
        moment_kind="repair",
        evidence_ids=[m.id for m in c.messages[:2]],
        quotes=[EvidenceQuote(message_id=c.messages[0].id, text="抱抱你")],
        novelty=8,
        caveat="Only the visible exchange.",
    )
    assert validate(SynthesisOutput(insights=[item]), packet, r)[1] == 1


def test_long_history_uses_contiguous_context_and_overlapping_partitions():
    c = ParsedConversation(platform="telegram", title="Long history")
    c.messages = [
        Message(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i),
            sender_name="A" if i % 2 else "B",
            text=f"你好 🫶 {i}",
        )
        for i in range(4000)
    ]
    c.finalize()
    r = build_report(c.messages, c.participants, c)
    packet = build_packet(r, c.messages, c.participants)
    samples = packet["samples"]
    assert len(samples) <= MAX_MESSAGES
    assert (
        samples[0]["id"] == c.messages[0].id and samples[-1]["id"] == c.messages[-1].id
    )
    assert (
        max(
            sum(m["window"] == w for m in samples)
            for w in {m["window"] for m in samples}
        )
        >= 60
    )
    chunks = partitions(packet)
    assert len(chunks) <= 4
    assert set(m["id"] for m in chunks[0]["samples"]) & set(
        m["id"] for m in chunks[1]["samples"]
    )
