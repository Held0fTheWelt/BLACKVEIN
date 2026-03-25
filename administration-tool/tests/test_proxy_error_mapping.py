"""Test proxy error mapping: timeouts, network errors, backend errors, malformed responses."""
from __future__ import annotations

import pytest
import socket
from io import BytesIO
from urllib.error import HTTPError, URLError

from conftest import load_frontend_module


class DummyUpstreamResponse:
    """Mock upstream response for testing."""
    def __init__(self, body: bytes, *, status: int = 200, content_type: str = "application/json") -> None:
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestProxyTimeoutError:
    """Test that backend timeouts are mapped to 502 Bad Gateway."""

    @pytest.mark.integration
    def test_proxy_timeout_returns_502(self, monkeypatch):
        """Verify URLError with socket timeout reason is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            # socket.timeout wrapped in URLError
            raise URLError(socket.timeout("Connection timed out"))

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        # URLError with timeout is mapped to 502
        assert response.status_code == 502

    @pytest.mark.integration
    def test_proxy_urlerror_timeout_returns_502(self, monkeypatch):
        """Verify URLError with timeout reason is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("_ssl.c:1000: The handshake operation timed out")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502


class TestProxyNetworkErrors:
    """Test that network errors are mapped to 502 Bad Gateway."""

    @pytest.mark.integration
    def test_proxy_urlerror_connection_refused_returns_502(self, monkeypatch):
        """Verify URLError with connection refused is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("[Errno 111] Connection refused")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502
        assert response.data == b"Upstream network error"

    @pytest.mark.integration
    def test_proxy_urlerror_name_resolution_returns_502(self, monkeypatch):
        """Verify URLError with DNS resolution failure is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("nodename nor servname provided, or not known")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502

    @pytest.mark.integration
    def test_proxy_urlerror_network_unreachable_returns_502(self, monkeypatch):
        """Verify URLError with network unreachable is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("[Errno 101] Network is unreachable")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502


class TestProxyBackendAuthErrors:
    """Test that backend 401/403 errors are forwarded correctly."""

    @pytest.mark.security
    def test_proxy_backend_401_forwarded(self, monkeypatch):
        """Verify backend 401 Unauthorized is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=401,
                msg="Unauthorized",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Unauthorized"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/protected")

        assert response.status_code == 401
        assert response.get_json() == {"error": "Unauthorized"}

    @pytest.mark.security
    def test_proxy_backend_403_forwarded(self, monkeypatch):
        """Verify backend 403 Forbidden is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=403,
                msg="Forbidden",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Access denied"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/restricted")

        assert response.status_code == 403
        assert response.get_json() == {"error": "Access denied"}


class TestProxyBackendNotFoundErrors:
    """Test that backend 404 errors are forwarded correctly."""

    @pytest.mark.contract
    def test_proxy_backend_404_forwarded(self, monkeypatch):
        """Verify backend 404 Not Found is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=404,
                msg="Not Found",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Resource not found"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/nonexistent")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Resource not found"}


class TestProxyBackendRateLimitErrors:
    """Test that backend 429 errors are forwarded correctly."""

    @pytest.mark.contract
    def test_proxy_backend_429_forwarded(self, monkeypatch):
        """Verify backend 429 Too Many Requests is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Rate limit exceeded"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 429
        assert response.get_json() == {"error": "Rate limit exceeded"}


class TestProxyBackendServerErrors:
    """Test that backend 500+ errors are forwarded correctly."""

    @pytest.mark.contract
    def test_proxy_backend_500_forwarded(self, monkeypatch):
        """Verify backend 500 Internal Server Error is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Internal server error"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Internal server error"}

    @pytest.mark.contract
    def test_proxy_backend_503_forwarded(self, monkeypatch):
        """Verify backend 503 Service Unavailable is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=503,
                msg="Service Unavailable",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Service unavailable"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 503
        assert response.get_json() == {"error": "Service unavailable"}

    @pytest.mark.contract
    def test_proxy_backend_502_forwarded(self, monkeypatch):
        """Verify backend 502 Bad Gateway is forwarded as-is."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=502,
                msg="Bad Gateway",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Bad gateway"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 502
        assert response.get_json() == {"error": "Bad gateway"}


