"""Technical backend information surface (/backend/*) and root redirect behavior."""

import pytest

pytestmark = pytest.mark.routes_core


_INFO_PATHS = (
    "/backend",
    "/backend/",
    "/backend/api",
    "/backend/api-explorer",
    "/backend/project-management",
    "/backend/data-model",
    "/backend/algorithms",
    "/backend/runtime",
    "/backend/engine",
    "/backend/ai",
    "/backend/observability",
    "/backend/mcp",
    "/backend/security-features",
    "/backend/auth",
    "/backend/ops",
)


@pytest.mark.parametrize("path", _INFO_PATHS)
def test_backend_info_pages_return_200(client, path):
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200
    assert b"Better Tomorrow" in response.data
    assert b"backend service" in response.data


def test_backend_info_home_has_navigation(client, monkeypatch):
    monkeypatch.delenv("LANGFUSE_UI_URL", raising=False)
    monkeypatch.delenv("LANGFUSE_MCP_BASE_URL", raising=False)
    monkeypatch.delenv("NEXTAUTH_URL", raising=False)
    monkeypatch.setenv("LANGFUSE_WEB_PORT", "3000")
    r = client.get("/backend/")
    assert r.status_code == 200
    assert b"<title>Better Tomorrow Backend" in r.data
    assert b"World of Shadows</title>" not in r.data
    assert b"/backend/api" in r.data
    assert b"/backend/project-management" in r.data
    assert b"/backend/data-model" in r.data
    assert b"/backend/algorithms" in r.data
    assert b"/backend/runtime" in r.data
    assert b"/backend/engine" in r.data
    assert b"/backend/observability" in r.data
    assert b"/backend/mcp" in r.data
    assert b"/backend/security-features" in r.data
    assert b"/manage/mcp-operations" in r.data
    assert b"http://localhost:3000" in r.data
    assert b"Langfuse" in r.data
    assert b"/static/favicon.ico" in r.data


