from collections import Counter
from app.analytics.interactions import resolver


def calculate(messages, participants, available):
    if not available:
        return None
    aliases = resolver(participants)
    given, received, common = Counter(), Counter(), Counter()
    for m in messages:
        for r in m.reactions:
            count = r.get("count", 1)
            common[r.get("emoji", "?")] += count
            if m.sender_id:
                received[m.sender_id] += count
            for actor in r.get("actors", []):
                if str(actor) in aliases:
                    given[aliases[str(actor)]] += 1
    return {
        "total": sum(common.values()),
        "given": given,
        "received": received,
        "common": dict(common.most_common()),
        "note": "Given counts include only identifiable actors exposed by the export.",
    }
