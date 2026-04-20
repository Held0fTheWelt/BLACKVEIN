from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError, URLError

from conftest import load_frontend_module


class DummyUpstreamResponse:
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



def test_proxy_preflight_returns_204(frontend_module):
    client = frontend_module.app.test_client()
    response = client.open("/_proxy/api/v1/news", method="OPTIONS")
    assert response.status_code == 204
    assert response.data == b""



def test_proxy_returns_500_when_backend_url_is_missing(frontend_module):
    frontend_module.app.config["BACKEND_API_URL"] = ""
    client = frontend_module.app.test_client()

    response = client.get("/_proxy/api/v1/news")

    assert response.status_code == 500
    assert b"Backend API URL not configured" in response.data



def test_proxy_forwards_query_headers_and_body(monkeypatch):
    module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")
    recorded: dict[str, object] = {}

    def fake_urlopen(request, timeout: int = 0):
        recorded["url"] = request.full_url
        recorded["method"] = request.get_method()
        recorded["headers"] = dict(request.header_items())
        recorded["body"] = request.data
        recorded["timeout"] = timeout
        return DummyUpstreamResponse(b'{"ok": true}', status=201)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = module.app.test_client()

    response = client.post(
        "/_proxy/api/v1/news?draft=true",
        data=b'{"title":"Hello"}',
        headers={
            "Authorization": "Bearer abc",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    assert response.status_code == 201
    assert response.get_json() == {"ok": True}
    assert recorded["url"] == "https://api.example.test/api/v1/news?draft=true"
    assert recorded["method"] == "POST"
    assert recorded["body"] == b'{"title":"Hello"}'
    assert recorded["headers"]["Authorization"] == "Bearer abc"
    assert recorded["headers"]["Content-type"] == "application/json"
    assert recorded["headers"]["Accept"] == "application/json"
    assert recorded["timeout"] == 20



def test_proxy_surfaces_http_errors(monkeypatch):
    module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

    def fake_urlopen(request, timeout: int = 0):
        raise HTTPError(
            url=request.full_url,
            code=418,
            msg="teapot",
            hdrs={"Content-Type": "application/json"},
            fp=BytesIO(b'{"error":"teapot"}'),
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = module.app.test_client()

    response = client.get("/_proxy/api/v1/news")

    assert response.status_code == 418
    assert response.get_json() == {"error": "teapot"}
    assert response.headers["Content-Type"].startswith("application/json")



def test_proxy_turns_network_errors_into_502(monkeypatch):
    module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

    def fake_urlopen(request, timeout: int = 0):
        raise URLError("offline")

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    client = module.app.test_client()

    response = client.get("/_proxy/api/v1/news")

    assert response.status_code == 502
    assert response.data == b"Upstream network error"
