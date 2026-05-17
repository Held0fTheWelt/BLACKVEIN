"""Documentation checks for at-rest encryption evidence boundaries."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AT_REST_DOC = REPO_ROOT / "docs" / "security" / "AT_REST_ENCRYPTION.md"
ADR_DOC = REPO_ROOT / "docs" / "ADR" / "adr-0047-at-rest-encryption-evidence-boundary.md"
GOVERNANCE_ADR_DOC = REPO_ROOT / "docs" / "ADR" / "adr-0051-storage-layer-encryption-governance.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_at_rest_encryption_doc_states_current_boundary() -> None:
    text = _read(AT_REST_DOC)

    assert "Full repository-managed at-rest encryption is not currently established." in text
    assert "ADR-0047: At-rest encryption evidence boundary" in text
    assert "ADR-0051: Storage-layer encryption governance" in text
    assert "storage_encryption_evidence" in text
    assert "storage_layer_encryption" in text
    assert "backend/instance/wos.db" in text
    assert "redis-data:/data" in text
    assert "RUN_STORE_BACKEND=json" in text
    assert "RUN_STORE_BACKEND=json_aead" in text
    assert "WORLD_ENGINE_JSON_AEAD_KEY" in text
    assert "langfuse-postgres-data" in text
    assert "No committed backup job proves encrypted backup output" in text


def test_at_rest_encryption_doc_links_to_code_evidence() -> None:
    text = _read(AT_REST_DOC)

    for evidence in (
        "backend/app/services/governance_secret_crypto_service.py",
        "backend/migrations/versions/044_observability_langfuse_configuration.py",
        "backend/app/services/encryption_service.py",
        "docker-compose.langfuse.yml",
        "docker-compose.yml",
        "world-engine/app/runtime/json_at_rest.py",
        "world-engine/app/runtime/store.py",
        "world-engine/tests/test_aead_json_persistence.py",
    ):
        assert evidence in text


def test_operator_docs_link_at_rest_encryption_evidence() -> None:
    linked_docs = (
        REPO_ROOT / "docs" / "security" / "README.md",
        REPO_ROOT / "docs" / "admin" / "security-and-compliance-overview.md",
        REPO_ROOT / "docs" / "database" / "README.md",
        REPO_ROOT / "docs" / "operations" / "README.md",
        REPO_ROOT / "docs" / "local-langfuse-docker.md",
        REPO_ROOT / "docs" / "INDEX.md",
        REPO_ROOT / "mkdocs.yml",
    )

    for path in linked_docs:
        assert "AT_REST_ENCRYPTION.md" in _read(path), f"Missing at-rest evidence link in {path}"


def test_at_rest_encryption_adr_records_evidence_boundary() -> None:
    text = _read(ADR_DOC)

    assert "Not Finished" in text
    assert "must not claim \"full at-rest encryption\"" in text
    assert "docs/security/AT_REST_ENCRYPTION.md" in text
    assert "backend/instance/wos.db" in text
    assert "redis-data:/data" in text
    assert "langfuse-postgres-data" in text
    assert "encrypted backup output" in text


def test_storage_layer_governance_adr_records_admin_and_diagnosis() -> None:
    text = _read(GOVERNANCE_ADR_DOC)

    assert "Accepted" in text
    assert "storage_encryption_evidence" in text
    assert "/manage/security-governance" in text
    assert "/api/v1/admin/security/governance" in text
    assert "RUN_STORE_BACKEND=json_aead" in text
    assert "WORLD_ENGINE_JSON_AEAD_KEY" in text
    assert "world-engine/app/runtime/json_at_rest.py" in text
    assert "No additional functional change is required in the base `docker-compose.yml`" in text
    assert "DATABASE_URI" in text
    assert "docker-compose.redis-production.yml" in text
    assert "storage_layer_encryption" in text
    assert "backups_snapshots" in text
    assert "does not replace deployment controls" in text
