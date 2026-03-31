from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import urlparse

import httpx
import pytest

from app.models.game_experience import GameExperienceTemplate
from app.services import game_service
from app.services.game_service import GameServiceConfigError, GameServiceError
from app.utils.errors import api_error, api_success


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, content: bytes | None = None):
        self.status_code = status_code
        self._payload = payload
        self.content = b"" if content is None else content

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    def __init__(self, *, response=None, exc=None, recorder=None, **kwargs):
        self.response = response
        self.exc = exc
        self.recorder = recorder if recorder is not None else []
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, path, json=None, headers=None):
        self.recorder.append({"method": method, "path": path, "json": json, "headers": headers, "client_kwargs": self.kwargs})
        if self.exc is not None:
            raise self.exc
        return self.response


@pytest.fixture
def flask_app(app):
    return app


def test_play_service_config_helpers(flask_app):
    with flask_app.app_context():
        flask_app.config.update(
            PLAY_SERVICE_PUBLIC_URL="https://play.example.com/",
            PLAY_SERVICE_INTERNAL_URL="http://internal.example.com/",
            PLAY_SERVICE_SHARED_SECRET="top-secret",
            PLAY_SERVICE_INTERNAL_API_KEY="internal-key",
        )
        assert game_service.has_complete_play_service_config() is True
        assert game_service.get_play_service_public_url() == "https://play.example.com"
        assert game_service.get_play_service_websocket_url() == "wss://play.example.com"
        assert game_service._internal_headers() == {
            "Accept": "application/json",
            "X-Play-Service-Key": "internal-key",
        }

        flask_app.config["PLAY_SERVICE_PUBLIC_URL"] = "http://play.example.com"
        assert game_service.get_play_service_websocket_url() == "ws://play.example.com"
        assert urlparse(game_service.get_play_service_websocket_url()).scheme == "ws"


def test_require_configured_url_and_shared_secret_errors(flask_app):
    with flask_app.app_context():
        flask_app.config.update(
            PLAY_SERVICE_PUBLIC_URL="",
            PLAY_SERVICE_INTERNAL_URL="",
            PLAY_SERVICE_SHARED_SECRET="",
        )
        assert game_service.has_complete_play_service_config() is False
        with pytest.raises(GameServiceConfigError, match="PLAY_SERVICE_PUBLIC_URL"):
            game_service.get_play_service_public_url()
        with pytest.raises(GameServiceConfigError, match="PLAY_SERVICE_INTERNAL_URL"):
            game_service._require_configured_url("internal")
        with pytest.raises(GameServiceConfigError, match="PLAY_SERVICE_SHARED_SECRET"):
            game_service.issue_play_ticket({"run_id": "r1"})


def test_request_success_and_error_paths(flask_app, monkeypatch):
    recorder = []
    with flask_app.app_context():
        flask_app.config.update(
            PLAY_SERVICE_PUBLIC_URL="https://play.example.com",
            PLAY_SERVICE_INTERNAL_URL="https://internal.example.com",
            PLAY_SERVICE_REQUEST_TIMEOUT=12,
            PLAY_SERVICE_INTERNAL_API_KEY="internal-key",
        )

        monkeypatch.setattr(
            game_service.httpx,
            "Client",
            lambda **kwargs: _FakeClient(response=_FakeResponse(200, payload=[{"id": "tmpl"}], content=b"[]"), recorder=recorder, **kwargs),
        )
        assert game_service.list_templates() == [{"id": "tmpl"}]
        assert recorder[-1]["path"] == "/api/templates"
        assert recorder[-1]["client_kwargs"]["timeout"] == 12.0

        monkeypatch.setattr(
            game_service.httpx,
            "Client",
            lambda **kwargs: _FakeClient(response=_FakeResponse(503, payload={"detail": "down"}, content=b"{}"), recorder=recorder, **kwargs),
        )
        with pytest.raises(GameServiceError, match="down") as excinfo:
            game_service.get_run_details("run-1")
        assert excinfo.value.status_code == 503

        monkeypatch.setattr(
            game_service.httpx,
            "Client",
            lambda **kwargs: _FakeClient(response=_FakeResponse(500, payload=None, content=b""), recorder=recorder, **kwargs),
        )
        with pytest.raises(GameServiceError, match="500") as excinfo:
            game_service.get_run_transcript("run-1")
        assert excinfo.value.status_code == 500

        request_exc = httpx.RequestError("boom", request=httpx.Request("GET", "https://play.example.com"))
        monkeypatch.setattr(
            game_service.httpx,
            "Client",
            lambda **kwargs: _FakeClient(exc=request_exc, recorder=recorder, **kwargs),
        )
        with pytest.raises(GameServiceError, match="unavailable") as excinfo:
            game_service.list_runs()
        assert excinfo.value.status_code == 502


