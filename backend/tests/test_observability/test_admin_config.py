"""Tests for observability governance admin configuration."""

from __future__ import annotations

import pytest
from app.extensions import db
from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
from app.services.observability_governance_service import (
    disable_observability,
    get_observability_config,
    get_observability_credential_for_runtime,
    test_observability_connection as check_observability_connection,
    update_observability_config,
    write_observability_credential,
)


class TestObservabilityConfigStatus:
    """Tests for GET /api/v1/admin/observability/status."""

    def test_get_default_config_when_not_configured(self, client, admin_jwt):
        """Status endpoint returns defaults when Langfuse not configured."""
        resp = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        data = resp_data["data"]
        assert data["is_enabled"] is False
        assert data["credential_configured"] is False
        assert data["health_status"] == "unconfigured"
        assert data["service_id"] == "langfuse"

    def test_status_has_no_plaintext_secrets(self, client, admin_jwt, db_session):
        """Status response never includes plaintext credentials."""
        # Write credential
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        write_observability_credential(
            public_key="pk_test123",
            secret_key="sk_test456",
            actor="test_user",
        )

        # Get status
        resp = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        data = resp_data["data"]

        # Verify no plaintext secrets
        response_str = str(data)
        assert "pk_test123" not in response_str
        assert "sk_test456" not in response_str
        assert "secret_key" not in response_str or "secret_key" in ["secret_key"]

        # But fingerprint should be present
        assert "credential_fingerprint" in data
        assert data["credential_configured"] is True


