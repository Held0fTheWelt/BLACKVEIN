"""Documentation checks for security governance and CSRF/browser mutation boundaries."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADMIN_DOC = REPO_ROOT / "docs" / "admin" / "security-governance.md"
ADR_DOC = REPO_ROOT / "docs" / "ADR" / "adr-0050-security-governance-browser-mutation-boundaries.md"
CONTROL_PLANE_ADR = REPO_ROOT / "docs" / "ADR" / "adr-0052-security-governance-admin-control-plane.md"
CSRF_MATRIX = REPO_ROOT / "docs" / "security" / "csrf-matrix.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_security_governance_admin_doc_records_operator_boundary() -> None:
    text = _read(ADMIN_DOC)

    assert "/manage/security-governance" in text
    assert "/api/v1/admin/security/governance" in text
    assert "site_settings.security_governance_config" in text
    assert "security_governance.v1" in text
    assert "Editable policy" in text
    assert "Non-editable boundaries" in text
    assert "Redis hardening" in text
    assert "Do not paste secrets" in text


def test_security_governance_adr_records_code_owned_enforcement() -> None:
    text = _read(ADR_DOC)

    assert "Accepted" in text
    assert "docs/security/csrf-matrix.md" in text
    assert "manage.ai_runtime_governance" in text
    assert "not hidden runtime toggles" in text
    assert "proxy cookie stripping" in text
    assert "Redis ACL/TLS/certificate files" in text


def test_security_governance_control_plane_adr_records_admin_redis_policy() -> None:
    text = _read(CONTROL_PLANE_ADR)

    assert "ADR-0052: Security Governance Admin Control Plane" in text
    assert "/manage/security-governance" in text
    assert "site_settings.security_governance_config" in text
    assert "production Redis hardening gates" in text
    assert "Redis password/TLS/ACL materialization remains host/deployment-owned" in text
    assert "ADR-0050" in text


def test_csrf_matrix_links_security_governance_surface() -> None:
    text = _read(CSRF_MATRIX)

    assert "Security Governance" in text
    assert "../admin/security-governance.md" in text
    assert "../ADR/adr-0050-security-governance-browser-mutation-boundaries.md" in text
    assert "../ADR/adr-0052-security-governance-admin-control-plane.md" in text


def test_primary_documentation_indexes_link_security_governance() -> None:
    linked_docs = (
        REPO_ROOT / "docs" / "admin" / "README.md",
        REPO_ROOT / "docs" / "admin" / "security-and-compliance-overview.md",
        REPO_ROOT / "docs" / "security" / "README.md",
        REPO_ROOT / "docs" / "INDEX.md",
        REPO_ROOT / "docs" / "reference" / "documentation-registry.md",
        REPO_ROOT / "docs" / "ADR" / "README.md",
        REPO_ROOT / "mkdocs.yml",
    )

    for path in linked_docs:
        text = _read(path)
        assert "security-governance.md" in text or "adr-0050-security-governance" in text, (
            f"Missing security governance link in {path}"
        )
    adr_index = _read(REPO_ROOT / "docs" / "ADR" / "README.md")
    assert "adr-0052-security-governance-admin-control-plane.md" in adr_index
    mkdocs = _read(REPO_ROOT / "mkdocs.yml")
    assert "admin/security-governance.md" in mkdocs
    assert "ADR/adr-0052-security-governance-admin-control-plane.md" in mkdocs
