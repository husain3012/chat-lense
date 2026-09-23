import calendar
from collections import Counter
from statistics import median
from app.schemas.report import TimelinePeriod
from app.insights.candidates import pct


def discover(c, out):
    periods = []
    if not c.obs:
        return periods
    first, last = c.obs[0].time.date(), c.obs[-1].time.date()
    for month, items in sorted(c.months.items()):
        year, m = map(int, month.split("-"))
        days = calendar.monthrange(year, m)[1]
        partial = (month == first.strftime("%Y-%m") and first.day != 1) or (
            month == last.strftime("%Y-%m") and last.day != days
        )
        late = pct(sum(c.late(o) for o in items), len(items))
        weekend = pct(sum(o.time.weekday() >= 5 for o in items), len(items))
        leader = Counter(o.sender_id for o in items).most_common(1)[0][0]
        title = (
            "The late-night chapter"
            if late >= 40 and len(items) >= 20
            else "The weekend chapter"
            if weekend >= 55 and len(items) >= 20
            else "A chapter of its own"
        )
        if out.tone == "analytical":
            title = "Monthly activity"
        periods.append(
            TimelinePeriod(
                period=month,
                title=title,
                summary=f"{len(items):,} messages across {len({o.time.date() for o in items})} active days. {c.name(leader)} contributed the most messages.",
                message_count=len(items),
                active_days=len({o.time.date() for o in items}),
                late_share=round(late, 1),
                weekend_share=round(weekend, 1),
                average_length=round(c.average(items), 1),
                leader=c.name(leader),
                evidence_ids=c.evidence(items),
                partial=partial,
            )
        )
    for prev, cur in zip(periods, periods[1:]):
        before = c.months[prev.period]
        after = c.months[cur.period]
        y1, m1 = map(int, prev.period.split("-"))
        y2, m2 = map(int, cur.period.split("-"))
        contiguous = (y2 * 12 + m2) - (y1 * 12 + m1) == 1
        if not contiguous:
            cur.summary = (
                "After a gap in recorded monthly activity, "
                + cur.summary[0].lower()
                + cur.summary[1:]
            )
        if (
            prev.partial
            or cur.partial
            or not contiguous
            or min(len(before), len(after)) < 20
        ):
            continue
        days1 = calendar.monthrange(y1, m1)[1]
        days2 = calendar.monthrange(y2, m2)[1]
        rate1 = len(before) / days1
        rate2 = len(after) / days2
        delta = (rate2 / rate1 - 1) * 100
        shift = cur.late_share - prev.late_share
        length_delta = (
            (cur.average_length / prev.average_length - 1) * 100
            if prev.average_length
            else 0
        )
        signals = [("Messages/day", delta)]
        if abs(shift) >= 15:
            signals.append(("Late-night share", shift))
        if abs(length_delta) >= 30:
            signals.append(("Average text length", length_delta))
        if abs(delta) >= 35:
            cur.title = (
                ("The comeback chapter" if delta > 0 else "The quieter chapter")
                if out.tone != "analytical"
                else "Activity increase"
                if delta > 0
                else "Activity decrease"
            )
            cur.summary = (
                f"Messages per calendar day {'rose' if delta > 0 else 'fell'} {abs(delta):.0f}% versus {prev.period}. "
                + cur.summary
            )
            text = f"From {prev.period} to {cur.period}, the daily pace goes from {rate1:.1f} to {rate2:.1f} messages ({delta:+.0f}%)."
            if len(signals) > 1:
                text += (
                    " At the same time, "
                    + (
                        "; ".join(
                            f"{name.lower()} changes {value:+.0f}{' percentage points' if name == 'Late-night share' else '%'}"
                            for name, value in signals[1:]
                        )
                    )
                    + ". More than one part of the rhythm changed."
                )
            out.add(
                "month-pace-" + cur.period,
                "Turning points",
                "The "
                + calendar.month_name[m2]
                + " "
                + ("comeback" if delta > 0 else "slowdown"),
                "Monthly pace change",
                text,
                f"{delta:+.0f}%",
                "change in messages per day",
                before[:6] + after[:6],
                facts=[
                    ("Before messages/day", rate1, "messages/day"),
                    ("After messages/day", rate2, "messages/day"),
                ]
                + [
                    (
                        name,
                        value,
                        "percentage points" if name == "Late-night share" else "%",
                    )
                    for name, value in signals[1:]
                ],
                visual=[(prev.period, rate1), (cur.period, rate2)],
                method="Compares adjacent complete calendar months with at least 20 messages each; day-count normalized. Independent timing/length changes added when large enough.",
                score=6 + min(abs(delta) / 100, 4) + len(signals),
                multi=len(signals) > 1,
            )
        elif abs(shift) >= 20:
            out.add(
                "hour-migration-" + cur.period,
                "Turning points",
                "The clock moved",
                "Late-night share shift",
                f"Late-night messages move from {prev.late_share:.0f}% in {prev.period} to {cur.late_share:.0f}% in {cur.period}: a {abs(shift):.0f}-point shift in when this conversation happens.",
                f"{shift:+.0f}pp",
                "late-night share change",
                before[:6] + after[:6],
                facts=[
                    ("Before late share", prev.late_share, "%"),
                    ("After late share", cur.late_share, "%"),
                ],
                visual=[(prev.period, prev.late_share), (cur.period, cur.late_share)],
                method="Complete adjacent months with at least 20 messages. Late night is 23:00–04:59 in the report timezone.",
                score=6,
            )
        else:
            cur.summary = (
                f"{'A steadier month' if abs(delta) < 15 else 'A change of pace'}: {delta:+.0f}% in messages per calendar day. "
                + cur.summary
            )
        before_counts = Counter(o.sender_id for o in before)
        after_counts = Counter(o.sender_id for o in after)
        shifts = []
        for pid, count in before_counts.items():
            if count < 10 or before_counts[pid] + after_counts[pid] < 20:
                continue
            a = pct(count, len(before))
            b = pct(after_counts[pid], len(after))
            difference = b - a
            if abs(difference) >= 20:
                shifts.append((abs(difference), pid, a, b))
        if shifts:
            _, pid, a, b = max(shifts)
            own_before = [o for o in before if o.sender_id == pid]
            own_after = [o for o in after if o.sender_id == pid]
            len1 = c.average(own_before)
            len2 = c.average(own_after)
            start1 = sum(
                s[0].sender_id == pid and s[0].time.strftime("%Y-%m") == prev.period
                for s in c.sessions
            )
            start2 = sum(
                s[0].sender_id == pid and s[0].time.strftime("%Y-%m") == cur.period
                for s in c.sessions
            )
            resp1 = [
                t
                for x, y, t in c.responses
                if y.sender_id == pid and y.time.strftime("%Y-%m") == prev.period
            ]
            resp2 = [
                t
                for x, y, t in c.responses
                if y.sender_id == pid and y.time.strftime("%Y-%m") == cur.period
            ]
            facts = [("Before message share", a, "%"), ("After message share", b, "%")]
            text = f"{c.name(pid)} goes from {a:.0f}% of messages in {prev.period} to {b:.0f}% in {cur.period}."
            if (
                len1
                and len2
                and min(len(own_before), len(own_after)) >= 5
                and abs(len2 / len1 - 1) >= 0.3
            ):
                text += f" Their average text also changes from {len1:.0f} to {len2:.0f} characters."
                facts += [
                    ("Before average length", len1, "characters"),
                    ("After average length", len2, "characters"),
                ]
            if (
                min(len(resp1), len(resp2)) >= 5
                and min(median(resp1), median(resp2)) > 0
                and max(median(resp1), median(resp2))
                / min(median(resp1), median(resp2))
                >= 1.8
            ):
                text += f" Median response time changes from {median(resp1) / 60:.1f} to {median(resp2) / 60:.1f} minutes."
                facts += [
                    ("Before response median", median(resp1), "seconds"),
                    ("After response median", median(resp2), "seconds"),
                ]
            if start1 >= 3 and abs(start2 - start1) >= 3:
                text += f" Session starts shift from {start1} to {start2}."
                facts += [
                    ("Before starts", start1, "sessions"),
                    ("After starts", start2, "sessions"),
                ]
            out.add(
                "participant-shift-" + cur.period,
                "Turning points",
                f"{c.name(pid)}’s change of pace",
                "Participant contribution shift",
                text,
                f"{b - a:+.0f}pp",
                "share of the conversation",
                own_before[:6] + own_after[:6],
                facts=facts,
                visual=[(prev.period, a), (cur.period, b)],
                method="Largest participant share shift between these complete months (at least 20 percentage points). Share can fall because others speak more; no cause or motive inferred.",
                score=7 + (len(facts) > 2) * 2,
                pids=[pid],
                multi=len(facts) > 2,
            )
    return periods
