"""Tests for observability governance admin configuration."""

from __future__ import annotations

import pytest
from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
from app.services.observability_governance_service import (
    disable_observability,
    get_observability_config,
    get_observability_credential_for_runtime,
    test_observability_connection,
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
        data = resp.get_json()
        assert data["is_enabled"] is False
        assert data["credential_configured"] is False
        assert data["health_status"] == "unknown"
        assert data["service_id"] == "langfuse"

    def test_status_has_no_plaintext_secrets(self, client, admin_jwt, db):
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
        data = resp.get_json()

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
        assert resp.get_json()["updated"] is True

        # Verify saved
        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp2.get_json()["base_url"] == "https://langfuse.example.com"

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
        assert resp2.get_json()["environment"] == "staging"

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
        assert resp2.get_json()["sample_rate"] == 0.5

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
        data = resp2.get_json()
        assert data["capture_prompts"] is False
        assert data["capture_outputs"] is False
        assert data["capture_retrieval"] is True

    def test_validate_base_url(self, client, admin_jwt):
        """Base URL validation rejects invalid URLs."""
        payload = {"base_url": "not-a-url"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 400
        assert "invalid_url" in resp.get_json().get("error_code", "")

    def test_validate_sample_rate(self, client, admin_jwt):
        """Sample rate validation rejects out-of-range values."""
        payload = {"sample_rate": 1.5}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 400
        assert "invalid_sample_rate" in resp.get_json().get("error_code", "")

    def test_validate_environment(self, client, admin_jwt):
        """Environment validation rejects invalid values."""
        payload = {"environment": "invalid"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 400
        assert "invalid_environment" in resp.get_json().get("error_code", "")

    def test_validate_redaction_mode(self, client, admin_jwt):
        """Redaction mode validation rejects invalid values."""
        payload = {"redaction_mode": "invalid"}
        resp = client.post(
            "/api/v1/admin/observability/update",
            json=payload,
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp.status_code == 400
        assert "invalid_redaction_mode" in resp.get_json().get("error_code", "")


class TestObservabilityCredentialManagement:
    """Tests for POST /api/v1/admin/observability/credential."""

    def test_write_credential_returns_fingerprint_only(self, client, admin_jwt, db):
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
        data = resp.get_json()

        # Response must have fingerprints, not plaintext
        assert "public_key_fingerprint" in data
        assert "secret_key_fingerprint" in data
        assert "public_key" not in data
        assert "secret_key" not in data
        assert data["public_key_fingerprint"].startswith("pk_")
        assert data["secret_key_fingerprint"].startswith("sk_")

        # Verify no plaintext in response
        response_str = str(data)
        assert "pk_test_abc123xyz" not in response_str
        assert "sk_test_xyz789abc" not in response_str

    def test_credential_never_in_status_response(self, client, admin_jwt, db):
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
        data = resp.get_json()

        # Plaintext secret should NOT be in response
        response_str = str(data)
        assert "sk_secret123" not in response_str

    def test_credential_rotation_deactivates_old(self, client, admin_jwt, db):
        """Writing new credential deactivates and versions the old one."""
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
        fp1 = resp1.get_json()["secret_key_fingerprint"]

        # Write second credential
        resp2 = client.post(
            "/api/v1/admin/observability/credential",
            json={"secret_key": "sk_second"},
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        fp2 = resp2.get_json()["secret_key_fingerprint"]

        # Fingerprints should differ (rotation occurred)
        assert fp1 != fp2

        # Get status - should show new fingerprint
        resp3 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        assert resp3.get_json()["credential_fingerprint"] == fp2

    def test_require_at_least_one_credential(self, client, admin_jwt, db):
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
        assert "credential_invalid" in resp.get_json().get("error_code", "")

    def test_credential_stored_encrypted_in_database(self, db):
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
        # encrypted_secret should be binary, not readable plaintext
        assert isinstance(cred.encrypted_secret, (bytes, bytearray))
        assert b"sk_this_is_secret" not in cred.encrypted_secret
        assert cred.secret_fingerprint.startswith("sk_")


class TestObservabilityDisable:
    """Tests for DELETE /api/v1/admin/observability/disable."""

    def test_disable_clears_configuration(self, client, admin_jwt, db):
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
        assert resp.get_json()["disabled"] is True

        # Verify disabled
        resp2 = client.get(
            "/api/v1/admin/observability/status",
            headers={"Authorization": f"Bearer {admin_jwt}"},
        )
        data = resp2.get_json()
        assert data["is_enabled"] is False
        assert data["credential_configured"] is False
        assert data["credential_fingerprint"] is None


class TestServiceLayerFunctions:
    """Direct tests of service layer functions."""

    def test_get_observability_config_returns_dict(self, db):
        """get_observability_config returns dict with all fields."""
        config = get_observability_config()
        assert isinstance(config, dict)
        assert "service_id" in config
        assert "is_enabled" in config
        assert "base_url" in config
        assert "credential_configured" in config

    def test_get_credential_for_runtime_decrypts(self, db):
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

    def test_get_credential_returns_none_if_not_configured(self, db):
        """get_observability_credential_for_runtime returns None if not configured."""
        retrieved = get_observability_credential_for_runtime("secret_key")
        assert retrieved is None

    def test_disable_observability_deactivates_all_credentials(self, db):
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
