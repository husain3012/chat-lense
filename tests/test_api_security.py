import io
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.models.database import Base, engine, SessionLocal
from app.models.chat import Message, Participant
from app.utils.uploads import prepare

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def client():
    Base.metadata.create_all(engine)
    yield TestClient(app)
    Base.metadata.drop_all(engine)


def test_acceptance(client):
    content = (EXAMPLES / "whatsapp_group.txt").read_bytes()
    files = {"file": ("whatsapp_group.txt", content, "text/plain")}
    assert (
        client.post("/api/import/detect", files=files).json()["platform"] == "whatsapp"
    )
    preview = client.post("/api/import/preview", files=files).json()["conversations"][0]
    assert preview["conversation_type"] == "group" and len(preview["participants"]) == 4
    response = client.post(
        "/api/import",
        files=files,
        data={
            "platform": "whatsapp",
            "current_user_index": "0",
            "chat_timezone": "UTC",
        },
    )
    assert response.status_code == 200, response.text
    cid = response.json()["id"]
    assert client.get("/api/conversations").json()["total"] == 1
    assert (
        client.get(f"/api/conversations/{cid}").json()["message_count"]
        == preview["message_count"]
    )
    people = client.get(f"/api/conversations/{cid}/participants").json()
    me = next(p for p in people if p["is_current_user"])
    messages = client.get(
        f"/api/conversations/{cid}/messages", params={"page_size": 2}
    ).json()
    assert len(messages["items"]) == 2 and messages["total"] > 2
    search = client.get(
        f"/api/conversations/{cid}/messages", params={"q": "coffee"}
    ).json()
    assert search["total"] == 1
    filtered = client.get(
        f"/api/conversations/{cid}/messages", params={"participant": me["id"]}
    ).json()
    assert all(m["sender_id"] == me["id"] for m in filtered["items"])
    assert (
        client.get(f"/api/conversations/{cid}/messages", params={"q": "%"}).json()[
            "total"
        ]
        == 0
    )
    analytics = client.get(f"/api/conversations/{cid}/analytics").json()
    assert analytics["total_messages"] == preview["message_count"]
    assert analytics["sessions"]["total"] > 0 and len(analytics["participants"]) == 4
    other = next(p for p in people if p["id"] != me["id"])
    assert (
        client.patch(
            f"/api/conversations/{cid}/participants/{other['id']}",
            json={"is_current_user": True},
        ).status_code
        == 200
    )
    assert (
        sum(
            p["is_current_user"]
            for p in client.get(f"/api/conversations/{cid}/participants").json()
        )
        == 1
    )
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Message)) == 0
        assert db.scalar(select(func.count()).select_from(Participant)) == 0


@pytest.mark.parametrize(
    "name",
    [
        "../escape.txt",
        "/absolute.txt",
        "folder/../../escape.txt",
        "..\\escape.txt",
        "C:/escape.txt",
    ],
)
def test_zip_traversal(tmp_path, name):
    p = tmp_path / "chat.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(name, "bad")
    with pytest.raises(ValueError):
        prepare(p)


def test_zip_bomb(tmp_path):
    p = tmp_path / "chat.zip"
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("chat.txt", "x" * 2_000_000)
    with pytest.raises(ValueError):
        prepare(p)


def test_zip_and_rejections(client, tmp_path):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("_chat.txt", (EXAMPLES / "whatsapp_group.txt").read_bytes())
        z.writestr("media.jpg", b"not-an-image")
    response = client.post(
        "/api/import/preview", files={"file": ("chat.zip", stream.getvalue())}
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/api/import/detect", files={"file": ("bad.exe", b"bad")}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/import/preview", files={"file": ("bad.json", b"invalid")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/import/preview", files={"file": ("bad.zip", b"invalid")}
        ).status_code
        == 422
    )
    assert client.get("/api/conversations/missing/messages").status_code == 404


@pytest.mark.parametrize(
    "filename",
    [
        "whatsapp_direct.txt",
        "telegram_direct.json",
        "telegram_group.json",
        "instagram_direct.json",
    ],
)
def test_all_json_imports(client, filename):
    files = {"file": (filename, (EXAMPLES / filename).read_bytes())}
    preview = client.post("/api/import/preview", files=files)
    assert preview.status_code == 200, preview.text
    saved = client.post(
        "/api/import",
        files=files,
        data={"current_user_index": "0", "chat_timezone": "UTC"},
    )
    assert saved.status_code == 200, saved.text
    cid = saved.json()["id"]
    analytics = client.get(f"/api/conversations/{cid}/analytics")
    assert analytics.status_code == 200
    assert analytics.json()["total_messages"] > 0
    if filename == "telegram_group.json":
        assert analytics.json()["interactions"]["signals"] == 3
        assert analytics.json()["reactions"]["total"] == 2
        network = client.get(f"/api/conversations/{cid}/reply-network").json()[
            "network"
        ]
        assert network["total_replies"] == 1
        assert network["edges"][0]["weight"] == 1
    assert client.delete(f"/api/conversations/{cid}").status_code == 204


