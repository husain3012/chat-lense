"""Server-owned settings. Credentials never appear in read responses."""

import os
from app.models.database import SessionLocal
from app.models.chat import AppSetting


def read():
    values = {
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "interval_seconds": float(os.getenv("GEMINI_INTERVAL_SECONDS", "2")),
        "max_retries": int(os.getenv("GEMINI_MAX_RETRIES", "8")),
        "input_budget": int(os.getenv("GEMINI_INPUT_BUDGET", "240000")),
        "output_tokens": int(os.getenv("GEMINI_OUTPUT_TOKENS", "8192")),
        "chunk_messages": int(os.getenv("GEMINI_CHUNK_MESSAGES", "2000")),
    }
    with SessionLocal() as db:
        row = db.get(AppSetting, "ai")
        if row:
            values.update(row.value)
    return values


def public():
    values = read()
    return {k: v for k, v in values.items() if k != "api_key"} | {
        "configured": bool(values["api_key"])
    }
