from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Any


LOOP_TITLES: dict[str, str] = {
    "gmail": "Gmail",
    "finance": "Finance",
    "home": "Home",
    "health": "Health",
    "food": "Food",
    "ai_news": "AI News",
}

LOOP_FILES: dict[str, str] = {
    "gmail": "gmail_state.json",
    "finance": "finance.json",
    "home": "home.json",
    "health": "health.json",
    "food": "food.json",
    "ai_news": "ai_news.json",
}

SECTION_TITLES: dict[str, str] = {
    "needs_attention": "Needs Attention",
    "recent_email_summary": "Recent Email Summary",
    "waiting_on": "Waiting On",
    "no_action_needed": "No Action Needed",
}

DONE_STATUSES = {"done", "closed", "archived", "dismissed", "resolved", "complete", "completed"}


class UnknownLoopError(ValueError):
    pass


class SaveConflictError(RuntimeError):
    pass


class InvalidLoopDataError(ValueError):
    pass


class ItemToggleError(ValueError):
    pass


class ItemAddError(ValueError):
    pass


@dataclass(frozen=True)
class LoopItem:
    id: str
    text: str
    checked: bool
    section: str | None = None
    details: str = ""
    link: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LoopSection:
    title: str
    items: list[LoopItem]


@dataclass(frozen=True)
class LoopInfo:
    id: str
    title: str
    path: str
    exists: bool
    modified_time: float | None
    item_count: int
    open_item_count: int


@dataclass(frozen=True)
class LoopContent:
    id: str
    title: str
    path: str
    exists: bool
    modified_time: float | None
    last_updated: str | None
    data: dict[str, Any]
    content: str
    sections: list[LoopSection]


