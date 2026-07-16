from __future__ import annotations

from datetime import datetime
from itertools import groupby
import json
from pathlib import Path

from nicegui import ui

from .storage import (
    LOOP_TITLES,
    InvalidLoopDataError,
    ItemAddError,
    ItemToggleError,
    LoopContent,
    LoopItem,
    LoopSection,
    LoopStorage,
    SaveConflictError,
)


LOOP_ICONS = {
    "gmail": "mail",
    "finance": "account_balance_wallet",
    "home": "home",
    "health": "fitness_center",
    "food": "restaurant",
    "ai_news": "newspaper",
}

_THEME_APPLIED = False


def create_ui(storage: LoopStorage) -> None:
    register_inbox_page(storage)
    register_loop_pages(storage)
    register_settings_page(storage)


def apply_theme() -> None:
    global _THEME_APPLIED
    if _THEME_APPLIED:
        return

    ui.colors(primary="#256f72", secondary="#a33f2f", accent="#d69e2e", positive="#4f8a5b")
    ui.add_head_html(
        """
        <style>
            * { box-sizing: border-box; }
            body { background: #f7f7f2; color: #252525; }
            .app-shell { max-width: 1380px; margin: 0 auto; }
            .app-page { min-width: 0; }
            .app-header { min-height: 56px; }
            .app-header-row { min-height: 56px; }
            .app-drawer .q-drawer__content { overflow-x: hidden; }
            .surface { background: #ffffff; border: 1px solid #deded6; border-radius: 8px; }
            .soft-panel { background: #fbfbf7; border: 1px solid #e4e1d8; border-radius: 8px; }
            .content-layout { flex-wrap: nowrap; }
            .content-panel { min-width: 0; }
            .loop-link { display: block; min-width: 0; }
            .loop-card { min-height: 112px; }
            .muted { color: #686760; }
            .item-row { min-height: 44px; }
            .item-row:hover { background: #f1f4ef; }
            .item-main { min-width: 0; }
            .item-row .q-field__native,
            .item-row .q-checkbox__label,
            .item-main,
            .item-details,
            .metadata-chip,
            .workout-checkbox .q-checkbox__label { overflow-wrap: anywhere; }
            .item-checkbox .q-checkbox__inner { margin-top: 0; }
            .item-details { white-space: pre-line; line-height: 1.45; }
            .metadata-chip { background: #efeee8; border-radius: 4px; padding: 1px 6px; }
            .metadata-row { flex-wrap: wrap; }
            .workout-card { background: #fbfbf7; border: 1px solid #e4e1d8; border-radius: 8px; }
            .workout-card.done { opacity: 0.68; }
            .workout-checkbox .q-checkbox__label { font-weight: 600; line-height: 1.35; }
            .json-preview { max-height: 560px; overflow: auto; }
            .json-editor textarea { font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; line-height: 1.45; }
            .settings-path { min-width: 0; overflow-x: auto; }

            @media (min-width: 1024px) {
                .mobile-menu-button { display: none !important; }
            }

            @media (min-width: 901px) {
                .content-layout > .content-panel { flex: 1 1 0; }
            }

            @media (max-width: 900px) {
                .app-shell { max-width: none; }
                .app-page { padding: 12px !important; gap: 12px !important; }
                .app-header-row { padding-left: 8px !important; padding-right: 8px !important; }
                .page-header {
                    align-items: flex-start !important;
                    gap: 8px !important;
                }
                .page-title {
                    font-size: 1.5rem !important;
                    line-height: 2rem !important;
                }
                .page-actions { flex-shrink: 0; }
                .content-layout {
                    flex-direction: column !important;
                    gap: 12px !important;
                }
                .content-panel,
                .surface,
                .soft-panel { padding: 12px !important; }
                .loop-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)) !important; gap: 10px !important; }
                .loop-card { min-height: 96px; }
                .section-heading { align-items: flex-start !important; }
                .item-row {
                    flex-wrap: wrap;
                    align-items: flex-start !important;
                    gap: 6px !important;
                    padding: 8px !important;
                    border: 1px solid #ece9df;
                    background: #fffdf8;
                }
                .item-main { flex: 1 1 calc(100% - 48px); }
                .item-id {
                    flex: 0 0 100%;
                    padding-left: 32px;
                }
                .item-action { margin-left: auto; }
                .workout-card { padding: 10px !important; }
                .json-preview { max-height: 320px; }
                .settings-row {
                    align-items: flex-start !important;
                    flex-direction: column !important;
                    gap: 8px !important;
                }
                .settings-path {
                    width: 100%;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
            }

            @media (max-width: 520px) {
                .loop-grid { grid-template-columns: 1fr !important; }
                .app-title { font-size: 1rem !important; }
                .content-panel,
                .surface,
                .soft-panel { border-radius: 6px; }
            }
        </style>
        """,
        shared=True,
    )
    _THEME_APPLIED = True


