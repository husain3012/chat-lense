from datetime import timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.database import Base, engine, SessionLocal
from app.models.chat import AnalysisJob, Conversation, Message
from app.services import jobs
from app.synthesis import gemini
from app.synthesis.contracts import SynthesisOutput
from app.parsers.whatsapp import WhatsAppParser

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(monkeypatch):
    from app.synthesis import behaviors

    monkeypatch.setattr(
        behaviors,
        "classify",
        lambda rows, offset, already, state, settings: {
            "processed": offset + len(rows),
            "categories": {},
            "interests": {},
        },
    )
    Base.metadata.create_all(engine)
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(
        jobs,
        "ask",
        lambda *args: {
            "title": "Making plans",
            "subtitle": "A practical exchange",
            "emoji": "🗓️",
            "eras": [],
            "summary": "They keep making room for one another.",
            "suggestion": "Keep checking in.",
            "finding_ids": [],
        },
    )
    yield TestClient(app)
    Base.metadata.drop_all(engine)


def imported(client, consent=True):
    r = client.post(
        "/api/import",
        files={
            "file": (
                "whatsapp_group.txt",
                (ROOT / "examples/whatsapp_group.txt").read_bytes(),
            )
        },
        data={
            "current_user_index": "0",
            "ai_consent": str(consent).lower(),
            "chat_timezone": "UTC",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def due(cid):
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        job.available_at = jobs.now() - timedelta(seconds=1)
        db.commit()


def test_durable_queue_resume_cache_and_cascade(client, monkeypatch):
    cid = imported(client)
    assert client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "queued"
    calls = []

    def generate(task, packet, settings):
        calls.append([m["id"] for m in packet["samples"]])
        return SynthesisOutput(insights=[]), {"input_tokens": 200, "output_tokens": 40}

    monkeypatch.setattr(gemini, "generate", generate)
    assert jobs.step()  # local report persisted before network
    with SessionLocal() as db:
        assert db.get(AnalysisJob, cid).result["local"]["title"]
    for _ in range(10):
        due(cid)
        jobs.step()
        if (
            client.get(f"/api/conversations/{cid}/analysis").json()["status"]
            == "completed"
        ):
            break
    state = client.get(f"/api/conversations/{cid}/analysis").json()
    assert state["status"] == "completed"
    assert state["progress"]["processed"] == state["progress"]["total"]
    assert len(calls) >= 1
    report = client.get(f"/api/conversations/{cid}/report").json()
    assert report["cover"]["title"] == "Making plans"
    assert report["verdict"]["summary"] == "They keep making room for one another."
    # Navigating/reading completed results makes no additional provider calls.
    client.get(f"/api/conversations/{cid}/report")
    before = len(calls)
    client.post(f"/api/conversations/{cid}/analysis", json={"consent": True})
    assert not jobs.step() and len(calls) == before
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    with SessionLocal() as db:
        assert db.get(AnalysisJob, cid) is None
        assert not db.scalars(
            select(Message).where(Message.conversation_id == cid)
        ).all()


def test_rate_limit_checkpoint_survives_and_resumes(client, monkeypatch):
    cid = imported(client)
    jobs.step()
    due(cid)
    jobs.step()  # orientation
    monkeypatch.setattr(
        gemini,
        "generate",
        lambda *args: (_ for _ in ()).throw(gemini.RetryableError("rate limited", 600)),
    )
    due(cid)
    jobs.step()
    state = client.get(f"/api/conversations/{cid}/analysis").json()
    assert state["status"] == "retry" and state["progress"]["processed"] == 0
    assert not jobs.step()  # backoff stored in DB, not browser timer
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        job.status = "running"
        job.available_at = jobs.now() - timedelta(minutes=20)
        db.commit()
    monkeypatch.setattr(
        gemini, "generate", lambda *args: (SynthesisOutput(insights=[]), {})
    )
    jobs.step()  # expired lease reclaimed after worker crash
    assert (
        client.get(f"/api/conversations/{cid}/analysis").json()["progress"]["processed"]
        > 0
    )


def test_local_only_never_calls_provider_and_settings_hide_key(client, monkeypatch):
    cid = imported(client, False)
    monkeypatch.setattr(gemini, "generate", lambda *args: pytest.fail("No consent"))
    jobs.step()
    assert (
        client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "completed"
    )
    assert (
        client.post(
            f"/api/conversations/{cid}/ask", json={"question": "What happened?"}
        ).status_code
        == 403
    )
    response = client.patch("/api/settings/ai", json={"api_key": "secret-test"})
    assert response.status_code == 200
    assert "secret-test" not in response.text and "api_key" not in response.json()
    assert client.get("/api/settings/ai").json()["configured"]
    assert client.patch("/api/settings/ai", json={"input_budget": 1}).status_code == 422


def test_deleted_job_cannot_be_resurrected(client):
    cid = imported(client)
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        job.progress = {"claim": "first"}
        db.commit()
    jobs.checkpoint(cid, "stale", {"processed": 99}, {}, "completed", 0)
    assert client.get(f"/api/conversations/{cid}/analysis").json()["progress"] == {
        "claim": "first"
    }
    client.delete(f"/api/conversations/{cid}")
    jobs.checkpoint(cid, "first", {}, {}, "completed", 0)
    with SessionLocal() as db:
        assert db.get(Conversation, cid) is None and db.get(AnalysisJob, cid) is None


def test_gif_is_media_but_sentence_about_marker_is_text(tmp_path):
    path = tmp_path / "chat.txt"
    path.write_text(
        "12/08/2026, 19:42 - A: GIF omitted\n12/08/2026, 19:43 - B: I see gif omitted in the export\n12/08/2026, 19:44 - A: <GIF omitted>"
    )
    chat = WhatsAppParser().parse(path)[0]
    assert [m.message_type for m in chat.messages] == ["video", "text", "video"]
    assert chat.messages[0].text is None and chat.messages[0].attachments


def test_long_multilingual_passages_cover_every_message(client, monkeypatch):
    monkeypatch.setenv("GEMINI_INPUT_BUDGET", "12000")
    from datetime import datetime, timezone
    from app.schemas.chat import ParsedConversation, Message as NormalizedMessage
    from app.services.imports import persist_conversation

    c = ParsedConversation(platform="whatsapp", title="Multilingual synthetic coverage")
    c.messages = [
        NormalizedMessage(
            sender_name="A" if i % 2 else "B",
            text="नमस्ते 世界 🌷" * 80,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i),
        )
        for i in range(48)
    ]
    c.finalize()
    with SessionLocal() as db:
        persist_conversation(db, c)
        jobs.enqueue(db, c.id, True)
        db.commit()
    observed = set()

    def generate(task, packet, settings):
        observed.update(m["id"] for m in packet["samples"])
        assert all("नमस्ते" in m["text"] for m in packet["samples"])
        return SynthesisOutput(insights=[]), {}

    monkeypatch.setattr(gemini, "generate", generate)
    for _ in range(60):
        due(c.id)
        jobs.step()
        if (
            client.get(f"/api/conversations/{c.id}/analysis").json()["status"]
            == "completed"
        ):
            break
    assert observed == {m.id for m in c.messages}
    assert (
        client.get(f"/api/conversations/{c.id}/analysis").json()["status"]
        == "completed"
    )


def test_questions_are_conversation_scoped_and_citations_checked(client, monkeypatch):
    import app.api.analysis as analysis

    cid = imported(client)
    other = imported(client)
    with SessionLocal() as db:
        other_id = db.scalar(select(Message.id).where(Message.conversation_id == other))
    seen = []

    def ask(task, context, settings):
        if "terms" in task:
            return {"terms": ["weekend"]}
        seen.extend(m["id"] for m in context["messages"])
        return {
            "answer": "They plan a weekend project.",
            "evidence_ids": [seen[0], other_id],
        }

    monkeypatch.setattr(analysis, "ask", ask)
    response = client.post(
        f"/api/conversations/{cid}/ask", json={"question": "What are they planning?"}
    )
    assert response.status_code == 200, response.text
    assert other_id not in seen and response.json()["evidence_ids"] == [seen[0]]
    assert (
        client.post(
            f"/api/conversations/{cid}/ask",
            json={"question": "Explain", "finding_id": "not-this-chat"},
        ).status_code
        == 404
    )


def test_upload_consent_upgrade_and_nonblocking_report(client, monkeypatch):
    cid = imported(client, False)
    import app.api.reports as reports

    original = reports.load
    monkeypatch.setattr(
        reports,
        "load",
        lambda *args: pytest.fail("Queued report must not compute in request"),
    )
    response = client.get(f"/api/conversations/{cid}/report?queued=true")
    assert response.status_code == 202 and response.json()["pending"]
    client.post(f"/api/conversations/{cid}/analysis", json={"consent": True})
    with SessionLocal() as db:
        assert db.get(AnalysisJob, cid).options["ai"] is True
    monkeypatch.setattr(reports, "load", original)
    jobs.step()
    assert client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "queued"


def test_consent_during_local_claim_and_after_local_completion(client):
    cid = imported(client, False)
    jobs.step()
    assert (
        client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "completed"
    )
    client.post(f"/api/conversations/{cid}/analysis", json={"consent": True})
    assert client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "queued"
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        progress, result = job.progress, job.result
    jobs.checkpoint(cid, progress["claim"], progress, result, "completed", 0)
    assert client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "queued"


def test_editorial_checkpoints_without_reprocessing_or_deleting_minor_moments(
    client, monkeypatch
):
    from app.synthesis import editorial

    cid = imported(client)
    jobs.step()
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        job.progress = {**job.progress, "processed": job.progress["total"]}
        minor = {
            "id": "small",
            "title": "Checking in",
            "description": "An ordinary greeting",
            "source_quotes": [],
            "evidence_ids": [],
        }
        job.result = {
            **job.result,
            "behaviors": {"version": 1},
            "initial_cover": True,
            "cover": {"title": "Synthetic", "eras": []},
            "moments": [minor],
            "synthesis": {"insights": [minor]},
        }
        db.commit()
    monkeypatch.setattr(
        gemini, "generate", lambda *args: pytest.fail("Must not reread messages")
    )
    calls = []

    def classify(*args):
        calls.append(1)
        return {"moments": [{"id": "small", "kind": "sweet", "score": 2}]}

    monkeypatch.setattr(editorial, "ask", classify)
    due(cid)
    jobs.step()
    with SessionLocal() as db:
        job = db.get(AnalysisJob, cid)
        assert job.result["moments"][0]["display_score"] == 2
        assert job.result["synthesis"]["insights"][0]["id"] == "small"
        assert job.progress["processed"] == job.progress["total"]
    seen = []

    def verdict(task, context, settings):
        seen.extend(context["findings"])
        return {
            "summary": "A brief exchange.",
            "suggestion": "",
            "finding_ids": ["small"],
        }

    monkeypatch.setattr(jobs, "ask", verdict)
    due(cid)
    jobs.step()
    assert len(calls) == 1 and any(f["id"] == "small" for f in seen)
    assert (
        client.get(f"/api/conversations/{cid}/analysis").json()["status"] == "completed"
    )
