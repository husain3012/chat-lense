from sqlalchemy import insert
from app.models.chat import Conversation, Participant, Message


def persist_conversation(db, c):
    """Persist a normalized import in one transaction using bounded insert batches."""
    values = c.model_dump(exclude={"messages", "participants", "warnings", "metadata"})
    db.add(Conversation(**values, extra=c.metadata))
    db.flush()
    db.execute(insert(Participant), [p.model_dump() for p in c.participants])
    for start in range(0, len(c.messages), 2000):
        batch = []
        for m in c.messages[start : start + 2000]:
            row = m.model_dump()
            row["extra"] = row.pop("metadata")
            batch.append(row)
        db.execute(insert(Message), batch)
    db.commit()
