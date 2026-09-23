from collections import Counter


def calculate(sessions):
    counts = Counter()
    for session in sessions:
        initiator = next(
            (
                m.sender_id
                for m in session
                if m.sender_id and m.message_type != "system"
            ),
            None,
        )
        if initiator:
            counts[initiator] += 1
    return counts