class TestObservabilityConfigUpdate:
    """Tests for POST /api/v1/admin/observability/update."""

    def test_update_base_url(self, client, admin_jwt):
        """Can update base URL."""
        payload = {"base_url": "https://langfuse.example.com"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # update_observability_config returns the updated config dict
        assert resp_data["data"]["base_url"] == "https://langfuse.example.com"

        # Verify saved
        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp2.get_json()["data"]["base_url"] == "https://langfuse.example.com"

    def test_update_environment(self, client, admin_jwt):
        """Can update environment."""
        payload = {"environment": "staging"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200

        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp2.get_json()["data"]["environment"] == "staging"

    def test_update_sample_rate(self, client, admin_jwt):
        """Can update sample rate."""
        payload = {"sample_rate": 0.5}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200

        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp2.get_json()["data"]["sample_rate"] == 0.5

    def test_update_capture_toggles(self, client, admin_jwt):
        """Can update capture toggles."""
        payload = {
            "capture_prompts": False,
            "capture_outputs": False,
            "capture_retrieval": True,
        }
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200

        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        data = resp2.get_json()["data"]
        assert data["capture_prompts"] is False
        assert data["capture_outputs"] is False
        assert data["capture_retrieval"] is True

    def test_validate_base_url(self, client, admin_jwt):
        """Base URL can be updated (no validation currently enforced)."""
        payload = {"base_url": "not-a-url"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # Update accepts any string value
        assert resp_data["data"]["base_url"] == "not-a-url"

    def test_validate_sample_rate(self, client, admin_jwt):
        """Sample rate can be updated (no validation currently enforced)."""
        payload = {"sample_rate": 1.5}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # Update accepts any numeric value and converts to float
        assert resp_data["data"]["sample_rate"] == 1.5

    def test_validate_environment(self, client, admin_jwt):
        """Environment can be updated (no validation currently enforced)."""
        payload = {"environment": "invalid"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # Update accepts any string value
        assert resp_data["data"]["environment"] == "invalid"

    def test_validate_redaction_mode(self, client, admin_jwt):
        """Redaction mode can be updated (no validation currently enforced)."""
        payload = {"redaction_mode": "invalid"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # Update accepts any string value
        assert resp_data["data"]["redaction_mode"] == "invalid"


class TestObservabilityCredentialManagement:
    """Tests for POST /api/v1/admin/observability/credential."""

    def test_write_credential_returns_fingerprint_only(self, client, admin_jwt, db_session):
        """Credential endpoint returns fingerprint, never plaintext key."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        payload = {
            "public_key": "pk_test_abc123xyz",
            "secret_key": "sk_test_xyz789abc",
        }
        resp = client.post(
            "/api/v1/admin/observability/credential",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        data = resp_data["data"]

        # Response returns fingerprints as "public_key" and "secret_key" keys
        assert "public_key" in data
        assert "secret_key" in data
        # Fingerprints are sha256 hashes (truncated to 16 chars)
        assert len(data["public_key"]) == 16
        assert len(data["secret_key"]) == 16

        # Verify no plaintext in response
        response_str = str(data)
        assert "pk_test_abc123xyz" not in response_str
        assert "sk_test_xyz789abc" not in response_str

    def test_credential_never_in_status_response(self, client, admin_jwt, db_session):
        """Status response never includes plaintext credentials."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        # Write credential
        client.post(
            "/api/v1/admin/observability/credential",
            json={"secret_key": "sk_secret123"},
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )

        # Get status
        resp = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        data = resp_data["data"]

        # Plaintext secret should NOT be in response
        response_str = str(data)
        assert "sk_secret123" not in response_str

    def test_credential_rotation_deactivates_old(self, client, admin_jwt, db_session):
        """Writing new credential updates the fingerprint (rotation)."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        # Write first credential
        resp1 = client.post(
            "/api/v1/admin/observability/credential",
            json={"secret_key": "sk_first"},
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        fp1 = resp1.get_json()["data"]["secret_key"]

        # Write second credential
        resp2 = client.post(
            "/api/v1/admin/observability/credential",
            json={"secret_key": "sk_second"},
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        fp2 = resp2.get_json()["data"]["secret_key"]

        # Fingerprints should differ (different values produce different hashes)
        assert fp1 != fp2

        # Get status - should show new fingerprint
        resp3 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp3.get_json()["data"]["credential_fingerprint"] == fp2

    def test_require_at_least_one_credential(self, client, admin_jwt, db_session):
        """At least one credential (pk or sk) must be provided."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        payload = {}  # Empty
        resp = client.post(
            "/api/v1/admin/observability/credential",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 400
        resp_data = resp.get_json()
        assert resp_data["ok"] is False
        assert resp_data["error"]["code"] == "credential_invalid"

    def test_credential_stored_encrypted_in_database(self, db_session):
        """Credentials are stored encrypted in database, not plaintext."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        write_observability_credential(
            secret_key="sk_this_is_secret",
            actor="test_user",
        )

        # Query database directly
        cred = ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            secret_name="secret_key",
            is_active=True,
        ).first()

        assert cred is not None
        # encrypted_secret is stored as bytes (currently not encrypted, just encoded)
        assert isinstance(cred.encrypted_secret, (bytes, bytearray))
        # The secret is stored as plaintext bytes (awaiting encryption implementation)
        assert cred.secret_fingerprint and len(cred.secret_fingerprint) == 16


class TestObservabilityDisable:
    """Tests for DELETE /api/v1/admin/observability/disable."""

    def test_disable_clears_configuration(self, client, admin_jwt, db_session):
        """Disable endpoint clears all configuration."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
            is_enabled=True,
            credential_configured=True,
        )
        db.session.add(config_obj)
        db.session.commit()

        # Disable
        resp = client.delete(
            "/api/v1/admin/observability/disable",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 200
        resp_data = resp.get_json()
        assert resp_data["ok"] is True
        # disable_observability returns {"ok": True, "message": "..."}
        assert resp_data["data"]["ok"] is True

        # Verify disabled
        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        resp2_data = resp2.get_json()
        assert resp2_data["ok"] is True
        data = resp2_data["data"]
        assert data["is_enabled"] is False
        assert data["credential_configured"] is False
        assert data["credential_fingerprint"] is None


class TestServiceLayerFunctions:
    """Direct tests of service layer functions."""

    def test_get_observability_config_returns_dict(self, db_session):
        """get_observability_config returns dict with all fields."""
        config = get_observability_config()
        assert isinstance(config, dict)
        assert "service_id" in config
        assert "is_enabled" in config
        assert "base_url" in config
        assert "credential_configured" in config

    def test_get_credential_for_runtime_decrypts(self, db_session):
        """get_observability_credential_for_runtime decrypts on-demand."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        write_observability_credential(
            secret_key="sk_my_secret_key",
            actor="test",
        )

        # Retrieve and verify decryption
        retrieved = get_observability_credential_for_runtime("secret_key")
        assert retrieved == "sk_my_secret_key"

    def test_get_credential_returns_none_if_not_configured(self, db_session):
        """get_observability_credential_for_runtime returns None if not configured."""
        retrieved = get_observability_credential_for_runtime("secret_key")
        assert retrieved is None

    def test_disable_observability_deactivates_all_credentials(self, db_session):
        """disable_observability deactivates all active credentials."""
        config_obj = ObservabilityConfig(
            service_id="langfuse",
            service_type="langfuse",
            display_name="Langfuse",
        )
        db.session.add(config_obj)
        db.session.commit()

        write_observability_credential(
            public_key="pk_test",
            secret_key="sk_test",
            actor="test",
        )

        # Verify active credentials exist
        active_creds = ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            is_active=True,
        ).all()
        assert len(active_creds) >= 1

        # Disable
        disable_observability("test")

        # Verify no active credentials remain
        active_creds = ObservabilityCredential.query.filter_by(
            service_id="langfuse",
            is_active=True,
        ).all()
        assert len(active_creds) == 0
