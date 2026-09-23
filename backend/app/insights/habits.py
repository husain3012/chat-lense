from collections import Counter
from datetime import timedelta
from statistics import median
from app.insights.candidates import pct, span, winner, fmt

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def discover(c, out):
    if not c.obs:
        return
    n = len(c.obs)
    peak = max(c.days, key=lambda d: (len(c.days[d]), d))
    batch = c.days[peak]
    out.add(
        "day-peak",
        "Conversation peaks",
        "The day the chat caught fire",
        "Busiest recorded day",
        f"{peak:%d %b %Y} packed in {len(batch):,} messages—{len(batch) / (n / len(c.days)):.1f}× an average active day.",
        fmt(len(batch)),
        "messages in one day",
        batch,
        facts=[
            ("Messages", len(batch), "messages"),
            ("Typical active day", n / len(c.days), "messages"),
        ],
        visual=[("Busiest day", len(batch)), ("Average active day", n / len(c.days))],
        method="Largest message count on one local calendar day, compared with the mean across active days.",
        section="micro",
        score=2,
    )
    peak_hour = winner({h: len(v) for h, v in c.hours.items()})
    if peak_hour:
        h, count = peak_hour
        out.add(
            "hour-peak",
            "Timing habits",
            "Your unofficial office hours",
            "Most common message hour",
            f"{h:02}:00–{h:02}:59 is the chat’s busiest hour, collecting {pct(count, n):.1f}% of participant messages.",
            f"{h:02}:00",
            "peak messaging hour",
            c.hours[h],
            visual=[(f"{hour:02}:00", len(c.hours[hour])) for hour in range(24)],
            facts=[
                ("Messages in hour", count, "messages"),
                ("Share", pct(count, n), "%"),
            ],
            method="Counts participant messages by hour in the selected timezone. Tied peaks do not produce a winner.",
            section="micro",
        )
    dates = sorted(c.days)
    best = current = [dates[0]]
    for day in dates[1:]:
        current = current + [day] if day - current[-1] == timedelta(days=1) else [day]
        if len(current) > len(best):
            best = current
    if len(best) >= 2:
        own = [o for d in best for o in c.days[d]]
        out.add(
            "daily-streak",
            "Recurring rituals",
            "The streak was real",
            "Longest daily conversation streak",
            f"A message every day for {len(best)} days, from {best[0]:%d %b} to {best[-1]:%d %b %Y}.",
            str(len(best)),
            "days without a blank",
            own,
            facts=[("Consecutive active days", len(best), "days")],
            method="Consecutive local dates with at least one participant message, including weekends.",
            section="micro",
            score=2,
        )
    if len(c.obs) > 1:
        a, b = max(
            zip(c.obs, c.obs[1:]),
            key=lambda x: x[1].time.timestamp() - x[0].time.timestamp(),
        )
        seconds = b.time.timestamp() - a.time.timestamp()
        if seconds >= 3600:
            out.add(
                "longest-silence",
                "Quiet periods",
                "And then… radio silence",
                "Longest recorded silence",
                f"{span(seconds)} between messages. {c.name(b.sender_id)} sent the first message back on {b.time:%d %b %Y}.",
                span(seconds),
                "longest gap",
                [a, b],
                facts=[("Gap", seconds, "seconds")],
                method="Largest gap between consecutive participant messages. This says nothing about contact outside this export.",
                section="micro",
                score=2,
            )
    window = c.peak_window()
    if len(window) >= 3:
        out.add(
            "ten-minute-sprint",
            "Burst messaging",
            "Ten-minute tornado",
            "Densest ten-minute window",
            f"{len(window)} messages landed within ten minutes on {window[0].time:%d %b %Y}. {len({o.sender_id for o in window})} participants were in that sprint.",
            str(len(window)),
            "messages / 10 minutes",
            window,
            facts=[
                ("Messages", len(window), "messages"),
                ("Participants", len({o.sender_id for o in window}), "people"),
            ],
            method="Sliding window of at most 600 seconds; boundary-inclusive. Counts each message once in a window.",
            section="micro",
            score=3,
        )
    longest = max(
        c.sessions, key=lambda s: s[-1].time.timestamp() - s[0].time.timestamp()
    )
    seconds = longest[-1].time.timestamp() - longest[0].time.timestamp()
    if seconds > 0:
        out.add(
            "session-marathon",
            "Conversation momentum",
            "One more message…",
            "Longest session",
            f"The session starting {longest[0].time:%d %b, %H:%M} lasted {span(seconds)}, with {len(longest)} messages from {len({o.sender_id for o in longest})} participants.",
            span(seconds),
            "longest session",
            longest,
            facts=[
                ("Length", seconds, "seconds"),
                ("Messages", len(longest), "messages"),
            ],
            method=f"Elapsed time from first to last participant message in a session; gaps up to {c.gap / 3600:g} hours can occur inside it.",
            section="micro",
            score=2,
        )
    span_days = (dates[-1] - dates[0]).days + 1
    if span_days >= 14:
        exposure = Counter(
            (dates[0] + timedelta(days=i)).weekday() for i in range(span_days)
        )
        rates = {d: len(c.weekdays[d]) / exposure[d] for d in range(7) if exposure[d]}
        peak_day = winner(rates)
        if peak_day:
            d, rate = peak_day
            quiet = min(rates, key=rates.get)
            out.add(
                "weekday-rhythm",
                "Activity habits",
                "The weekly rhythm",
                "Weekday activity rhythm",
                f"{DAYS[d]} averages {rate:.1f} messages per calendar occurrence. {DAYS[quiet]} is the quiet end at {rates[quiet]:.1f}.",
                DAYS[d],
                "busiest weekday",
                c.weekdays[d],
                facts=[
                    ("Peak weekday average", rate, "messages/day"),
                    ("Quiet weekday average", rates[quiet], "messages/day"),
                ],
                visual=[(DAYS[d][:3], rates[d]) for d in sorted(rates)],
                method="Divides each weekday count by its number of calendar occurrences, including silent days; at least 14 days of coverage.",
                score=3,
            )
        weekend = sum(len(c.weekdays[d]) for d in [5, 6])
        weekday = n - weekend
        weekend_days = exposure[5] + exposure[6]
        weekday_days = span_days - weekend_days
        ratio = (
            (weekend / weekend_days) / (weekday / weekday_days)
            if weekday and weekday_days and weekend_days
            else 0
        )
        if ratio >= 1.5 or 0 < ratio <= 0.6:
            out.add(
                "weekend-switch",
                "Activity habits",
                "Weekend takeover" if ratio >= 1 else "The weekday club",
                "Weekend vs weekday pace",
                f"Weekend days average {weekend / weekend_days:.1f} messages, versus {weekday / weekday_days:.1f} on weekdays—{ratio:.2f}× the weekday pace.",
                f"{ratio:.2f}×",
                "weekend / weekday pace",
                [o for o in c.obs if o.time.weekday() >= 5],
                facts=[
                    ("Weekend rate", weekend / weekend_days, "messages/day"),
                    ("Weekday rate", weekday / weekday_days, "messages/day"),
                ],
                visual=[
                    ("Weekends", weekend / weekend_days),
                    ("Weekdays", weekday / weekday_days),
                ],
                method="Exposure-normalized calendar-day rates; silent days included. This does not infer work or social topics.",
                score=4 + abs(ratio - 1),
            )
    late = [s for s in c.sessions if c.late(s[0])]
    long = [
        s for s in c.sessions if len(s) >= max(5, median([len(s) for s in c.sessions]))
    ]
    nightlong = [s for s in long if c.late(s[0])]
    if len(long) >= 5 and nightlong and pct(len(nightlong), len(long)) >= 35:
        share = pct(len(nightlong), len(long))
        baseline = pct(len(late), len(c.sessions))
        out.add(
            "night-long-sessions",
            "Late-night behavior",
            "Night shift, extended edition",
            "Late starts among long sessions",
            f"{share:.0f}% of the longer sessions start between 23:00 and 04:59, compared with {baseline:.0f}% of all sessions.",
            f"{share:.0f}%",
            "of longer sessions start late",
            [o for s in nightlong for o in s],
            facts=[
                ("Long-session late-start share", share, "%"),
                ("All-session late-start share", baseline, "%"),
            ],
            visual=[("Long sessions", share), ("All sessions", baseline)],
            method="Long sessions have at least five messages and meet/exceed the median session message count. Night refers to the start, not every message.",
            score=4 + abs(share - baseline) / 20,
        )
    if len(c.sessions) >= 4:
        sizes = [len(s) for s in c.sessions]
        single = sum(v == 1 for v in sizes)
        if pct(single, len(sizes)) >= 25:
            out.add(
                "single-message-sessions",
                "Conversation endings",
                "The one-message cameo",
                "Single-message sessions",
                f"{single} of {len(sizes)} sessions contain just one participant message. This chat has a habit of little drop-ins.",
                f"{pct(single, len(sizes)):.0f}%",
                "single-message sessions",
                [s[0] for s in c.sessions if len(s) == 1],
                facts=[
                    ("Single-message sessions", single, "sessions"),
                    ("All sessions", len(sizes), "sessions"),
                ],
                method="One-message sessions under the chosen gap threshold; no claim that anyone saw or ignored the message.",
                score=3,
            )
    if len(c.obs) >= 20:
        media = [
            o
            for o in c.obs
            if o.source.message_type in {"image", "video", "audio", "file", "sticker"}
        ]
        calls = [o for o in c.obs if o.source.message_type == "call"]
        if len(media) >= 3:
            types = Counter(o.source.message_type for o in media)
            out.add(
                "media-mix",
                "Media sharing",
                "The chat has a camera roll",
                "Media mix",
                f"{pct(len(media), n):.1f}% of participant messages are media. {types.most_common(1)[0][0].capitalize()} leads the mix.",
                f"{pct(len(media), n):.1f}%",
                "media messages",
                media,
                visual=list(types.items()),
                facts=[("Media", len(media), "messages"), ("Total", n, "messages")],
                method="Counts normalized image/video/audio/file/sticker records, not attachment bytes or omitted-media contents.",
                score=2,
            )
        if len(calls) >= 3:
            out.add(
                "call-footprints",
                "Communication quirks",
                "Sometimes the chat gets a voice",
                "Recorded call events",
                f"The export records {len(calls)} call events across {len({o.time.date() for o in calls})} days.",
                str(len(calls)),
                "call events",
                calls,
                facts=[("Calls", len(calls), "events")],
                method="Counts exported call records; durations and answered status may be unavailable.",
                score=2,
            )
    if c.kind == "group" and len(c.own) >= 3:
        full = [
            items
            for items in c.days.values()
            if len({o.sender_id for o in items}) == len(c.own)
        ]
        smaller = [
            items
            for items in c.days.values()
            if len({o.sender_id for o in items}) < len(c.own)
        ]
        if len(full) >= 3 and len(smaller) >= 3:
            a = sum(map(len, full)) / len(full)
            b = sum(map(len, smaller)) / len(smaller)
            if b and a / b >= 1.5:
                out.add(
                    "full-cast-momentum",
                    "Communication dynamics",
                    "Full cast, fuller chat",
                    "Participation breadth and daily momentum",
                    f"On the {len(full)} days when all {len(c.own)} active participants speak, the chat averages {a:.1f} messages. Other active days average {b:.1f}—a {a / b:.1f}× difference.",
                    f"{a / b:.1f}×",
                    "messages on full-cast days",
                    [o for items in full for o in items],
                    facts=[
                        ("Full-cast average", a, "messages/day"),
                        ("Other active-day average", b, "messages/day"),
                        ("Full-cast days", len(full), "days"),
                    ],
                    visual=[("Full cast", a), ("Other days", b)],
                    method="Compares days containing every observed sender with other active days. Participation breadth and volume are associated; no causal claim. At least three days in each group.",
                    score=5,
                    multi=True,
                )
