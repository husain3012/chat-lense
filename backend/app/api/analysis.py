import json
import re
import threading
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.chat import AnalysisJob, AppSetting, Message
from app.api.routes import require_conversation
from app.services import ai_settings, jobs
from app.synthesis.chat_provider import ask
from app.synthesis.gemini import ProviderError

router = APIRouter(prefix="/api")
question_gate = threading.Lock()


class QueueRequest(BaseModel):
    consent: bool = False
    refresh: bool = False


@router.post("/conversations/{cid}/analysis", status_code=202)
def queue(cid: str, body: QueueRequest, db: Session = Depends(get_db)):
    require_conversation(db, cid)
    existing = db.get(AnalysisJob, cid)
    if body.refresh and existing and existing.status in ("failed", "completed"):
        db.delete(existing)
        db.flush()
    job = jobs.enqueue(db, cid, body.consent)
    db.commit()
    return jobs.status(job)


@router.get("/conversations/{cid}/analysis")
def progress(cid: str, db: Session = Depends(get_db)):
    require_conversation(db, cid)
    return jobs.status(db.get(AnalysisJob, cid))


@router.get("/settings/ai")
def settings():
    return ai_settings.public()


class SettingsPatch(BaseModel):
    api_key: str | None = Field(default=None, max_length=300)
    model: str = Field(
        default="gemini-3.5-flash-lite", pattern=r"^[A-Za-z0-9._-]{1,100}$"
    )
    interval_seconds: float = Field(default=2, ge=1, le=3600)
    max_retries: int = Field(default=8, ge=0, le=20)
    input_budget: int = Field(default=240000, ge=12000, le=500000)
    output_tokens: int = Field(default=8192, ge=2048, le=32768)
    chunk_messages: int = Field(default=2000, ge=20, le=5000)


@router.patch("/settings/ai")
def update_settings(body: SettingsPatch, db: Session = Depends(get_db)):
    row = db.get(AppSetting, "ai")
    value = {**(row.value if row else {}), **body.model_dump(exclude={"api_key"})}
    if body.api_key is not None:
        value["api_key"] = body.api_key.strip()
    if row:
        row.value = value
    else:
        db.add(AppSetting(name="ai", value=value))
    db.commit()
    return ai_settings.public()


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    finding_id: str | None = Field(default=None, max_length=100)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=6)


@router.post("/conversations/{cid}/ask")
def question(cid: str, body: Question, db: Session = Depends(get_db)):
    c = require_conversation(db, cid)
    if not c.extra.get("ai_consent"):
        raise HTTPException(
            403, "Enable Gemini for this conversation before asking questions."
        )
    if not question_gate.acquire(blocking=False):
        raise HTTPException(
            429, "Another question is being answered. Try again shortly."
        )
    try:
        settings = ai_settings.read()
        job = db.get(AnalysisJob, cid)
        result = job.result if job else {}
        findings = result.get("moments", []) + result.get("local", {}).get(
            "insights", []
        )
        selected = next((f for f in findings if f["id"] == body.finding_id), None)
        if body.finding_id and not selected:
            raise HTTPException(404, "Finding not available in this conversation.")
        context = {
            "question": body.question,
            "history": [
                {"role": h.get("role", "user")[:20], "text": h.get("text", "")[:2000]}
                for h in body.history
            ],
            "finding": selected,
            "snapshot": result.get("local", {}).get("snapshot", {}),
            "cover": result.get("cover"),
            "final_perspective": result.get("verdict"),
            "messages": [],
        }
        # Retrieval uses scoped literal search + nearby exchanges, not embeddings.
        plan = ask(
            'Propose up to four literal search terms or short phrases in the likely original languages to find evidence for this question. Return {"terms":[string]}. Do not answer yet.',
            {
                "question": body.question,
                "cover": result.get("cover"),
                "finding": selected and selected["description"],
            },
            settings,
        )
        if not isinstance(plan, dict) or not isinstance(plan.get("terms"), list):
            raise ProviderError("Gemini could not plan a search. Please retry.")
        ids = list(selected.get("evidence_ids", [])) if selected else []
        for term in plan.get("terms", [])[:4]:
            if isinstance(term, str) and term.strip():
                rows = db.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == cid,
                        Message.text.contains(term[:120], autoescape=True),
                    )
                    .order_by(Message.timestamp)
                    .limit(8)
                ).all()
                ids.extend(m.id for m in rows)
        if not ids:
            ids = [mid for f in findings[:8] for mid in f.get("evidence_ids", [])[:2]]
        anchors = db.scalars(
            select(Message).where(
                Message.conversation_id == cid, Message.id.in_(ids[:40])
            )
        ).all()
        found = {m.id: m for m in anchors}
        for anchor in anchors[:16]:
            for row in db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == cid,
                    Message.timestamp >= anchor.timestamp - timedelta(minutes=10),
                    Message.timestamp <= anchor.timestamp + timedelta(minutes=10),
                )
                .order_by(Message.timestamp, Message.sequence)
                .limit(16)
            ):
                found[row.id] = row
        for row in sorted(found.values(), key=lambda m: (m.timestamp, m.sequence)):
            item = {
                "id": row.id,
                "sender": row.sender_name,
                "time": row.timestamp.isoformat(),
                "text": (row.text or "")[:2000],
                "type": row.message_type,
            }
            context["messages"].append(item)
            if (
                len(json.dumps(context, ensure_ascii=False).encode())
                > settings["input_budget"] - 2500
            ):
                context["messages"].pop()
                break
        db.rollback()
        answer = ask(
            'Answer this question conversationally from the supplied evidence and measurements. Search is partial, never say no matching evidence proves something never happened. Acknowledge missing context. Return {"answer":string (up to 2000 characters), "evidence_ids":[supplied message IDs]}. Put citations only in evidence_ids, never raw IDs in the answer prose. No diagnosis, definitive claims of lying or hidden motives.',
            context,
            settings,
        )
        if not isinstance(answer, dict) or not isinstance(
            answer.get("evidence_ids"), list
        ):
            raise ProviderError("Gemini returned an invalid answer. Please retry.")
        supplied = {m["id"] for m in context["messages"]}
        citations = [mid for mid in answer.get("evidence_ids", []) if mid in supplied][
            :12
        ]
        if not isinstance(answer.get("answer"), str):
            raise ProviderError("Gemini returned an invalid answer.")
        return {
            "answer": re.sub(r"\s*\[[0-9a-f-]{36}\]", "", answer["answer"])[:4000],
            "evidence_ids": citations,
            "searched_messages": len(context["messages"]),
            "method": "Conversation-scoped literal search with nearby exchanges; incomplete retrieval, not a full-history verdict.",
        }
    except ProviderError as e:
        raise HTTPException(502, str(e)) from e
    finally:
        question_gate.release()
