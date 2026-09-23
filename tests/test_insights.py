from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta, timezone
from app.parsers.telegram import TelegramParser
from app.parsers.whatsapp import WhatsAppParser
from app.insights.engine import build_report
from app.insights.context import Context
from app.insights.candidates import winner
from app.schemas.chat import ParsedConversation, Message
from app.synthesis.packet import (
    build_packet,
    partitions,
    MAX_MESSAGES,
    MAX_TEXT,
    MAX_PACKET_BYTES,
)
from app.synthesis.contracts import SynthesisOutput, Interpretation
from app.synthesis.validation import validate
import json

ROOT = Path(__file__).resolve().parents[1]


def story():
    return TelegramParser().parse(ROOT / "examples/telegram_story_group.json")[0]


def report_for(c, **kwargs):
    return build_report(c.messages, c.participants, c, **kwargs)


def test_report_acceptance():
    c = story()
    r = report_for(c)
    sections = Counter(i.section for i in r.insights)
    assert len(r.insights) >= 20
    assert sections["top"] >= 5
    assert sections["micro"] >= 5
    assert sections["participants"] >= 3
    assert sections["superlatives"] >= 2
    assert sections["pairs"] >= 2
    assert len(r.timeline) >= 6
    assert any(i.interpretation and len(i.facts) >= 2 for i in r.insights)
    assert len({i.family for i in r.insights}) == len(r.insights)
    ids = {m.id for m in c.messages}
    assert all(i.evidence_ids and set(i.evidence_ids) <= ids for i in r.insights)
    assert all(len(i.evidence_ids) <= 12 for i in r.insights)


def test_tones_preserve_measurements():
    c = story()
    fun = report_for(c)
    analytical = report_for(c, tone="analytical")
    assert fun.snapshot == analytical.snapshot
    assert {i.id: [f.model_dump() for f in i.facts] for i in fun.insights} == {
        i.id: [f.model_dump() for f in i.facts] for i in analytical.insights
    }
    assert fun.insights[0].title != analytical.insights[0].title


def test_ties_no_fabricated_winner():
    assert winner({"a": 10, "b": 10}) is None
    assert winner({"a": 0, "b": 0}) is None
    assert winner({"a": 3, "b": 2}) == ("a", 3)


def test_missing_group_links_are_not_inferred():
    c = WhatsAppParser().parse(ROOT / "examples/whatsapp_group.txt")[0]
    r = report_for(c)
    assert not any(i.section == "pairs" for i in r.insights)
    assert not any(i.id == "response-speed-gap" for i in r.insights)
    assert r.coverage["explicit_replies"] == 0
    assert not r.coverage["reaction_data_available"]


def test_empty_tiny_and_system_messages():
    c = ParsedConversation(platform="whatsapp", title="Empty").finalize()
    assert report_for(c).insights == []
    c.messages = [
        Message(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            text="System",
            message_type="system",
        )
    ]
    c.finalize()
    assert report_for(c).snapshot["messages"] == 0
    c.messages.append(
        Message(
            timestamp=datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
            text="Hello",
            sender_name="Alice",
        )
    )
    c.finalize()
    r = report_for(c)
    assert not any(
        i.section in ("participants", "pairs", "superlatives") for i in r.insights
    )


def test_revival_boundary_and_first_message():
    c = ParsedConversation(platform="telegram", title="Boundary")
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.messages = [
        Message(
            timestamp=t + timedelta(hours=h),
            sender_name="A" if n % 2 else "B",
            text="Hi",
        )
        for n, h in enumerate([0, 7.99, 16, 24])
    ]
    c.finalize()
    context = Context(c.messages, c.participants, "direct", {})
    assert len(context.revivals) == 2


def test_timezone_changes_habits_not_total():
    c = story()
    a = report_for(c)
    b = report_for(c, timezone_name="Asia/Kolkata")
    assert a.snapshot["messages"] == b.snapshot["messages"]
    assert a.timeline[0].late_share != b.timeline[0].late_share


def test_incomplete_months_not_compared():
    c = ParsedConversation(platform="whatsapp", title="Partial")
    t = datetime(2026, 1, 30, tzinfo=timezone.utc)
    c.messages = [
        Message(
            timestamp=t + timedelta(hours=i),
            sender_name="Alice" if i % 2 else "Sam",
            text="Hello",
        )
        for i in range(100)
    ]
    c.finalize()
    r = report_for(c)
    assert all(p.partial for p in r.timeline)
    assert not any(i.id.startswith("month-pace-") for i in r.insights)


def test_packet_bounded_and_stratified():
    c = story()
    r = report_for(c)
    packet = build_packet(r, c.messages, c.participants)
    assert len(packet["samples"]) <= MAX_MESSAGES
    assert len(json.dumps(packet, ensure_ascii=False).encode()) <= MAX_PACKET_BYTES
    assert all(len(m["text"]) <= MAX_TEXT for m in packet["samples"])
    assert len(partitions(packet)) <= 4
    assert len({m["timestamp"][:7] for m in packet["samples"]}) >= 6
    assert not any("api_key" in k.lower() for k in packet)


