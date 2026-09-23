def calculate(messages, gap_seconds):
    sessions = []
    for m in messages:
        if (
            not sessions
            or (m.timestamp - sessions[-1][-1].timestamp).total_seconds() > gap_seconds
        ):
            sessions.append([])
        sessions[-1].append(m)
    return sessions
