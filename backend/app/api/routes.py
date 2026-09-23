import os
import tempfile
from pathlib import Path
from typing import Literal
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from types import SimpleNamespace
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.models.database import get_db
from app.models.chat import Conversation, Participant, Message
from app.parsers.registry import detect, parse
from app.utils.uploads import MAX_UPLOAD, ACCEPTED, prepare
from app.analytics.overview import calculate
from app.services.imports import persist_conversation
from app.services.import_timezone import apply_timezone

router = APIRouter(prefix="/api")


def serialize(row):
    return {
        c.name: getattr(row, "extra" if c.name == "metadata" else c.name)
        for c in row.__table__.columns
    }


def require_conversation(db, cid):
    c = db.get(Conversation, cid)
    if not c:
        raise HTTPException(404, "Conversation not found")
    return c


async def process(file, platform=None, date_order="auto", detection=False):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ACCEPTED:
        raise HTTPException(400, "Supported uploads: TXT, JSON, chat.db/SQLite, ZIP")
    with tempfile.TemporaryDirectory(prefix="chatlens-") as temp:
        # Preserve a safe basename for conversation titles, never a user-provided path.
        name = Path((file.filename or "upload").replace("\\", "/")).name
        name = "".join(c for c in name if c.isalnum() or c in " ._-")[:160]
        path = Path(temp) / (name or ("upload" + suffix))
        size = 0
        with path.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, "Upload exceeds configured size limit")
                stream.write(chunk)
        try:

            def work():
                root = prepare(path)
                detected = detect(root)
                if detection:
                    return detected
                chats = parse(root, platform or detected["platform"], date_order)
                if (
                    suffix == ".zip"
                    and len(chats) == 1
                    and chats[0].title in ("_chat", "chat")
                ):
                    chats[0].title = path.stem.removeprefix(
                        "WhatsApp Chat - "
                    ).removeprefix("WhatsApp Chat with ")
                return chats

            return await run_in_threadpool(work)
        except (ValueError, OSError, KeyError, TypeError, OverflowError) as e:
            raise HTTPException(422, f"Cannot parse this export: {str(e)[:250]}") from e
        except Exception as e:
            # Do not expose local paths, message contents or database internals.
            raise HTTPException(
                422, "Unreadable or unsupported export. Check its format and try again."
            ) from e
        finally:
            await file.close()


@router.post("/import/detect")
async def detect_import(file: UploadFile = File(...)):
    return await process(file, detection=True)


@router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    platform: str | None = Form(None),
    date_order: Literal["auto", "dmy", "mdy"] = Form("auto"),
    chat_timezone: str | None = Form(None),
):
    chats = await process(file, platform, date_order)
    for c in chats:
        apply_timezone(c, chat_timezone)
    return {
        "conversations": [
            dict(c.model_dump(exclude={"messages"}), selection_index=i)
            for i, c in enumerate(chats)
        ]
    }


@router.post("/import")
async def save_import(
    file: UploadFile = File(...),
    platform: str | None = Form(None),
    date_order: Literal["auto", "dmy", "mdy"] = Form("auto"),
    selection_index: int = Form(0),
    current_user_index: int = Form(-1),
    current_user_indices: str | None = Form(None),
    conversation_type: Literal["direct", "group"] | None = Form(None),
    ai_consent: bool = Form(False),
    chat_timezone: str | None = Form(None),
    db: Session = Depends(get_db),
):
    chats = await process(file, platform, date_order)
    if not 0 <= selection_index < len(chats):
        raise HTTPException(422, "Invalid conversation selection")
    c = chats[selection_index]
    apply_timezone(c, chat_timezone, required=True)
    try:
        identity_indices = (
            [int(value) for value in current_user_indices.split(",") if value.strip()]
            if current_user_indices is not None
            else [current_user_index]
        )
    except ValueError as exc:
        raise HTTPException(422, "Invalid participant identity selection") from exc
    from app.services.identity import merge_current_user_aliases

    merge_current_user_aliases(c, identity_indices)
    if conversation_type:
        c.conversation_type = conversation_type
    await run_in_threadpool(persist_conversation, db, c)
    from app.services.jobs import enqueue

    enqueue(
        db, c.id, ai_consent, {"timezone": c.metadata.get("source_timezone", "UTC")}
    )
    db.commit()
    return {"id": c.id, "message_count": c.message_count, "warnings": c.warnings}