def default_loops_dir() -> Path:
    configured = os.environ.get("LOOPS_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[1] / "data" / "loops"


class LoopStorage:
    def __init__(self, loops_dir: Path | str | None = None) -> None:
        self.loops_dir = Path(loops_dir) if loops_dir is not None else default_loops_dir()

    def loop_ids(self) -> list[str]:
        return list(LOOP_TITLES)

    def title_for(self, loop_id: str) -> str:
        self._validate_loop(loop_id)
        return LOOP_TITLES[loop_id]

    def path_for(self, loop_id: str) -> Path:
        self._validate_loop(loop_id)
        return self.loops_dir / LOOP_FILES[loop_id]

    def list_loops(self) -> list[LoopInfo]:
        return [self._info_for(loop_id) for loop_id in self.loop_ids()]

    def read_loop(self, loop_id: str) -> LoopContent:
        path = self.path_for(loop_id)
        data = self._read_data(path, loop_id) if path.exists() else self._empty_document(loop_id)
        return LoopContent(
            id=loop_id,
            title=LOOP_TITLES[loop_id],
            path=str(path),
            exists=path.exists(),
            modified_time=self._modified_time(path),
            last_updated=self._last_updated(data),
            data=data,
            content=self._format_json(data),
            sections=self._sections_for(data),
        )

    def save_loop(
        self,
        loop_id: str,
        data: dict[str, Any] | str,
        expected_modified_time: float | None = None,
    ) -> LoopContent:
        path = self.path_for(loop_id)
        self._raise_if_conflict(path, expected_modified_time)
        document = self._normalize_saved_document(loop_id, data)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._format_json(document), encoding="utf-8")
        return self.read_loop(loop_id)

    def toggle_item(self, loop_id: str, item_id: str, expected_modified_time: float | None = None) -> LoopContent:
        path = self.path_for(loop_id)
        if not path.exists():
            raise ItemToggleError(f"{LOOP_TITLES[loop_id]} file does not exist")
        self._raise_if_conflict(path, expected_modified_time)
        data = self._read_data(path, loop_id)
        self._toggle_item_in_document(data, item_id)
        path.write_text(self._format_json(data), encoding="utf-8")
        return self.read_loop(loop_id)

    def add_item(
        self,
        loop_id: str,
        section: str,
        text: str,
        details: str = "",
        link: str = "",
        expected_modified_time: float | None = None,
    ) -> LoopContent:
        section = section.strip()
        text = text.strip()
        details = details.strip()
        link = link.strip()
        if not section:
            raise ItemAddError("section is required")
        if not text:
            raise ItemAddError("text is required")

        path = self.path_for(loop_id)
        self._raise_if_conflict(path, expected_modified_time)
        data = self._read_data(path, loop_id) if path.exists() else self._empty_document(loop_id)
        self._add_item_to_document(data, section, text, details, link)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._format_json(data), encoding="utf-8")
        return self.read_loop(loop_id)

    def _info_for(self, loop_id: str) -> LoopInfo:
        loop = self.read_loop(loop_id)
        items = [item for section in loop.sections for item in section.items]
        return LoopInfo(
            id=loop.id,
            title=loop.title,
            path=loop.path,
            exists=loop.exists,
            modified_time=loop.modified_time,
            item_count=len(items),
            open_item_count=sum(1 for item in items if not item.checked),
        )

    def _validate_loop(self, loop_id: str) -> None:
        if loop_id not in LOOP_TITLES:
            raise UnknownLoopError(f"unknown loop: {loop_id}")

    def _read_data(self, path: Path, loop_id: str) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InvalidLoopDataError(f"{path.name} is not valid JSON") from exc
        if not isinstance(data, dict):
            raise InvalidLoopDataError(f"{path.name} must contain a JSON object")
        return self._normalize_saved_document(loop_id, data)

    def _normalize_saved_document(self, loop_id: str, data: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError as exc:
                raise InvalidLoopDataError("content is not valid JSON") from exc
        else:
            parsed = data

        if not isinstance(parsed, dict):
            raise InvalidLoopDataError("loop content must be a JSON object")

        document = dict(parsed)
        document.setdefault("id", loop_id)
        document.setdefault("title", LOOP_TITLES[loop_id])
        if "sections" not in document and "emails" not in document:
            document["sections"] = []
        return document

    @staticmethod
    def _empty_document(loop_id: str) -> dict[str, Any]:
        return {
            "id": loop_id,
            "title": LOOP_TITLES[loop_id],
            "last_updated": None,
            "sections": [],
        }

    @classmethod
    def _sections_for(cls, data: dict[str, Any]) -> list[LoopSection]:
        if isinstance(data.get("emails"), list):
            return cls._sections_from_emails(data["emails"])
        return cls._sections_from_sections(data.get("sections"))

    @classmethod
    def _sections_from_sections(cls, sections: Any) -> list[LoopSection]:
        if not isinstance(sections, list):
            return []

        parsed_sections: list[LoopSection] = []
        for section_index, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                continue
            title = str(section.get("title") or f"Section {section_index}")
            items = []
            raw_items = section.get("items", [])
            if isinstance(raw_items, list):
                for item_index, item in enumerate(raw_items, start=1):
                    if not isinstance(item, dict):
                        continue
                    item_id = str(item.get("id") or f"section-{section_index}-item-{item_index}")
                    items.append(
                        LoopItem(
                            id=item_id,
                            text=str(item.get("text") or item.get("title") or item_id),
                            checked=bool(item.get("checked", False)),
                            section=title,
                            details=cls._string_or_joined_lines(item.get("details", "")),
                            link=cls._optional_string(item.get("link")),
                            metadata=cls._metadata_without(
                                item,
                                {"id", "text", "title", "checked", "details", "link"},
                            ),
                        )
                    )
            parsed_sections.append(LoopSection(title=title, items=items))
        return parsed_sections

    @classmethod
    def _sections_from_emails(cls, emails: list[Any]) -> list[LoopSection]:
        grouped: dict[str, list[LoopItem]] = {}
        section_order: list[str] = []

        for index, email in enumerate(emails, start=1):
            if not isinstance(email, dict):
                continue
            section_key = str(email.get("section") or "recent_email_summary")
            title = cls._section_title(section_key)
            if title not in grouped:
                grouped[title] = []
                section_order.append(title)

            item_id = str(email.get("message_id") or email.get("id") or email.get("thread_id") or f"email-{index}")
            status = str(email.get("status") or "open").lower()
            grouped[title].append(
                LoopItem(
                    id=item_id,
                    text=str(email.get("subject") or email.get("summary") or item_id),
                    checked=bool(email.get("dismissed", False)) or status in DONE_STATUSES,
                    section=title,
                    details=cls._string_or_joined_lines(email.get("summary", "")),
                    link=cls._optional_string(email.get("gmail_link") or email.get("link")),
                    metadata=cls._metadata_without(
                        email,
                        {"message_id", "id", "subject", "summary", "section", "status", "gmail_link", "link"},
                    )
                    | {"status": status},
                )
            )

        ordered_titles = [SECTION_TITLES[key] for key in SECTION_TITLES if SECTION_TITLES[key] in grouped]
        ordered_titles.extend(title for title in section_order if title not in ordered_titles)
        return [LoopSection(title=title, items=grouped[title]) for title in ordered_titles]

    @staticmethod
    def _section_title(section_key: str) -> str:
        normalized = section_key.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in SECTION_TITLES:
            return SECTION_TITLES[normalized]
        return section_key.replace("_", " ").strip().title() or "Recent Email Summary"

    @staticmethod
    def _last_updated(data: dict[str, Any]) -> str | None:
        value = data.get("last_updated") or data.get("updated")
        return str(value) if value not in {None, ""} else None

    @staticmethod
    def _string_or_joined_lines(value: Any) -> str:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value) if value not in {None, ""} else ""

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None or value == "":
            return None
        return str(value)

    @staticmethod
    def _metadata_without(source: dict[str, Any], excluded: set[str]) -> dict[str, Any]:
        return {
            key: value
            for key, value in source.items()
            if key not in excluded and value is not None and value != ""
        }

    @staticmethod
    def _format_json(data: dict[str, Any]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=True) + "\n"

    def _toggle_item_in_document(self, data: dict[str, Any], item_id: str) -> None:
        if isinstance(data.get("emails"), list):
            for email in data["emails"]:
                if not isinstance(email, dict):
                    continue
                candidate_ids = {
                    str(email.get("message_id") or ""),
                    str(email.get("id") or ""),
                    str(email.get("thread_id") or ""),
                }
                if item_id in candidate_ids:
                    status = str(email.get("status") or "open").lower()
                    email["status"] = "open" if status in DONE_STATUSES else "done"
                    return
            raise ItemToggleError(f"item {item_id} does not exist")

        sections = data.get("sections")
        if not isinstance(sections, list):
            raise ItemToggleError("loop has no items")

        for section in sections:
            if not isinstance(section, dict):
                continue
            items = section.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and str(item.get("id") or "") == item_id:
                    item["checked"] = not bool(item.get("checked", False))
                    return
        raise ItemToggleError(f"item {item_id} does not exist")

    def _add_item_to_document(
        self,
        data: dict[str, Any],
        section: str,
        text: str,
        details: str,
        link: str,
    ) -> None:
        if isinstance(data.get("emails"), list):
            item_id = self._unique_id(data["emails"], text, id_keys=("message_id", "id"))
            email = {
                "message_id": item_id,
                "sender": "Manual",
                "subject": text,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "summary": details or text,
                "section": self._section_key(section),
                "status": "open",
            }
            if link:
                email["gmail_link"] = link
            data["emails"].append(email)
            return

        sections = data.setdefault("sections", [])
        if not isinstance(sections, list):
            raise ItemAddError("sections must be a list")

        target_section = self._find_or_create_section(sections, section)
        items = target_section.setdefault("items", [])
        if not isinstance(items, list):
            raise ItemAddError("section items must be a list")

        item = {
            "id": self._unique_id(items, text, id_keys=("id",)),
            "text": text,
            "checked": False,
        }
        if details:
            item["details"] = details
        if link:
            item["link"] = link
        items.append(item)

    @staticmethod
    def _find_or_create_section(sections: list[Any], title: str) -> dict[str, Any]:
        for section in sections:
            if isinstance(section, dict) and str(section.get("title") or "").casefold() == title.casefold():
                return section
        section = {"title": title, "items": []}
        sections.append(section)
        return section

    @classmethod
    def _unique_id(cls, items: list[Any], text: str, id_keys: tuple[str, ...]) -> str:
        existing_ids = {
            str(item.get(key))
            for item in items
            if isinstance(item, dict)
            for key in id_keys
            if item.get(key)
        }
        base = cls._slugify(text) or "item"
        candidate = base
        suffix = 2
        while candidate in existing_ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug[:64].strip("-")

    @staticmethod
    def _section_key(section: str) -> str:
        normalized = section.strip().lower().replace("-", "_").replace(" ", "_")
        for key, title in SECTION_TITLES.items():
            if normalized == key or normalized == title.lower().replace(" ", "_"):
                return key
        return normalized or "recent_email_summary"

    @staticmethod
    def _modified_time(path: Path) -> float | None:
        return path.stat().st_mtime if path.exists() else None

    @staticmethod
    def _raise_if_conflict(path: Path, expected_modified_time: float | None) -> None:
        if expected_modified_time is None or not path.exists():
            return
        current_modified_time = path.stat().st_mtime
        if current_modified_time > expected_modified_time + 0.000001:
            raise SaveConflictError("file changed on disk after it was loaded")
