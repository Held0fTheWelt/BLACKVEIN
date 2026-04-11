"""Tests for backend_loader and backend_source template HTTP loading."""

from __future__ import annotations

import httpx
import pytest

from app.content.backend_loader import BackendContentLoadError, load_published_templates
from app.content.backend_source import RemoteContentError, load_remote_templates


VALID_TEMPLATE = {
    "id": "patch-template",
    "title": "Patch Template",
    "kind": "solo_story",
    "join_policy": "owner_only",
    "summary": "Patch coverage template.",
    "max_humans": 1,
    "min_humans_to_start": 1,
    "persistent": False,
    "initial_beat_id": "intro",
    "roles": [
        {
            "id": "visitor",
            "display_name": "Visitor",
            "description": "Player role",
            "mode": "human",
            "initial_room_id": "hallway",
            "can_join": True,
        }
    ],
    "rooms": [
        {
            "id": "hallway",
            "name": "Hallway",
            "description": "Start room",
            "exits": [],
            "prop_ids": [],
            "action_ids": [],
            "artwork_prompt": None,
        }
    ],
    "props": [],
    "actions": [],
    "beats": [
        {
            "id": "intro",
            "name": "Intro",
            "description": "Opening beat",
            "summary": "Opening summary",
        }
    ],
    "tags": ["patch"],
    "style_profile": "retro_pulp",
}


class FakeResponse:
    def __init__(self, payload, status_code: int = 200, raise_exc: Exception | None = None):
        self._payload = payload
        self.status_code = status_code
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc is not None:
            raise self._raise_exc
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("GET", "https://example.invalid"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, response: FakeResponse | Exception):
        self.response = response
        self.calls: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str):
        self.calls.append(url)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_load_published_templates_returns_empty_for_blank_source_url():
    assert load_published_templates("   ") == {}


def test_load_published_templates_parses_valid_payload(monkeypatch):
    def fake_get(url: str, timeout: float):
        assert url == "https://content.example/templates"
        assert timeout == 2.5
        return FakeResponse({"templates": [VALID_TEMPLATE]})

    monkeypatch.setattr("app.content.backend_loader.httpx.get", fake_get)

    templates = load_published_templates("https://content.example/templates", timeout=2.5)

    assert list(templates) == ["patch-template"]
    assert templates["patch-template"].title == "Patch Template"


def test_load_published_templates_rejects_non_list_templates_payload(monkeypatch):
    monkeypatch.setattr(
        "app.content.backend_loader.httpx.get",
        lambda url, timeout: FakeResponse({"templates": {"bad": "shape"}}),
    )

    with pytest.raises(BackendContentLoadError, match="invalid templates payload"):
        load_published_templates("https://content.example/templates")


def test_load_published_templates_wraps_transport_errors(monkeypatch):
    monkeypatch.setattr(
        "app.content.backend_loader.httpx.get",
        lambda url, timeout: (_ for _ in ()).throw(RuntimeError("socket closed")),
    )

    with pytest.raises(BackendContentLoadError, match="Unable to load backend content feed: socket closed"):
        load_published_templates("https://content.example/templates")


def test_load_published_templates_rejects_invalid_template_rows(monkeypatch):
    invalid = dict(VALID_TEMPLATE)
    invalid.pop("id")

    monkeypatch.setattr(
        "app.content.backend_loader.httpx.get",
        lambda url, timeout: FakeResponse({"templates": [invalid]}),
    )

    with pytest.raises(BackendContentLoadError, match="Invalid backend template payload"):
        load_published_templates("https://content.example/templates")


def test_load_remote_templates_returns_empty_for_blank_url():
    assert load_remote_templates("  ") == {}


def test_load_remote_templates_normalizes_url_and_accepts_list_payload(monkeypatch):
    fake_client = FakeClient(FakeResponse([VALID_TEMPLATE]))

    monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: fake_client)

    templates = load_remote_templates("https://remote.example/feed///")

    assert fake_client.calls == ["https://remote.example/feed"]
    assert list(templates) == ["patch-template"]


def test_load_remote_templates_supports_items_wrapper_and_skips_invalid_rows(monkeypatch):
    duplicate = dict(VALID_TEMPLATE)
    duplicate["title"] = "Override Title"
    fake_client = FakeClient(
        FakeResponse(
            {
                "items": [
                    "not-a-dict",
                    {"payload": "bad-payload"},
                    VALID_TEMPLATE,
                    {"payload": duplicate},
                ]
            }
        )
    )

    monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: fake_client)

    templates = load_remote_templates("https://remote.example/feed")

    assert list(templates) == ["patch-template"]
    assert templates["patch-template"].title == "Override Title"


def test_load_remote_templates_wraps_request_errors(monkeypatch):
    request = httpx.Request("GET", "https://remote.example/feed")
    fake_client = FakeClient(httpx.RequestError("boom", request=request))

    monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: fake_client)

    with pytest.raises(RemoteContentError, match="Failed to fetch remote templates: boom"):
        load_remote_templates("https://remote.example/feed")


def test_load_remote_templates_rejects_http_error_status(monkeypatch):
    fake_client = FakeClient(FakeResponse({"items": []}, status_code=503))

    monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: fake_client)

    with pytest.raises(RemoteContentError, match="HTTP 503"):
        load_remote_templates("https://remote.example/feed")


def test_load_remote_templates_rejects_unexpected_payload_shape(monkeypatch):
    fake_client = FakeClient(FakeResponse({"items": "not-a-list"}))

    monkeypatch.setattr("app.content.backend_source.httpx.Client", lambda timeout=10.0: fake_client)

    with pytest.raises(RemoteContentError, match="unexpected payload"):
        load_remote_templates("https://remote.example/feed")
