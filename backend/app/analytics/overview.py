from statistics import mean, median
from app.analytics import (
    sessions,
    initiations,
    participants,
    temporal,
    response_times,
    interactions,
    reactions,
)


def calculate(messages, people, conversation_type, metadata, gap_hours=4):
    grouped = sessions.calculate(messages, gap_hours * 3600)
    starts = initiations.calculate(grouped)
    response = response_times.calculate(messages, conversation_type, gap_hours * 3600)
    durations = [(s[-1].timestamp - s[0].timestamp).total_seconds() for s in grouped]
    active = len({m.timestamp.date() for m in messages})
    return {
        "total_messages": len(messages),
        "text_messages": sum(m.message_type == "text" for m in messages),
        "media_messages": sum(m.message_type in participants.MEDIA for m in messages),
        "started_at": messages[0].timestamp if messages else None,
        "ended_at": messages[-1].timestamp if messages else None,
        "active_days": active,
        "messages_per_active_day": len(messages) / active if active else 0,
        "longest_inactivity_seconds": max(
            (
                (b.timestamp - a.timestamp).total_seconds()
                for a, b in zip(messages, messages[1:])
            ),
            default=0,
        ),
        "sessions": {
            "total": len(grouped),
            "average_messages": mean([len(s) for s in grouped]) if grouped else 0,
            "median_length_seconds": median(durations) if durations else 0,
            "longest_seconds": max(durations, default=0),
            "longest_message_count": max(map(len, grouped), default=0),
            "gap_hours": gap_hours,
            "initiations": dict(starts),
        },
        "participants": participants.calculate(messages, people, starts, response),
        "activity": temporal.calculate(messages),
        "interactions": interactions.calculate(messages, people),
        "reactions": reactions.calculate(
            messages, people, metadata.get("reactions_available", False)
        ),
        "response_method": "Consecutive sender turns within session gap"
        if conversation_type == "direct"
        else "Explicit replies only; mentions count as interactions, not timed responses",
        "timezone": "UTC; timezone-less exports preserve original wall time",
    }
