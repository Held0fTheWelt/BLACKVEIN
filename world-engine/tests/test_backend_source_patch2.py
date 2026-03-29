from __future__ import annotations

import httpx
import pytest

from app.content.backend_source import RemoteContentError, load_remote_templates


class _Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.requested_url = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        self.requested_url = url
        if self.exc is not None:
            raise self.exc
        return self.response


class TestBackendSourceAdditionalCoverage:
    def test_blank_source_url_returns_empty_mapping(self):
        assert load_remote_templates("") == {}
        assert load_remote_templates("   ") == {}

    def test_load_remote_templates_supports_payload_wrappers_and_skips_invalid_rows(self, monkeypatch):
        client = _Client(
            response=_Response(
                payload={
                    "items": [
                        {
                            "payload": {
                                "id": "remote_story",
                                "title": "Remote Story",
                                "kind": "solo_story",
                                "join_policy": "owner_only",
                                "summary": "Loaded from backend.",
                                "max_humans": 1,
                                "initial_beat_id": "intro",
                                "roles": [
                                    {
                                        "id": "visitor",
                                        "display_name": "Visitor",
                                        "description": "Human role",
                                        "mode": "human",
                                        "initial_room_id": "hall",
                                        "can_join": True,
                                    }
                                ],
                                "rooms": [{"id": "hall", "name": "Hall", "description": "Room"}],
                                "props": [],
                                "actions": [],
                                "beats": [
                                    {
                                        "id": "intro",
                                        "name": "Intro",
                                        "description": "Beginning",
                                        "summary": "Start here",
                                    }
                                ],
                            }
                        },
                        "bad-row",
                        {"payload": "bad-payload"},
                    ]
                }
            )
        )
        monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: client)

        templates = load_remote_templates(" https://backend.example/api/templates/ ")

        assert list(templates) == ["remote_story"]
        assert templates["remote_story"].title == "Remote Story"
        assert client.requested_url == "https://backend.example/api/templates"

    def test_load_remote_templates_raises_for_http_and_transport_errors(self, monkeypatch):
        failing_client = _Client(response=_Response(status_code=500, payload={}))
        monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: failing_client)
        with pytest.raises(RemoteContentError, match="HTTP 500"):
            load_remote_templates("https://backend.example/api/templates")

        request_error = httpx.RequestError("boom")
        exploding_client = _Client(exc=request_error)
        monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: exploding_client)
        with pytest.raises(RemoteContentError, match="Failed to fetch remote templates"):
            load_remote_templates("https://backend.example/api/templates")

    def test_load_remote_templates_rejects_unexpected_payload_shape(self, monkeypatch):
        client = _Client(response=_Response(payload={"items": {"not": "a-list"}}))
        monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: client)

        with pytest.raises(RemoteContentError, match="unexpected payload"):
            load_remote_templates("https://backend.example/api/templates")
