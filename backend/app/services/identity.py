"""Resolve multiple export labels that represent the same current user."""

from collections import Counter
from fastapi import HTTPException


def merge_current_user_aliases(chat, indices: list[int]):
    unique = list(dict.fromkeys(indices))
    if not unique or any(i < 0 or i >= len(chat.participants) for i in unique):
        raise HTTPException(422, "Select at least one participant that represents you")

    selected = [chat.participants[i] for i in unique]
    message_counts = Counter(m.sender_id for m in chat.messages if m.sender_id)
    canonical = max(
        selected,
        key=lambda p: (message_counts[p.id], -chat.participants.index(p)),
    )
    aliases = [p.display_name for p in selected if p.id != canonical.id]
    selected_ids = {p.id for p in selected}

    for message in chat.messages:
        if message.sender_id in selected_ids:
            message.sender_id = canonical.id
            message.sender_name = canonical.display_name
        if message.mentions:
            message.mentions = [
                canonical.display_name if mention in aliases else mention
                for mention in message.mentions
            ]

    chat.participants = [
        participant
        for participant in chat.participants
        if participant.id == canonical.id or participant.id not in selected_ids
    ]
    canonical.is_current_user = True
    chat.metadata = {
        **chat.metadata,
        "current_user_aliases": [canonical.display_name, *aliases],
    }
    chat.finalize()
    return canonical
