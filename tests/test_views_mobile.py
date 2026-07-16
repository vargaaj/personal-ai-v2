from __future__ import annotations

from pathlib import Path

import pytest

from loop_review import views
from loop_review.storage import LoopContent, LoopInfo, LoopItem, LoopSection


def test_create_ui_registers_pages_without_global_theme(monkeypatch: pytest.MonkeyPatch) -> None:
    registered_pages: list[str] = []

    def fake_page(path: str):
        def decorator(func):
            registered_pages.append(path)
            return func

        return decorator

    def fail_if_theme_applied() -> None:
        pytest.fail("theme should be applied while rendering a page, not while registering pages")

    monkeypatch.setattr(views.ui, "page", fake_page)
    monkeypatch.setattr(views, "apply_theme", fail_if_theme_applied)

    views.create_ui(storage=object())  # type: ignore[arg-type]

    assert registered_pages == ["/", "/loop/{loop_id}", "/settings"]


def test_apply_theme_defines_mobile_layout_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {"head_calls": 0}

    def fake_colors(**colors: str) -> None:
        captured["colors"] = colors

    def fake_add_head_html(html: str, *, shared: bool = False) -> None:
        captured["head_calls"] = int(captured["head_calls"]) + 1
        captured["html"] = html
        captured["shared"] = shared

    monkeypatch.setattr(views, "_THEME_APPLIED", False)
    monkeypatch.setattr(views.ui, "colors", fake_colors)
    monkeypatch.setattr(views.ui, "add_head_html", fake_add_head_html)

    views.apply_theme()
    views.apply_theme()

    css = str(captured["html"])
    assert captured["head_calls"] == 1
    assert captured["colors"] == {
        "primary": "#256f72",
        "secondary": "#a33f2f",
        "accent": "#d69e2e",
        "positive": "#4f8a5b",
    }
    assert captured["shared"] is True
    assert (
        "@media (min-width: 1024px) {\n"
        "                .mobile-menu-button { display: none !important; }\n"
        "            }"
    ) in css
    assert "@media (min-width: 901px)" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 520px)" in css
    assert ".mobile-menu-button" in css
    assert ".content-layout" in css
    assert "flex-direction: column" in css
    assert ".loop-grid { grid-template-columns: 1fr !important; }" in css
    assert "overflow-wrap: anywhere" in css
    assert ".settings-path" in css
    assert "word-break: break-word" in css


class FakeElement:
    def __init__(
        self,
        kind: str,
        records: dict[str, object],
        entry: dict[str, object] | None = None,
        value: object = None,
    ) -> None:
        self.kind = kind
        self.records = records
        self.entry = entry
        self.value = value

    def __enter__(self) -> "FakeElement":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def classes(self, value: str) -> "FakeElement":
        self.records.setdefault("classes", []).append((self.kind, value))  # type: ignore[attr-defined]
        if self.entry is not None:
            self.entry.setdefault("classes", []).append(value)  # type: ignore[attr-defined]
        return self

    def props(self, value: str) -> "FakeElement":
        self.records.setdefault("props", []).append((self.kind, value))  # type: ignore[attr-defined]
        if self.entry is not None:
            self.entry.setdefault("props", []).append(value)  # type: ignore[attr-defined]
        return self

    def tooltip(self, value: str) -> "FakeElement":
        self.records.setdefault("tooltips", []).append((self.kind, value))  # type: ignore[attr-defined]
        if self.entry is not None:
            self.entry.setdefault("tooltips", []).append(value)  # type: ignore[attr-defined]
        return self

    def toggle(self) -> None:
        self.records["drawer_toggle_available"] = True

    def set_text(self, value: str) -> None:
        self.value = value
        self.records.setdefault("set_text", []).append((self.kind, value))  # type: ignore[attr-defined]


