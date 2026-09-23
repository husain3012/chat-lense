import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.models.database import Base, engine, SessionLocal
from app.models.chat import SynthesisRun
from app.synthesis.contracts import SynthesisOutput, Interpretation
from app.synthesis import gemini

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)


def imported(client, name="telegram_story_group.json"):
    response = client.post(
        "/api/import",
        files={"file": (name, (ROOT / "examples" / name).read_bytes())},
        data={"current_user_index": "0", "chat_timezone": "UTC"},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_report_evidence_scope_and_config(client):
    cid = imported(client)
    response = client.get(f"/api/conversations/{cid}/report")
    assert response.status_code == 200, response.text
    report = response.json()
    assert len(report["insights"]) >= 20
    ids = report["insights"][0]["evidence_ids"]
    evidence = client.get(
        f"/api/conversations/{cid}/evidence", params={"ids": ",".join(ids)}
    ).json()["items"]
    assert len(evidence) == len(ids)
    context = client.get(f"/api/conversations/{cid}/messages/{ids[0]}/context")
    assert context.status_code == 200 and len(context.json()["items"]) <= 61
    other = imported(client, "telegram_direct.json")
    assert (
        client.get(
            f"/api/conversations/{other}/evidence", params={"ids": ",".join(ids)}
        ).json()["items"]
        == []
    )
    assert (
        client.get(f"/api/conversations/{other}/messages/{ids[0]}/context").status_code
        == 404
    )
    assert (
        client.get(
            f"/api/conversations/{cid}/report", params={"timezone": "not/a/timezone"}
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/conversations/{cid}/report", params={"tone": "insulting"}
        ).status_code
        == 422
    )
    config = client.get("/api/analysis/config").json()
    assert "api_key" not in config


def test_synthesis_opt_in_cache_and_cascade(client, monkeypatch):
    cid = imported(client)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    endpoint = f"/api/conversations/{cid}/report/synthesize"
    assert client.post(endpoint, json={"consent": False}).status_code == 422
    assert client.post(endpoint, json={"consent": True}).status_code == 503
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    calls = []

    def provider(task, packet):
        calls.append(task)
        quoted = next(m for m in packet["samples"] if len(m["text"].split()) >= 5)
        return SynthesisOutput(
            insights=[
                Interpretation(
                    family="links-as-proposals",
                    title="The plan arrives as a link",
                    description=f"The sampled exchange includes “{quoted['text'][:80]}”. This frames a proposal for the group to explore.",
                    category="Topic habits",
                    evidence_ids=[
                        quoted["id"],
                        next(
                            m["id"]
                            for m in packet["samples"]
                            if m["id"] != quoted["id"]
                        ),
                    ],
                    fact_ids=[],
                    novelty=8,
                    section="topics",
                    caveat="A reading of sampled messages, not the full history.",
                )
            ]
        ), {"input_tokens": 100, "output_tokens": 50}

    monkeypatch.setattr(gemini, "generate", provider)
    result = client.post(endpoint, json={"consent": True})
    assert result.status_code == 200, result.text
    data = result.json()
    assert len(data["insights"]) == 1 and len(calls) <= 5
    before = len(calls)
    assert client.post(endpoint, json={"consent": True}).status_code == 200
    assert len(calls) == before
    report = client.get(f"/api/conversations/{cid}/report").json()
    assert report["synthesis"]["insights"][0]["evidence_ids"]
    assert all(i["source"] == "measured" for i in report["insights"])
    assert "test-key-not-real" not in json.dumps(data)
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SynthesisRun)) == 0


def test_provider_failure_preserves_local_report(client, monkeypatch):
    cid = imported(client, "telegram_direct.json")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fail(task, packet):
        raise gemini.ProviderError(
            "Gemini timed out. Your local report remains available."
        )

    monkeypatch.setattr(gemini, "generate", fail)
    result = client.post(
        f"/api/conversations/{cid}/report/synthesize", json={"consent": True}
    )
    assert result.status_code == 502
    assert client.get(f"/api/conversations/{cid}/report").status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SynthesisRun)) == 0


