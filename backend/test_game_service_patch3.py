from __future__ import annotations

import base64
import json
import types

import httpx
import pytest

from app.services.game_service import (
    GameServiceConfigError,
    GameServiceError,
    PlayJoinContext,
    _internal_headers,
    _request,
    create_run,
    get_play_service_public_url,
    get_play_service_websocket_url,
    get_run_details,
    get_run_transcript,
    has_complete_play_service_config,
    issue_play_ticket,
    list_runs,
    list_templates,
    resolve_join_context,
    terminate_run,
)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b"x"):
        self.status_code = status_code
        self._payload = payload
        self.content = content

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    def __init__(self, response=None, error=None, capture=None, **kwargs):
        self.response = response
        self.error = error
        self.capture = capture if capture is not None else {}
        self.capture["init_kwargs"] = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, path, json=None, headers=None):
        self.capture["method"] = method
        self.capture["path"] = path
        self.capture["json"] = json
        self.capture["headers"] = headers
        if self.error is not None:
            raise self.error
        return self.response


class TestGameServicePatch3:
    def test_config_helpers_and_websocket_url(self, app):
        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = " https://play.example.com/ "
            app.config["PLAY_SERVICE_INTERNAL_URL"] = " https://internal.example.com/ "
            app.config["PLAY_SERVICE_SHARED_SECRET"] = "super-secret-value"
            app.config["PLAY_SERVICE_INTERNAL_API_KEY"] = "internal-key"

            assert has_complete_play_service_config() is True
            assert get_play_service_public_url() == "https://play.example.com"
            assert get_play_service_websocket_url() == "wss://play.example.com"
            assert _internal_headers() == {
                "Accept": "application/json",
                "X-Play-Service-Key": "internal-key",
            }

            app.config["PLAY_SERVICE_PUBLIC_URL"] = "http://play.example.com"
            assert get_play_service_websocket_url() == "ws://play.example.com"

    def test_missing_config_raises_clear_errors(self, app):
        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = ""
            app.config["PLAY_SERVICE_INTERNAL_URL"] = ""
            app.config["PLAY_SERVICE_SHARED_SECRET"] = ""

            assert has_complete_play_service_config() is False
            with pytest.raises(GameServiceConfigError, match="PLAY_SERVICE_PUBLIC_URL"):
                get_play_service_public_url()
            with pytest.raises(GameServiceConfigError, match="PLAY_SERVICE_SHARED_SECRET"):
                issue_play_ticket({"run_id": "run-1"})

    def test_request_success_error_and_empty_payload_paths(self, app, monkeypatch):
        capture = {}
        response = _FakeResponse(status_code=200, payload={"ok": True})
        monkeypatch.setattr(
            "app.services.game_service.httpx.Client",
            lambda **kwargs: _FakeClient(response=response, capture=capture, **kwargs),
        )

        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
            app.config["PLAY_SERVICE_REQUEST_TIMEOUT"] = 12
            payload = _request("GET", "/api/templates")

        assert payload == {"ok": True}
        assert capture["init_kwargs"]["base_url"] == "https://play.example.com"
        assert capture["init_kwargs"]["timeout"] == 12.0
        assert capture["method"] == "GET"
        assert capture["path"] == "/api/templates"

        error_capture = {}
        error_response = _FakeResponse(status_code=404, payload={"detail": "Run not found"})
        monkeypatch.setattr(
            "app.services.game_service.httpx.Client",
            lambda **kwargs: _FakeClient(response=error_response, capture=error_capture, **kwargs),
        )
        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
            with pytest.raises(GameServiceError, match="Run not found") as exc:
                _request("GET", "/api/runs/missing")
            assert exc.value.status_code == 404

        empty_capture = {}
        empty_response = _FakeResponse(status_code=200, payload={"ignored": True}, content=b"")
        monkeypatch.setattr(
            "app.services.game_service.httpx.Client",
            lambda **kwargs: _FakeClient(response=empty_response, capture=empty_capture, **kwargs),
        )
        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
            assert _request("GET", "/api/runs") is None

    def test_request_wraps_transport_failures(self, app, monkeypatch):
        transport_error = httpx.RequestError("down", request=httpx.Request("GET", "https://play.example.com"))
        monkeypatch.setattr(
            "app.services.game_service.httpx.Client",
            lambda **kwargs: _FakeClient(error=transport_error, **kwargs),
        )

        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
            with pytest.raises(GameServiceError, match="Play service unavailable") as exc:
                _request("GET", "/api/templates")
            assert exc.value.status_code == 502

    def test_wrapper_functions_validate_payload_shapes(self, app, monkeypatch):
        with app.app_context():
            app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
            app.config["PLAY_SERVICE_INTERNAL_URL"] = "https://play-internal.example.com"

            monkeypatch.setattr("app.services.game_service._request", lambda *args, **kwargs: [{"id": "tpl-1"}])
            assert list_templates() == [{"id": "tpl-1"}]
            assert list_runs() == [{"id": "tpl-1"}]

            monkeypatch.setattr("app.services.game_service._request", lambda *args, **kwargs: {"not": "a list"})
            assert list_templates() == []
            assert list_runs() == []

            monkeypatch.setattr("app.services.game_service._request", lambda *args, **kwargs: {"run": {"id": "run-1"}})
            assert create_run(template_id="tpl-1", account_id="7", display_name="Bruno") == {"run": {"id": "run-1"}}
            assert get_run_details("run-1") == {"run": {"id": "run-1"}}
            assert get_run_transcript("run-1") == {"run": {"id": "run-1"}}
            assert terminate_run("run-1") == {"run": {"id": "run-1"}}

            monkeypatch.setattr(
                "app.services.game_service._request",
                lambda *args, **kwargs: {
                    "run_id": "run-1",
                    "participant_id": "p-1",
                    "role_id": "mediator",
                    "display_name": "Bruno",
                    "account_id": "7",
                    "character_id": "11",
                },
            )
            join_context = resolve_join_context(run_id="run-1", account_id="7", display_name="Bruno")
            assert join_context == PlayJoinContext(
                run_id="run-1",
                participant_id="p-1",
                role_id="mediator",
                display_name="Bruno",
                account_id="7",
                character_id="11",
            )

            monkeypatch.setattr("app.services.game_service._request", lambda *args, **kwargs: ["unexpected"])
            with pytest.raises(GameServiceError, match="unexpected create_run payload"):
                create_run(template_id="tpl-1", account_id="7", display_name="Bruno")
            with pytest.raises(GameServiceError, match="unexpected join-context payload"):
                resolve_join_context(run_id="run-1", account_id="7", display_name="Bruno")
            with pytest.raises(GameServiceError, match="unexpected run detail payload"):
                get_run_details("run-1")
            with pytest.raises(GameServiceError, match="unexpected transcript payload"):
                get_run_transcript("run-1")
            with pytest.raises(GameServiceError, match="unexpected terminate payload"):
                terminate_run("run-1")

    def test_issue_play_ticket_encodes_signed_payload(self, app, monkeypatch):
        monkeypatch.setattr("app.services.game_service.time.time", lambda: 1_700_000_000)
        with app.app_context():
            app.config["PLAY_SERVICE_SHARED_SECRET"] = "shared-secret-value"
            app.config["GAME_TICKET_TTL_SECONDS"] = 120
            ticket = issue_play_ticket({"run_id": "run-1", "participant_id": "p-1"})

        raw = base64.urlsafe_b64decode(ticket.encode("ascii"))
        body_bytes, signature = raw.rsplit(b".", 1)
        payload = json.loads(body_bytes.decode("utf-8"))

        assert payload["run_id"] == "run-1"
        assert payload["participant_id"] == "p-1"
        assert payload["iat"] == 1_700_000_000
        assert payload["exp"] == 1_700_000_120
        assert len(signature) == 64
