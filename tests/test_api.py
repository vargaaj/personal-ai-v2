from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from loop_review.api import create_api_router
from loop_review.storage import LoopStorage


def build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(create_api_router(LoopStorage(tmp_path)))
    return TestClient(app)


def test_list_loops(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/loops")

    assert response.status_code == 200
    assert [loop["id"] for loop in response.json()] == ["gmail", "finance", "home", "health", "food", "ai_news"]


def test_get_loop_returns_json_content_and_items(tmp_path: Path) -> None:
    (tmp_path / "home.json").write_text(
        '{"sections":[{"title":"Maintenance","items":[{"id":"replace-filter","text":"Replace HVAC filter","checked":false}]}]}',
        encoding="utf-8",
    )
    client = build_client(tmp_path)

    response = client.get("/api/loops/home")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["sections"][0]["title"] == "Maintenance"
    assert body["sections"][0]["items"][0]["id"] == "replace-filter"


def test_put_loop_replaces_content(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.put("/api/loops/home", json={"data": {"sections": []}})

    assert response.status_code == 200
    assert '"sections": []' in (tmp_path / "home.json").read_text(encoding="utf-8")


def test_patch_item_toggles_json_item(tmp_path: Path) -> None:
    (tmp_path / "home.json").write_text(
        '{"sections":[{"title":"Maintenance","items":[{"id":"replace-filter","text":"Replace HVAC filter","checked":false}]}]}',
        encoding="utf-8",
    )
    client = build_client(tmp_path)

    response = client.patch("/api/loops/home/items/replace-filter", json={})

    assert response.status_code == 200
    assert response.json()["sections"][0]["items"][0]["checked"] is True
    assert '"checked": true' in (tmp_path / "home.json").read_text(encoding="utf-8")


def test_post_item_adds_json_item(tmp_path: Path) -> None:
    (tmp_path / "home.json").write_text('{"sections":[{"title":"Maintenance","items":[]}]}', encoding="utf-8")
    client = build_client(tmp_path)

    response = client.post(
        "/api/loops/home/items",
        json={"section": "Maintenance", "text": "Clean dryer vent", "details": "Before weekend"},
    )

    assert response.status_code == 200
    item = response.json()["sections"][0]["items"][0]
    assert item["id"] == "clean-dryer-vent"
    assert item["text"] == "Clean dryer vent"
