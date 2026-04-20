"""Committed sample JSON under ``examples/`` stays structurally compatible with the audit CLI."""
from __future__ import annotations

import json
from pathlib import Path

_DISCOVERY_KEYS = frozenset({"contracts", "projections", "relations", "automation_tiers_sample"})
_AUDIT_KEYS = frozenset(
    {
        "generated_at",
        "repo_root",
        "contracts",
        "projections",
        "relations",
        "drift_findings",
        "conflicts",
        "actionable_units",
        "stats",
        "disclaimer",
    }
)


def _examples_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "examples"


def test_sample_contract_discovery_json_shape() -> None:
    path = _examples_dir() / "contract_discovery.sample.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert _DISCOVERY_KEYS <= data.keys()
    assert isinstance(data["contracts"], list)
    assert len(data["contracts"]) >= 1


def test_sample_contract_audit_json_shape() -> None:
    path = _examples_dir() / "contract_audit.sample.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert _AUDIT_KEYS <= data.keys()
    assert data["stats"]["n_contracts"] >= 0
    assert data["conflicts"]
    c0 = data["conflicts"][0]
    for key in (
        "classification",
        "normative_sources",
        "observed_or_projection_sources",
        "requires_human_review",
        "severity",
        "kind",
    ):
        assert key in c0