def test_zip_symlink(tmp_path):
    p = tmp_path / "link.zip"
    info = zipfile.ZipInfo("chat.txt")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(info, "/etc/passwd")
    with pytest.raises(ValueError):
        prepare(p)


def test_request_size_guard(client):
    from app.utils.uploads import MAX_UPLOAD

    response = client.post(
        "/api/import/detect",
        content=b"",
        headers={"content-length": str(MAX_UPLOAD + 2 * 1024 * 1024)},
    )
    assert response.status_code == 413


def test_invalid_identity_does_not_save(client):
    response = client.post(
        "/api/import",
        files={"file": ("chat.txt", (EXAMPLES / "whatsapp_direct.txt").read_bytes())},
        data={"current_user_index": "999", "chat_timezone": "UTC"},
    )
    assert response.status_code == 422
    assert client.get("/api/conversations").json()["total"] == 0


def test_multiple_current_user_aliases_are_merged(client):
    content = (
        "01/01/2026, 09:00 - Husain: first\n"
        "01/01/2026, 09:01 - Alice: hello\n"
        "01/01/2026, 09:02 - You: second\n"
        "01/01/2026, 09:03 - Husain: third"
    )
    preview = client.post(
        "/api/import/preview",
        files={"file": ("aliases.txt", content.encode())},
        data={"chat_timezone": "UTC"},
    ).json()["conversations"][0]
    positions = {p["display_name"]: i for i, p in enumerate(preview["participants"])}
    response = client.post(
        "/api/import",
        files={"file": ("aliases.txt", content.encode())},
        data={
            "current_user_indices": f"{positions['You']},{positions['Husain']}",
            "chat_timezone": "UTC",
        },
    )
    assert response.status_code == 200, response.text
    cid = response.json()["id"]
    people = client.get(f"/api/conversations/{cid}/participants").json()
    assert len(people) == 2
    current = next(p for p in people if p["is_current_user"])
    assert current["display_name"] == "Husain"
    messages = client.get(f"/api/conversations/{cid}/messages").json()["items"]
    own = [m for m in messages if m["sender_id"] == current["id"]]
    assert len(own) == 3 and {m["sender_name"] for m in own} == {"Husain"}
    conversation = client.get(f"/api/conversations/{cid}").json()
    assert conversation["metadata"]["current_user_aliases"] == ["Husain", "You"]


def test_invalid_multiple_identity_selection_does_not_save(client):
    response = client.post(
        "/api/import",
        files={"file": ("chat.txt", (EXAMPLES / "whatsapp_direct.txt").read_bytes())},
        data={"current_user_indices": "0,999", "chat_timezone": "UTC"},
    )
    assert response.status_code == 422


def test_equal_timestamp_order(client):
    content = "01/01/2026, 09:00 - Alice: first\n01/01/2026, 09:00 - Bob: second\n01/01/2026, 09:00 - Alice: third"
    response = client.post(
        "/api/import",
        files={"file": ("chat.txt", content.encode())},
        data={"current_user_index": "0", "chat_timezone": "UTC"},
    )
    assert response.status_code == 200, response.text
    cid = response.json()["id"]
    messages = client.get(f"/api/conversations/{cid}/messages").json()["items"]
    assert [m["text"] for m in messages] == ["first", "second", "third"]


def test_import_timezone_is_required_and_activity_uses_selected_clock(client):
    files = {
        "file": (
            "chat.txt",
            b"02/01/2026, 00:15 - Alice: Hello\n02/01/2026, 00:16 - Bob: Hi",
        )
    }
    assert (
        client.post(
            "/api/import", files=files, data={"current_user_index": "0"}
        ).status_code
        == 422
    )
    result = client.post(
        "/api/import",
        files=files,
        data={"current_user_index": "0", "chat_timezone": "Asia/Kolkata"},
    )
    assert result.status_code == 200, result.text
    cid = result.json()["id"]
    chat = client.get(f"/api/conversations/{cid}").json()
    assert chat["metadata"]["source_timezone"] == "Asia/Kolkata"
    stats = client.get(f"/api/conversations/{cid}/analytics").json()
    assert stats["timezone"] == "Asia/Kolkata"
    assert stats["activity"]["hourly"][0]["count"] == 2
    assert (
        client.get(f"/api/conversations/{cid}/reply-network").json()["network"] is None
    )


def test_imessage_api(client, tmp_path):
    from test_parsers import make_imessage

    path = tmp_path / "chat.db"
    make_imessage(path)
    files = {"file": ("chat.db", path.read_bytes())}
    preview = client.post("/api/import/preview", files=files)
    assert preview.status_code == 200, preview.text
    assert len(preview.json()["conversations"]) == 2
    saved = client.post(
        "/api/import",
        files=files,
        data={"selection_index": "1", "current_user_index": "0"},
    )
    assert saved.status_code == 200, saved.text
    cid = saved.json()["id"]
    assert (
        client.get(f"/api/conversations/{cid}").json()["conversation_type"] == "group"
    )
    assert (
        client.get(f"/api/conversations/{cid}/analytics").json()["total_messages"] == 3
    )
