from pathlib import Path

from contractify.tools.discovery import discover_contracts_and_projections, projection_backref_ok
from contractify.tools.repo_paths import repo_root


def test_discovery_finds_normative_index() -> None:
    root = repo_root()
    contracts, projections, relations = discover_contracts_and_projections(root, max_contracts=40)
    ids = {c.id for c in contracts}
    assert "CTR-NORM-INDEX-001" in ids
    assert any(c.anchor_location.endswith("normative-contracts-index.md") for c in contracts)


def test_projection_backref_detects_link() -> None:
    root = repo_root()
    sample = root / "docs" / "dev" / "README.md"
    if sample.is_file():
        ok, _reason = projection_backref_ok(sample)
        assert ok


def test_postman_manifest_projection_when_openapi_present() -> None:
    root = repo_root()
    if not (root / "docs" / "api" / "openapi.yaml").is_file():
        return
    _c, projections, _r = discover_contracts_and_projections(root, max_contracts=40)
    assert any(p.id.startswith("PRJ-POSTMANIFY") for p in projections)