def test_backend_favicon_is_served(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.mimetype == "image/vnd.microsoft.icon"
    assert r.data.startswith(b"\x00\x00\x01\x00")


def test_backend_info_css_darkens_main_canvas(client):
    styles = client.get("/backend/static/styles.css")
    manage = client.get("/backend/static/manage.css")
    info = client.get("/backend/static/backend-info.css")

    assert styles.status_code == 200
    assert manage.status_code == 200
    assert info.status_code == 200
    assert b"--shared-view-background" in styles.data
    assert b"background: var(--shared-view-background)" in manage.data
    assert b"body.manage-body .manage-shell-main" in info.data
    assert b"rgba(5, 7, 12, 0.58)" in info.data


def test_root_redirects_to_backend_info(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers.get("Location", "")
    assert loc.endswith("/backend/") or loc.endswith("/backend")


def test_create_app_registers_info_blueprint(app):
    assert "info.backend_home" in app.view_functions
    assert "info.api_overview" in app.view_functions
    assert "info.api_explorer_catalog" in app.view_functions
    assert "info.project_management" in app.view_functions
    assert "info.data_model" in app.view_functions
    assert "info.runtime_algorithms" in app.view_functions
    assert "info.mcp_integration" in app.view_functions
    assert "info.security_features" in app.view_functions
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert any(str(r).startswith("/backend") for r in rules)


def test_project_management_page_explains_runtime_store_and_bootstrap(client):
    r = client.get("/backend/project-management")
    assert r.status_code == 200
    assert b"ADR Runtime Store" in r.data
    assert b"docker-up.py" in r.data
    assert b"langfuse-redis" in r.data


def test_security_features_page_explains_local_evidence_boundary(client):
    r = client.get("/backend/security-features")
    assert r.status_code == 200
    assert b"Security Features" in r.data
    assert b"local_only" in r.data
    assert b"local_only: true" in r.data
    assert b"LANGFUSE_SECRET_KEY" in r.data
    assert "Secret-Management-Grenze".encode() in r.data
    assert "Local-Dev bleibt".encode() in r.data
    assert b"docker-up.py init-env" in r.data
    assert b"docker-up.py up" in r.data
    assert b"dedizierter Secret-Store" in r.data
    assert "Docker-Up darf nicht brechen".encode() in r.data
    assert b"Cloud-Login" in r.data
    assert b"Production Redis Hardening" in r.data
    assert b"docker-up.py init-production-redis" in r.data
    assert b"docker-up.py validate-production-redis" in r.data
    assert b"docker-up.py --production-redis up" in r.data
    assert b"docker-compose.redis-production.yml" in r.data
    assert b"APP_REDIS_URL" in r.data
    assert b"LANGFUSE_REDIS_CONNECTION_STRING" in r.data
    assert b"LANGFUSE_REDIS_USERNAME" in r.data
    assert b".docker/redis-production/" in r.data
    assert b"app-users.acl" in r.data
    assert b"langfuse-users.acl" in r.data
    assert "At-rest-Verschlüsselung".encode() in r.data
    assert "vollständige at-rest Verschlüsselung".encode() in r.data
    assert b"ADR-0047" in r.data
    assert b"ADR-0051" in r.data
    assert b"docs/security/AT_REST_ENCRYPTION.md" in r.data
    assert b"docker-compose.yml" in r.data
    assert b"keine weitere funktionale" in r.data
    assert b"DATABASE_URI" in r.data
    assert b"storage_encryption_evidence" in r.data
    assert b"storage_layer_encryption" in r.data
    assert b"/manage/security-governance" in r.data
    assert b"backend/instance/wos.db" in r.data
    assert b"redis-data:/data" in r.data
    assert b"docker-compose.redis-production.yml" in r.data
    assert b"RUN_STORE_BACKEND=json" in r.data
    assert b"RUN_STORE_BACKEND=json_aead" in r.data
    assert b"RUN_STORE_BACKEND=sqlalchemy" in r.data
    assert b"WORLD_ENGINE_JSON_AEAD_KEY" in r.data
    assert b"langfuse-postgres-data" in r.data
    assert b"Encrypted Backup Output" in r.data
    assert b"Provider- &amp; Evaluator-Governance" in r.data
    assert b"ADR-0049" in r.data
    assert b"docs/security/PROVIDER_CREDENTIAL_GOVERNANCE.md" in r.data
    assert b"AI Runtime Governance" in r.data
    assert b"OPENAI_API_KEY=" in r.data
    assert b"OPENROUTER_API_KEY=" in r.data
    assert b"ANTHROPIC_API_KEY=" in r.data
    assert b"HF_TOKEN=" in r.data
    assert b"Governed Provider Routing" in r.data
    assert b"OpenAIChatAdapter" in r.data
    assert b"governed_provider_adapter_service.py" in r.data
    assert b"get_provider_credential_for_runtime" in r.data
    assert b"provider_credential_source" in r.data
    assert b"backend_governance_or_secret_manager" in r.data
    assert b"evidence_scope=local_langfuse" in r.data
    assert b"proof_level=local_only" in r.data
    assert b"live_or_staging_evidence=false" in r.data
    assert b"tools/mcp_server/handlers/langfuse_verify/" in r.data
    assert "Zentrales Limit-Inventar".encode() in r.data
    assert "Explizite Route-Limits".encode() in r.data
    assert b"/api/v1/auth/login" in r.data
    assert b"route_decorator" in r.data
    assert b"30 per minute" in r.data
    assert b"mcp_json_rpc_dispatch" in r.data or b"MCP-Dispatch-Limiter" in r.data
    assert b"Production-Tuning &amp; Telemetry" in r.data
    assert b"inventory_only" in r.data
    assert b"rate_limit_hits_total" in r.data
    assert b"rate_limit_quota_utilization_ratio" in r.data
    assert b"edge_throttle_events_total" in r.data
    assert b"Shadow-Tuning" in r.data
    assert b"hashed limiter key" in r.data


def test_security_features_page_explains_csrf_matrix_regression_gate(client):
    r = client.get("/backend/security-features")

    assert r.status_code == 200
    assert "CSRF-Matrix &amp; Browser-Mutation-Grenze".encode() in r.data
    assert "Admin- und Frontend-Session-Cookies nutzen SameSite".encode() in r.data
    assert b"Authorization: Bearer ..." in r.data
    assert b"same-origin Proxies" in r.data
    assert b"docs/security/csrf-matrix.md" in r.data
    assert b"ADR-0050" in r.data
    assert "Backend-, Frontend-, Frontend-API-Client- und Proxy-Regressionstests".encode() in r.data
    assert b"Backend Web Routes" in r.data
    assert b"Frontend Same-Origin API Proxy" in r.data
    assert b"/api/v1/&lt;path&gt;" in r.data
    assert b"administration-tool/tests/test_proxy_contract.py" in r.data
    assert b"frontend/tests/test_api_client.py" in r.data
    assert b"frontend/tests/test_csrf_matrix.py" in r.data


def test_api_explorer_catalog_describes_implemented_routes(client):
    r = client.get("/backend/api-explorer/catalog.json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["stats"]["endpoints"] >= 100
    assert data["stats"]["implemented"] == data["stats"]["endpoints"]

    health = next(
        endpoint
        for endpoint in data["endpoints"]
        if endpoint["method"] == "GET" and endpoint["path"] == "/api/v1/health"
    )
    assert health["tag"] == "System"
    assert health["auth_kind"] == "public"
    assert "handler" in health
    assert "curl -X GET" in health["curl"]
    assert health["rate_limit"]["limit"] == "100 per minute"
    assert health["rate_limit"]["source"] == "route_decorator"

    login = next(
        endpoint
        for endpoint in data["endpoints"]
        if endpoint["method"] == "POST" and endpoint["path"] == "/api/v1/auth/login"
    )
    assert login["rate_limit"]["limit"] == "20 per minute"
    assert login["rate_limit"]["source"] == "route_decorator"

    forgot_password = next(
        endpoint
        for endpoint in data["endpoints"]
        if endpoint["method"] == "POST" and endpoint["path"] == "/api/v1/auth/forgot-password"
    )
    assert forgot_password["rate_limit"]["limit"] == "5 per hour"
    assert forgot_password["rate_limit"]["key"] == "custom route key_func"


def test_backend_info_pages_render_limit_inventory(client):
    api = client.get("/backend/api")
    assert api.status_code == 200
    assert "Limit-Inventar".encode() in api.data
    assert b"/api/v1/auth/login" in api.data

    auth = client.get("/backend/auth")
    assert auth.status_code == 200
    assert "Auth-Limit-Inventar".encode() in auth.data
    assert b"20 per minute" in auth.data
    assert b"/api/v1/auth/forgot-password" in auth.data

    mcp = client.get("/backend/mcp")
    assert mcp.status_code == 200
    assert "Tool-Limit-Inventar".encode() in mcp.data
    assert b"30 per minute" in mcp.data
    assert b"wos.system.health" in mcp.data


def test_api_explorer_page_has_search_shell(client):
    r = client.get("/backend/api-explorer")
    assert r.status_code == 200
    assert b'id="api-explorer-app"' in r.data
    assert b'data-catalog-url="/backend/api-explorer/catalog.json"' in r.data
    assert b"tag:Auth" in r.data


def test_old_web_routes_removed_not_html_shell(client, app):
    """Old web paths must not become canonical HTML hosts."""
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    for path in ("/login", "/dashboard", "/play", "/game-menu"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 404
    app.config["FRONTEND_URL"] = None
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 404


def test_api_health_unaffected_next_to_backend_namespace(client):
    """Backend info URLs must not shadow /api/v1/* JSON routes."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.is_json
    assert r.get_json().get("status") == "ok"
