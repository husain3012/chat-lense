def resolver(participants):
    aliases = {}
    for p in participants:
        for alias in (
            p.id,
            p.platform_identifier,
            p.display_name,
            "@" + p.display_name,
        ):
            if alias:
                aliases[str(alias)] = p.id
        if p.platform_identifier and p.platform_identifier.startswith("user"):
            aliases[p.platform_identifier[4:]] = p.id
    return aliases


def calculate(messages, participants):
    aliases = resolver(participants)
    ids = [p.id for p in participants]
    index = {p: i for i, p in enumerate(ids)}
    matrix = [[0] * len(ids) for _ in ids]
    by_id = {m.platform_message_id: m for m in messages if m.platform_message_id}
    signals = 0

    def add(source, target):
        nonlocal signals
        if source in index and target in index and source != target:
            matrix[index[source]][index[target]] += 1
            signals += 1

    for m in messages:
        reply = by_id.get(m.reply_to_id)
        if reply:
            add(m.sender_id, reply.sender_id)
        for mention in set(m.mentions):
            add(m.sender_id, aliases.get(str(mention)))
        for r in m.reactions:
            for actor in r.get("actors", []):
                add(aliases.get(str(actor)), m.sender_id)
    return (
        {
            "participants": [
                {"id": p.id, "name": p.display_name} for p in participants
            ],
            "matrix": matrix,
            "signals": signals,
        }
        if signals
        else None
    )
