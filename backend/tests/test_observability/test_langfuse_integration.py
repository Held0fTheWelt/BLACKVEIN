"""Tests for Langfuse integration with backend credentials."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from app.extensions import db
from app.models.backend.governance_core import ObservabilityConfig
from app.services.governance.observability_governance_service import (
    test_observability_connection as run_observability_connection_test,
    write_observability_credential,
)


class TestLangfuseCredentialsEndpoint:
    """Tests for the internal Langfuse credentials endpoint that world-engine uses."""

    def test_internal_credentials_endpoint_requires_token(self, client):
        """Credentials endpoint requires X-Internal-Config-Token header."""
        resp = client.get("/api/v1/internal/observability/langfuse-credentials")
        assert resp.status_code == 403
        resp_data = resp.get_json()
        assert resp_data["ok"] is False

    def test_internal_credentials_endpoint_with_invalid_token(self, client):
        """Credentials endpoint rejects invalid tokens."""
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"X-Internal-Config-Token": "wrong_token"}
        )
        assert resp.status_code == 403
        resp_data = resp.get_json()
        assert resp_data["ok"] is False

    def test_internal_credentials_endpoint_returns_disabled_when_not_configured(self, client, app):
        """When Langfuse is not enabled, endpoint returns disabled config."""
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"X-Internal-Config-Token": token}
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        assert resp_data["data"]["enabled"] is False
        assert resp_data["data"]["public_key"] is None
        assert resp_data["data"]["secret_key"] is None

    def test_internal_credentials_endpoint_returns_credentials_when_enabled(self, client, app, db_session):
        """When Langfuse is enabled and configured, endpoint returns credentials."""
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")

        # Create config and credentials
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="https://cloud.langfuse.com",
            enabled_observation_trees=["minimal", "graph_path", "model_io", "retrieval"],
        )
        db.session.add(config)
        db.session.commit()

        write_observability_credential(
            public_key="pk_test_1234567890",
            secret_key="sk_test_abcdefghij",
            actor="test_system",
        )

        # Fetch credentials
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"X-Internal-Config-Token": token}
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        data = resp_data["data"]

        assert data["enabled"] is True
        assert data["public_key"] == "pk_test_1234567890"
        assert data["secret_key"] == "sk_test_abcdefghij"
        assert data["base_url"] == "https://cloud.langfuse.com"
        assert data["environment"] == "development"
        assert data["release"] == "unknown"
        assert data["sample_rate"] == 1.0
        assert data["capture_prompts"] is True
        assert data["capture_outputs"] is True
        assert data["capture_retrieval"] is False
        assert data["redaction_mode"] == "strict"
        assert data["enabled_observation_trees"] == ["minimal", "graph_path", "model_io", "retrieval"]

    def test_internal_credentials_maps_localhost_to_docker_runtime_url(
        self,
        client,
        app,
        db_session,
        monkeypatch,
    ):
        """Runtime callers inside Docker receive service DNS, not host-local browser URLs."""
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")
        monkeypatch.setenv("WOS_BACKEND_RUNNING_IN_DOCKER", "1")
        monkeypatch.setenv("LANGFUSE_BASE_URL", "http://langfuse-web:3000")

        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="http://localhost:3000",
        )
        db.session.add(config)
        db.session.commit()

        write_observability_credential(
            public_key="pk_local_runtime",
            secret_key="sk_local_runtime",
            actor="test_system",
        )

        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"X-Internal-Config-Token": token},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["base_url"] == "http://langfuse-web:3000"
        assert data["configured_base_url"] == "http://localhost:3000"
        assert data["base_url_source"] == "docker_service_env_for_localhost"

    def test_internal_credentials_endpoint_returns_empty_when_enabled_but_no_secret(self, client, app, db_session):
        """When enabled but no secret key, credentials are marked as not ready."""
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")

        # Create config without credentials
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
        )
        db.session.add(config)
        db.session.commit()

        # Fetch credentials
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"X-Internal-Config-Token": token}
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True

        # Should return disabled=True because there's no secret_key
        assert resp_data["data"]["enabled"] is False


class TestLangfuseCredentialsEndpointJwtAuth:
    """Credentials endpoint: admin JWT bearer path is diagnostics-only."""

    def test_admin_jwt_cannot_fetch_raw_secret_when_enabled(self, client, admin_jwt, db_session):
        """Admin JWT bearer token must not expose raw Langfuse secret material."""
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="https://cloud.langfuse.com",
        )
        db.session.add(config)
        db.session.commit()

        write_observability_credential(
            public_key="pk_mcp_test",
            secret_key="sk_mcp_test",
            actor="test_mcp",
        )

        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["enabled"] is False
        assert data["public_key"] == "pk_mcp_test"
        assert data["secret_key"] is None
        assert data["secret_key_configured"] is True
        assert data["secret_key_redacted"] is True
        assert data["credential_fingerprint"]

    def test_non_admin_jwt_is_rejected(self, client, auth_headers):
        """Regular user JWT is rejected — endpoint requires admin role."""
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.get_json()["ok"] is False

    def test_no_auth_at_all_is_rejected(self, client):
        """No auth header at all returns 403."""
        resp = client.get("/api/v1/internal/observability/langfuse-credentials")
        assert resp.status_code == 403
        assert resp.get_json()["ok"] is False

    def test_admin_jwt_returns_disabled_when_not_configured(self, client, admin_jwt):
        """Admin JWT path respects enabled=False same as token path."""
        resp = client.get(
            "/api/v1/internal/observability/langfuse-credentials",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["enabled"] is False
        assert data["public_key"] is None
        assert data["secret_key"] is None


class TestLangfuseInitializationEndpoint:
    """Tests for the bootstrap initialization endpoint."""

    def test_internal_initialize_endpoint_creates_config_and_credentials(self, client, db_session):
        """Bootstrap endpoint creates config and stores credentials."""
        payload = {
            "enabled": True,
            "base_url": "https://cloud.langfuse.com",
            "environment": "development",
            "release": "1.0.0",
            "sample_rate": 1.0,
            "capture_prompts": True,
            "capture_outputs": True,
            "capture_retrieval": False,
            "redaction_mode": "strict",
            "enabled_observation_trees": ["minimal", "model_io", "scores"],
            "public_key": "pk_bootstrap_1234",
            "secret_key": "sk_bootstrap_5678",
        }

        resp = client.post(
            "/api/v1/internal/observability/initialize",
            json=payload,
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        assert resp_data["data"]["initialized"] is True
        assert resp_data["data"]["is_enabled"] is True

        # Verify credentials were stored
        from app.services.governance.observability_governance_service import get_observability_credential_for_runtime
        public_key = get_observability_credential_for_runtime("public_key")
        secret_key = get_observability_credential_for_runtime("secret_key")

        assert public_key == "pk_bootstrap_1234"
        assert secret_key == "sk_bootstrap_5678"
        config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
        assert config.enabled_observation_trees == ["minimal", "model_io", "scores"]

    def test_internal_initialize_endpoint_creates_config_with_minimal_payload(self, client, db_session):
        """Bootstrap endpoint works with minimal payload."""
        payload = {
            "enabled": False,
        }

        resp = client.post(
            "/api/v1/internal/observability/initialize",
            json=payload,
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        assert resp_data["data"]["initialized"] is True

    def test_internal_initialize_endpoint_preserves_existing_credentials_by_default(self, client, db_session):
        """Bootstrap imports must not overwrite admin-managed Langfuse settings on restart."""
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="http://langfuse-web:3000",
            environment="local",
            release="admin-managed",
        )
        db.session.add(config)
        db.session.commit()
        write_observability_credential(
            public_key="pk_existing",
            secret_key="sk_existing",
            actor="test_admin",
        )

        resp = client.post(
            "/api/v1/internal/observability/initialize",
            json={
                "enabled": True,
                "base_url": "https://cloud.langfuse.com",
                "environment": "production",
                "release": "env-import",
                "public_key": "pk_env",
                "secret_key": "sk_env",
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["initialized"] is False
        assert data["skipped_existing"] is True

        from app.services.governance.observability_governance_service import get_observability_credential_for_runtime

        assert get_observability_credential_for_runtime("public_key") == "pk_existing"
        assert get_observability_credential_for_runtime("secret_key") == "sk_existing"
        saved = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
        assert saved.base_url == "http://langfuse-web:3000"
        assert saved.environment == "local"
        assert saved.release == "admin-managed"

    def test_internal_initialize_endpoint_can_overwrite_when_explicit(self, client, db_session):
        """Explicit overwrite keeps recovery/env re-import available."""
        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="http://langfuse-web:3000",
        )
        db.session.add(config)
        db.session.commit()
        write_observability_credential(
            public_key="pk_existing",
            secret_key="sk_existing",
            actor="test_admin",
        )

        resp = client.post(
            "/api/v1/internal/observability/initialize",
            json={
                "enabled": True,
                "base_url": "http://langfuse-web:3000",
                "environment": "local",
                "release": "env-import",
                "public_key": "pk_env",
                "secret_key": "sk_env",
                "overwrite_existing": True,
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["initialized"] is True
        assert "skipped_existing" not in data

        from app.services.governance.observability_governance_service import get_observability_credential_for_runtime

        assert get_observability_credential_for_runtime("public_key") == "pk_env"
        assert get_observability_credential_for_runtime("secret_key") == "sk_env"
        saved = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
        assert saved.release == "env-import"


class TestLangfuseAdapterIntegration:
    """Tests for the backend Langfuse adapter."""

    def test_langfuse_adapter_loads_from_database(self, db_session):
        """LangfuseAdapter loads governed runtime settings from database."""
        from app.observability.langfuse_adapter import LangfuseConfig, LangfuseAdapter

        config_row = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="https://cloud.langfuse.com",
        )
        db.session.add(config_row)
        db.session.commit()
        write_observability_credential(
            public_key="pk_test_database",
            secret_key="sk_test_database",
            actor="test_system",
        )

        LangfuseAdapter.reset_instance()
        config = LangfuseConfig()
        assert config.enabled is True
        assert config.public_key == "pk_test_database"
        assert config.secret_key == "sk_test_database"
        assert config.is_valid is True
        assert config.enabled_observation_trees == ["minimal"]

    def test_langfuse_adapter_methods_exist(self):
        """LangfuseAdapter has all required methods for tracing."""
        from app.observability.langfuse_adapter import LangfuseAdapter

        adapter = LangfuseAdapter.get_instance()

        # Verify methods exist
        assert hasattr(adapter, "start_trace")
        assert hasattr(adapter, "end_trace")
        assert hasattr(adapter, "add_span")
        assert hasattr(adapter, "record_generation")
        assert hasattr(adapter, "record_retrieval")
        assert hasattr(adapter, "record_validation")
        assert hasattr(adapter, "create_child_span")
        assert hasattr(adapter, "set_active_span")
        assert hasattr(adapter, "get_active_span")
        assert hasattr(adapter, "flush")
        assert hasattr(adapter, "shutdown")

        # Verify is_enabled works (in test environment with .env, it may be enabled)
        assert isinstance(adapter.is_enabled(), bool)

    def test_langfuse_adapter_singleton_pattern(self):
        """LangfuseAdapter uses singleton pattern correctly."""
        from app.observability.langfuse_adapter import LangfuseAdapter

        adapter1 = LangfuseAdapter.get_instance()
        adapter2 = LangfuseAdapter.get_instance()

        assert adapter1 is adapter2

    def test_langfuse_adapter_reset_for_testing(self):
        """LangfuseAdapter can be reset between tests."""
        from app.observability.langfuse_adapter import LangfuseAdapter

        adapter1 = LangfuseAdapter.get_instance()
        LangfuseAdapter.reset_instance()
        adapter2 = LangfuseAdapter.get_instance()

        # Should be different instances after reset
        assert adapter1 is not adapter2

    def test_langfuse_connection(self, db_session, app, monkeypatch):
        """Connection test uses governed backend Langfuse data, not direct Cloud/env fields."""
        from app.services.governance.observability_governance_service import get_observability_config

        config = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            base_url="http://langfuse-web:3000",
            environment="test",
            release="pytest",
        )
        db.session.add(config)
        db.session.commit()
        write_observability_credential(
            public_key="pk-lf-backend-test",
            secret_key="sk-lf-backend-test",
            actor="pytest",
        )

        seen: dict[str, object] = {}

        class FakeSpan:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def update(self, **kwargs):
                seen["span_update"] = kwargs

        class FakeTraceApi:
            def get(self, trace_id):
                seen["fetched_trace_id"] = trace_id
                return SimpleNamespace(id=trace_id)

        class FakeLangfuse:
            def __init__(self, *, public_key, secret_key, base_url, environment, release, sample_rate):
                seen["client_init"] = {
                    "public_key": public_key,
                    "secret_key": secret_key,
                    "base_url": base_url,
                    "environment": environment,
                    "release": release,
                    "sample_rate": sample_rate,
                }
                self.api = SimpleNamespace(trace=FakeTraceApi())
                self._trace_id = "trace-backend-observability"

            def start_as_current_observation(self, *, as_type, name, metadata):
                seen["observation"] = {
                    "as_type": as_type,
                    "name": name,
                    "metadata": metadata,
                }
                return FakeSpan()

            def get_current_trace_id(self):
                return self._trace_id

            def flush(self):
                seen["flush_count"] = int(seen.get("flush_count", 0)) + 1

            def get_trace_url(self, *, trace_id):
                return f"http://langfuse-web:3000/project/traces/{trace_id}"

        def fake_resolve_base_url(*, public_key, secret_key, configured_base_url):
            seen["resolved_credentials"] = {
                "public_key": public_key,
                "secret_key": secret_key,
                "configured_base_url": configured_base_url,
            }
            return configured_base_url, None, ["backend-test-project"]

        monkeypatch.setitem(sys.modules, "langfuse", SimpleNamespace(Langfuse=FakeLangfuse))
        monkeypatch.setattr(
            "app.services.governance.observability_governance_service._resolve_langfuse_base_url_for_credentials",
            fake_resolve_base_url,
        )

        with app.app_context():
            result = run_observability_connection_test("pytest")

        assert result["ok"] is True
        assert result["health_status"] == "connected"
        assert result["credentials_source"] == "backend_observability_credentials"
        assert result["base_url"] == "http://langfuse-web:3000"
        assert result["trace_id"] == "trace-backend-observability"
        assert result["verified_trace_id"] == "trace-backend-observability"
        assert seen["resolved_credentials"] == {
            "public_key": "pk-lf-backend-test",
            "secret_key": "sk-lf-backend-test",
            "configured_base_url": "http://langfuse-web:3000",
        }
        assert seen["client_init"] == {
            "public_key": "pk-lf-backend-test",
            "secret_key": "sk-lf-backend-test",
            "base_url": "http://langfuse-web:3000",
            "environment": "test",
            "release": "pytest",
            "sample_rate": 1.0,
        }

        status = get_observability_config()
        assert status["health_status"] == "connected"
        assert status["last_tested_at"] is not None


class TestLangfuseVerifyToolEndpoint:
    """HTTP parity with MCP Langfuse verify tools (same Python handlers)."""

    def test_verify_tool_requires_auth(self, client):
        resp = client.post("/api/v1/internal/observability/langfuse-verify-tool", json={})
        assert resp.status_code == 403
        assert resp.get_json()["ok"] is False

    def test_verify_tool_rejects_unknown_tool(self, client, app):
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")
        resp = client.post(
            "/api/v1/internal/observability/langfuse-verify-tool",
            json={"tool": "not_a_real_tool", "arguments": {}},
            headers={"X-Internal-Config-Token": token},
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["ok"] is False
        assert "allowed" in body["error"]["details"]

    def test_verify_tool_dispatches_handler(self, client, app):
        token = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "")
        fake_handlers = {
            "fetch_langfuse_trace_scores": lambda a: {"ok": True, "echo_arguments": a},
        }
        with patch(
            "app.api.v1.observability_governance_routes._langfuse_verify_handlers",
            return_value=fake_handlers,
        ):
            resp = client.post(
                "/api/v1/internal/observability/langfuse-verify-tool",
                json={
                    "tool": "fetch_langfuse_trace_scores",
                    "arguments": {"trace_id": "trace-abc"},
                },
                headers={"X-Internal-Config-Token": token},
            )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["data"]["tool"] == "fetch_langfuse_trace_scores"
        assert body["data"]["result"]["echo_arguments"]["trace_id"] == "trace-abc"
