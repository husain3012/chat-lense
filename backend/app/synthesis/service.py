from datetime import datetime, timezone
from app.synthesis import gemini
from app.synthesis.packet import partitions
from app.synthesis.prompts import MAP_TASK, REDUCE_TASK
from app.synthesis.validation import validate

PROMPT_VERSION = "2026-09-relationship-v4"


def synthesize(report, packet, provider=None):
    provider = provider or gemini.generate
    mapped = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    calls = 0
    rejected = 0
    for partition in partitions(packet):
        result, tokens = provider(MAP_TASK, partition)
        calls += 1
        accepted, dropped = validate(result, partition, report)
        rejected += dropped
        mapped.extend(sorted(accepted, key=lambda i: -i.score)[:6])
        for key in usage:
            usage[key] += tokens.get(key, 0)
    if not mapped:
        return {
            "insights": [],
            "model": gemini.config()["model"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "coverage": packet["coverage"],
            "calls": calls,
            "usage": usage,
            "rejected_candidates": rejected,
            "note": "No moments had enough context to keep this time. Your local discoveries are still here.",
        }
    combined = {
        **packet,
        "window_candidates": [i.model_dump(exclude={"score"}) for i in mapped],
    }
    result, tokens = provider(REDUCE_TASK, combined)
    calls += 1
    accepted, dropped = validate(result, packet, report)
    rejected += dropped
    for key in usage:
        usage[key] += tokens.get(key, 0)
    return {
        "insights": [
            i.model_dump() for i in sorted(accepted, key=lambda i: -i.score)[:16]
        ],
        "model": gemini.config()["model"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "coverage": packet["coverage"],
        "calls": calls,
        "usage": usage,
        "rejected_candidates": rejected,
        "note": "A reading of your shared moments, with the original messages a tap away.",
    }
