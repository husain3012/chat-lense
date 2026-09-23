"""Source references and quantitative narration are checked, not semantic truth."""

import re
import unicodedata
from app.schemas.report import Insight, Fact

BANNED = re.compile(
    r"\b(narcissis\w*|obsessed|cheater|emotionally unavailable|psychopath\w*)\b",
    re.I,
)
NUM = re.compile(r"(?<![\w])\d+(?:[.,]\d+)*(?:%|×)?")
QUOTE = re.compile(r'[“"]([^“”"]{8,})[”"]')
UNIVERSAL = re.compile(r"\b(every|always|never|each day|ensures no)\b", re.I)


def contextual(text):
    # Compatibility for old mocked/provider prose. No whitespace-based language gate.
    return bool(QUOTE.search(text)) and not UNIVERSAL.search(QUOTE.sub("", text))


def filter_contextual(payload):
    return {
        **payload,
        "insights": [
            i
            for i in payload.get("insights", [])
            if i.get("source_quotes") or contextual(i["title"] + " " + i["description"])
        ],
    }


def exact_quote(quote, source):
    return unicodedata.normalize("NFC", quote) in unicodedata.normalize("NFC", source)


def words(text):
    return set(re.findall(r"\w{4,}", text.casefold()))


def validate(output, packet, report):
    samples = {m["id"]: m for m in packet["samples"]}
    facts = packet["measured_findings"]
    valid = []
    rejected = 0
    families = set()
    existing = [words(i.title + " " + i.description) for i in report.insights]
    for item in output.insights:
        citations = list(dict.fromkeys(item.evidence_ids))
        if (
            len(citations) < 2
            or any(mid not in samples for mid in citations)
            or any(fid not in facts for fid in item.fact_ids)
        ):
            rejected += 1
            continue
        text = item.title + " " + item.description
        if BANNED.search(text) or (not item.quotes and not contextual(text)):
            rejected += 1
            continue
        if any(
            not any(exact_quote(quote, samples[mid]["text"]) for mid in citations)
            for quote in QUOTE.findall(text)
        ):
            rejected += 1
            continue
        if any(
            q.message_id not in citations
            or not exact_quote(q.text, samples[q.message_id]["text"])
            for q in item.quotes
        ):
            rejected += 1
            continue
        if item.moment_kind in ("repair", "tension") and (
            len(citations) < 3
            or len({samples[mid].get("window", 0) for mid in citations}) > 1
        ):
            rejected += 1
            continue
        source_quotes = []
        names = {p["id"]: p["name"] for p in packet["participants"]}
        for q in item.quotes:
            sample = samples[q.message_id]
            source_quotes.append(
                {
                    "message_id": q.message_id,
                    "text": q.text,
                    "sender_name": names.get(sample["sender_id"], "Participant"),
                    "sender_id": sample["sender_id"],
                    "timestamp": sample["timestamp"],
                }
            )
        bound = [f for fid in item.fact_ids for f in facts[fid]["facts"]]
        # A correct number attached to the wrong actor is still a false claim.
        # Keep numerical narration in deterministic cards; AI can quote source
        # text and attach trusted facts separately, but cannot rewrite statistics.
        if NUM.search(QUOTE.sub("", text)):
            rejected += 1
            continue
        key = item.family.casefold().strip()
        lex = words(text)
        if key in families or any(
            len(lex & other) / max(1, min(len(lex), len(other))) > 0.65
            for other in existing
        ):
            rejected += 1
            continue
        families.add(key)
        existing.append(lex)
        valid.append(
            Insight(
                id="ai-" + str(len(valid) + 1),
                family="ai:" + key,
                category=item.category,
                section=item.section,
                title=item.title,
                description=item.description,
                value="Interpretation",
                label="Gemini · grounded in sampled messages",
                facts=[Fact(**f) for f in bound][:8],
                evidence_ids=citations,
                evidence_total=len(citations),
                method="Gemini interpretation of a bounded sample. Message IDs and quotations were checked. Numerical narration is reserved for deterministic findings; those checks do not independently prove the interpretation.",
                caveat=item.caveat
                or "Interpretation from sampled evidence, not a claim about motives.",
                score=item.novelty,
                interpretation=True,
                source="ai",
                moment_kind=item.moment_kind,
                source_quotes=source_quotes,
                visual_type="none",
            )
        )
    return valid, rejected
