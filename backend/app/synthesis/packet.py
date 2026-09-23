"""Language-neutral conversation windows and compact provider transport."""

import json
from datetime import timezone

MAX_MESSAGES = 1200
MAX_TEXT = 2000
MAX_PACKET_BYTES = 480_000
WINDOW_SIZE = 60


def build_packet(report, messages, participants, *, full_passage=False):
    eligible = sorted(
        (m for m in messages if m.sender_id and m.message_type != "system"),
        key=lambda m: (m.timestamp, m.sequence, m.id),
    )
    position = {m.id: i for i, m in enumerate(eligible)}
    chosen = set()
    if full_passage or len(eligible) <= MAX_MESSAGES:
        chosen.update(range(len(eligible)))
    else:
        # Whole passages across the history, not isolated lines picked by English keywords.
        for j in range(12):
            start = round(j * (len(eligible) - WINDOW_SIZE) / 11)
            chosen.update(range(start, min(start + WINDOW_SIZE, len(eligible))))
        for insight in sorted(report.insights, key=lambda i: -i.score):
            for mid in insight.evidence_ids[:2]:
                if mid not in position or len(chosen) >= MAX_MESSAGES:
                    continue
                start = max(0, position[mid] - WINDOW_SIZE // 2)
                for index in range(start, min(start + WINDOW_SIZE, len(eligible))):
                    if len(chosen) < MAX_MESSAGES:
                        chosen.add(index)
    samples = []
    previous = None
    window = 0
    for index in sorted(chosen):
        m = eligible[index]
        # Explicitly mark missing stretches so the model cannot join them.
        if previous is None or index != previous + 1:
            window += 1
        t = (
            m.timestamp.replace(tzinfo=timezone.utc)
            if m.timestamp.tzinfo is None
            else m.timestamp
        )
        samples.append(
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "timestamp": t.isoformat(),
                "text": (m.text or "")[:MAX_TEXT],
                "truncated": len(m.text or "") > MAX_TEXT,
                "type": m.message_type,
                "reply_to_source_id": m.reply_to_id,
                "window": window,
            }
        )
        previous = index
    facts = {
        i.id: {
            "title": i.title,
            "description": i.description,
            "facts": [f.model_dump() for f in i.facts],
            "method": i.method,
            "comparison": [p.model_dump() for p in i.visual],
            "participant_ids": i.participant_ids,
            "evidence_ids": i.evidence_ids,
        }
        for i in report.insights
    }
    packet = {
        "conversation_id": report.conversation_id,
        "tone": report.tone,
        "timezone": report.timezone,
        "snapshot": report.snapshot,
        "participants": [{"id": p.id, "name": p.display_name} for p in participants],
        "measured_findings": facts,
        "timeline": [p.model_dump() for p in report.timeline],
        "samples": samples,
        "coverage": {
            "sampled_messages": len(samples),
            "eligible_messages": len(eligible),
            "max_text_characters": MAX_TEXT,
            "sampling": "Contiguous passages spread across the history plus measured-event neighborhoods. Window changes mark missing context; timestamps preserve pauses. No language detection, stop-word removal, translation or sentiment keywords.",
        },
    }
    # Reduce evenly across the history, dropping whole passages where possible.
    while (
        not full_passage
        and len(json.dumps(packet, ensure_ascii=False).encode()) > MAX_PACKET_BYTES
        and packet["samples"]
    ):
        windows = list(dict.fromkeys(m["window"] for m in packet["samples"]))
        if len(windows) > 1:
            remove = set(windows[1::2])
            packet["samples"] = [
                m for m in packet["samples"] if m["window"] not in remove
            ]
        else:
            packet["samples"] = packet["samples"][: len(packet["samples"]) // 2]
    packet["coverage"]["sampled_messages"] = len(packet["samples"])
    if (
        not full_passage
        and len(json.dumps(packet, ensure_ascii=False).encode()) > MAX_PACKET_BYTES
    ):
        raise ValueError(
            "Report metadata exceeds the bounded synthesis packet size; use a smaller conversation."
        )
    return packet


def partitions(packet):
    samples = packet["samples"]
    count = min(4, max(1, (len(samples) + 299) // 300))
    size = max(1, (len(samples) + count - 1) // count)
    # Overlap adjacent chunks to retain context when a passage crosses a boundary.
    return [
        {
            **packet,
            "samples": samples[max(0, start - 6) : min(len(samples), start + size + 6)],
        }
        for start in range(0, len(samples), size)
    ]


def compact_packet(packet):
    """Short reversible IDs and columnar rows save tokens without altering any language."""
    mids = {m["id"]: f"m{i}" for i, m in enumerate(packet["samples"])}
    pids = {p["id"]: f"p{i}" for i, p in enumerate(packet["participants"])}
    facts = {
        key: {
            k: v
            for k, v in item.items()
            if k not in ("evidence_ids", "participant_ids", "method")
        }
        for key, item in packet["measured_findings"].items()
    }
    data = {
        "tone": packet["tone"],
        "timezone": packet["timezone"],
        "coverage": packet["coverage"],
        "people": {pids[p["id"]]: p["name"] for p in packet["participants"]},
        "columns": [
            "id",
            "speaker",
            "time",
            "original_text",
            "type",
            "window",
            "truncated",
        ],
        "messages": [
            [
                mids[m["id"]],
                pids.get(m["sender_id"], "?"),
                m["timestamp"],
                m["text"],
                m["type"],
                m.get("window", 0),
                m["truncated"],
            ]
            for m in packet["samples"]
        ],
        "measured_findings": facts,
    }
    if "window_candidates" in packet:
        candidates = []
        for candidate in packet["window_candidates"]:
            candidates.append(
                {
                    k: v
                    for k, v in candidate.items()
                    if k
                    in (
                        "family",
                        "title",
                        "description",
                        "category",
                        "moment_kind",
                        "caveat",
                    )
                }
                | {
                    "evidence_ids": [
                        mids[mid] for mid in candidate["evidence_ids"] if mid in mids
                    ],
                    "quotes": [
                        {"message_id": mids[q["message_id"]], "text": q["text"]}
                        for q in candidate.get("source_quotes", [])
                        if q["message_id"] in mids
                    ],
                }
            )
        data["window_candidates"] = candidates
    return data, {v: k for k, v in mids.items()}
