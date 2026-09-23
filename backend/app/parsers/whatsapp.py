import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from app.parsers.base import ChatParser, files
from app.schemas.chat import Message, ParsedConversation

HEADER = re.compile(
    r"^\[?(\d{1,4}[/.-]\d{1,2}[/.-]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]\.?m\.?)?)\]?\s*(?:-\s*)?(.*)$",
    re.I,
)


def clean(value):
    return (
        value.replace("\u200e", "")
        .replace("\u200f", "")
        .replace("\ufeff", "")
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
    )


def system_event(text):
    value = clean(text).strip().lower()
    return bool(
        re.search(
            r"^(?:messages and calls are end-to-end encrypted\b|only messages that mention or people share with @meta ai\b|you pinned (?:a )?message$)",
            value,
        )
        or re.search(r"\badded you$", value)
    )


class WhatsAppParser(ChatParser):
    def __init__(self, date_order="auto"):
        self.date_order = date_order

    @classmethod
    def detect(cls, input_path):
        for p in files(input_path, ".txt"):
            with p.open(encoding="utf-8-sig", errors="replace") as f:
                if any(HEADER.match(clean(f.readline())) for _ in range(30)):
                    return 0.98
        return 0.0

    def parse(self, input_path: Path):
        result = []
        for path in files(input_path, ".txt"):
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            records = []
            preamble = 0
            for line in raw.splitlines():
                match = HEADER.match(clean(line))
                if match:
                    records.append(list(match.groups()))
                elif records:
                    records[-1][2] += "\n" + line
                elif line.strip():
                    preamble += 1
            if not records:
                continue
            order = self.date_order
            if order == "auto":
                order = "dmy"
                for date, _, _ in records:
                    a, b, _ = re.split(r"[/.-]", date)
                    if len(a) < 4 and int(b) > 12:
                        order = "mdy"
                        break
            c = ParsedConversation(
                platform="whatsapp",
                title=re.sub(r"^(WhatsApp Chat with |WhatsApp Chat - )", "", path.stem),
            )
            c.warnings.append(
                f"WhatsApp timestamps have no timezone; choose the chat timezone before importing. Date order: {order}."
            )
            if preamble:
                c.warnings.append(
                    f"Skipped {preamble} lines before the first timestamp."
                )
            system_labels = Counter()
            for date, clock, body in records:
                parts = re.split(r"[/.-]", date)
                fmt = (
                    "%Y/%m/%d"
                    if len(parts[0]) == 4
                    else ("%d/%m/" if order == "dmy" else "%m/%d/")
                    + ("%Y" if len(parts[2]) == 4 else "%y")
                )
                clock = clock.strip().upper().replace(".", "")
                clock = re.sub(r"\s*(AM|PM)$", r" \1", clock)
                time_fmt = "%I:%M" if clock.endswith(("AM", "PM")) else "%H:%M"
                if clock.count(":") == 2:
                    time_fmt += ":%S"
                if clock.endswith(("AM", "PM")):
                    time_fmt += " %p"
                try:
                    timestamp = datetime.strptime(
                        "/".join(parts) + " " + clock, fmt + " " + time_fmt
                    ).replace(tzinfo=timezone.utc)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid WhatsApp timestamp; try the other date order: {date} {clock}"
                    ) from e
                sender, text = body.split(": ", 1) if ": " in body else (None, body)
                kind = "text" if sender else "system"
                metadata = {}
                if sender and system_event(text):
                    system_labels[sender] += 1
                    metadata["export_system_label"] = sender
                    sender, kind = None, "system"
                lower = text.lower()
                attachments = []
                if sender:
                    for marker, media_type in [
                        ("image omitted", "image"),
                        ("video omitted", "video"),
                        ("gif omitted", "video"),
                        ("audio omitted", "audio"),
                        ("sticker omitted", "sticker"),
                        ("document omitted", "file"),
                        ("<media omitted>", "file"),
                        ("attached:", "file"),
                        ("(file attached)", "file"),
                    ]:
                        omitted = "omitted" in marker
                        matches = (
                            clean(lower).strip().strip("<>").strip()
                            == marker.strip("<>")
                            if omitted
                            else marker in lower
                        )
                        if matches:
                            kind = media_type
                            attachments = [{"reference": text, "available": False}]
                            if omitted:
                                text = None
                            break
                    if re.search(
                        r"^(missed |voice call|video call|group call|call ended)", lower
                    ):
                        kind = "call"
                    if lower in (
                        "this message was deleted",
                        "you deleted this message",
                    ):
                        kind = "other"
                if not sender and re.search(
                    r"created (?:this |the )?group|added | left$|joined |changed the subject",
                    lower,
                ):
                    c.conversation_type = "group"
                if not sender:
                    title_match = re.search(
                        r'(?:created (?:this |the )?group|changed the subject (?:from .+ )?to) ["“](.+?)["”]$',
                        text,
                        re.I,
                    )
                    if title_match:
                        c.title = title_match.group(1)
                c.messages.append(
                    Message(
                        timestamp=timestamp,
                        sender_name=sender,
                        text=text,
                        message_type=kind,
                        attachments=attachments,
                        metadata=metadata,
                    )
                )
            if c.title.casefold() in {"_chat", "chat"} and system_labels:
                c.title = system_labels.most_common(1)[0][0]
            result.append(c.finalize())
        return result
