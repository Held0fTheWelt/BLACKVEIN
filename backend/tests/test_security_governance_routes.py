"""Security governance API contract tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.routes_core


def test_security_governance_get_returns_policy_and_matrix(client, admin_headers):
    response = client.get("/api/v1/admin/security/governance", headers=admin_headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["contract"] == "security_governance.v1"
    assert data["settings"]["target_session_samesite"] == "Lax"
    assert data["settings"]["secret_store_mode"] == "production_secret_store"
    assert data["settings"]["secret_store_provider"] == "deployment_managed"
    assert data["settings"]["secret_rotation_interval_days"] == 90
    assert data["settings"]["preserve_docker_up_local_bootstrap"] is True
    assert data["settings"]["redis_hardening_profile"] == "production_compose"
    assert data["settings"]["require_redis_tls"] is True
    assert data["settings"]["require_redis_acl_users"] is True
    assert data["settings"]["storage_encryption_profile"] == "mixed_evidence_pack"
    assert data["settings"]["require_storage_encryption_evidence"] is True
    assert data["settings"]["require_backup_encryption_evidence"] is True
    assert data["settings"]["require_storage_key_custody_evidence"] is True
    assert data["settings"]["require_storage_restore_test_evidence"] is True
    assert data["secret_management_governance"]["production"]["required"] is True
    assert data["secret_management_governance"]["local_bootstrap"]["preserved"] is True
    assert "python docker-up.py init-env" in data["secret_management_governance"]["local_bootstrap"]["commands"]
    assert data["redis_governance"]["compose_override"] == "docker-compose.redis-production.yml"
    assert "python docker-up.py init-production-redis" in data["redis_governance"]["commands"]
    assert any(check["id"] == "redis_acl_users" for check in data["redis_governance"]["checks"])
    assert any(check["id"] == "redis_no_host_ports" for check in data["redis_governance"]["checks"])
    assert data["storage_encryption_governance"]["status"] == "needs_attention"
    assert data["storage_encryption_governance"]["api_endpoint"] == "/api/v1/admin/security/governance"
    assert data["storage_encryption_governance"]["diagnosis_check"] == "storage_layer_encryption"
    assert data["storage_encryption_governance"]["coverage"]["surface_count"] >= 9
    surfaces = data["storage_encryption_governance"]["surfaces"]
    assert any(surface["id"] == "backend_sqlite" for surface in surfaces)
    json_surface = next(surface for surface in surfaces if surface["id"] == "world_engine_json_run_store")
    assert "RUN_STORE_BACKEND=json_aead" in json_surface["persistence"]
    assert "*.json.enc" in json_surface["persistence"]
    sql_surface = next(surface for surface in surfaces if surface["id"] == "world_engine_sqlalchemy_run_store")
    assert "encrypted managed database" in sql_surface["persistence"]
    assert any(
        check["id"] == "storage_evidence_backend_sqlite"
        for check in data["storage_encryption_governance"]["checks"]
    )
    assert data["effective_posture"]["backend_csrf"]["api_v1_exempt"] is True
    assert any(row["flow"] == "admin_proxy" for row in data["csrf_matrix"])
    assert "api_v1 CSRF exemption is code-owned in factory_app.py" in data["non_editable_boundaries"]
    assert "docker-up.py local .env bootstrap must remain independent from production secret stores" in data["non_editable_boundaries"]
    assert "Redis password/TLS/ACL materialization is host-owned by docker-up.py, not executed from the admin browser" in data["non_editable_boundaries"]
    assert "Storage-layer encryption evidence is operator-owned" in data["non_editable_boundaries"][-1]


def test_security_governance_patch_persists_operator_policy(client, admin_headers):
    patch_response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={
            "review_status": "needs_review",
            "target_session_samesite": "Strict",
            "require_csrf_regression_tests": True,
            "secret_store_mode": "production_secret_store",
            "secret_store_provider": "vault",
            "secret_rotation_interval_days": 45,
            "secret_store_audit_required": True,
            "secret_store_access_separation_required": True,
            "preserve_docker_up_local_bootstrap": True,
            "redis_hardening_profile": "managed_service",
            "require_production_redis_hardening": True,
            "require_redis_tls": True,
            "require_redis_acl_users": True,
            "require_redis_instance_separation": True,
            "require_redis_no_host_ports": False,
            "require_redis_validation_gate": True,
            "storage_encryption_profile": "managed_encrypted_services",
            "require_storage_encryption_evidence": True,
            "require_backup_encryption_evidence": True,
            "require_storage_key_custody_evidence": True,
            "require_storage_restore_test_evidence": True,
            "storage_encryption_evidence": {
                "backend_sqlite": {
                    "status": "verified",
                    "control_type": "managed_service_kms",
                    "evidence_ref": "ops/evidence/prod-db-encryption",
                    "key_ref": "kms://prod/sqlite-host-key",
                    "last_verified_at": "2026-05-17",
                    "notes": "Production deployment replaces local SQLite with encrypted managed storage.",
                }
            },
            "operator_notes": "Review before production.",
        },
    )

    assert patch_response.status_code == 200
    patched = patch_response.get_json()["data"]["settings"]
    assert patched["review_status"] == "needs_review"
    assert patched["target_session_samesite"] == "Strict"
    assert patched["secret_store_provider"] == "vault"
    assert patched["secret_rotation_interval_days"] == 45
    assert patched["redis_hardening_profile"] == "managed_service"
    assert patched["require_redis_no_host_ports"] is False
    assert patched["storage_encryption_profile"] == "managed_encrypted_services"
    assert patched["storage_encryption_evidence"]["backend_sqlite"]["status"] == "verified"
    assert patched["storage_encryption_evidence"]["backend_sqlite"]["key_ref"] == "kms://prod/sqlite-host-key"
    assert patched["operator_notes"] == "Review before production."

    get_response = client.get("/api/v1/admin/security/governance", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.get_json()["data"]["settings"]["target_session_samesite"] == "Strict"
    assert get_response.get_json()["data"]["secret_management_governance"]["production"]["provider"] == "vault"
    assert get_response.get_json()["data"]["redis_governance"]["profile"] == "managed_service"
    assert (
        get_response.get_json()["data"]["storage_encryption_governance"]["surfaces"][0]["evidence_ref"]
        == "ops/evidence/prod-db-encryption"
    )


def test_security_governance_patch_rejects_unknown_fields(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"disable_csrf_everywhere": True},
    )

    assert response.status_code == 400
    assert response.get_json()["ok"] is False
    assert "Unknown security governance field" in response.get_json()["error"]["message"]


def test_security_governance_patch_validates_secret_store_values(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"secret_store_mode": "magic_file"},
    )

    assert response.status_code == 400
    assert "secret_store_mode" in response.get_json()["error"]["message"]

    rotation_response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"secret_rotation_interval_days": 0},
    )

    assert rotation_response.status_code == 400
    assert "secret_rotation_interval_days" in rotation_response.get_json()["error"]["message"]


def test_security_governance_patch_validates_redis_profile(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"redis_hardening_profile": "shared_plaintext_cache"},
    )

    assert response.status_code == 400
    assert "redis_hardening_profile" in response.get_json()["error"]["message"]


def test_security_governance_patch_validates_storage_evidence(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"storage_encryption_profile": "plaintext_volumes"},
    )

    assert response.status_code == 400
    assert "storage_encryption_profile" in response.get_json()["error"]["message"]

    bad_surface = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"storage_encryption_evidence": {"unknown_volume": {"status": "verified"}}},
    )

    assert bad_surface.status_code == 400
    assert "Unknown storage encryption evidence surface" in bad_surface.get_json()["error"]["message"]

    bad_status = client.patch(
        "/api/v1/admin/security/governance",
        headers=admin_headers,
        json={"storage_encryption_evidence": {"backend_sqlite": {"status": "magic"}}},
    )

    assert bad_status.status_code == 400
    assert "storage_encryption_evidence.backend_sqlite.status" in bad_status.get_json()["error"]["message"]
