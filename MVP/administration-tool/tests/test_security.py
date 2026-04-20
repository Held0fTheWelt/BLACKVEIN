from __future__ import annotations

from conftest import load_frontend_module



def test_security_headers_are_added_to_html_responses(frontend_module):
    client = frontend_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp



def test_csp_connect_src_includes_backend_origin(monkeypatch):
    module = load_frontend_module(monkeypatch, backend_url="https://backend.example.test/api-root")
    client = module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "connect-src 'self' https: https://backend.example.test" in csp



def test_explicit_secret_key_is_used(monkeypatch):
    module = load_frontend_module(monkeypatch, secret="frontend-secret")
    assert module.app.secret_key == "frontend-secret"



def test_secret_key_is_generated_when_missing(monkeypatch):
    module = load_frontend_module(monkeypatch, secret=None)
    assert isinstance(module.app.secret_key, str)
    assert len(module.app.secret_key) >= 20
