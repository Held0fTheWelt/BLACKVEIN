"""Coverage for app factory error handlers and security headers."""

def test_api_unknown_route_returns_json_404(client):
    r = client.get("/api/v1/nonexistent-endpoint-xyz-12345")
    assert r.status_code == 404
    assert r.is_json
    assert "error" in r.get_json()


def test_csp_connect_src_includes_play_service_url(client, app):
    app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://playsvc.example.org/v1"
    r = client.get("/api/v1/site/settings")
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy") or ""
    assert "https://playsvc.example.org" in csp
    assert "wss://playsvc.example.org" in csp


def test_error_handler_429_returns_json(client, app):
    from werkzeug.exceptions import TooManyRequests

    def _raise_429():
        raise TooManyRequests()

    app.add_url_rule("/api/v1/__coverage_429", "cov_429", _raise_429, methods=["GET"])
    r = client.get("/api/v1/__coverage_429")
    assert r.status_code == 429
    assert r.is_json
    assert "too many requests" in r.get_json().get("error", "").lower()


def test_error_handler_500_api_returns_json(client, app):
    def _raise_500():
        raise RuntimeError("coverage")

    app.add_url_rule("/api/v1/__coverage_500", "cov_500", _raise_500, methods=["GET"])
    prev_testing = app.testing
    app.testing = False
    try:
        r = client.get("/api/v1/__coverage_500")
    finally:
        app.testing = prev_testing
    assert r.status_code == 500
    assert r.is_json
    assert "error" in r.get_json()