def install_fake_ui(monkeypatch: pytest.MonkeyPatch, records: dict[str, object]) -> None:
    def fake_element(
        kind: str,
        *args: object,
        entry: dict[str, object] | None = None,
        **kwargs: object,
    ) -> FakeElement:
        records.setdefault("elements", []).append({"kind": kind, "args": args, "kwargs": kwargs})  # type: ignore[attr-defined]
        return FakeElement(kind, records, entry=entry, value=kwargs.get("value"))

    def fake_left_drawer(**kwargs: object) -> FakeElement:
        records["drawer_kwargs"] = kwargs
        drawer = fake_element("left_drawer")
        records["drawer"] = drawer
        return drawer

    def fake_button(*args: object, **kwargs: object) -> FakeElement:
        entry: dict[str, object] = {"args": args, "kwargs": kwargs}
        records.setdefault("buttons", []).append(entry)  # type: ignore[attr-defined]
        return fake_element("button", *args, entry=entry, **kwargs)

    def fake_refreshable(func):
        func.refresh = lambda: None
        return func

    monkeypatch.setattr(views.ui, "left_drawer", fake_left_drawer)
    monkeypatch.setattr(views.ui, "button", fake_button)
    monkeypatch.setattr(views.ui, "refreshable", fake_refreshable)

    for name in [
        "header",
        "row",
        "column",
        "grid",
        "link",
        "icon",
        "label",
        "separator",
        "code",
        "badge",
        "checkbox",
        "input",
        "textarea",
        "expansion",
    ]:
        monkeypatch.setattr(
            views.ui,
            name,
            lambda *args, _name=name, **kwargs: fake_element(_name, *args, **kwargs),
        )


def test_render_shell_uses_responsive_drawer_and_mobile_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    records: dict[str, object] = {}

    install_fake_ui(monkeypatch, records)
    monkeypatch.setattr(views, "apply_theme", lambda: records.setdefault("theme_applied", True))
    monkeypatch.setattr(views.ui, "page_title", lambda title: records.setdefault("page_title", title))

    views.render_shell(storage=object(), active="inbox", title="Action Inbox")  # type: ignore[arg-type]

    assert records["theme_applied"] is True
    assert records["page_title"] == "Action Inbox - Loop Review Console"
    assert records["drawer_kwargs"] == {"value": None, "bordered": True}
    assert any("app-drawer" in classes for kind, classes in records["classes"] if kind == "left_drawer")  # type: ignore[index]
    menu_buttons = [button for button in records["buttons"] if button["kwargs"].get("icon") == "menu"]  # type: ignore[index]
    assert len(menu_buttons) == 1
    assert any("mobile-menu-button" in classes for classes in menu_buttons[0]["classes"])  # type: ignore[index]
    menu_buttons[0]["kwargs"]["on_click"]()  # type: ignore[index,operator]
    assert records["drawer_toggle_available"] is True


class FakeStorage:
    loops_dir = Path("C:/fake-loops")

    def loop_ids(self) -> list[str]:
        return ["home"]

    def list_loops(self) -> list[LoopInfo]:
        return [
            LoopInfo(
                id="home",
                title="Home",
                path=str(self.loops_dir / "home.json"),
                exists=True,
                modified_time=None,
                item_count=1,
                open_item_count=1,
            )
        ]

    def read_loop(self, loop_id: str) -> LoopContent:
        item = LoopItem(
            id="replace-filter",
            text="Replace HVAC filter",
            checked=False,
            section="Maintenance",
            details="Before Friday",
            link="https://example.com/filter",
            metadata={"due_date": "Friday"},
        )
        return LoopContent(
            id=loop_id,
            title="Home",
            path=str(self.loops_dir / "home.json"),
            exists=True,
            modified_time=None,
            last_updated=None,
            data={"sections": []},
            content='{"sections": []}',
            sections=[LoopSection(title="Maintenance", items=[item])],
        )


def test_responsive_classes_are_applied_to_page_and_item_views(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {}
    records: dict[str, object] = {}

    def fake_page(path: str):
        def decorator(func):
            pages[path] = func
            return func

        return decorator

    monkeypatch.setattr(views.ui, "page", fake_page)
    monkeypatch.setattr(views, "render_shell", lambda *args, **kwargs: None)
    install_fake_ui(monkeypatch, records)

    views.create_ui(FakeStorage())  # type: ignore[arg-type]
    pages["/"]()
    pages["/loop/{loop_id}"]("home")
    pages["/settings"]()

    rendered_classes = [classes for _, classes in records["classes"]]  # type: ignore[index]
    for expected_class in [
        "loop-grid",
        "content-layout",
        "settings-row",
        "settings-path",
        "item-main",
        "item-id",
        "metadata-row",
    ]:
        assert any(expected_class in classes for classes in rendered_classes)
