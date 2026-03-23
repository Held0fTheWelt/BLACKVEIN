from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.http import router as http_router
from app.api.ws import router as ws_router
from app.auth.tickets import TicketManager
from app.config import APP_TITLE, APP_VERSION, RUN_STORE_DIR
from app.runtime.manager import RuntimeManager

WEB_ROOT = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.manager = RuntimeManager(store_root=RUN_STORE_DIR)
    app.state.ticket_manager = TicketManager()
    yield


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
app.include_router(http_router)
app.include_router(ws_router)
app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "templates" / "index.html")
