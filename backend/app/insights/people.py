from collections import Counter, defaultdict
from statistics import mean, median
from app.insights.candidates import pct, fmt, span, winner
from app.insights.context import MEDIA


def discover(c, out):
    if len(c.obs) < 6:
        return
    n = len(c.obs)
    session_n = len(c.sessions)
    most = winner({p: len(v) for p, v in c.own.items()}, 3)
    if most and session_n >= 3:
        pid, count = most
        start = c.starts[pid]
        if start and pct(count, n) >= 30 and pct(start, session_n) >= 30:
            share = pct(count, n)
            initiations = pct(start, session_n)
            out.add(
                "conversation-engine",
                "Communication dynamics",
                "The chat’s ignition key",
                "Message share and session initiation",
                f"{c.name(pid)} contributes {share:.0f}% of participant messages and starts {initiations:.0f}% of sessions. Two different measures point to the same conversation engine.",
                f"{share:.0f}%",
                "of messages · plus the starts",
                c.own[pid],
                facts=[
                    ("Message share", share, "%"),
                    ("Session-start share", initiations, "%"),
                ],
                visual=[("Messages", share), ("Session starts", initiations)],
                method="Combines message contribution with first-participant session initiation. The label describes recorded behavior, not responsibility or motive.",
                score=7,
                pids=[pid],
                multi=True,
            )
    revived = Counter(b.sender_id for a, b in c.revivals)
    leader = winner(revived, 2)
    if leader and len(c.revivals) >= 3:
        pid, count = leader
        out.add(
            "revival-specialist",
            "Conversation revival",
            "Chat resurrection specialist",
            "Starts after long silences",
            f"After at least {max(8, c.gap / 3600):g} hours of silence, {c.name(pid)} sends the first message back {count} times—{pct(count, len(c.revivals)):.0f}% of recorded comebacks.",
            f"{pct(count, len(c.revivals)):.0f}%",
            "of long-silence comebacks",
            [o for pair in c.revivals if pair[1].sender_id == pid for o in pair],
            facts=[
                ("Revivals", count, "sessions"),
                ("All revivals", len(c.revivals), "sessions"),
            ],
            visual=[(c.name(p), v) for p, v in revived.most_common()],
            method=f"First participant message after a gap of at least {max(8, c.gap / 3600):g} hours; initial message in the export is excluded.",
            score=6,
            pids=[pid],
        )
    # Distinctive style cards: compare rates, not just whoever sends the most.
    styles = [
        (
            "length",
            "Essay energy",
            "Long-form writer",
            lambda v: (
                mean([o.length for o in v if o.source.message_type == "text"])
                if any(o.source.message_type == "text" for o in v)
                else 0
            ),
            lambda o: o.source.message_type == "text",
            "characters / text message",
            10,
        ),
        (
            "questions",
            "The question asker",
            "Question asker",
            lambda v: pct(sum(o.questions for o in v), len(v)),
            lambda o: o.questions,
            "% of messages contain a question mark",
            3,
        ),
        (
            "short",
            "Small words, big presence",
            "One-word writer",
            lambda v: pct(
                sum(len(o.words) == 1 for o in v), sum(bool(o.words) for o in v)
            ),
            lambda o: len(o.words) == 1,
            "% of word-bearing messages use one word",
            3,
        ),
        (
            "night",
            "Night owl mode",
            "Night owl",
            lambda v: pct(sum(c.late(o) for o in v), len(v)),
            c.late,
            "% of messages sent from 23:00 to 04:59",
            3,
        ),
        (
            "links",
            "The link dropper",
            "Link sharer",
            lambda v: pct(sum(o.links > 0 for o in v), len(v)),
            lambda o: o.links > 0,
            "% of messages contain a URL",
            2,
        ),
        (
            "media",
            "Camera-roll correspondent",
            "Media sharer",
            lambda v: pct(sum(o.source.message_type in MEDIA for o in v), len(v)),
            lambda o: o.source.message_type in MEDIA,
            "% of messages are media",
            2,
        ),
        (
            "emoji",
            "Emoji punctuation",
            "Emoji enthusiast",
            lambda v: pct(sum(o.emoji for o in v), len(v)),
            lambda o: o.emoji,
            "% of text/media records contain an emoji-like symbol in text",
            3,
        ),
    ]
    if not any(i.id == "conversation-engine" for i in out.items):
        starts = {s[0].id for s in c.sessions}
        styles.append(
            (
                "opener",
                "Conversation starter",
                "Session opener",
                lambda v: pct(sum(o.id in starts for o in v), len(v)),
                lambda o: o.id in starts,
                "% of messages open a detected session",
                3,
            )
        )
    options = []
    for key, fun, plain, fn, predicate, unit, minimum in styles:
        baseline = fn(c.obs)
        for pid, items in c.own.items():
            if len(items) < 5:
                continue
            support = [o for o in items if predicate(o)]
            rate = fn(items)
            peers = [o for o in c.obs if o.sender_id != pid]
            peer = fn(peers)
            ratio = rate / peer if peer else (2 if rate else 0)
            if (
                not support
                or (key != "length" and len(support) < minimum)
                or rate < baseline * 1.05
            ):
                continue
            options.append(
                (ratio, len(support), pid, key, fun, plain, rate, peer, unit, support)
            )
    chosen_people = set()
    chosen_styles = set()
    for ratio, _, pid, key, fun, plain, rate, peer, unit, support in sorted(
        options, key=lambda x: (-x[0], -x[1], x[2], x[3])
    ):
        if pid in chosen_people or key in chosen_styles:
            continue
        chosen_people.add(pid)
        chosen_styles.add(key)
        if key == "length":
            text = f"{c.name(pid)} averages {rate:.0f} characters per text message; everyone else averages {peer:.0f}. A little more room for the details."
            value = f"{rate:.0f}"
            label = "characters per text message"
        else:
            text = f"{rate:.0f}{unit.split(' of')[0]} of {c.name(pid)}’s messages fit this habit, compared with {peer:.0f}% for everyone else. {len(support)} recorded examples back it up."
            if key == "short":
                text = f"{rate:.0f}% of {c.name(pid)}’s word-bearing messages are just one word, compared with {peer:.0f}% for everyone else."
            value = f"{rate:.0f}%"
            label = unit.removeprefix("% of ")
        out.add(
            "style-" + key,
            "Communication style",
            fun,
            plain,
            text,
            value,
            label,
            support,
            facts=[
                ("Participant rate", rate, "chars" if key == "length" else "%"),
                ("Other participants", peer, "chars" if key == "length" else "%"),
            ],
            visual=[(c.name(pid), rate), ("Everyone else", peer)],
            method="Rate within participant messages compared with all other participants. One-word detection uses Unicode word tokens; emoji detection is a symbol-range heuristic.",
            section="participants",
            score=3 + min(ratio, 5),
            pids=[pid],
        )
    # Bursts are a separate structural behavior from message-length cards.
    if len(c.bursts) >= 3:
        counts = Counter(r[0].sender_id for r in c.bursts)
        w = winner(counts, 2)
        if w:
            pid, count = w
            own = [r for r in c.bursts if r[0].sender_id == pid]
            out.add(
                "burst-habit",
                "Burst messaging",
                "Sent in instalments",
                "Rapid consecutive-message runs",
                f"{c.name(pid)} sends {count} bursts of at least three consecutive messages within two minutes. Their typical burst contains {median([len(r) for r in own]):.0f} messages.",
                str(count),
                "rapid-fire bursts",
                [o for r in own for o in r],
                facts=[
                    ("Bursts", count, "bursts"),
                    ("Median burst", median([len(r) for r in own]), "messages"),
                ],
                visual=[(c.name(p), v) for p, v in counts.most_common()],
                method="Maximal same-sender runs, bounded by session gaps; at least three messages and the entire run spans at most 120 seconds.",
                score=5,
                pids=[pid],
            )
    if c.kind == "direct":
        turns = Counter(r[0].sender_id for r in c.runs)
        followups = Counter(r[0].sender_id for r in c.runs if len(r) >= 2)
        rates = {
            p: pct(followups[p], count) for p, count in turns.items() if count >= 5
        }
        w = winner(rates)
        if w and len(rates) == 2 and max(rates.values()) - min(rates.values()) >= 15:
            pid, rate = w
            out.add(
                "followup-habit",
                "Reply patterns",
                "The double-text habit",
                "Consecutive follow-up turns",
                f"{c.name(pid)} sends another message before the other person speaks in {rate:.0f}% of their turns. The other participant does so in {min(rates.values()):.0f}%.",
                f"{rate:.0f}%",
                "turns contain a follow-up",
                [o for r in c.runs if r[0].sender_id == pid and len(r) >= 2 for o in r],
                facts=[
                    ("Follow-up turn share", rate, "%"),
                    ("Other participant", min(rates.values()), "%"),
                ],
                visual=[(c.name(p), v) for p, v in rates.items()],
                method="Two or more consecutive messages within a session constitute a follow-up turn. This does not establish whether a response was expected.",
                score=5,
                pids=[pid],
            )
    by_responder = defaultdict(list)
    by_recipient = defaultdict(list)
    for a, b, seconds in c.responses:
        by_responder[b.sender_id].append((a, b, seconds))
        by_recipient[a.sender_id].append((a, b, seconds))
    eligible = {
        p: median(x[2] for x in items)
        for p, items in by_responder.items()
        if len(items) >= 5
    }
    if (
        len(eligible) >= 2
        and max(eligible.values()) > max(1, min(eligible.values())) * 2
    ):
        fast = min(eligible, key=eligible.get)
        slow = max(eligible, key=eligible.get)
        slow_replies = [b for a, b, t in by_responder[slow]]
        fast_replies = [b for a, b, t in by_responder[fast]]
        length_s = c.average(slow_replies)
        length_f = c.average(fast_replies)
        multi = length_s >= length_f * 1.4 and length_f > 0
        text = f"{c.name(slow)}’s median response is {span(eligible[slow])}; {c.name(fast)}’s is {span(eligible[fast])}."
        if multi:
            text += f" But {c.name(slow)}’s responses average {length_s:.0f} characters versus {length_f:.0f}—a slower pace with more words."
        out.add(
            "response-speed-gap",
            "Reply patterns",
            "The slow-burn reply" if multi else "Different reply gears",
            "Response time comparison",
            text,
            span(eligible[slow]),
            "slower median response",
            [o for p in [fast, slow] for a, b, t in by_responder[p] for o in [a, b]],
            facts=[
                ("Slower median", eligible[slow], "seconds"),
                ("Faster median", eligible[fast], "seconds"),
            ]
            + (
                [
                    ("Slower responder length", length_s, "characters"),
                    ("Faster responder length", length_f, "characters"),
                ]
                if multi
                else []
            ),
            visual=[(c.name(p), v) for p, v in eligible.items()],
            method="At least five observed responses per participant; group responses require explicit reply links. Gaps above the session threshold excluded.",
            score=7 if multi else 5,
            pids=[slow, fast],
            multi=multi,
        )
    if c.kind == "group" and not any(i.id == "response-speed-gap" for i in out.items):
        received_times = {
            pid: median(t for _, _, t in rows)
            for pid, rows in by_recipient.items()
            if len(rows) >= 5
        }
        ordered = sorted(received_times.items(), key=lambda item: (item[1], item[0]))
        if len(ordered) >= 2 and ordered[0][1] < ordered[1][1]:
            pid, speed = ordered[0]
            baseline = median(t for _, _, t in c.responses)
            if baseline > 0 and speed <= baseline * 0.6:
                out.add(
                    "fastest-received",
                    "Reply patterns",
                    "The fast lane",
                    "Quickly answered messages",
                    f"Explicit replies to {c.name(pid)} arrive in a median of {span(speed)}, compared with {span(baseline)} across the group’s observed replies.",
                    span(speed),
                    "median time until an explicit reply",
                    [o for a, b, t in by_recipient[pid] for o in (a, b)],
                    facts=[
                        ("Median received response", speed, "seconds"),
                        ("All observed responses", baseline, "seconds"),
                    ],
                    visual=[(c.name(p), t) for p, t in received_times.items()],
                    method="Time from the source message to each explicit reply within the session threshold. At least five responses per compared participant; tied leads omitted. Reflects export timestamp resolution.",
                    score=5,
                    pids=[pid],
                )
    # Awards use metrics not already used for ranked findings or style cards.
    if c.kind == "group":
        award_specs = [
            (
                "morning",
                "First light regular",
                "Most early-morning messages",
                {
                    p: sum(5 <= o.time.hour < 9 for o in items)
                    for p, items in c.own.items()
                },
                lambda p: [o for o in c.own[p] if 5 <= o.time.hour < 9],
                "Messages sent between 05:00 and 08:59 in the selected timezone.",
            ),
            (
                "closer",
                "The final word",
                "Most session endings",
                dict(c.ends),
                lambda p: [s[-1] for s in c.sessions if s[-1].sender_id == p],
                "Last participant message in each detected session; not proof that the person deliberately ended it.",
            ),
            (
                "consecutive",
                "The uninterrupted run",
                "Longest consecutive-message run",
                {
                    p: max([len(r) for r in c.runs if r[0].sender_id == p], default=0)
                    for p in c.own
                },
                lambda p: max([r for r in c.runs if r[0].sender_id == p], key=len),
                "Largest same-sender run with no intervening participant; bounded by the session threshold.",
            ),
            (
                "late-starts",
                "The midnight opener",
                "Most late-night session starts",
                dict(Counter(s[0].sender_id for s in c.sessions if c.late(s[0]))),
                lambda p: [
                    s[0] for s in c.sessions if s[0].sender_id == p and c.late(s[0])
                ],
                "Sessions whose first participant message falls between 23:00 and 04:59.",
            ),
        ]
        for key, fun, plain, values, evidence, method in award_specs:
            w = winner(values, 2)
            if not w:
                continue
            pid, value = w
            out.add(
                "award-" + key,
                "Superlatives",
                fun,
                plain,
                f"{c.name(pid)} leads this measure with {value:g}.",
                fmt(value),
                plain.lower(),
                evidence(pid),
                facts=[(plain, value, "count")],
                visual=[
                    (c.name(p), v)
                    for p, v in sorted(values.items(), key=lambda x: -x[1])[:8]
                ],
                method=method + " A tied lead is not awarded.",
                section="superlatives",
                score=2,
                pids=[pid],
            )
    if c.metadata.get("reactions_available") and c.reaction_events:
        given = Counter(p for p, o, e in c.reaction_events)
        received = c.reaction_received
        if c.kind == "group" and not c.unknown_reactors:
            w = winner(given, 3)
            if w:
                pid, value = w
                out.add(
                    "award-reactions-given",
                    "Superlatives",
                    "The applause department",
                    "Most reactions given",
                    f"{c.name(pid)} gives {value} recorded reactions. A different way of showing up in the conversation.",
                    str(value),
                    "recorded reactions given",
                    [o for p, o, e in c.reaction_events if p == pid],
                    facts=[("Reactions given", value, "reactions")],
                    visual=[(c.name(p), v) for p, v in given.most_common()],
                    method="Counts exposed reaction actors. Award suppressed when any reaction actors are unknown; counts are not read receipts.",
                    section="superlatives",
                    score=3,
                    pids=[pid],
                )
        w = winner(received, 3)
        if w:
            pid, value = w
            out.add(
                "reaction-magnet",
                "Reactions",
                "That landed",
                "Most reactions received",
                f"{c.name(pid)}’s messages collect {value} reactions, {pct(value, c.reaction_total):.0f}% of the exported total.",
                str(value),
                "reactions received",
                [o for o in c.own[pid] if o.source.reactions],
                facts=[
                    ("Received", value, "reactions"),
                    ("Share", pct(value, c.reaction_total), "%"),
                ],
                visual=[(c.name(p), v) for p, v in received.most_common()],
                method="Uses exported aggregate reaction counts on messages. It does not infer agreement, sentiment or popularity beyond these counts.",
                score=4,
                pids=[pid],
            )
        for pid, count in given.items():
            replies = sum(b.sender_id == pid for a, b in c.explicit)
            if count >= 5 and replies >= 2 and count >= 2 * replies:
                out.add(
                    "reaction-reply-" + pid,
                    "Reactions",
                    "Reaction mode",
                    "Reactions versus explicit replies",
                    f"{c.name(pid)} gives {count} known reactions versus {replies} explicit replies—{count / replies:.1f}× as many reactions. Unthreaded messages are not counted as replies here.",
                    f"{count / replies:.1f}×",
                    "reactions / explicit replies",
                    [o for p, o, e in c.reaction_events if p == pid],
                    facts=[
                        ("Known reactions", count, "reactions"),
                        ("Explicit replies", replies, "replies"),
                    ],
                    visual=[("Reactions", count), ("Explicit replies", replies)],
                    method="Compares identifiable reaction events with explicit reply links only; no claim about reaction-only days or reading activity.",
                    score=4,
                    pids=[pid],
                )
