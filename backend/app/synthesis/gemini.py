import json
import os
import re
import httpx
from pydantic import ValidationError
from app.synthesis.contracts import Interpretation, SynthesisOutput
from app.synthesis.prompts import SYSTEM
from app.synthesis.packet import compact_packet, MAX_MESSAGES, MAX_TEXT


class ProviderError(Exception):
    pass


class RetryableError(ProviderError):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


class UnreadableResponseError(RetryableError):
    """The provider replied, but not with a usable structured envelope."""


def parse_output(text):
    """Keep valid findings even if Gemini emits one locally invalid item.

    Gemini's response schema is intentionally smaller than our local Pydantic
    contract. For example, the API schema does not enforce our two-citation
    minimum. Rejecting the whole passage for one such item can permanently
    stall a job at its final, often sparse, batch.
    """
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        payload = json.loads(candidate)
    except (TypeError, json.JSONDecodeError) as exc:
        raise UnreadableResponseError(
            "Gemini returned malformed JSON; analysis will retry this saved passage."
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("insights"), list):
        raise UnreadableResponseError(
            "Gemini returned an invalid response envelope; analysis will retry this saved passage."
        )
    insights = []
    rejected = 0
    for raw in payload["insights"]:
        try:
            insights.append(Interpretation.model_validate(raw))
        except (ValidationError, TypeError):
            rejected += 1
    return SynthesisOutput(insights=insights), rejected


def response_schema():
    """Compact Gemini Schema subset; enforce all limits locally with Pydantic."""
    schema = SynthesisOutput.model_json_schema()

    def compact(node):
        if "$ref" in node:
            return compact(schema["$defs"][node["$ref"].split("/")[-1]])
        result = {
            key: value
            for key, value in node.items()
            if key in ("type", "enum", "required", "description")
        }
        if "properties" in node:
            result["properties"] = {
                name: compact(value) for name, value in node["properties"].items()
            }
            if "quotes" in node["properties"]:
                result["required"] = list(
                    dict.fromkeys([*result.get("required", []), "quotes"])
                )
        if "items" in node:
            result["items"] = compact(node["items"])
        return result

    return compact(schema)


def config():
    return {
        "provider": "gemini",
        "configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "max_messages": MAX_MESSAGES,
        "max_text_characters": MAX_TEXT,
        "max_calls": 5,
        "consent_required": True,
    }


def generate(task, packet, settings=None):
    settings = settings or {}
    key = settings.get("api_key", os.getenv("GEMINI_API_KEY", "")).strip()
    if not key:
        raise ProviderError(
            "Gemini is not configured. Set GEMINI_API_KEY in the root .env and recreate the backend container."
        )
    model = settings.get("model", config()["model"])
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model):
        raise ProviderError("Invalid GEMINI_MODEL configuration.")
    compact, message_ids = compact_packet(packet)
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": task
                        + "\n"
                        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 1,
            "maxOutputTokens": settings.get("output_tokens", 16384),
            "responseMimeType": "application/json",
            "responseSchema": response_schema(),
        },
    }
    if model.startswith("gemini-3"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "low"}
    try:
        with httpx.Client(
            timeout=httpx.Timeout(90, connect=10), follow_redirects=False
        ) as client:
            response = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json=body,
            )
        if response.status_code in (401, 403):
            raise ProviderError(
                "Gemini rejected the API key or its permissions. Check backend configuration."
            )
        if response.status_code == 429:
            retry = response.headers.get("retry-after", "60")
            raise RetryableError(
                "Gemini rate limit reached; analysis will retry.",
                min(86400, float(retry)) if retry.isdigit() else 60,
            )
        if response.status_code == 404:
            raise ProviderError(
                "Configured Gemini model is unavailable. Set GEMINI_MODEL to a model available to your API key."
            )
        if response.status_code in (500, 502, 503, 504):
            raise RetryableError(
                "Gemini is temporarily unavailable or experiencing high demand. Try again later, or configure another available GEMINI_MODEL. Your local report is unchanged."
            )
        if response.status_code == 400:
            raise ProviderError(
                "Gemini rejected the request format. Check the configured model’s structured-output support. Your local report is unchanged."
            )
        if response.status_code >= 400:
            raise ProviderError(
                "Gemini could not complete this request. The local report is unchanged."
            )
        data = response.json()
        candidate = data.get("candidates", [{}])[0]
        if candidate.get("finishReason") == "MAX_TOKENS":
            raise ProviderError(
                "Gemini reached its output limit before finishing. No partial interpretation was saved; try again."
            )
        if candidate.get("finishReason") not in (None, "STOP"):
            raise ProviderError(
                "Gemini returned an incomplete or blocked response; no partial interpretation was saved."
            )
        text = "".join(
            p.get("text", "")
            for p in candidate.get("content", {}).get("parts", [])
            if not p.get("thought")
        )
        parsed, malformed = parse_output(text)
        for item in parsed.insights:
            item.evidence_ids = [
                message_ids.get(mid, "unknown:" + mid) for mid in item.evidence_ids
            ]
            for quote in item.quotes:
                quote.message_id = message_ids.get(
                    quote.message_id, "unknown:" + quote.message_id
                )
        usage = data.get("usageMetadata", {})
        return parsed, {
            "input_tokens": usage.get("promptTokenCount", 0),
            "output_tokens": usage.get("candidatesTokenCount", 0),
            "malformed_insights": malformed,
        }
    except ProviderError:
        raise
    except httpx.TimeoutException as e:
        raise RetryableError(
            "Gemini timed out. Your local report remains available."
        ) from e
    except httpx.HTTPError as e:
        raise RetryableError("Gemini connection failed; analysis will retry.") from e
    except (ValueError, KeyError, IndexError) as e:
        raise UnreadableResponseError(
            "Gemini returned an unreadable result; analysis will retry this saved passage."
        ) from e
