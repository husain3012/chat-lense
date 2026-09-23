import hashlib
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from app.models.database import get_db
from app.models.chat import (
    Message,
    Participant,
    SynthesisRun,
    Conversation,
    AnalysisJob,
)
from app.api.routes import require_conversation, serialize
from app.schemas.report import Tone
from app.insights.engine import build_report
from app.synthesis.packet import build_packet
from app.synthesis import gemini
from app.synthesis.contracts import SynthesisRequest
from app.synthesis.service import synthesize, PROMPT_VERSION
from app.synthesis.validation import filter_contextual

router = APIRouter(prefix="/api")
_gate = threading.Lock()


@router.get("/conversations/{cid}/reply-network")
def reply_network(cid: str, db: Session = Depends(get_db)):
    from app.analytics.reply_network import calculate

    conversation = require_conversation(db, cid)
    if conversation.conversation_type != "group":
        return {"network": None}
    messages = db.execute(
        select(
            Message.id,
            Message.sender_id,
            Message.platform_message_id,
            Message.reply_to_id,
            Message.message_type,
        )
        .where(Message.conversation_id == cid)
        .order_by(Message.timestamp, Message.sequence, Message.id)
    ).all()
    people = db.scalars(
        select(Participant)
        .where(Participant.conversation_id == cid)
        .order_by(Participant.id)
    ).all()
    return {"network": calculate(messages, people)}


def load(db, cid, tone, gap, zone):
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            422, "Choose a valid IANA timezone, for example UTC or Asia/Kolkata."
        )
    conversation = require_conversation(db, cid)
    participants = db.scalars(
        select(Participant)
        .where(Participant.conversation_id == cid)
        .order_by(Participant.id)
    ).all()
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == cid)
        .order_by(Message.timestamp, Message.sequence, Message.id)
    ).all()
    report = build_report(messages, participants, conversation, tone, gap, zone)
    return report, messages, participants


def cache_key(report):
    return hashlib.sha256(
        (report.fingerprint + gemini.config()["model"] + PROMPT_VERSION).encode()
    ).hexdigest()


@router.get("/analysis/config")
def configuration():
    return gemini.config()


@router.get("/conversations/{cid}/report")
def report(
    cid: str,
    tone: Tone = "fun",
    session_gap: float = Query(4, gt=0, le=168),
    timezone: str = Query("UTC", max_length=100),
    queued: bool = False,
    db: Session = Depends(get_db),
):
    require_conversation(db, cid)
    job = db.get(AnalysisJob, cid)
    if queued and job and not job.result.get("local"):
        return JSONResponse({"pending": True, "status": job.status}, status_code=202)
    if job and job.result.get("local"):
        result = dict(job.result["local"])
        if (tone, session_gap, timezone) != (
            result["tone"],
            result["session_gap_hours"],
            result["timezone"],
        ):
            local, _, _ = load(db, cid, tone, session_gap, timezone)
            result = local.model_dump(mode="json")
        if job.result.get("synthesis"):
            result["synthesis"] = job.result["synthesis"]
        result["cover"] = job.result.get("cover")
        # A previously completed perspective remains readable during comparison backfills.
        result["verdict"] = job.result.get("verdict")
        from app.synthesis.behaviors import present

        result["behaviors"] = present(job.result.get("behaviors"))
        result["analysis"] = {"status": job.status, "progress": job.progress}
        return result
    result, _, _ = load(db, cid, tone, session_gap, timezone)
    existing = db.get(SynthesisRun, cache_key(result))
    if existing:
        result.synthesis = filter_contextual(existing.payload)
    return result


@router.get("/conversations/{cid}/report/packet")
def packet_preview(
    cid: str,
    tone: Tone = "fun",
    session_gap: float = Query(4, gt=0, le=168),
    timezone: str = Query("UTC", max_length=100),
    db: Session = Depends(get_db),
):
    result, messages, participants = load(db, cid, tone, session_gap, timezone)
    try:
        return build_packet(result, messages, participants)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/conversations/{cid}/report/synthesize")
