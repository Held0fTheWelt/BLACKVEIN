"""Documentation checks for provider credential governance boundaries."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOC = REPO_ROOT / "docs" / "security" / "PROVIDER_CREDENTIAL_GOVERNANCE.md"
ADR_DOC = (
    REPO_ROOT
    / "docs"
    / "ADR"
    / "adr-0049-provider-credential-governance-and-local-evaluator-evidence.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_provider_credential_governance_doc_states_current_boundary() -> None:
    text = _read(GOVERNANCE_DOC)

    assert "ADR-0049: Provider credential governance and local evaluator evidence" in text
    assert "Provider API keys for backend and play-service runtime access are governed credentials" in text
    assert "OPENAI_API_KEY=" in text
    assert "OPENROUTER_API_KEY=" in text
    assert "ANTHROPIC_API_KEY=" in text
    assert "HF_TOKEN=" in text
    assert "local_only: true" in text
    assert "live_or_staging_evidence=false" in text


def test_provider_credential_governance_doc_links_to_code_evidence() -> None:
    text = _read(GOVERNANCE_DOC)

    for evidence in (
        "docker-compose.yml",
        ".env.example",
        "docker-up.py",
        "backend/app/services/governed_provider_adapter_service.py",
        "backend/app/services/writers_room_pipeline_workflow.py",
        "backend/app/services/improvement_task2a_routing.py",
        "story_runtime_core/adapters.py",
        "story_runtime_core/langfuse_tracing_environment.py",
        "world-engine/app/api/http.py",
        "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    ):
        assert evidence in text


def test_operator_docs_link_provider_credential_governance() -> None:
    linked_docs = (
        REPO_ROOT / "docs" / "security" / "README.md",
        REPO_ROOT / "docs" / "admin" / "README.md",
        REPO_ROOT / "docs" / "admin" / "security-and-compliance-overview.md",
        REPO_ROOT / "docs" / "operations" / "README.md",
        REPO_ROOT / "docs" / "INDEX.md",
        REPO_ROOT / "docs" / "reference" / "documentation-registry.md",
        REPO_ROOT / "mkdocs.yml",
        REPO_ROOT / "backend" / "app" / "info" / "templates" / "security_features.html",
    )

    for path in linked_docs:
        assert "PROVIDER_CREDENTIAL_GOVERNANCE.md" in _read(path), (
            f"Missing provider credential governance link in {path}"
        )


def test_provider_credential_governance_adr_records_evidence_boundary() -> None:
    text = _read(ADR_DOC)

    assert "Accepted" in text
    assert "Direct provider credentials are not a Compose-owned runtime control" in text
    assert "backend_governance_or_secret_manager" in text
    assert "local_only: true" in text
    assert "live_or_staging_evidence=false" in text
    assert "docs/security/PROVIDER_CREDENTIAL_GOVERNANCE.md" in text