class TestProxyErrorResponseBodies:
    """Test that error response bodies from backend are preserved."""

    @pytest.mark.contract
    def test_proxy_preserves_json_error_body(self, monkeypatch):
        """Verify JSON error body is preserved from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        error_body = b'{"error": "Validation failed", "details": {"field": "email"}}'

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=400,
                msg="Bad Request",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(error_body),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.post("/_proxy/api/v1/users", data=b'{"invalid": "data"}')

        assert response.status_code == 400
        assert response.data == error_body

    @pytest.mark.contract
    def test_proxy_preserves_plain_text_error_body(self, monkeypatch):
        """Verify plain text error body is preserved from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        error_body = b"Bad Request: Missing required field"

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=400,
                msg="Bad Request",
                hdrs={"Content-Type": "text/plain"},
                fp=BytesIO(error_body),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.post("/_proxy/api/v1/users", data=b'{}')

        assert response.status_code == 400
        assert response.data == error_body

    @pytest.mark.contract
    def test_proxy_preserves_html_error_body(self, monkeypatch):
        """Verify HTML error body is preserved from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        error_body = b'<html><body><h1>500 Internal Server Error</h1></body></html>'

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs={"Content-Type": "text/html"},
                fp=BytesIO(error_body),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")

        assert response.status_code == 500
        assert response.data == error_body

    @pytest.mark.contract
    def test_proxy_preserves_empty_error_body(self, monkeypatch):
        """Verify empty error body is preserved from backend."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=401,
                msg="Unauthorized",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b''),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/protected")

        assert response.status_code == 401
        assert response.data == b''


class TestProxyErrorContentTypeHeaders:
    """Test that Content-Type header is preserved in error responses."""

    @pytest.mark.contract
    @pytest.mark.parametrize("status_code,content_type", [
        (400, "application/json"),
        (401, "text/plain"),
        (403, "text/html"),
        (404, "application/xml"),
        (500, "application/json"),
    ])
    def test_proxy_preserves_error_content_type(self, monkeypatch, status_code, content_type):
        """Verify Content-Type header is preserved in error responses."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=status_code,
                msg="Error",
                hdrs={"Content-Type": content_type},
                fp=BytesIO(b'{"error": "test"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        assert response.status_code == status_code
        assert response.headers["Content-Type"].startswith(content_type)


class TestProxyErrorMappingComprehensive:
    """Test error mapping for all common HTTP error codes."""

    @pytest.mark.contract
    @pytest.mark.parametrize("status_code", [
        400,  # Bad Request
        401,  # Unauthorized
        403,  # Forbidden
        404,  # Not Found
        405,  # Method Not Allowed
        408,  # Request Timeout
        409,  # Conflict
        410,  # Gone
        413,  # Payload Too Large
        415,  # Unsupported Media Type
        429,  # Too Many Requests
        500,  # Internal Server Error
        501,  # Not Implemented
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ])
    def test_proxy_forwards_all_error_codes(self, monkeypatch, status_code):
        """Verify all common HTTP error codes are forwarded correctly."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=status_code,
                msg="Error",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "test"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        assert response.status_code == status_code


class TestProxyErrorMappingWithMethods:
    """Test error handling for different HTTP methods."""

    @pytest.mark.contract
    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_proxy_error_mapping_for_all_methods(self, monkeypatch, method):
        """Verify error codes are forwarded correctly for all HTTP methods."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=400,
                msg="Bad Request",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error": "Invalid request"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.open(
            "/_proxy/api/v1/users",
            method=method,
            data=b'{"invalid": "data"}',
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400
        assert response.get_json() == {"error": "Invalid request"}


class TestProxyMalformedResponses:
    """Test handling of malformed backend responses."""

    @pytest.mark.integration
    def test_proxy_handles_non_utf8_response(self, monkeypatch):
        """Verify non-UTF8 response bodies are handled."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        # Invalid UTF-8 sequence
        invalid_body = b'\x80\x81\x82\x83'

        def fake_urlopen(request, timeout=0):
            raise HTTPError(
                url=request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs={"Content-Type": "application/octet-stream"},
                fp=BytesIO(invalid_body),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        # Should still return the body as-is (bytes)
        assert response.status_code == 500
        assert response.data == invalid_body

    @pytest.mark.integration
    def test_proxy_handles_large_response(self, monkeypatch):
        """Verify large response bodies are handled."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        # 1MB response
        large_body = b'{"data": "' + (b'x' * (1024 * 1024 - 20)) + b'"}'

        def fake_urlopen(request, timeout=0):
            return DummyUpstreamResponse(large_body, status=200)

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/large-data")

        assert response.status_code == 200
        assert len(response.data) > 1024 * 1000  # At least 1MB


class TestProxyNetworkErrorVariations:
    """Test various network error scenarios."""

    @pytest.mark.integration
    def test_proxy_generic_urlerror_returns_502(self, monkeypatch):
        """Verify generic URLError is mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("Unknown network error")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        assert response.status_code == 502

    @pytest.mark.integration
    def test_proxy_ssl_error_returns_502(self, monkeypatch):
        """Verify SSL errors are mapped to 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout=0):
            raise URLError("SSL: CERTIFICATE_VERIFY_FAILED")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/test")

        assert response.status_code == 502
