"""Interpret timezone-less exports only after an explicit user choice."""

from datetime import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import HTTPException


def apply_timezone(chat, name, required=False):
    if chat.platform != "whatsapp":
        return
    if not name:
        if required:
            raise HTTPException(
                422, "Choose the WhatsApp chat's timezone before importing."
            )
        chat.metadata["timezone_required"] = True
        return
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Choose a valid IANA timezone, such as Asia/Kolkata.")
    ambiguous = 0
    for message in chat.messages:
        wall = message.timestamp.replace(tzinfo=None)
        localized = wall.replace(tzinfo=zone, fold=0)
        if (
            localized.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
            != wall
        ):
            raise HTTPException(
                422,
                "A timestamp falls in a daylight-saving clock gap. Check the chosen timezone.",
            )
        ambiguous += (
            localized.utcoffset() != wall.replace(tzinfo=zone, fold=1).utcoffset()
        )
        message.timestamp = localized.astimezone(timezone.utc)
    chat.metadata.update(source_timezone=name, timezone_required=False)
    chat.warnings = [w for w in chat.warnings if "timestamps have no timezone" not in w]
    chat.warnings.append(
        f"Chat timezone: {name}. Timestamps converted to UTC for storage."
    )
    if ambiguous:
        chat.warnings.append(
            f"{ambiguous} timestamps fall in a repeated daylight-saving hour; the first occurrence is used."
        )
    chat.finalize()