def test_game_service_payload_shape_validation(flask_app, monkeypatch):
    with flask_app.app_context():
        flask_app.config.update(
            PLAY_SERVICE_PUBLIC_URL="https://play.example.com",
            PLAY_SERVICE_INTERNAL_URL="https://internal.example.com",
            PLAY_SERVICE_SHARED_SECRET="secret",
        )

        monkeypatch.setattr(game_service, "_request", lambda *args, **kwargs: {"id": "unexpected"})
        assert game_service.list_templates() == []
        assert game_service.list_runs() == []

        with pytest.raises(GameServiceError, match="unexpected create_run payload"):
            game_service.create_run(template_id="solo", account_id="1", display_name="Alice")

        with pytest.raises(GameServiceError, match="unexpected join-context payload"):
            game_service.resolve_join_context(run_id="r1", account_id="1", display_name="Alice")

        with pytest.raises(GameServiceError, match="unexpected run detail payload"):
            game_service.get_run_details("r1")

        with pytest.raises(GameServiceError, match="unexpected transcript payload"):
            game_service.get_run_transcript("r1")

        with pytest.raises(GameServiceError, match="unexpected terminate payload"):
            game_service.terminate_run("r1")

        monkeypatch.setattr(
            game_service,
            "_request",
            lambda *args, **kwargs: {
                "run_id": "r1",
                "participant_id": "p1",
                "role_id": "visitor",
                "display_name": "Alice",
                "account_id": "1",
                "character_id": "7",
            },
        )
        ctx = game_service.resolve_join_context(run_id="r1", account_id="1", display_name="Alice")
        assert ctx.run_id == "r1"
        assert ctx.participant_id == "p1"
        assert ctx.role_id == "visitor"
        assert ctx.account_id == "1"
        assert ctx.character_id == "7"


def test_issue_play_ticket_generates_signed_payload(flask_app, monkeypatch):
    with flask_app.app_context():
        flask_app.config.update(PLAY_SERVICE_SHARED_SECRET="super-secret", GAME_TICKET_TTL_SECONDS=15)
        monkeypatch.setattr(game_service.time, "time", lambda: 1000)

        token = game_service.issue_play_ticket({"run_id": "run-1", "participant_id": "p1"})
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, signature = decoded.rsplit(b".", 1)
        expected = hmac.new(b"super-secret", raw, hashlib.sha256).hexdigest().encode("ascii")
        assert signature == expected

        payload = json.loads(raw.decode("utf-8"))
        assert payload == {
            "run_id": "run-1",
            "participant_id": "p1",
            "iat": 1000,
            "exp": 1015,
        }


def test_api_error_and_success_helpers(flask_app):
    with flask_app.app_context():
        response, status = api_error("User not found", "USER_NOT_FOUND")
        assert status == 404
        assert response.get_json() == {"error": "User not found", "code": "USER_NOT_FOUND"}

        response, status = api_error("Nope", "CUSTOM_CODE", 418)
        assert status == 418
        assert response.get_json() == {"error": "Nope", "code": "CUSTOM_CODE"}

        response, status = api_success({"id": 1}, message="created", status_code=201)
        assert status == 201
        assert response.get_json() == {"id": 1, "message": "created"}

        response, status = api_success(message="done")
        assert status == 200
        assert response.get_json() == {"message": "done"}

        response, status = api_success()
        assert status == 200
        assert response.get_json() == {}


@pytest.mark.usefixtures("isolated_app_context")
def test_game_experience_template_to_dict_variants():
    template = GameExperienceTemplate(
        id=5,
        key="god_of_carnage",
        title="God of Carnage",
        experience_type=GameExperienceTemplate.TYPE_SOLO,
        summary="summary",
        tags=["a", "b"],
        style_profile="retro_pulp",
        status=GameExperienceTemplate.STATUS_PUBLISHED,
        current_version=3,
        published_version=2,
        draft_payload={"draft": True},
        published_payload={"published": True},
        created_by=1,
        updated_by=2,
        published_by=3,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    full = template.to_dict(include_payload=True, include_published_payload=True)
    assert full["draft_payload"] == {"draft": True}
    assert full["published_payload"] == {"published": True}
    assert full["status"] == GameExperienceTemplate.STATUS_PUBLISHED
    assert full["created_at"].startswith("2026-01-01T")

    compact = template.to_dict(include_payload=False, include_published_payload=False)
    assert "draft_payload" not in compact
    assert "published_payload" not in compact
    assert compact["tags"] == ["a", "b"]
