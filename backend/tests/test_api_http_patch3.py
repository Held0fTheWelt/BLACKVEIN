from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@dataclass
class _Dumpable:
    payload: dict

    def model_dump(self, mode: str = "json") -> dict:
        return dict(self.payload)


@dataclass
class _Participant:
    id: str
    role_id: str
    display_name: str
    account_id: str | None = None
    character_id: str | None = None


class _TicketManager:
    def __init__(self) -> None:
        self.issued_payloads: list[dict] = []

    def issue(self, payload: dict) -> str:
        self.issued_payloads.append(dict(payload))
        return f"ticket-for-{payload['participant_id']}"


class _Store:
    def describe(self) -> dict[str, str]:
        return {"backend": "memory", "root": "/tmp/runtime"}


class _Manager:
    def __init__(self) -> None:
        self.store = _Store()
        self.created_runs: list[dict] = []
        self.join_calls: list[dict] = []
        self.instances = {
            "run-1": types.SimpleNamespace(
                id="run-1",
                transcript=[
                    _Dumpable({"kind": "speech_committed", "text": "hello"}),
                    _Dumpable({"kind": "npc_reacted", "text": "world"}),
                ],
            )
        }

    def list_templates(self):
        return [_Dumpable({"id": "solo", "title": "Solo Template"})]

    def list_runs(self):
        return [_Dumpable({"id": "run-1", "status": "running"})]

    def get_run_details(self, run_id: str):
        if run_id == "missing":
            raise KeyError(run_id)
        return {"run": {"id": run_id}, "store": self.store.describe()}

    def create_run(self, template_id: str, display_name: str, account_id=None, character_id=None):
        if template_id == "unknown":
            raise KeyError(template_id)
        if template_id == "bad":
            raise ValueError("Bad template payload")
        payload = {
            "id": "created-run",
            "template_id": template_id,
            "display_name": display_name,
            "account_id": account_id,
            "character_id": character_id,
        }
        self.created_runs.append(payload)
        self.instances["created-run"] = types.SimpleNamespace(id="created-run", transcript=[])
        return types.SimpleNamespace(id="created-run")

    def get_instance(self, run_id: str):
        if run_id == "missing":
            raise KeyError(run_id)
        instance = self.instances.get(run_id)
        if instance is None:
            raise KeyError(run_id)
        return _Dumpable({"id": instance.id, "status": "running"})

    def find_or_join_run(self, run_id: str, display_name: str, account_id=None, character_id=None, preferred_role_id=None):
        if run_id == "missing":
            raise KeyError(run_id)
        if run_id == "forbidden":
            raise PermissionError("private")
        if run_id == "full":
            raise RuntimeError("full")
        participant = _Participant(
            id="participant-1",
            role_id=preferred_role_id or "visitor",
            display_name=display_name,
            account_id=account_id,
            character_id=character_id,
        )
        self.join_calls.append(
            {
                "run_id": run_id,
                "display_name": display_name,
                "account_id": account_id,
                "character_id": character_id,
                "preferred_role_id": preferred_role_id,
            }
        )
        return participant

    def build_snapshot(self, run_id: str, participant_id: str):
        if run_id == "missing" or participant_id == "missing":
            raise KeyError("not found")
        return _Dumpable({"run_id": run_id, "viewer_participant_id": participant_id})


@pytest.fixture
def http_module(monkeypatch):
    fake_manager_module = types.ModuleType("app.runtime.manager")
    fake_manager_module.RuntimeManager = _Manager
    monkeypatch.setitem(sys.modules, "app.runtime.manager", fake_manager_module)
    sys.modules.pop("app.api.http", None)
    module = importlib.import_module("app.api.http")
    monkeypatch.setattr(module, "PLAY_SERVICE_INTERNAL_API_KEY", "internal-secret", raising=False)
    return module


@pytest.fixture
def http_client(http_module):
    app = FastAPI(title="World of Shadows Test API")
    app.include_router(http_module.router)
    app.state.manager = _Manager()
    app.state.ticket_manager = _TicketManager()
    return TestClient(app)


def test_health_ready_templates_and_runs_endpoints(http_client):
    assert http_client.get("/api/health").json() == {"status": "ok"}

    ready = http_client.get("/api/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "ready",
        "app": "World of Shadows Test API",
        "store": {"backend": "memory", "root": "/tmp/runtime"},
        "template_count": 1,
        "run_count": 1,
    }

    templates = http_client.get("/api/templates")
    assert templates.status_code == 200
    assert templates.json() == [{"id": "solo", "title": "Solo Template"}]

    runs = http_client.get("/api/runs")
    assert runs.status_code == 200
    assert runs.json() == [{"id": "run-1", "status": "running"}]


