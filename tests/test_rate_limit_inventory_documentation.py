"""Documentation checks for rate-limit inventory and production telemetry."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RATE_LIMIT_DOC = REPO_ROOT / "docs" / "security" / "rate-limit-inventory.md"
ADR_DOC = REPO_ROOT / "docs" / "ADR" / "adr-0048-central-route-and-mcp-rate-limit-inventory.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rate_limit_inventory_doc_records_production_telemetry_contract() -> None:
    text = _read(RATE_LIMIT_DOC)

    assert "Current readiness: `inventory_only`" in text
    assert "rate_limit_requests_total" in text
    assert "rate_limit_hits_total" in text
    assert "rate_limit_quota_utilization_ratio" in text
    assert "edge_throttle_events_total" in text
    assert "Shadow-Tuning" in text
    assert "hashed limiter key" in text
    assert "never raw bearer tokens" in text


def test_rate_limit_inventory_adr_requires_telemetry_before_tuning_claims() -> None:
    text = _read(ADR_DOC)

    assert "Production limit changes must not be justified from inventory coverage alone" in text
    assert "hashed limiter keys only" in text
    assert "rate_limit_hits_total" in text
    assert "canary result" in text


def test_primary_docs_link_rate_limit_inventory() -> None:
    linked_docs = (
        REPO_ROOT / "docs" / "security" / "README.md",
        REPO_ROOT / "docs" / "INDEX.md",
        REPO_ROOT / "docs" / "reference" / "documentation-registry.md",
        REPO_ROOT / "docs" / "ADR" / "README.md",
        REPO_ROOT / "mkdocs.yml",
    )

    for path in linked_docs:
        assert "rate-limit-inventory" in _read(path), f"Missing rate-limit inventory link in {path}"
