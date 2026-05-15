"""HTTP contract tests for remote template feeds (stdlib server, real httpx client)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from app.content.backend_loader import BackendContentLoadError, load_published_templates
from app.content.backend_source import RemoteContentError, load_remote_templates
from app.content.models import BeatTemplate, ExperienceKind, ExperienceTemplate, JoinPolicy


class _TemplateFeedHandler(BaseHTTPRequestHandler):
    payload: dict[str, Any] = {}
    status_code: int = 200

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.status_code >= 400:
            self.send_response(self.status_code)
            self.end_headers()
            return
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _minimal_template_dict(*, template_id: str = "tpl_http") -> dict[str, Any]:
    return ExperienceTemplate(
        id=template_id,
        title="HTTP Fixture",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary="fixture",
        max_humans=1,
        initial_beat_id="opening",
        roles=[],
        rooms=[],
        props=[],
        actions=[],
        beats=[
            BeatTemplate(
                id="opening",
                name="Opening",
                description="fixture",
                summary="fixture",
            )
        ],
    ).model_dump(mode="json")


@pytest.fixture
def template_feed_url() -> str:
    _TemplateFeedHandler.payload = {
        "templates": [_minimal_template_dict()],
        "items": [{"payload": _minimal_template_dict(template_id="tpl_remote")}],
    }
    _TemplateFeedHandler.status_code = 200
    server = HTTPServer(("127.0.0.1", 0), _TemplateFeedHandler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    base = f"http://{server.server_address[0]}:{server.server_address[1]}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.contract
def test_load_published_templates_from_backend_feed(template_feed_url: str) -> None:
    templates = load_published_templates(f"{template_feed_url}/feed")
    assert "tpl_http" in templates
    assert isinstance(templates["tpl_http"], ExperienceTemplate)


@pytest.mark.contract
def test_load_remote_templates_items_shape(template_feed_url: str) -> None:
    templates = load_remote_templates(f"{template_feed_url}/remote")
    assert "tpl_remote" in templates


@pytest.mark.contract
def test_load_published_templates_empty_url_returns_empty() -> None:
    assert load_published_templates("   ") == {}


@pytest.mark.contract
def test_load_remote_templates_empty_url_returns_empty() -> None:
    assert load_remote_templates("   ") == {}


def test_load_remote_templates_rejects_http_error() -> None:
    with pytest.raises(RemoteContentError, match="Failed to fetch remote templates"):
        load_remote_templates("http://127.0.0.1:1/not-running-feed")


@pytest.mark.contract
def test_load_remote_templates_rejects_http_status(template_feed_url: str) -> None:
    _TemplateFeedHandler.status_code = 503
    try:
        with pytest.raises(RemoteContentError, match="HTTP 503"):
            load_remote_templates(f"{template_feed_url}/remote")
    finally:
        _TemplateFeedHandler.status_code = 200


@pytest.mark.contract
def test_load_remote_templates_rejects_unexpected_payload(template_feed_url: str) -> None:
    _TemplateFeedHandler.payload = {"items": "not-a-list"}
    with pytest.raises(RemoteContentError, match="unexpected payload"):
        load_remote_templates(f"{template_feed_url}/remote")


@pytest.mark.contract
def test_load_remote_templates_skips_malformed_rows(template_feed_url: str) -> None:
    _TemplateFeedHandler.payload = {
        "items": [
            "skip-me",
            {"payload": "also-skip"},
            {"payload": _minimal_template_dict(template_id="tpl_row")},
        ]
    }
    templates = load_remote_templates(f"{template_feed_url}/remote")
    assert list(templates) == ["tpl_row"]


@pytest.mark.contract
def test_load_published_templates_rejects_invalid_payload(template_feed_url: str) -> None:
    _TemplateFeedHandler.payload = {"not_templates": True}
    with pytest.raises(BackendContentLoadError, match="invalid templates payload"):
        load_published_templates(f"{template_feed_url}/bad")
