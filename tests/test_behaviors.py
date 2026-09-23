from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from app.synthesis import behaviors
from app.synthesis.gemini import RetryableError


def rows():
    return [
        SimpleNamespace(
            id=f"m{i}",
            sender_id="a" if i % 2 == 0 else "b",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            text=text,
            message_type="text",
        )
        for i, text in enumerate(["मुझे भूख लगी है", "我喜欢下棋", "Te quiero"])
    ]


def test_multilingual_counts_deduplicate_overlap_and_keep_evidence(monkeypatch):
    def ask(task, context, settings):
        assert context["messages"][0]["text"] == "मुझे भूख लगी है"
        return {
            "through": 2,
            "events": [[0, "hunger"], [0, "hunger"], [2, "affection"], [99, "money"]],
            "interests": [[1, "Chess"]],
        }

    monkeypatch.setattr(behaviors, "ask", ask)
    state = behaviors.classify(rows(), 0, 0, {}, {"input_budget": 12000})
    assert state["categories"]["hunger"]["a"] == {"count": 1, "evidence_ids": ["m0"]}
    assert state["interests"]["chess"]["b"]["count"] == 1
    assert "money" not in state["categories"]
    assert state["participant_messages"] == {"a": 2, "b": 1}
    # Only the new part of an overlapping passage is counted.
    state = behaviors.classify(rows(), 0, 2, {}, {"input_budget": 12000})
    assert list(state["categories"]) == ["affection"]
    assert not state["interests"]


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"through": 1, "events": [], "interests": []},
        {"through": 2, "events": [[0, "diagnosis"]], "interests": []},
        {"through": 2, "events": [[True, "hunger"]], "interests": []},
    ],
)
def test_bad_responses_leave_checkpoint_untouched(monkeypatch, response):
    monkeypatch.setattr(behaviors, "ask", lambda *args: response)
    saved = {"processed": 0, "categories": {}}
    with pytest.raises(RetryableError):
        behaviors.classify(rows(), 0, 0, saved, {"input_budget": 12000})
    assert saved == {"processed": 0, "categories": {}}
