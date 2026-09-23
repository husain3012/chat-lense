from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, engine
from app.services import jobs
from app.services.wraps import WrapRequest, slides, document
from app.api import exports


def test_wrap_escapes_content_and_aliases_without_corrupting_words():
    data = {
        "snapshot": {"messages": 12, "active_days": 2},
        "synthesis": None,
        "insights": [
            {
                "id": "x",
                "title": "Ann and A",
                "category": "<img src=x>",
                "description": "Ann likes an anniversary. A agrees. <script>alert(1)</script>",
                "source": "ai",
            }
        ],
    }
    people = [SimpleNamespace(display_name="A"), SimpleNamespace(display_name="Ann")]
    result = slides(data, people, WrapRequest(finding_ids=["x", "x"]))
    assert len(result) == 3
    assert result[1]["title"] == "Person 2 and Person 1"
    assert "anniversary" in result[1]["body"]
    assert "Person 2 likes" in result[1]["body"]
    markup = document(result)
    assert "<script>" not in markup and "<img src=x>" not in markup
    assert "&lt;script&gt;" in markup
    assert "AI interpretation" in markup
    with pytest.raises(ValueError):
        slides(data, people, WrapRequest(finding_ids=["someone-elses-finding"]))


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)


def test_long_multilingual_readings_continue_without_losing_text():
    body = "नमस्ते世界" * 240
    report = {
        "insights": [
            {
                "id": "long",
                "title": "A long reading",
                "description": body,
                "caveat": "Keep the surrounding context.",
                "source": "ai",
            }
        ]
    }
    result = slides(report, [], WrapRequest(finding_ids=["long"]))
    readings = result[1:-1]
    assert len(readings) > 1
    assert "".join(s["body"] for s in readings) == body
    assert all(len(s["body"]) <= 650 for s in readings)
    assert readings[-1]["caveat"] == "Keep the surrounding context."
    assert result[-1]["number"] == len(result)


def test_final_perspective_requires_selection_and_aliases_can_be_disabled():
    report = {"verdict": {"summary": "Alice shows up.", "suggestion": "Keep talking."}}
    people = [SimpleNamespace(display_name="Alice")]
    assert len(slides(report, people, WrapRequest())) == 2
    result = slides(report, people, WrapRequest(aliases=False, include_verdict=True))
    assert result[1]["body"] == "Alice shows up."
    assert "perspective, not a diagnosis" in result[1]["note"]


def test_export_api_readiness_scope_limits_and_cleanup(client, monkeypatch):
    sample = Path(__file__).resolve().parents[1] / "examples/telegram_story_group.json"
    cid = client.post(
        "/api/import",
        files={"file": (sample.name, sample.read_bytes())},
        data={"current_user_index": "0"},
    ).json()["id"]
    base = f"/api/conversations/{cid}/export"
    assert client.post(base + "/preview", json={}).status_code == 409
    jobs.step()
    report = client.get(f"/api/conversations/{cid}/report").json()
    fid = report["insights"][0]["id"]
    preview = client.post(base + "/preview", json={"finding_ids": [fid]}).json()
    assert preview["count"] == 3 and preview["duration"] == 18
    assert (
        client.post(base + "/preview", json={"finding_ids": ["foreign"]}).status_code
        == 422
    )
    assert (
        client.post(
            base + "/preview", json={"palette": "url(https://attacker)"}
        ).status_code
        == 422
    )
    assert (
        client.post(base + "/mp4", json={"finding_ids": [fid] * 9}).status_code == 422
    )
    assert (
        client.post(base + "/preview", json={"finding_ids": [fid] * 51}).status_code
        == 422
    )
    assert (
        client.post("/api/conversations/missing/export/preview", json={}).status_code
        == 404
    )
    folders = []

    def renderer(items, format, folder, seconds):
        folders.append(folder)
        output = folder / f"chatlens-wrap.{format}"
        output.write_bytes(b"%PDF-1.7 synthetic mock")
        return output

    monkeypatch.setattr(exports, "render", renderer)
    response = client.post(base + "/pdf", json={"finding_ids": [fid]})
    assert (
        response.status_code == 200
        and response.headers["content-type"] == "application/pdf"
    )
    assert response.headers["cache-control"] == "no-store"
    assert not folders[-1].exists()

    def broken(*args):
        folders.append(args[2])
        raise RuntimeError("private text must not leak")

    monkeypatch.setattr(exports, "render", broken)
    response = client.post(base + "/pdf", json={})
    assert response.status_code == 503 and "private text" not in response.text
    assert not folders[-1].exists()
    assert exports._renderer.acquire(blocking=False)
    exports._renderer.release()
