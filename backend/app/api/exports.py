import shutil
import tempfile
import threading
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.chat import AnalysisJob, Participant
from app.api.routes import require_conversation
from app.services.wraps import WrapRequest, slides, document, render

router = APIRouter(prefix="/api")
_renderer = threading.BoundedSemaphore(1)


def prepare(db, cid, request):
    require_conversation(db, cid)
    job = db.get(AnalysisJob, cid)
    if not job or not job.result.get("local"):
        raise HTTPException(
            409, "Your report is still being prepared. Try again once insights appear."
        )
    report = {
        **job.result["local"],
        "synthesis": job.result.get("synthesis"),
        "verdict": job.result.get("verdict"),
    }
    people = db.scalars(
        select(Participant)
        .where(Participant.conversation_id == cid)
        .order_by(Participant.id)
    ).all()
    try:
        return slides(report, people, request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/conversations/{cid}/export/preview")
def preview(cid: str, request: WrapRequest, db: Session = Depends(get_db)):
    items = prepare(db, cid, request)
    return {
        "pages": [document([s]) for s in items],
        "count": len(items),
        "duration": len(items) * request.seconds_per_slide,
    }


@router.post("/conversations/{cid}/export/{format}")
def export(
    cid: str,
    format: Literal["mp4", "pdf"],
    request: WrapRequest,
    db: Session = Depends(get_db),
):
    if format == "mp4" and len(request.finding_ids) > 8:
        raise HTTPException(
            422, "Choose up to eight highlights for a video. PDF supports up to fifty."
        )
    items = prepare(db, cid, request)
    db.rollback()
    if not _renderer.acquire(blocking=False):
        raise HTTPException(429, "Another wrap is rendering. Please try again shortly.")
    folder = Path(tempfile.mkdtemp(prefix="chatlens-wrap-"))
    try:
        output = render(items, format, folder, request.seconds_per_slide)
        if output.stat().st_size > 64 * 1024 * 1024:
            raise ValueError(
                "This export is too large. Select fewer highlights or a quicker video pace."
            )
        return Response(
            output.read_bytes(),
            media_type="video/mp4" if format == "mp4" else "application/pdf",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="chatlens-wrap.{format}"',
            },
        )
    except ValueError as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(
            503,
            "Export could not finish. Check that Chromium and FFmpeg are installed, then retry. Your report is unchanged.",
        ) from exc
    finally:
        # Clean before sending the response, including disconnected clients.
        shutil.rmtree(folder, ignore_errors=True)
        _renderer.release()