def test_synthesis_citation_number_and_duplicate_validation():
    c = story()
    r = report_for(c)
    packet = build_packet(r, c.messages, c.participants)
    quoted = next(m for m in packet["samples"] if len(m["text"].split()) >= 5)
    mids = [
        quoted["id"],
        next(m["id"] for m in packet["samples"] if m["id"] != quoted["id"]),
    ]
    base = dict(
        family="ritual-of-planning",
        title="Plans travel in links",
        description=f"The sampled planning exchange includes “{quoted['text'][:80]}”. This frames ideas as concrete proposals.",
        category="Topic habits",
        evidence_ids=mids,
        fact_ids=[],
        novelty=8,
        section="topics",
        caveat="Sampled examples only.",
    )
    valid = Interpretation(**base)
    bad_id = valid.model_copy(
        update={"family": "bad-id", "evidence_ids": ["invented", mids[0]]}
    )
    bad_number = valid.model_copy(
        update={
            "family": "bad-number",
            "description": "This happens in 9999999% of messages.",
        }
    )
    bad_quote = valid.model_copy(
        update={
            "family": "bad-quote",
            "description": "They say “a completely fabricated sentence”.",
        }
    )
    accepted, rejected = validate(
        SynthesisOutput(insights=[valid, bad_id, bad_number, bad_quote, valid]),
        packet,
        r,
    )
    assert len(accepted) == 1 and rejected == 4


def test_integer_float_parameters_have_identical_fingerprint():
    c = story()
    assert (
        report_for(c, gap_hours=4).fingerprint
        == report_for(c, gap_hours=4.0).fingerprint
    )


def test_dst_durations_use_elapsed_time():
    c = ParsedConversation(platform="telegram", title="DST")
    c.messages = [
        Message(
            timestamp=datetime(2026, 11, 1, 5, 55, tzinfo=timezone.utc),
            sender_name="A",
            text="Hi",
        ),
        Message(
            timestamp=datetime(2026, 11, 1, 6, 5, tzinfo=timezone.utc),
            sender_name="B",
            text="Hello",
        ),
    ]
    c.finalize()
    context = Context(
        c.messages, c.participants, "direct", {}, timezone_name="America/New_York"
    )
    assert context.responses[0][2] == 600
    assert len(context.peak_window()) == 2


def test_original_small_group_has_supported_diversity():
    c = WhatsAppParser().parse(ROOT / "examples/whatsapp_group.txt")[0]
    r = report_for(c)
    sections = Counter(i.section for i in r.insights)
    assert len(r.insights) >= 10
    assert sections["micro"] >= 5 and sections["participants"] >= 3
    assert sections["superlatives"] >= 1
    assert any(i.interpretation and len(i.facts) >= 2 for i in r.insights)
    assert sections["pairs"] == 0  # WhatsApp TXT cannot supply those links.


def test_uniform_data_does_not_fill_a_quota():
    c = ParsedConversation(platform="whatsapp", title="Uniform")
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.messages = [
        Message(
            timestamp=t + timedelta(minutes=i),
            sender_name="A" if i % 2 else "B",
            text="Same message",
        )
        for i in range(200)
    ]
    c.finalize()
    r = report_for(c)
    assert len(r.insights) < 15
    assert not any(i.section == "participants" for i in r.insights)


def test_peak_window_exact_boundary():
    c = ParsedConversation(platform="telegram", title="Peak")
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.messages = [
        Message(timestamp=t + timedelta(seconds=i), sender_name="A", text="Hi")
        for i in (0, 300, 600, 901)
    ]
    c.finalize()
    context = Context(c.messages, c.participants, "direct", {})
    assert len(context.peak_window()) == 3


def test_one_way_reactions_are_not_called_mutual_or_repeated():
    c = story()
    r = report_for(c)
    pair = next(i for i in r.insights if i.id == "pair-reaction")
    assert "mutual" not in pair.title.lower()
    assert min(v.value for v in pair.visual) == 0
    assert not any(
        i.id in ("reaction-magnet", "award-reactions-given") for i in r.insights
    )


def test_phrase_candidates_do_not_repeat_the_same_message_population():
    c = ParsedConversation(platform="telegram", title="Repeated language")
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.messages = [
        Message(
            timestamp=t + timedelta(days=i),
            sender_name="A",
            text="another lovely recommendation for movie night tonight everyone together",
        )
        for i in range(12)
    ]
    c.finalize()
    r = report_for(c)
    phrases = [i for i in r.insights if i.id.startswith("phrase-")]
    assert len(phrases) == 1
    assert "1 participant," in phrases[0].description


def test_ai_cannot_reassign_a_valid_number_to_the_wrong_person():
    c = story()
    r = report_for(c)
    packet = build_packet(r, c.messages, c.participants)
    reaction = next(i for i in r.insights if i.id == "pair-reaction")
    item = Interpretation(
        family="wrong-reaction-actor",
        title="Emotional glue",
        description="Mia gives 100% of the reactions to Rahul.",
        category="Reactions",
        evidence_ids=[m["id"] for m in packet["samples"][:2]],
        fact_ids=[reaction.id],
        novelty=8,
        caveat="Sampled",
    )
    accepted, rejected = validate(SynthesisOutput(insights=[item]), packet, r)
    assert not accepted and rejected == 1


def test_cached_interpretations_need_specific_context_without_universal_claims():
    from app.synthesis.validation import filter_contextual

    items = [
        {"title": "Generic", "description": "The group is busier on weekends."},
        {"title": "Overclaim", "description": "Every plan ends with “bring snacks”."},
        {
            "title": "Concrete",
            "description": "The sampled plans include “make room for a quiet break” alongside shared food.",
        },
    ]
    assert filter_contextual({"insights": items, "model": "test"})["insights"] == [
        items[2]
    ]