def test_get_run_details_and_transcript_endpoints(http_client):
    response = http_client.get("/api/runs/run-1")
    assert response.status_code == 200
    assert response.json()["run"]["id"] == "run-1"

    transcript = http_client.get("/api/runs/run-1/transcript")
    assert transcript.status_code == 200
    assert transcript.json() == {
        "run_id": "run-1",
        "entries": [
            {"kind": "speech_committed", "text": "hello"},
            {"kind": "npc_reacted", "text": "world"},
        ],
    }

    missing = http_client.get("/api/runs/missing")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Run not found"}

    missing_transcript = http_client.get("/api/runs/missing/transcript")
    assert missing_transcript.status_code == 404
    assert missing_transcript.json() == {"detail": "Run not found"}


def test_create_run_success_and_error_mapping(http_client):
    response = http_client.post(
        "/api/runs",
        json={
            "template_id": "solo",
            "account_id": "42",
            "character_id": "7",
            "player_name": "  Proxy Player  ",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["run"]["id"] == "created-run"
    assert data["store"]["backend"] == "memory"
    assert "Use POST /api/tickets" in data["hint"]

    created = http_client.app.state.manager.created_runs[-1]
    assert created == {
        "id": "created-run",
        "template_id": "solo",
        "display_name": "Proxy Player",
        "account_id": "42",
        "character_id": "7",
    }

    missing_template = http_client.post("/api/runs", json={"template_id": "unknown"})
    assert missing_template.status_code == 404
    assert missing_template.json() == {"detail": "Unknown template id"}

    bad_template = http_client.post("/api/runs", json={"template_id": "bad"})
    assert bad_template.status_code == 400
    assert bad_template.json() == {"detail": "Bad template payload"}


def test_ticket_and_join_context_endpoints(http_client):
    ticket = http_client.post(
        "/api/tickets",
        json={
            "run_id": "run-1",
            "account_id": "42",
            "display_name": "  Alice  ",
            "preferred_role_id": "visitor",
        },
    )
    assert ticket.status_code == 200
    assert ticket.json() == {
        "ticket": "ticket-for-participant-1",
        "run_id": "run-1",
        "participant_id": "participant-1",
        "role_id": "visitor",
        "display_name": "Alice",
    }
    assert http_client.app.state.ticket_manager.issued_payloads[-1]["display_name"] == "Alice"

    unauthorized = http_client.post("/api/internal/join-context", json={"run_id": "run-1"})
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "Missing or invalid internal API key"}

    join_context = http_client.post(
        "/api/internal/join-context",
        headers={"X-Play-Service-Key": "internal-secret"},
        json={"run_id": "run-1", "display_name": "Guest", "preferred_role_id": "observer"},
    )
    assert join_context.status_code == 200
    assert join_context.json() == {
        "run_id": "run-1",
        "participant_id": "participant-1",
        "role_id": "observer",
        "display_name": "Guest",
        "account_id": None,
        "character_id": None,
    }


@pytest.mark.parametrize(
    ("endpoint", "run_id", "expected_status", "expected_detail"),
    [
        ("/api/tickets", "missing", 404, "Run not found"),
        ("/api/tickets", "forbidden", 403, "private"),
        ("/api/tickets", "full", 409, "full"),
        ("/api/internal/join-context", "missing", 404, "Run not found"),
        ("/api/internal/join-context", "forbidden", 403, "private"),
        ("/api/internal/join-context", "full", 409, "full"),
    ],
)
def test_ticket_and_join_context_error_mapping(http_client, endpoint, run_id, expected_status, expected_detail):
    headers = {}
    if endpoint.endswith("join-context"):
        headers["X-Play-Service-Key"] = "internal-secret"

    response = http_client.post(endpoint, headers=headers, json={"run_id": run_id, "display_name": "Guest"})
    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_snapshot_endpoint_and_identity_payload_helpers(http_client, http_module):
    snapshot = http_client.get("/api/runs/run-1/snapshot/participant-1")
    assert snapshot.status_code == 200
    assert snapshot.json() == {"run_id": "run-1", "viewer_participant_id": "participant-1"}

    missing = http_client.get("/api/runs/missing/snapshot/participant-1")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Run or participant not found"}

    payload = http_module.IdentityPayload(display_name=None, player_name="  fallback  ")
    assert payload.resolved_display_name() == "fallback"

    guest = http_module.IdentityPayload(display_name=None, player_name=None)
    assert guest.resolved_display_name() == "Guest"
