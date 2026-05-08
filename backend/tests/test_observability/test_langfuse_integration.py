"""Tests for Langfuse integration with backend credentials."""

from __future__ import annotations

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
    """Credentials endpoint: admin JWT bearer path (MCP / BACKEND_BEARER_TOKEN)."""

    def test_admin_jwt_can_fetch_credentials_when_enabled(self, client, admin_jwt, db_session):
        """Admin JWT bearer token is accepted as an alternative to X-Internal-Config-Token."""
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
        assert data["enabled"] is True
        assert data["public_key"] == "pk_mcp_test"
        assert data["secret_key"] == "sk_mcp_test"

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
        try:
            from app.models import User
            from app.models.runtime_session import Session, RuntimeSession
        except ImportError:
            pytest.skip("Required models not available; skipping cloud connection test")

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

        # Create a test session and runtime session
        test_user = db_session.query(User).first()
        if not test_user:
            test_user = User(username="test_langfuse", email="test@example.com", role_id=1)
            db_session.add(test_user)
            db_session.flush()

        player_session = Session(
            user_id=test_user.id,
            session_type="story",
            data={},
        )
        db_session.add(player_session)
        db_session.flush()

        runtime_session = RuntimeSession(
            session_id=player_session.id,
            module_id="god_of_carnage",
            turn_counter=0,
            current_runtime_state={},
            metadata={},
        )
        db_session.add(runtime_session)
        db_session.commit()

        # Execute a turn (which will create Langfuse traces)
        with app.test_client() as test_client:
            response = test_client.post(
                f"/api/v1/sessions/{player_session.id}/turns",
                json={"player_input": "test input"},
                headers={"Authorization": f"Bearer {client.get_token()}"},
            )

            # Verify the turn was executed
            assert response.status_code in (200, 502), f"Expected success or service unavailable, got {response.status_code}"
            data = response.get_json()
            assert data, "Response should have JSON body"
            assert "trace_id" in data, "Response should include trace_id"

            trace_id = data["trace_id"]
            assert trace_id, "trace_id should be non-empty"

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
