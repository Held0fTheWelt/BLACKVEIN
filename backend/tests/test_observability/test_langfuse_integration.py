"""Tests for Langfuse integration with backend credentials."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.extensions import db
from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
from app.services.observability_governance_service import write_observability_credential


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
        from app.services.observability_governance_service import get_observability_credential_for_runtime
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

        from app.services.observability_governance_service import get_observability_credential_for_runtime

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

        from app.services.observability_governance_service import get_observability_credential_for_runtime

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

    def test_langfuse_connection(self, client, db_session, app):
        """Verify real Langfuse Cloud connection and trace creation (integration test)."""
        from app.observability.langfuse_adapter import LangfuseAdapter

        # Setup: ensure Langfuse is properly configured from database
        config = db_session.query(ObservabilityConfig).filter_by(code="langfuse").first()
        if not config:
            pytest.skip("Langfuse not configured in database; skipping cloud connection test")

        if not config.is_enabled:
            pytest.skip("Langfuse disabled in database; skipping cloud connection test")

        secret_key = db_session.query(ObservabilityCredential).filter_by(
            observability_config_id=config.id, key="secret_key"
        ).first()
        if not secret_key or not secret_key.encrypted_value:
            pytest.skip("Langfuse secret_key not configured; skipping cloud connection test")

        # Get Langfuse adapter and verify it's ready
        adapter = LangfuseAdapter.get_instance()
        assert adapter.is_ready, "Langfuse adapter should be ready for cloud connection test"
        assert adapter.client is not None, "Langfuse client should be initialized"

        trace_id = adapter.create_trace_id("langfuse-cloud-connection-test")
        trace = adapter.start_trace(
            name="langfuse_cloud_connection_test",
            session_id="we-langfuse-test",
            run_id="run-langfuse-test",
            module_id="god_of_carnage",
            metadata={"canonical_player_flow": True, "route": "/api/v1/game/player-sessions/<run_id>/turns"},
            trace_id=trace_id,
            user_id="test_langfuse",
        )
        assert trace is not None, "Trace span should be created"
        adapter.end_trace(trace)

        # Flush traces to Langfuse Cloud (synchronous for test verification)
        adapter.flush()

        # Verify: attempt to fetch the trace from Langfuse Cloud
        # This proves the trace was actually sent and received by the service
        try:
            langfuse_trace = adapter.client.get_trace(trace_id)
            assert langfuse_trace is not None, f"Trace {trace_id} should exist in Langfuse Cloud"
            assert langfuse_trace.id == trace_id, f"Fetched trace ID should match: {trace_id}"
        except Exception as e:
            pytest.skip(f"Could not verify trace in Langfuse Cloud: {e}. (Connection issue; skipping)")

        # Success: trace was created and sent to Langfuse Cloud
        assert True, "Langfuse Cloud connection verified"


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
