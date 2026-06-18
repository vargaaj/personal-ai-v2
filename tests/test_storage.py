from pathlib import Path

import pytest

from loop_review.storage import ItemToggleError, LoopStorage, SaveConflictError


def test_read_missing_loop_file_returns_empty_json_document(tmp_path: Path) -> None:
    storage = LoopStorage(tmp_path)

    loop = storage.read_loop("gmail")

    assert loop.exists is False
    assert loop.data["id"] == "gmail"
    assert loop.sections == []


def test_save_loop_creates_file_and_parses_items(tmp_path: Path) -> None:
    storage = LoopStorage(tmp_path)

    loop = storage.save_loop(
        "home",
        {
            "sections": [
                {
                    "title": "Maintenance",
                    "items": [{"id": "replace-filter", "text": "Replace HVAC filter", "checked": False}],
                }
            ]
        },
    )

    assert loop.exists is True
    assert loop.sections[0].items[0].text == "Replace HVAC filter"
    assert '"replace-filter"' in (tmp_path / "home.json").read_text(encoding="utf-8")


def test_toggle_item_rewrites_json_item(tmp_path: Path) -> None:
    (tmp_path / "home.json").write_text(
        '{"sections":[{"title":"Maintenance","items":[{"id":"replace-filter","text":"Replace HVAC filter","checked":false}]}]}',
        encoding="utf-8",
    )
    storage = LoopStorage(tmp_path)

    loop = storage.toggle_item("home", "replace-filter")

    assert loop.sections[0].items[0].checked is True
    assert '"checked": true' in (tmp_path / "home.json").read_text(encoding="utf-8")


def test_add_item_appends_to_existing_section(tmp_path: Path) -> None:
    (tmp_path / "home.json").write_text(
        '{"sections":[{"title":"Maintenance","items":[]}]}',
        encoding="utf-8",
    )
    storage = LoopStorage(tmp_path)

    loop = storage.add_item("home", "Maintenance", "Clean dryer vent", "Before weekend")

    item = loop.sections[0].items[0]
    assert item.id == "clean-dryer-vent"
    assert item.text == "Clean dryer vent"
    assert item.details == "Before weekend"


def test_add_item_creates_missing_section(tmp_path: Path) -> None:
    storage = LoopStorage(tmp_path)

    loop = storage.add_item("home", "Errands", "Pick up filters")

    assert loop.sections[0].title == "Errands"
    assert loop.sections[0].items[0].text == "Pick up filters"


def test_toggle_missing_file_raises_item_error(tmp_path: Path) -> None:
    storage = LoopStorage(tmp_path)

    with pytest.raises(ItemToggleError):
        storage.toggle_item("gmail", "message-1")


def test_save_conflict_detects_newer_disk_file(tmp_path: Path) -> None:
    file_path = tmp_path / "home.json"
    file_path.write_text('{"sections":[]}', encoding="utf-8")
    storage = LoopStorage(tmp_path)
    loaded = storage.read_loop("home")

    with pytest.raises(SaveConflictError):
        storage.save_loop("home", {"sections": []}, expected_modified_time=loaded.modified_time - 10)


def test_gmail_email_state_is_displayed_as_sections(tmp_path: Path) -> None:
    (tmp_path / "gmail_state.json").write_text(
        """
        {
          "last_updated": "2026-06-11",
          "emails": [
            {
              "message_id": "m1",
              "sender": "Alex",
              "subject": "Friday timeline",
              "date": "2026-06-11",
              "summary": "Reply needed about Friday.",
              "section": "needs_attention",
              "status": "open"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    storage = LoopStorage(tmp_path)

    loop = storage.read_loop("gmail")

    assert loop.sections[0].title == "Needs Attention"
    assert loop.sections[0].items[0].id == "m1"
    assert loop.sections[0].items[0].metadata["sender"] == "Alex"


def test_add_item_to_gmail_state_appends_manual_email(tmp_path: Path) -> None:
    (tmp_path / "gmail_state.json").write_text('{"last_updated":"2026-06-11","emails":[]}', encoding="utf-8")
    storage = LoopStorage(tmp_path)

    loop = storage.add_item("gmail", "Needs Attention", "Call dentist", "Confirm appointment")

    email = loop.data["emails"][0]
    assert email["message_id"] == "call-dentist"
    assert email["section"] == "needs_attention"
    assert email["status"] == "open"
    assert loop.sections[0].items[0].details == "Confirm appointment"


def test_food_loop_uses_food_json(tmp_path: Path) -> None:
    (tmp_path / "food.json").write_text(
        """
        {
          "sections": [
            {
              "title": "This Week's Dinners",
              "items": [
                {
                  "id": "monday-dinner",
                  "text": "Lemon chicken bowls",
                  "checked": false,
                  "day": "Monday"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    storage = LoopStorage(tmp_path)

    loop = storage.read_loop("food")

    assert loop.path.endswith("food.json")
    assert loop.sections[0].items[0].text == "Lemon chicken bowls"
    assert loop.sections[0].items[0].metadata["day"] == "Monday"


def test_ai_news_loop_uses_ai_news_json(tmp_path: Path) -> None:
    (tmp_path / "ai_news.json").write_text(
        """
        {
          "sections": [
            {
              "title": "Top AI News",
              "items": [
                {
                  "id": "model-release",
                  "text": "New model release",
                  "checked": false,
                  "details": "Short summary of the model release.",
                  "link": "https://example.com/model-release",
                  "source": "Example News",
                  "source_type": "article",
                  "published_date": "2026-06-11"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    storage = LoopStorage(tmp_path)

    loop = storage.read_loop("ai_news")

    item = loop.sections[0].items[0]
    assert loop.path.endswith("ai_news.json")
    assert item.text == "New model release"
    assert item.details == "Short summary of the model release."
    assert item.link == "https://example.com/model-release"
    assert item.metadata["source"] == "Example News"
    assert item.metadata["source_type"] == "article"