def generate_report(cid: str, body: SynthesisRequest, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(
            422,
            "Explicit consent is required to send the previewed evidence packet to Gemini.",
        )
    if not gemini.config()["configured"]:
        raise HTTPException(
            503,
            "Set GEMINI_API_KEY in the root .env and recreate the backend container. Local reports work without a key.",
        )
    if not _gate.acquire(blocking=False):
        raise HTTPException(
            409, "Another synthesis is running. Please wait for it to finish."
        )
    try:
        report, messages, participants = load(
            db, cid, body.tone, body.session_gap, body.timezone
        )
        key = cache_key(report)
        existing = db.get(SynthesisRun, key)
        if existing and not body.refresh:
            return filter_contextual(existing.payload)
        try:
            packet = build_packet(report, messages, participants)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        if len(packet["samples"]) < 2:
            raise HTTPException(
                422, "At least two participant messages are needed for synthesis."
            )
        # Release the read transaction while network work happens in this worker thread.
        db.rollback()
        try:
            payload = synthesize(report, packet)
        except gemini.ProviderError as e:
            raise HTTPException(502, str(e)) from e
        if not db.get(Conversation, cid):
            raise HTTPException(
                409, "Conversation was deleted while synthesis ran. Nothing was saved."
            )
        row = db.get(SynthesisRun, key)
        if row:
            row.payload = payload
        else:
            db.add(SynthesisRun(id=key, conversation_id=cid, payload=payload))
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                409, "Conversation changed during synthesis; result was not saved."
            ) from e
        return payload
    finally:
        _gate.release()


@router.get("/conversations/{cid}/evidence")
def evidence(
    cid: str, ids: str = Query("", max_length=2000), db: Session = Depends(get_db)
):
    require_conversation(db, cid)
    requested = list(dict.fromkeys(ids.split(","))) if ids else []
    if len(requested) > 20:
        raise HTTPException(422, "Request up to 20 evidence messages at a time.")
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == cid, Message.id.in_(requested))
        .order_by(Message.timestamp, Message.sequence, Message.id)
    ).all()
    return {"items": [serialize(m) for m in rows]}


@router.get("/conversations/{cid}/messages/{mid}/context")
def message_context(
    cid: str,
    mid: str,
    direction: str = Query("around", pattern="^(around|before|after)$"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    require_conversation(db, cid)
    target = db.scalar(
        select(Message).where(Message.id == mid, Message.conversation_id == cid)
    )
    if not target:
        raise HTTPException(404, "Message not found in this conversation.")
    # Stable timestamp+source sequence ordering, with UUID as the final tie-breaker.
    previous = or_(
        Message.timestamp < target.timestamp,
        and_(Message.timestamp == target.timestamp, Message.sequence < target.sequence),
        and_(
            Message.timestamp == target.timestamp,
            Message.sequence == target.sequence,
            Message.id < target.id,
        ),
    )
    following = or_(
        Message.timestamp > target.timestamp,
        and_(Message.timestamp == target.timestamp, Message.sequence > target.sequence),
        and_(
            Message.timestamp == target.timestamp,
            Message.sequence == target.sequence,
            Message.id > target.id,
        ),
    )
    before = db.scalars(
        select(Message)
        .where(Message.conversation_id == cid, previous)
        .order_by(Message.timestamp.desc(), Message.sequence.desc(), Message.id.desc())
        .limit(limit + 1)
    ).all()
    after = db.scalars(
        select(Message)
        .where(Message.conversation_id == cid, following)
        .order_by(Message.timestamp, Message.sequence, Message.id)
        .limit(limit + 1)
    ).all()
    rows = list(reversed(before[:limit])) if direction != "after" else []
    if direction == "around":
        rows.append(target)
    if direction != "before":
        rows.extend(after[:limit])
    return {
        "items": [serialize(m) for m in rows],
        "has_before": len(before) > limit,
        "has_after": len(after) > limit,
    }
