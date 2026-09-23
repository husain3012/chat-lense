"""Opt-in integration/performance check against a running Docker Compose stack.
Run: cd backend && uv run python ../tests/smoke_compose.py [--large]
Creates synthetic conversations and deletes only those created by this run.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--large", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
with httpx.Client(base_url="http://localhost:3000/api", timeout=300) as client:
    content = (root / "examples/whatsapp_group.txt").read_bytes()
    if args.large:
        start = datetime(2024, 1, 1)
        content = "\n".join(
            f"{(start + timedelta(minutes=i)).strftime('%d/%m/%Y, %H:%M')} - {'Alice' if i % 2 else 'Sam'}: Synthetic benchmark message {i}"
            for i in range(100_000)
        ).encode()
    files = {"file": ("synthetic.txt", content)}
    started = perf_counter()
    detection = client.post("/import/detect", files=files)
    detection.raise_for_status()
    assert detection.json()["platform"] == "whatsapp"
    preview = client.post("/import/preview", files=files)
    preview.raise_for_status()
    count = preview.json()["conversations"][0]["message_count"]
    response = client.post(
        "/import", files=files, data={"current_user_index": 0, "chat_timezone": "UTC"}
    )
    response.raise_for_status()
    cid = response.json()["id"]
    imported = perf_counter()
    try:
        a = client.get(f"/conversations/{cid}/analytics")
        a.raise_for_status()
        assert a.json()["total_messages"] == count
        analyzed = perf_counter()
        p = client.get(f"/conversations/{cid}/participants").json()
        page = client.get(
            f"/conversations/{cid}/messages", params={"page": 2, "page_size": 10}
        ).json()
        assert len(page["items"]) == 10
        assert all(
            m["sender_id"] == p[0]["id"]
            for m in client.get(
                f"/conversations/{cid}/messages", params={"participant": p[0]["id"]}
            ).json()["items"]
        )
        query = "99999" if args.large else "coffee"
        assert (
            client.get(f"/conversations/{cid}/messages", params={"q": query}).json()[
                "total"
            ]
            == 1
        )
        print(
            {
                "messages": count,
                "detect_preview_import_seconds": round(imported - started, 2),
                "analytics_seconds": round(analyzed - imported, 2),
                "pagination_search_filter": "passed",
            }
        )
    finally:
        deleted = client.delete(f"/conversations/{cid}")
        deleted.raise_for_status()
        assert client.get(f"/conversations/{cid}").status_code == 404
