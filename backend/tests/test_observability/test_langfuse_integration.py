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

    def test_langfuse_adapter_loads_from_environment(self):
        """LangfuseAdapter can be initialized from environment variables."""
        import os
        from app.observability.langfuse_adapter import LangfuseConfig, LangfuseAdapter

        # Save original values
        orig_enabled = os.environ.get("LANGFUSE_ENABLED")
        orig_public = os.environ.get("LANGFUSE_PUBLIC_KEY")
        orig_secret = os.environ.get("LANGFUSE_SECRET_KEY")

        try:
            # Set env vars
            os.environ["LANGFUSE_ENABLED"] = "false"  # Don't try to connect
            os.environ["LANGFUSE_PUBLIC_KEY"] = ""
            os.environ["LANGFUSE_SECRET_KEY"] = ""

            config = LangfuseConfig()
            assert config.enabled is False
            assert config.is_valid is True  # Valid because not enabled
            assert config.is_ready is False  # Not ready because not enabled

        finally:
            # Restore original values
            if orig_enabled is not None:
                os.environ["LANGFUSE_ENABLED"] = orig_enabled
            elif "LANGFUSE_ENABLED" in os.environ:
                del os.environ["LANGFUSE_ENABLED"]

            if orig_public is not None:
                os.environ["LANGFUSE_PUBLIC_KEY"] = orig_public
            elif "LANGFUSE_PUBLIC_KEY" in os.environ:
                del os.environ["LANGFUSE_PUBLIC_KEY"]

            if orig_secret is not None:
                os.environ["LANGFUSE_SECRET_KEY"] = orig_secret
            elif "LANGFUSE_SECRET_KEY" in os.environ:
                del os.environ["LANGFUSE_SECRET_KEY"]

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

        # Verify is_enabled works (should be False since no credentials)
        assert adapter.is_enabled() is False

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
