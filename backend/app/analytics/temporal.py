from collections import Counter


def series(counter):
    return [{"date": k, "count": v} for k, v in sorted(counter.items())]


def calculate(messages):
    days, weeks, months, hours, weekdays = (Counter() for _ in range(5))
    for m in messages:
        t = m.timestamp
        days[t.date().isoformat()] += 1
        iso = t.isocalendar()
        weeks[f"{iso.year}-W{iso.week:02}"] += 1
        months[t.strftime("%Y-%m")] += 1
        hours[t.hour] += 1
        weekdays[t.weekday()] += 1
    return {
        "daily": series(days),
        "weekly": series(weeks),
        "monthly": series(months),
        "hourly": [{"label": f"{i:02}:00", "count": hours[i]} for i in range(24)],
        "weekday": [
            {"label": day, "count": weekdays[i]}
            for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        ],
    }