@router.get("/conversations")
def conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Conversation)
        .order_by(Conversation.ended_at.desc(), Conversation.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize(c) for c in rows],
        "total": db.scalar(select(func.count()).select_from(Conversation)),
        "page": page,
        "page_size": page_size,
    }


@router.get("/conversations/{cid}")
def conversation(cid: str, db: Session = Depends(get_db)):
    return serialize(require_conversation(db, cid))


@router.delete("/conversations/{cid}", status_code=204)
def delete_conversation(cid: str, db: Session = Depends(get_db)):
    require_conversation(db, cid)
    db.execute(delete(Conversation).where(Conversation.id == cid))
    db.commit()


@router.get("/conversations/{cid}/participants")
def participants(cid: str, db: Session = Depends(get_db)):
    require_conversation(db, cid)
    return [
        serialize(p)
        for p in db.scalars(
            select(Participant)
            .where(Participant.conversation_id == cid)
            .order_by(Participant.display_name, Participant.id)
        )
    ]


class ParticipantPatch(BaseModel):
    is_current_user: bool


@router.patch("/conversations/{cid}/participants/{pid}")
def patch_participant(
    cid: str, pid: str, body: ParticipantPatch, db: Session = Depends(get_db)
):
    c = require_conversation(db, cid)
    # Serialize identity edits for this conversation.
    db.scalar(select(Conversation).where(Conversation.id == c.id).with_for_update())
    p = db.scalar(
        select(Participant).where(
            Participant.id == pid, Participant.conversation_id == cid
        )
    )
    if not p:
        raise HTTPException(404, "Participant not found")
    if body.is_current_user:
        db.execute(
            update(Participant)
            .where(Participant.conversation_id == cid)
            .values(is_current_user=False)
        )
    p.is_current_user = body.is_current_user
    db.commit()
    return serialize(p)


@router.get("/conversations/{cid}/messages")
def messages(
    cid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    participant: str | None = None,
    message_type: str | None = None,
    q: str | None = Query(None, max_length=500),
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
):
    require_conversation(db, cid)
    conditions = [Message.conversation_id == cid]
    if participant:
        conditions.append(Message.sender_id == participant)
    if message_type:
        conditions.append(Message.message_type == message_type)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Message.text.ilike("%" + escaped + "%", escape="\\"))
    if start:
        conditions.append(Message.timestamp >= start)
    if end:
        conditions.append(Message.timestamp <= end)
    total = db.scalar(select(func.count()).select_from(Message).where(*conditions))
    rows = db.scalars(
        select(Message)
        .where(*conditions)
        .order_by(Message.timestamp, Message.sequence, Message.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [serialize(m) for m in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/conversations/{cid}/analytics")
def analytics(
    cid: str,
    session_gap: float = Query(
        float(os.getenv("SESSION_GAP_HOURS", "4")), gt=0, le=168
    ),
    db: Session = Depends(get_db),
):
    c = require_conversation(db, cid)
    people = db.scalars(
        select(Participant).where(Participant.conversation_id == cid)
    ).all()
    # Linear-time analytics, ordered indexed read; never sends message bodies to React.
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == cid)
        .order_by(Message.timestamp, Message.sequence, Message.id)
    ).all()
    zone = c.extra.get("source_timezone", "UTC")
    localized = [
        SimpleNamespace(
            **{
                **serialize(m),
                "timestamp": (
                    m.timestamp.replace(tzinfo=timezone.utc)
                    if m.timestamp.tzinfo is None
                    else m.timestamp
                ).astimezone(ZoneInfo(zone)),
            }
        )
        for m in messages
    ]
    result = calculate(messages, people, c.conversation_type, c.extra, session_gap)
    from app.analytics.temporal import calculate as activity
    from collections import defaultdict

    result["activity"] = activity(localized)
    result["active_days"] = len({m.timestamp.date() for m in localized})
    result["messages_per_active_day"] = (
        len(messages) / result["active_days"] if result["active_days"] else 0
    )
    by_sender = defaultdict(list)
    for message in localized:
        by_sender[message.sender_id].append(message)
    for participant in result["participants"]:
        own = by_sender[participant["id"]]
        participant["active_days"] = len({m.timestamp.date() for m in own})
        participant["activity"] = activity(own)
    result["timezone"] = zone
    return result
