from __future__ import annotations

from pathlib import Path

from conftest import captured_templates


def test_manage_security_governance_route_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get("/manage/security-governance")

    assert response.status_code == 200
    assert templates[-1][0] == "manage/security_governance.html"


def test_manage_base_includes_security_governance_nav(client):
    response = client.get("/manage")
    html = response.get_data(as_text=True)

    assert "manage-nav-security-governance" in html
    assert "/manage/security-governance" in html
    assert 'data-feature="manage.ai_runtime_governance"' in html


def test_manage_security_governance_exposes_secret_store_controls(client):
    response = client.get("/manage/security-governance")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Secret-store boundary" in html
    assert "manage-sg-field-secret-store-mode" in html
    assert "manage-sg-field-secret-store-provider" in html
    assert "manage-sg-field-secret-rotation-days" in html
    assert "manage-sg-field-secret-audit" in html
    assert "manage-sg-field-secret-access-separation" in html
    assert "manage-sg-field-preserve-docker-up" in html
    assert "manage-sg-secret-governance" in html
    assert "manage_security_governance.js" in html
    assert "docker-up.py" in html


def test_manage_security_governance_exposes_redis_controls(client):
    response = client.get("/manage/security-governance")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Redis hardening" in html
    assert "Production Redis" in html
    assert "manage-sg-redis-profile" in html
    assert "manage-sg-redis-status" in html
    assert "manage-sg-field-redis-profile" in html
    assert "manage-sg-field-redis-tls" in html
    assert "manage-sg-field-redis-acl" in html
    assert "manage-sg-field-redis-separate" in html
    assert "manage-sg-field-redis-no-host-ports" in html
    assert "manage-sg-field-redis-validation" in html
    assert "manage-sg-redis-checks" in html
    assert "manage-sg-redis-commands" in html


def test_manage_security_governance_exposes_storage_layer_controls(client):
    response = client.get("/manage/security-governance")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Storage-layer encryption" in html
    assert "Storage Evidence" in html
    assert "manage-sg-storage-status" in html
    assert "manage-sg-field-storage-profile" in html
    assert "manage-sg-field-storage-evidence-required" in html
    assert "manage-sg-field-backup-evidence-required" in html
    assert "manage-sg-field-storage-key-custody" in html
    assert "manage-sg-field-storage-restore-test" in html
    assert "manage-sg-field-storage-evidence-json" in html
    assert "manage-sg-storage-effective-list" in html
    assert "manage-sg-storage-checks" in html


def test_manage_security_governance_js_uses_backend_governance_endpoint():
    js = Path(__file__).resolve().parents[1] / "static" / "manage_security_governance.js"
    text = js.read_text(encoding="utf-8")

    assert '"/api/v1/admin/security/governance"' in text
    assert "ManageAuth.apiFetchWithAuth" in text
    assert 'method: "PATCH"' in text
    assert "secret_store_mode" in text
    assert "preserve_docker_up_local_bootstrap" in text
    assert "redis_hardening_profile" in text
    assert "require_redis_tls" in text
    assert "manage-sg-redis-checks" in text
    assert "storage_encryption_profile" in text
    assert "storage_encryption_evidence" in text
    assert "require_storage_key_custody_evidence" in text
    assert "manage-sg-storage-checks" in text
