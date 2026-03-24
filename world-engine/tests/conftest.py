from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None



@pytest.fixture
def sqlalchemy_available() -> bool:
    return SQLALCHEMY_AVAILABLE



def receive_until_snapshot(websocket, predicate, attempts: int = 6):
    last = None
    for _ in range(attempts):
        last = websocket.receive_json()
        if last.get("type") == "snapshot" and predicate(last["data"]):
            return last
    raise AssertionError(f"Did not receive matching snapshot; last payload was: {last}")



def build_test_app(tmp_path: Path, *, store_backend: str = "json", store_url: str | None = None) -> FastAPI:
    tickets_module = importlib.import_module("app.auth.tickets")
    runtime_manager_module = importlib.import_module("app.runtime.manager")
    http_module = importlib.import_module("app.api.http")
    ws_module = importlib.import_module("app.api.ws")
    ws_module = importlib.reload(ws_module)

    app = FastAPI()
    app.state.manager = runtime_manager_module.RuntimeManager(
        store_root=tmp_path,
        store_backend=store_backend,
        store_url=store_url,
    )
    app.state.ticket_manager = tickets_module.TicketManager("test-secret")
    app.include_router(http_module.router)
    app.include_router(ws_module.router)
    return app


@pytest.fixture
def app(tmp_path: Path):
    return build_test_app(tmp_path)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