def test_provider_schema_preserves_fields_and_local_constraints():
    from app.synthesis.gemini import response_schema
    from app.synthesis.contracts import Interpretation
    from pydantic import ValidationError
    import pytest

    schema = response_schema()
    item = schema["properties"]["insights"]["items"]
    assert set(item["required"]) <= set(item["properties"])
    assert item["properties"]["title"]["type"] == "string"
    assert item["properties"]["section"]["enum"] == ["topics", "deep", "turning_points"]
    assert "$ref" not in str(schema) and "$defs" not in str(schema)
    with pytest.raises(ValidationError):
        Interpretation(
            family="test",
            title="x" * 91,
            description="test",
            category="test",
            evidence_ids=["a", "b"],
            novelty=5,
            caveat="sample",
        )


def test_provider_high_demand_error_is_actionable_and_does_not_echo_secrets(
    monkeypatch,
):
    import httpx
    import pytest
    from app.synthesis import gemini

    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-never-show")

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return httpx.Response(
                503, json={"error": {"message": "test-secret-never-show"}}
            )

    monkeypatch.setattr(gemini.httpx, "Client", Client)
    with pytest.raises(gemini.ProviderError, match="high demand") as error:
        gemini.generate(
            "test",
            {
                "samples": [],
                "participants": [],
                "measured_findings": {},
                "tone": "fun",
                "timezone": "UTC",
                "coverage": {},
            },
        )
    assert "test-secret-never-show" not in str(error.value)


def test_provider_parser_keeps_valid_items_and_discards_only_invalid_ones():
    from app.synthesis import gemini

    valid = {
        "family": "shared joke",
        "title": "The callback lands",
        "description": "A recurring joke gets a well-timed reply.",
        "category": "Funny moments",
        "evidence_ids": ["m1", "m2"],
        "fact_ids": [],
        "novelty": 7,
        "section": "deep",
        "caveat": "This reading uses the supplied exchange.",
        "moment_kind": "funny",
        "quotes": [{"message_id": "m1", "text": "the callback"}],
    }
    invalid = {**valid, "evidence_ids": ["m1"]}
    parsed, rejected = gemini.parse_output(
        "```json\n" + json.dumps({"insights": [invalid, valid]}) + "\n```"
    )
    assert len(parsed.insights) == 1
    assert parsed.insights[0].evidence_ids == ["m1", "m2"]
    assert rejected == 1


def test_provider_parser_retries_only_for_unusable_envelope():
    from app.synthesis import gemini

    with pytest.raises(gemini.UnreadableResponseError):
        gemini.parse_output("not json")
    with pytest.raises(gemini.UnreadableResponseError):
        gemini.parse_output(json.dumps({"answer": "wrong task"}))


def test_context_can_walk_entire_chat_in_both_directions(client):
    cid = imported(client, "whatsapp_group.txt")
    messages = client.get(f"/api/conversations/{cid}/messages?page_size=100").json()[
        "items"
    ]
    assert len(messages) > 6
    anchor = messages[len(messages) // 2]["id"]
    endpoint = f"/api/conversations/{cid}/messages"
    page = client.get(f"{endpoint}/{anchor}/context?limit=2").json()
    collected = page["items"]
    while page["has_before"]:
        page = client.get(
            f"{endpoint}/{collected[0]['id']}/context?direction=before&limit=2"
        ).json()
        collected = page["items"] + collected
    page = client.get(
        f"{endpoint}/{collected[-1]['id']}/context?direction=after&limit=2"
    ).json()
    collected += page["items"]
    while page["has_after"]:
        page = client.get(
            f"{endpoint}/{collected[-1]['id']}/context?direction=after&limit=2"
        ).json()
        collected += page["items"]
    assert [m["id"] for m in collected] == [m["id"] for m in messages]
    other = imported(client)
    assert (
        client.get(f"/api/conversations/{other}/messages/{anchor}/context").status_code
        == 404
    )
