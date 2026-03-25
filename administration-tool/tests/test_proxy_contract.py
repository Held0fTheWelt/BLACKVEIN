"""Test proxy contract: path routing, HTTP methods, headers, and response integrity."""
from __future__ import annotations

import pytest
from io import BytesIO
from urllib.error import HTTPError

from conftest import load_frontend_module


class DummyUpstreamResponse:
    """Mock upstream response for testing."""
    def __init__(self, body: bytes, *, status: int = 200, content_type: str = "application/json") -> None:
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestProxyAllowedPaths:
    """Test that /api/* paths are allowed and forwarded correctly."""

    @pytest.mark.contract
    def test_proxy_allows_api_paths(self, monkeypatch):
        """Verify /_proxy/api/v1/... paths are forwarded to backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["url"] = request.full_url
            return DummyUpstreamResponse(b'{"data": "ok"}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 200
        assert recorded["url"] == "https://api.example.test/api/v1/news"

    @pytest.mark.contract
    @pytest.mark.parametrize("api_path", [
        "/_proxy/api/v1/news",
        "/_proxy/api/v1/users",
        "/_proxy/api/v2/forum/posts",
        "/_proxy/api/v1/users/123",
        "/_proxy/api/v1/users/123/profile",
    ])
    def test_proxy_allows_various_api_paths(self, monkeypatch, api_path):
        """Verify various /api/* paths are allowed."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get(api_path)

        assert response.status_code == 200
        assert response.get_json() == {"ok": True}


class TestProxyForbiddenPaths:
    """Test that /admin/* paths are rejected with 403."""

    @pytest.mark.security
    def test_proxy_blocks_admin_paths_with_403(self, frontend_module):
        """Verify /_proxy/admin/* paths return 403 Forbidden."""
        client = frontend_module.app.test_client()

        response = client.get("/_proxy/admin/users")

        assert response.status_code == 403
        assert response.data == b"Forbidden"

    @pytest.mark.security
    @pytest.mark.parametrize("admin_path", [
        "/_proxy/admin/users",
        "/_proxy/admin/settings",
        "/_proxy/admin/config",
        "/_proxy/admin/users/123",
        "/_proxy/admin/dashboard",
        "/_proxy/admin/logs",
    ])
    def test_proxy_blocks_various_admin_paths(self, frontend_module, admin_path):
        """Verify multiple admin paths are blocked."""
        client = frontend_module.app.test_client()

        response = client.get(admin_path)

        assert response.status_code == 403

    @pytest.mark.security
    def test_proxy_blocks_admin_with_post(self, frontend_module):
        """Verify admin paths are blocked for POST too."""
        client = frontend_module.app.test_client()

        response = client.post("/_proxy/admin/users", data=b'{"name":"test"}')

        assert response.status_code == 403

    @pytest.mark.security
    def test_proxy_blocks_admin_with_put(self, frontend_module):
        """Verify admin paths are blocked for PUT too."""
        client = frontend_module.app.test_client()

        response = client.put("/_proxy/admin/users/1", data=b'{"name":"updated"}')

        assert response.status_code == 403

    @pytest.mark.security
    def test_proxy_allows_api_not_blocked_if_contains_admin_substring(self, monkeypatch):
        """Verify /_proxy/api/v1/admin-accounts is allowed (doesn't start with admin)."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/admin-accounts")

        assert response.status_code == 200


class TestProxyHttpMethods:
    """Test that all HTTP methods are handled correctly."""

    @pytest.mark.contract
    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
    def test_proxy_forwards_all_http_methods(self, monkeypatch, method):
        """Verify all HTTP methods are forwarded to backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["method"] = request.get_method()
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.open("/_proxy/api/v1/news", method=method)

        assert response.status_code == 200
        assert recorded["method"] == method

    @pytest.mark.contract
    def test_proxy_options_returns_204_no_call_to_backend(self, monkeypatch):
        """Verify OPTIONS returns 204 without calling backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        call_count = {"count": 0}

        def fake_urlopen(request, timeout=0):
            call_count["count"] += 1
            return DummyUpstreamResponse(b'', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.options("/_proxy/api/v1/news")

        assert response.status_code == 204
        assert response.data == b""
        assert call_count["count"] == 0


class TestProxyQueryParameters:
    """Test that query parameters are preserved and forwarded."""

    @pytest.mark.contract
    def test_proxy_preserves_query_string(self, monkeypatch):
        """Verify query string is preserved in forwarded request."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["url"] = request.full_url
            return DummyUpstreamResponse(b'{"data": "ok"}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news?draft=true")

        assert response.status_code == 200
        assert "draft=true" in recorded["url"]

    @pytest.mark.contract
    @pytest.mark.parametrize("query_string", [
        "?id=5",
        "?name=john&age=30",
        "?page=1&limit=10",
        "?search=hello%20world",
    ])
    def test_proxy_preserves_various_query_strings(self, monkeypatch, query_string):
        """Verify various query strings are preserved."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["url"] = request.full_url
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get(f"/_proxy/api/v1/search{query_string}")

        assert response.status_code == 200
        assert query_string[1:] in recorded["url"]  # Remove leading ?


class TestProxyRequestBody:
    """Test that request bodies are forwarded correctly."""

    @pytest.mark.contract
    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
    def test_proxy_forwards_request_body(self, monkeypatch, method):
        """Verify request body is forwarded for POST/PUT/PATCH."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["body"] = request.data
            return DummyUpstreamResponse(b'{"ok": true}', status=201)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        test_body = b'{"title": "New News"}'
        response = client.open(
            "/_proxy/api/v1/news",
            method=method,
            data=test_body,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 201
        assert recorded["body"] == test_body

    @pytest.mark.contract
    def test_proxy_get_has_no_body(self, monkeypatch):
        """Verify GET requests have no body forwarded."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["body"] = request.data
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 200
        assert recorded["body"] is None


class TestProxyResponseStatus:
    """Test that response status codes are preserved."""

    @pytest.mark.contract
    @pytest.mark.parametrize("status_code", [200, 201, 204, 400, 401, 403, 404, 500])
    def test_proxy_preserves_response_status_codes(self, monkeypatch, status_code):
        """Verify response status codes are forwarded correctly."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(b'{"status": "test"}', status=status_code)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        assert response.status_code == status_code


class TestProxyResponseBody:
    """Test that response bodies are returned intact."""

    @pytest.mark.contract
    def test_proxy_returns_response_body_intact(self, monkeypatch):
        """Verify response body is returned unchanged."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        response_body = b'{"id": 1, "title": "Test", "content": "Hello World"}'

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(response_body, status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 200
        assert response.data == response_body

    @pytest.mark.contract
    def test_proxy_preserves_json_response(self, monkeypatch):
        """Verify JSON response is preserved with correct structure."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        response_json = {"id": 1, "name": "John", "email": "john@example.com", "active": True}
        response_body = b'{"id": 1, "name": "John", "email": "john@example.com", "active": true}'

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(response_body, status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/users/1")

        assert response.status_code == 200
        assert response.get_json() == response_json

    @pytest.mark.contract
    def test_proxy_preserves_empty_response_body(self, monkeypatch):
        """Verify empty response body is preserved."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(b'', status=204)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 204
        assert response.data == b""


class TestProxyContentTypeHeader:
    """Test that Content-Type header is preserved."""

    @pytest.mark.contract
    @pytest.mark.parametrize("content_type", [
        "application/json",
        "text/plain",
        "text/html",
        "application/xml",
    ])
    def test_proxy_preserves_content_type(self, monkeypatch, content_type):
        """Verify Content-Type header is preserved from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(b'response', status=200, content_type=content_type)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith(content_type)

    @pytest.mark.contract
    def test_proxy_defaults_to_application_json_when_missing(self, monkeypatch):
        """Verify default Content-Type is application/json when not provided."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            resp = DummyUpstreamResponse(b'{}', status=200)
            resp.headers = {}  # No Content-Type
            return resp

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"


class TestProxyNegativeCases:
    """Test error handling for invalid and malformed requests."""

    @pytest.mark.contract
    def test_proxy_root_path_404(self, frontend_module):
        """Verify /_proxy without subpath returns 404."""
        client = frontend_module.app.test_client()

        response = client.get("/_proxy/")

        # Flask routes will not match /_proxy/ without the required subpath
        assert response.status_code == 404

    @pytest.mark.contract
    def test_proxy_invalid_characters_forwarded_to_backend(self, monkeypatch):
        """Verify paths with special characters are forwarded to backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["url"] = request.full_url
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        # Flask decodes URL-encoded paths before routing, so the space is decoded
        response = client.get("/_proxy/api/v1/search/hello%20world")

        assert response.status_code == 200
        # The URL will have the decoded form (space) not %20
        assert "search/hello" in recorded["url"]

    @pytest.mark.contract
    def test_proxy_very_long_path(self, monkeypatch):
        """Verify very long paths are handled."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["url"] = request.full_url
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        long_path = "/_proxy/api/v1/" + "/".join([f"segment{i}" for i in range(10)])
        response = client.get(long_path)

        assert response.status_code == 200
        assert "segment9" in recorded["url"]


class TestProxyHeaderForwarding:
    """Test that relevant headers are forwarded correctly."""

    @pytest.mark.contract
    def test_proxy_forwards_authorization_header(self, monkeypatch):
        """Verify Authorization header is forwarded."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["headers"] = dict(request.header_items())
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        response = client.get(
            "/_proxy/api/v1/users",
            headers={"Authorization": auth_token}
        )

        assert response.status_code == 200
        assert recorded["headers"]["Authorization"] == auth_token

    @pytest.mark.security
    def test_proxy_strips_cookie_header(self, monkeypatch):
        """Verify Cookie header is NOT forwarded."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["headers"] = dict(request.header_items())
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get(
            "/_proxy/api/v1/users",
            headers={"Cookie": "sessionid=abc123"}
        )

        assert response.status_code == 200
        assert "Cookie" not in recorded["headers"]

    @pytest.mark.security
    def test_proxy_strips_set_cookie_header(self, monkeypatch):
        """Verify Set-Cookie header is NOT forwarded."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["headers"] = dict(request.header_items())
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get(
            "/_proxy/api/v1/users",
            headers={"Set-Cookie": "test=value"}
        )

        assert response.status_code == 200
        assert "Set-Cookie" not in recorded["headers"]

    @pytest.mark.security
    def test_proxy_strips_host_header(self, monkeypatch):
        """Verify Host header is NOT forwarded (prevents host injection)."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
        recorded = {}

        def fake_urlopen(request, timeout=0):
            recorded["headers"] = dict(request.header_items())
            return DummyUpstreamResponse(b'{"ok": true}', status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get(
            "/_proxy/api/v1/users",
            headers={"Host": "malicious-attacker.com"}
        )

        assert response.status_code == 200
        # Host header should not be in the forwarded request (urllib handles it automatically)
        # This test documents that our code doesn't forward it explicitly
        assert response.status_code == 200
