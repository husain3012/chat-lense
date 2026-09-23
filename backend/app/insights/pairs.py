from collections import Counter, defaultdict
from app.insights.candidates import pct, winner


def discover(c, out):
    if c.kind != "group":
        return
    replies = defaultdict(list)
    reactions = defaultdict(list)
    for a, b in c.explicit:
        replies[tuple(sorted([a.sender_id, b.sender_id]))].append((a, b))
    for p, o, e in c.reaction_events:
        if p != o.sender_id:
            reactions[tuple(sorted([p, o.sender_id]))].append((p, o))
    seen = set()
    for key, groups, fun, plain, threshold in [
        (
            "reply",
            replies,
            "The back-and-forth duo",
            "Most explicit replies exchanged",
            3,
        ),
        (
            "reaction",
            reactions,
            "The mutual applause society",
            "Most reactions exchanged",
            3,
        ),
    ]:
        win = winner({pair: len(v) for pair, v in groups.items()}, threshold)
        if not win:
            continue
        pair, count = win
        seen.add((key, pair))
        total = sum(map(len, groups.values()))
        a, b = pair
        evidence = [
            o
            for entry in groups[pair]
            for o in (entry if key == "reply" else [entry[1]])
        ]
        forward = (
            sum(entry[1].sender_id == a for entry in groups[pair])
            if key == "reply"
            else sum(entry[0] == a for entry in groups[pair])
        )
        if min(forward, count - forward) == 0:
            fun = (
                "The reaction connection"
                if key == "reaction"
                else "The reply connection"
            )
        out.add(
            "pair-" + key,
            "Pair dynamics",
            fun,
            plain,
            f"{c.name(a)} ↔ {c.name(b)} account for {count} {'explicit replies' if key == 'reply' else 'identifiable reactions'}, {pct(count, total):.0f}% of all {'explicit replies' if key == 'reply' else 'identifiable cross-participant reactions'} in this export.",
            str(count),
            "exchanges",
            evidence,
            facts=[("Exchanges", count, "events"), ("Share", pct(count, total), "%")],
            visual=[
                (c.name(a) + " → " + c.name(b), forward),
                (c.name(b) + " → " + c.name(a), count - forward),
            ],
            method="Undirected pair totals from explicit reply links or identifiable reaction actors. Co-occurrence does not count. Tied leads are omitted.",
            section="pairs",
            score=5,
            pids=list(pair),
        )
    night = defaultdict(list)
    for a, b in c.explicit:
        if c.late(b):
            night[tuple(sorted([a.sender_id, b.sender_id]))].append((a, b))
    win = winner({pair: len(v) for pair, v in night.items()}, 3)
    if win:
        pair, count = win
        all_count = len(replies[pair])
        share = pct(count, all_count)
        baseline = pct(sum(map(len, night.values())), len(c.explicit))
        if share >= baseline + 15:
            out.add(
                "pair-night",
                "Pair dynamics",
                "After-hours connection",
                "Late-night reply concentration",
                f"{share:.0f}% of {c.name(pair[0])} ↔ {c.name(pair[1])}’s explicit exchanges happen after 23:00 or before 05:00. The group baseline is {baseline:.0f}%.",
                f"{share:.0f}%",
                "pair exchanges at night",
                [o for pair_ in night[pair] for o in pair_],
                facts=[
                    ("Pair late share", share, "%"),
                    ("Group late share", baseline, "%"),
                ],
                visual=[("This pair", share), ("All pairs", baseline)],
                method="Time of the replying message defines night; requires three late exchanges and a 15-point difference from the group.",
                section="pairs",
                score=5,
                pids=list(pair),
            )
    balanced = []
    for pair, events in replies.items():
        if len(events) < 6:
            continue
        directions = Counter(b.sender_id for a, b in events)
        balance = min(directions.get(p, 0) for p in pair) / len(events)
        if balance >= 0.4:
            balanced.append((balance, len(events), pair))
    if balanced:
        balanced.sort(reverse=True)
        if len(balanced) == 1 or balanced[0][:2] != balanced[1][:2]:
            balance, count, pair = balanced[0]
            if ("reply", pair) not in seen:
                out.add(
                    "pair-balance",
                    "Pair dynamics",
                    "A two-way street",
                    "Balanced explicit exchange",
                    f"{c.name(pair[0])} ↔ {c.name(pair[1])} split their {count} explicit replies almost evenly: {balance * 100:.0f}% in one direction and {(1 - balance) * 100:.0f}% in the other.",
                    f"{balance * 100:.0f}/{(1 - balance) * 100:.0f}",
                    "reply split",
                    [o for entry in replies[pair] for o in entry],
                    facts=[
                        ("Smaller-direction share", balance * 100, "%"),
                        ("Replies", count, "replies"),
                    ],
                    visual=[
                        (
                            c.name(pair[0]),
                            sum(b.sender_id == pair[0] for a, b in replies[pair]),
                        ),
                        (
                            c.name(pair[1]),
                            sum(b.sender_id == pair[1] for a, b in replies[pair]),
                        ),
                    ],
                    method="At least six explicit replies; both directions contribute at least 40%. This is reciprocity of recorded replies, not a relationship assessment.",
                    section="pairs",
                    score=4,
                    pids=list(pair),
                )
