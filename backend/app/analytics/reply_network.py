"""Observed reply traffic, never a model of emotional closeness."""

from collections import Counter


def calculate(messages, participants):
    people = {p.id: p.display_name for p in participants}
    internal = {m.id: m for m in messages}
    external = {m.platform_message_id: m for m in messages if m.platform_message_id}
    edges = {}
    sent = Counter()
    total = 0
    for message in messages:
        if not message.reply_to_id or message.message_type == "system":
            continue
        target = external.get(message.reply_to_id) or internal.get(message.reply_to_id)
        if not target or target.id == message.id or target.message_type == "system":
            continue
        source, recipient = message.sender_id, target.sender_id
        if source not in people or recipient not in people or source == recipient:
            continue
        a, b = sorted((source, recipient))
        edge = edges.setdefault(
            (a, b),
            {
                "source": a,
                "target": b,
                "weight": 0,
                "forward": 0,
                "backward": 0,
                "evidence_ids": [],
            },
        )
        edge["weight"] += 1
        edge["forward" if source == a else "backward"] += 1
        for mid in (target.id, message.id):
            if mid not in edge["evidence_ids"] and len(edge["evidence_ids"]) < 8:
                edge["evidence_ids"].append(mid)
        sent[source] += 1
        total += 1
    if not total:
        return None
    return {
        "nodes": [
            {"id": pid, "name": name, "replies_sent": sent[pid]}
            for pid, name in people.items()
        ],
        "edges": sorted(
            edges.values(), key=lambda e: (-e["weight"], e["source"], e["target"])
        ),
        "total_replies": total,
        "method": "Line weight counts explicit replies between two participants in either direction. A reply is counted once; self-replies, missing targets, system events, mentions and reactions are excluded. Frequency measures observed exchange, not emotional closeness.",
    }
