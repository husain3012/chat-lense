import hashlib
from app.schemas.report import Report
from app.insights.context import Context
from app.insights.candidates import Candidates
from app.insights import habits, people, pairs, timeline, language

METHODS = [
    "The report is generated from measured candidates, ranked by contrast, size, supporting observations and independent signals. The ranking is editorial, not a statistical confidence score.",
    "Each finding has one canonical section and one metric-family ID. Small or uniform exports produce fewer findings; no quota is filled with invented behavior. Tied superlatives have no winner.",
    "Report habits exclude system messages. Text-style metrics exclude media placeholders. Existing raw-statistics totals may include system records.",
    "A session ends after a gap greater than the selected session threshold. The first/last participant message supplies the opener/closer. Revivals require at least 8 hours, or the session gap if longer.",
    "Direct response times use consecutive sender turns; group times and reply pairs require explicit source reply links. No visible reply does not mean ignored, and no messages does not mean someone was reading.",
    "Complete adjacent months, sufficient supporting messages and calendar-day normalization are required for change comparisons. First/last partial months remain visible without causal claims.",
    "New WhatsApp imports use the timezone explicitly chosen at import and store converted UTC timestamps. Older imports without a source timezone retain their original UTC wall-clock convention. Report habits use the report timezone.",
    "Emoji-like symbols, question marks, Unicode word tokens and literal phrases are deterministic lexical proxies. They do not establish sentiment, topic changes, psychological traits or inside-joke meaning.",
    "Evidence links show bounded examples from the underlying measurement, not its entire population. The method and supporting counts describe the population. Missing reaction actors suppress reaction-given awards.",
    "Gemini synthesis is optional and labelled as interpretation. Its evidence packet is sampled and bounded; citations are checked against supplied messages and numbers. Interpretations still deserve human review.",
]


def build_report(
    messages, participants, conversation, tone="fun", gap_hours=4, timezone_name="UTC"
):
    metadata = getattr(conversation, "extra", None)
    if metadata is None:
        metadata = getattr(conversation, "metadata", {})
    c = Context(
        messages,
        participants,
        conversation.conversation_type,
        metadata,
        gap_hours,
        timezone_name,
    )
    out = Candidates(c, tone)
    habits.discover(c, out)
    people.discover(c, out)
    pairs.discover(c, out)
    periods = timeline.discover(c, out)
    language.discover(c, out)
    findings = out.sorted()
    signature = "|".join(
        [
            conversation.id,
            str(len(messages)),
            tone,
            f"{float(gap_hours):g}",
            timezone_name,
            "2.0",
        ]
        + [f"{p.id}:{p.display_name}" for p in participants]
    )
    fingerprint = hashlib.sha256(signature.encode()).hexdigest()
    return Report(
        conversation_id=conversation.id,
        title=conversation.title,
        tone=tone,
        timezone=timezone_name,
        session_gap_hours=gap_hours,
        snapshot={
            "messages": len(c.obs),
            "all_records": len(messages),
            "participants": len(participants),
            "active_days": len(c.days),
            "sessions": len(c.sessions),
            "first": c.obs[0].time.isoformat() if c.obs else None,
            "last": c.obs[-1].time.isoformat() if c.obs else None,
        },
        insights=findings,
        timeline=periods,
        coverage={
            "explicit_replies": len(c.explicit),
            "known_reactions": len(c.reaction_events),
            "unknown_reaction_actors": c.unknown_reactors,
            "reaction_data_available": bool(metadata.get("reactions_available")),
            "eligible_findings": len(out.items),
            "shown_findings": len(findings),
            "small_sample": len(c.obs) < 100,
            "months": len(periods),
        },
        methodology=METHODS,
        fingerprint=fingerprint,
    )
