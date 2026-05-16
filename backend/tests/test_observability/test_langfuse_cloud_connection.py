"""Integration test: Langfuse Cloud uses the same backend DB credentials as runtime.

The Admin Tool "Test connection" button and this test both call
``verify_langfuse_runtime_connectivity()`` in ``observability_governance_service``.
"""

from __future__ import annotations

import pytest

from app.services.observability_governance_service import verify_langfuse_runtime_connectivity


class TestLangfuseCloudConnection:
    """Integration tests for real Langfuse Cloud communication."""

    def test_langfuse_sends_trace_to_cloud(self, app):
        """Verify Langfuse ingest using governed backend credentials (not env overrides)."""
        pytest.importorskip(
            "langfuse",
            reason="langfuse SDK not installed; skipping cloud connection test",
        )

        with app.app_context():
            result = verify_langfuse_runtime_connectivity(poll_attempts=90, poll_interval_s=1.0)

        health = result.get("health_status")
        if health == "disabled":
            pytest.skip("Langfuse is disabled in current backend settings; skipping cloud connection test")
        if health == "credential_missing":
            pytest.skip("Langfuse credentials are not configured in backend storage; skipping cloud connection test")
        if health == "sdk_missing":
            pytest.skip(result.get("message", "langfuse SDK missing"))

        assert result.get("credentials_source") == "backend_observability_credentials"
        assert result.get("ok") is True, result.get("message")
        assert result.get("trace_id")
        assert result.get("verified_trace_id")

    def test_langfuse_adapter_has_client_configured(self, app):
        """Verify the Langfuse adapter is properly configured with valid client."""
        from app.observability.langfuse_adapter import LangfuseAdapter

        adapter = LangfuseAdapter.get_instance()

        if adapter.is_ready:
            assert adapter.client is not None, "Ready adapter must have a client"
            assert adapter.is_enabled(), "Ready adapter must report is_enabled() = True"

    def test_langfuse_credentials_from_database(self, app, db_session):
        """Verify Langfuse credentials are loaded from database when configured."""
        from app.observability.langfuse_adapter import LangfuseAdapter
        from app.models.governance_core import ObservabilityConfig, ObservabilityCredential

        adapter = LangfuseAdapter.get_instance()
        config = db_session.query(ObservabilityConfig).filter_by(service_id="langfuse").first()

        if config and config.is_enabled:
            secret = db_session.query(ObservabilityCredential).filter_by(
                service_id=config.service_id, secret_name="secret_key", is_active=True
            ).first()

            if secret and secret.encrypted_secret:
                assert adapter.is_ready, "Adapter should be ready when DB has valid credentials"
            else:
                print("\n[TEST] Langfuse enabled in DB but secret_key missing")
        else:
            print("\n[TEST] Langfuse not configured in database")
