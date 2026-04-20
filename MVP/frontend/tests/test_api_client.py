"""Tests for app.api_client (backend HTTP helper)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app import create_app
from app.api_client import (
    BackendApiError,
    require_success,
    request_backend,
)
from app.config import TestingConfig


@pytest.fixture
def app_ctx():
    app = create_app(TestingConfig)
    with app.test_request_context():
        yield app


def test_backend_api_error_attrs():
    exc = BackendApiError("nope", status_code=418, payload={"x": 1})
    assert str(exc) == "nope"
    assert exc.status_code == 418
    assert exc.payload == {"x": 1}


def test_api_url_with_and_without_leading_slash(app_ctx):
    app_ctx.config["BACKEND_API_URL"] = "http://api.example/"
    from app.api_client import _api_url

    assert _api_url("/v1/x") == "http://api.example/v1/x"
    assert _api_url("v1/x") == "http://api.example/v1/x"


def test_auth_headers_empty_and_with_token(app_ctx):
    from app.api_client import _auth_headers
    from flask import session

    session.clear()
    assert _auth_headers() == {}

    session["access_token"] = "tok"
    assert _auth_headers() == {"Authorization": "Bearer tok"}


def test_refresh_tokens_no_refresh(app_ctx):
    from app.api_client import _refresh_tokens
    from flask import session

    session.clear()
    assert _refresh_tokens() is False


def test_refresh_tokens_non_200(app_ctx, monkeypatch):
    from app.api_client import _refresh_tokens
    from flask import session

    session["refresh_token"] = "r1"
    monkeypatch.setattr(
        "app.api_client.requests.post",
        lambda *a, **k: MagicMock(status_code=401),
    )
    assert _refresh_tokens() is False


def test_refresh_tokens_invalid_payload(app_ctx, monkeypatch):
    from app.api_client import _refresh_tokens
    from flask import session

    session["refresh_token"] = "r1"
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"access_token": "a"}
    monkeypatch.setattr("app.api_client.requests.post", lambda *a, **k: mock_resp)
    assert _refresh_tokens() is False


def test_refresh_tokens_success(app_ctx, monkeypatch):
    from app.api_client import _refresh_tokens
    from flask import session

    session["refresh_token"] = "old-r"
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"access_token": "new-a", "refresh_token": "new-r"}
    monkeypatch.setattr("app.api_client.requests.post", lambda *a, **k: mock_resp)
    assert _refresh_tokens() is True
    assert session["access_token"] == "new-a"
    assert session["refresh_token"] == "new-r"


def test_request_backend_no_retry_on_401_when_refresh_disabled(app_ctx, monkeypatch):
    calls: list[MagicMock] = []

    def fake_request(*a, **k):
        m = MagicMock()
        m.status_code = 401
        m.ok = False
        calls.append(m)
        return m

    monkeypatch.setattr("app.api_client.requests.request", fake_request)
    monkeypatch.setattr("app.api_client._refresh_tokens", lambda: True)
    r = request_backend("GET", "/x", allow_refresh=False)
    assert r.status_code == 401
    assert len(calls) == 1


def test_request_backend_retries_after_refresh(app_ctx, monkeypatch):
    responses: list[MagicMock] = [
        MagicMock(status_code=401, ok=False),
        MagicMock(status_code=200, ok=True),
    ]

    def fake_request(*a, **k):
        return responses.pop(0)

    monkeypatch.setattr("app.api_client.requests.request", fake_request)
    monkeypatch.setattr("app.api_client._refresh_tokens", lambda: True)
    r = request_backend("GET", "/ok")
    assert r.status_code == 200
    assert len(responses) == 0


def test_request_backend_401_refresh_fails_no_second_call(app_ctx, monkeypatch):
    calls = 0

    def fake_request(*a, **k):
        nonlocal calls
        calls += 1
        m = MagicMock()
        m.status_code = 401
        m.ok = False
        return m

    monkeypatch.setattr("app.api_client.requests.request", fake_request)
    monkeypatch.setattr("app.api_client._refresh_tokens", lambda: False)
    r = request_backend("GET", "/x")
    assert r.status_code == 401
    assert calls == 1


def test_require_success_ok():
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"items": [1]}
    assert require_success(resp, "fail") == {"items": [1]}


def test_require_success_error_with_error_key():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 400
    resp.json.return_value = {"error": "bad"}
    with pytest.raises(BackendApiError) as ei:
        require_success(resp, "default")
    assert ei.value.status_code == 400
    assert str(ei.value) == "bad"


def test_require_success_error_uses_message_key():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 422
    resp.json.return_value = {"message": "msg"}
    with pytest.raises(BackendApiError) as ei:
        require_success(resp, "default")
    assert str(ei.value) == "msg"


def test_require_success_error_falls_back_to_default():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 500
    resp.json.return_value = {}
    with pytest.raises(BackendApiError) as ei:
        require_success(resp, "fallback msg")
    assert str(ei.value) == "fallback msg"


def test_require_success_invalid_json_body():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 502
    resp.json.side_effect = ValueError()
    with pytest.raises(BackendApiError) as ei:
        require_success(resp, "x")
    assert str(ei.value) == "x"


def test_handle_request_exception_api_path_json(client, monkeypatch):
    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr("app.routes.request_backend", boom)
    r = client.get("/api/v1/news")
    assert r.status_code == 503
    assert r.is_json
    assert r.get_json()["error"] == "Backend API unavailable."


def test_handle_request_exception_html_redirect(client, monkeypatch):
    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr("app.routes.request_backend", boom)
    r = client.get("/news", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/")


def test_handle_backend_error_api_json(client, monkeypatch):
    def fail(*a, **k):
        raise BackendApiError("be", status_code=409, payload={"code": 1})

    monkeypatch.setattr("app.routes.request_backend", fail)
    r = client.get("/api/v1/foo/bar")
    assert r.status_code == 409
    body = r.get_json()
    assert body["error"] == "be"
    assert body["code"] == 1


def test_handle_backend_error_html_redirect(client, monkeypatch):
    def fail(*a, **k):
        raise BackendApiError("be", status_code=500)

    monkeypatch.setattr("app.routes.request_backend", fail)
    r = client.get("/news", follow_redirects=False)
    assert r.status_code == 302