def register_inbox_page(storage: LoopStorage) -> None:
    @ui.page("/")
    def inbox_page() -> None:
        render_shell(storage, active="inbox", title="Action Inbox")

        @ui.refreshable
        def inbox_content() -> None:
            loops = storage.list_loops()
            all_items = [
                (loop.id, loop.title, item)
                for loop in (storage.read_loop(loop_id) for loop_id in storage.loop_ids())
                for section in loop.sections
                for item in section.items
            ]
            open_items = [(loop_id, title, item) for loop_id, title, item in all_items if not item.checked]

            with ui.column().classes("app-shell app-page w-full gap-4 p-4"):
                with ui.row().classes("page-header w-full items-center justify-between gap-3"):
                    with ui.column().classes("gap-0"):
                        ui.label("Action Inbox").classes("page-title text-3xl font-semibold")
                        ui.label(f"{len(open_items)} open items across {len(loops)} loops").classes("muted")
                    ui.button(icon="refresh", on_click=inbox_content.refresh).props("flat round").classes("page-actions").tooltip(
                        "Refresh"
                    )

                with ui.grid(columns="repeat(auto-fit, minmax(180px, 1fr))").classes("loop-grid w-full gap-3"):
                    for loop in loops:
                        with ui.link(target=f"/loop/{loop.id}").classes("loop-link no-underline text-black"):
                            with ui.column().classes("loop-card surface p-4 gap-1 w-full"):
                                ui.icon(LOOP_ICONS[loop.id]).classes("text-2xl text-primary")
                                ui.label(loop.title).classes("font-semibold")
                                ui.label(f"{loop.open_item_count} open / {loop.item_count} total").classes("muted text-sm")

                if not open_items:
                    with ui.column().classes("soft-panel w-full p-6 items-center"):
                        ui.icon("task_alt").classes("text-4xl text-positive")
                        ui.label("No open items").classes("text-lg font-medium")
                else:
                    for loop_id, group in groupby(open_items, key=lambda item: item[0]):
                        grouped = list(group)
                        title = grouped[0][1]
                        with ui.column().classes("surface w-full p-4 gap-2"):
                            with ui.row().classes("section-heading w-full items-center justify-between gap-2"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.icon(LOOP_ICONS[loop_id]).classes("text-primary")
                                    ui.label(title).classes("text-xl font-semibold")
                                ui.link("Open", f"/loop/{loop_id}").classes("text-primary")
                            for _, _, item in grouped:
                                render_item_row(storage, loop_id, item, refresh=inbox_content.refresh)

        inbox_content()


def register_loop_pages(storage: LoopStorage) -> None:
    @ui.page("/loop/{loop_id}")
    def loop_page(loop_id: str) -> None:
        if loop_id not in LOOP_TITLES:
            render_shell(storage, active="", title="Unknown Loop")
            with ui.column().classes("app-shell app-page w-full p-4"):
                ui.label("Unknown loop").classes("page-title text-2xl font-semibold")
                ui.link("Back to inbox", "/").classes("text-primary")
            return

        render_shell(storage, active=loop_id, title=LOOP_TITLES[loop_id])
        state = {"loop": storage.read_loop(loop_id)}

        def reload_loop() -> None:
            state["loop"] = storage.read_loop(loop_id)
            editor.value = state["loop"].content
            status_label.set_text(format_file_status(state["loop"]))
            loop_content.refresh()
            ui.notify("Reloaded", type="positive")

        def save_loop() -> None:
            loaded: LoopContent = state["loop"]
            try:
                data = json.loads(editor.value or "{}")
            except json.JSONDecodeError as exc:
                ui.notify(f"Invalid JSON: {exc.msg}", type="negative")
                return
            try:
                state["loop"] = storage.save_loop(loop_id, data, loaded.modified_time)
            except InvalidLoopDataError as exc:
                ui.notify(str(exc), type="negative")
                return
            except SaveConflictError:
                ui.notify("File changed on disk. Reload before saving.", type="warning")
                return
            status_label.set_text(format_file_status(state["loop"]))
            loop_content.refresh()
            ui.notify("Saved", type="positive")

        def add_manual_item(section: str, text_input, details_input, link_input, refresh) -> None:
            loaded: LoopContent = state["loop"]
            text = (text_input.value or "").strip()
            details = (details_input.value or "").strip()
            link = (link_input.value or "").strip()
            if not text:
                ui.notify("Add an item title first.", type="warning")
                return
            try:
                state["loop"] = storage.add_item(loop_id, section, text, details, link, loaded.modified_time)
            except SaveConflictError:
                ui.notify("File changed on disk. Reload before adding.", type="warning")
                return
            except ItemAddError as exc:
                ui.notify(str(exc), type="negative")
                return
            text_input.value = ""
            details_input.value = ""
            link_input.value = ""
            editor.value = state["loop"].content
            status_label.set_text(format_file_status(state["loop"]))
            refresh()
            ui.notify("Added", type="positive")

        with ui.column().classes("app-shell app-page w-full gap-4 p-4"):
            with ui.row().classes("page-header w-full items-center justify-between gap-3"):
                with ui.column().classes("gap-0"):
                    ui.label(LOOP_TITLES[loop_id]).classes("page-title text-3xl font-semibold")
                    status_label = ui.label(format_file_status(state["loop"])).classes("muted")
                with ui.row().classes("page-actions gap-2"):
                    ui.button(icon="refresh", on_click=reload_loop).props("flat round").tooltip("Reload")
                    ui.button(icon="save", on_click=save_loop).props("unelevated round color=primary").tooltip("Save")

            with ui.row().classes("content-layout w-full gap-4 items-start"):
                with ui.column().classes("content-panel surface p-4 gap-3 w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("checklist").classes("text-primary")
                        ui.label(open_items_title(loop_id)).classes("text-lg font-semibold")

                    @ui.refreshable
                    def loop_content() -> None:
                        loaded: LoopContent = state["loop"]
                        if loop_id == "health":
                            render_health_workouts(
                                storage,
                                loaded,
                                expected_modified_time=loaded.modified_time,
                                refresh=lambda: refresh_loop_after_toggle(storage, loop_id, state, editor, loop_content.refresh),
                                add_item=lambda section, text, details, link: add_manual_item(
                                    section, text, details, link, loop_content.refresh
                                ),
                            )
                        else:
                            if not loaded.sections:
                                ui.label(empty_items_text(loop_id)).classes("muted")
                                render_add_item_form(
                                    "General",
                                    lambda section, text, details, link: add_manual_item(
                                        section, text, details, link, loop_content.refresh
                                    ),
                                )
                            for section in loaded.sections:
                                render_section_panel(
                                    storage,
                                    loop_id,
                                    section,
                                    expected_modified_time=loaded.modified_time,
                                    refresh=lambda: refresh_loop_after_toggle(storage, loop_id, state, editor, loop_content.refresh),
                                    add_item=lambda section_title, text, details, link: add_manual_item(
                                        section_title, text, details, link, loop_content.refresh
                                    ),
                                )

                            if loaded.content:
                                with ui.expansion("Full JSON", icon="data_object").classes("w-full"):
                                    ui.code(loaded.content).classes("json-preview w-full")

                    loop_content()

                with ui.column().classes("content-panel surface p-4 gap-3 w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("edit_note").classes("text-secondary")
                        ui.label("JSON Editor").classes("text-lg font-semibold")
                    editor = ui.textarea(value=state["loop"].content).props("outlined autogrow spellcheck=false").classes(
                        "json-editor w-full"
                    )
                    ui.label("Saves replace the current JSON file.").classes("muted text-sm")


def register_settings_page(storage: LoopStorage) -> None:
    @ui.page("/settings")
    def settings_page() -> None:
        render_shell(storage, active="settings", title="Settings")
        with ui.column().classes("app-shell app-page w-full gap-4 p-4"):
            ui.label("Settings").classes("page-title text-3xl font-semibold")
            with ui.column().classes("surface p-4 gap-3 w-full"):
                ui.label("Loop Folder").classes("text-lg font-semibold")
                ui.code(str(storage.loops_dir)).classes("settings-path w-full")
            with ui.column().classes("surface p-4 gap-3 w-full"):
                ui.label("Loop Files").classes("text-lg font-semibold")
                for loop in storage.list_loops():
                    with ui.row().classes("settings-row w-full items-center justify-between gap-4"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(LOOP_ICONS[loop.id]).classes("text-primary")
                            ui.label(loop.title).classes("font-medium")
                        ui.code(loop.path).classes("settings-path grow")
                        ui.badge("found" if loop.exists else "missing", color="positive" if loop.exists else "warning")


def render_shell(storage: LoopStorage, active: str, title: str) -> None:
    apply_theme()
    ui.page_title(f"{title} - Loop Review Console")
    drawer = ui.left_drawer(value=None, bordered=True).classes("app-drawer bg-white border-r border-gray-200")

    with ui.header().classes("app-header bg-white text-black border-b border-gray-200"):
        with ui.row().classes("app-header-row app-shell w-full items-center justify-between px-4"):
            with ui.row().classes("items-center gap-2"):
                ui.button(icon="menu", on_click=drawer.toggle).props("flat round").classes("mobile-menu-button").tooltip("Menu")
                ui.icon("dashboard").classes("text-primary text-2xl")
                ui.label("Loop Review").classes("app-title text-lg font-semibold")
            ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props("flat round").tooltip("Settings")

    with drawer:
        with ui.column().classes("w-full gap-1 p-3"):
            nav_button("Inbox", "/", "inbox", active == "inbox")
            for loop_id, title in LOOP_TITLES.items():
                nav_button(title, f"/loop/{loop_id}", LOOP_ICONS[loop_id], active == loop_id)
            ui.separator().classes("my-2")
            nav_button("Settings", "/settings", "settings", active == "settings")


def nav_button(label: str, target: str, icon: str, selected: bool) -> None:
    color = "primary" if selected else "grey-8"
    button = ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(target)).props(f"flat no-caps align=left color={color}")
    button.classes("w-full justify-start")


def open_items_title(loop_id: str) -> str:
    if loop_id == "health":
        return "Workouts"
    if loop_id == "food":
        return "Dinner Plan"
    if loop_id == "ai_news":
        return "AI News"
    return "Open Items"


def empty_items_text(loop_id: str) -> str:
    if loop_id == "health":
        return "All workouts checked off"
    if loop_id == "food":
        return "No dinners planned"
    if loop_id == "ai_news":
        return "No AI news items"
    return "No open items"


def render_health_workouts(
    storage: LoopStorage,
    loop: LoopContent,
    expected_modified_time: float | None,
    refresh,
    add_item,
) -> None:
    if not loop.sections:
        ui.label("No workout items found").classes("muted")
        render_add_item_form("Workout Routine", add_item)
        return

    for section in loop.sections:
        with ui.column().classes("soft-panel w-full p-3 gap-2"):
            with ui.row().classes("section-heading w-full items-center justify-between gap-2"):
                ui.label(section.title).classes("font-semibold")
                ui.badge(f"{sum(1 for item in section.items if not item.checked)} open", color="primary")
            if not section.items:
                ui.label("No items in this section").classes("muted")
            for item in section.items:
                render_workout_card(storage, loop, item, expected_modified_time, refresh)
            render_add_item_form(section.title, add_item)


def render_section_panel(
    storage: LoopStorage,
    loop_id: str,
    section: LoopSection,
    expected_modified_time: float | None,
    refresh,
    add_item,
) -> None:
    open_items = [item for item in section.items if not item.checked]
    with ui.column().classes("soft-panel w-full p-3 gap-2"):
        with ui.row().classes("section-heading w-full items-center justify-between gap-2"):
            ui.label(section.title).classes("font-semibold")
            ui.badge(f"{len(open_items)} open", color="primary")
        if not open_items:
            ui.label("No open items in this section").classes("muted")
        for item in open_items:
            render_item_row(
                storage,
                loop_id,
                item,
                expected_modified_time=expected_modified_time,
                refresh=refresh,
            )
        render_add_item_form(section.title, add_item)


def render_add_item_form(section_title: str, add_item) -> None:
    with ui.expansion("Add item", icon="add").classes("w-full"):
        with ui.column().classes("w-full gap-2"):
            text_input = ui.input("Item", placeholder="What needs to be tracked?").props("outlined dense").classes("w-full")
            details_input = ui.textarea("Details", placeholder="Optional notes").props("outlined autogrow").classes("w-full")
            link_input = ui.input("Link", placeholder="Optional URL").props("outlined dense").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button(
                    "Add",
                    icon="add",
                    on_click=lambda: add_item(section_title, text_input, details_input, link_input),
                ).props("unelevated color=primary")


def render_workout_card(
    storage: LoopStorage,
    loop: LoopContent,
    item: LoopItem,
    expected_modified_time: float | None,
    refresh,
) -> None:
    def toggle_item() -> None:
        try:
            storage.toggle_item(loop.id, item.id, expected_modified_time)
        except SaveConflictError:
            ui.notify("File changed on disk. Reload before toggling.", type="warning")
            return
        except ItemToggleError as exc:
            ui.notify(str(exc), type="negative")
            return
        refresh()

    card_class = "workout-card done w-full p-3 gap-2" if item.checked else "workout-card w-full p-3 gap-2"
    with ui.column().classes(card_class):
        with ui.row().classes("w-full items-center gap-2"):
            ui.checkbox(item.text, value=item.checked, on_change=lambda _: toggle_item()).props("dense").classes(
                "workout-checkbox grow"
            )
            ui.label(item.id).classes("item-id muted text-xs")
        ui.label("Done" if item.checked else "Ready").classes("muted text-xs pl-8")

        if item.details:
            ui.label(item.details).classes("item-details w-full pl-8 text-sm")


def render_item_row(
    storage: LoopStorage,
    loop_id: str,
    item: LoopItem,
    refresh,
    expected_modified_time: float | None = None,
) -> None:
    def toggle_item() -> None:
        try:
            storage.toggle_item(loop_id, item.id, expected_modified_time)
        except SaveConflictError:
            ui.notify("File changed on disk. Reload before toggling.", type="warning")
            return
        except ItemToggleError as exc:
            ui.notify(str(exc), type="negative")
            return
        refresh()

    with ui.row().classes("item-row w-full items-start gap-2 px-2 py-1 rounded"):
        ui.checkbox(value=item.checked, on_change=lambda _: toggle_item()).props("dense").classes("item-checkbox")
        with ui.column().classes("item-main gap-0 grow"):
            ui.label(item.text).classes("w-full")
            if item.details:
                ui.label(item.details).classes("item-details muted text-sm")
            render_item_metadata(item)
        if item.link:
            ui.button(
                icon="open_in_new",
                on_click=lambda link=item.link: ui.run_javascript(f"window.open({json.dumps(link)}, '_blank')"),
            ).props("flat round").classes("item-action").tooltip("Open link")
        ui.label(item.id).classes("item-id muted text-xs")


def render_item_metadata(item: LoopItem) -> None:
    visible_keys = [
        "day",
        "date",
        "published_date",
        "source",
        "source_type",
        "sender",
        "received_date",
        "status",
        "due_date",
        "protein",
        "prep_time",
    ]
    values = [(key, item.metadata[key]) for key in visible_keys if key in item.metadata]
    if item.section:
        values.insert(0, ("section", item.section))
    if not values:
        return

    with ui.row().classes("metadata-row gap-1 mt-1"):
        for key, value in values:
            ui.label(f"{key}: {value}").classes("metadata-chip muted text-xs")


def refresh_loop_after_toggle(storage: LoopStorage, loop_id: str, state: dict, editor, refresh) -> None:
    state["loop"] = storage.read_loop(loop_id)
    editor.value = state["loop"].content
    refresh()


def format_file_status(loop: LoopContent) -> str:
    if not loop.exists:
        return f"{Path(loop.path).name} missing"
    if loop.modified_time is None:
        return f"{Path(loop.path).name}"
    modified = datetime.fromtimestamp(loop.modified_time).strftime("%Y-%m-%d %H:%M")
    return f"{Path(loop.path).name} modified {modified}"
