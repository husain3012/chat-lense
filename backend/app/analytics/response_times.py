from collections import defaultdict
from statistics import mean, median


def percentile(values, p):
    values = sorted(values)
    position = (len(values) - 1) * p
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)


def calculate(messages, conversation_type, gap_seconds):
    durations = defaultdict(list)
    previous = None
    by_id = {m.platform_message_id: m for m in messages if m.platform_message_id}
    for m in messages:
        if not m.sender_id or m.message_type == "system":
            continue
        target = previous if conversation_type == "direct" else by_id.get(m.reply_to_id)
        if (
            target
            and target.sender_id
            and target.sender_id != m.sender_id
            and target.message_type != "system"
        ):
            gap = (m.timestamp - target.timestamp).total_seconds()
            if 0 <= gap <= gap_seconds:
                durations[m.sender_id].append(gap)
        previous = m
    return {
        p: {
            "count": len(v),
            "median": median(v),
            "mean": mean(v),
            "p25": percentile(v, 0.25),
            "p75": percentile(v, 0.75),
            "p90": percentile(v, 0.9),
        }
        for p, v in durations.items()
    }
