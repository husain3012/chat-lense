from collections import defaultdict
from statistics import mean, median
from app.analytics.temporal import calculate as activity

MEDIA = {"image", "video", "audio", "file", "sticker"}


def calculate(messages, participants, initiations, responses):
    groups = defaultdict(list)
    for m in messages:
        groups[m.sender_id].append(m)
    output = []
    for p in participants:
        own = groups[p.id]
        lengths = [len(m.text or "") for m in own if m.message_type == "text"]
        output.append(
            {
                "id": p.id,
                "name": p.display_name,
                "is_current_user": p.is_current_user,
                "message_count": len(own),
                "percentage": len(own) / len(messages) * 100 if messages else 0,
                "text_count": sum(m.message_type == "text" for m in own),
                "media_count": sum(m.message_type in MEDIA for m in own),
                "total_characters": sum(lengths),
                "average_length": mean(lengths) if lengths else 0,
                "median_length": median(lengths) if lengths else 0,
                "first_message": own[0].timestamp if own else None,
                "last_message": own[-1].timestamp if own else None,
                "active_days": len({m.timestamp.date() for m in own}),
                "sessions_started": initiations[p.id],
                "response_times": responses.get(p.id),
                "activity": activity(own),
                "types": dict(
                    (k, sum(m.message_type == k for m in own))
                    for k in sorted({m.message_type for m in own})
                ),
            }
        )
    return output
