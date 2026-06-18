from __future__ import annotations

from fastapi import FastAPI
from nicegui import ui
import uvicorn

from .api import create_api_router
from .storage import LoopStorage
from .views import create_ui


storage = LoopStorage()
app = FastAPI(title="Loop Review Console")
app.include_router(create_api_router(storage))
create_ui(storage)
ui.run_with(app, title="Loop Review Console", mount_path="/", show_welcome_message=False)


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8080, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    run()
