"""Assemble discovery, drift, conflicts, and actionable inventory messages."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.drift_analysis import detect_conflicts, run_all_drifts
from contractify.tools.models import automation_tier, serialise


def build_actionable_units(drifts: list[Any], conflicts: list[Any]) -> list[str]:
    """Human-oriented backlog strings (not raw counts)."""
    units: list[str] = []
    for d in drifts:
        units.append(f"[{d.severity}] {d.summary} → {d.recommended_follow_up}")
    for c in conflicts:
        if c.requires_human_review:
            units.append(f"[conflict] {c.summary} (review: {', '.join(c.sources[:5])})")
    return units


def run_audit(
    repo: Path,
    *,
    max_contracts: int = 30,
) -> dict[str, Any]:
    """Full machine-readable audit (restart-safe JSON contract)."""
    repo = repo.resolve()
    contracts, projections, relations = discover_contracts_and_projections(
        repo,
        max_contracts=max_contracts,
    )
    drifts = run_all_drifts(repo)
    conflicts = detect_conflicts(repo)

    # attach drift ids onto contracts (lightweight cross-index)
    drift_by_contract: dict[str, list[str]] = {}
    for d in drifts:
        for cid in d.involved_contract_ids:
            drift_by_contract.setdefault(cid, []).append(d.id)
    for c in contracts:
        c.drift_signals = drift_by_contract.get(c.id, [])

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo),
        "prework_reality_doc": "'fy'-suites/contractify/state/PREWORK_REPOSITORY_CONTRACT_REALITY.md",
        "governance_scope_doc": "'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md",
        "rollout_limits": {
            "phase1_discovery_contract_ceiling": max_contracts,
            "mature_inventory_soft_ceiling": 200,
            "hard_review_ceiling": 500,
        },
        "automation_policy": {
            "gte_0_90": "may_auto_classify_high_confidence",
            "0_60_to_0_89": "curator_review_required",
            "lt_0_60": "candidate_only_no_auto_anchor",
        },
        "contracts": [serialise(c) for c in contracts],
        "projections": [serialise(p) for p in projections],
        "relations": [serialise(r) for r in relations],
        "drift_findings": [serialise(d) for d in drifts],
        "conflicts": [serialise(c) for c in conflicts],
        "actionable_units": build_actionable_units(drifts, conflicts),
        "stats": {
            "n_contracts": len(contracts),
            "n_projections": len(projections),
            "n_relations": len(relations),
            "n_drifts": len(drifts),
            "n_conflicts": len(conflicts),
        },
        "disclaimer": "Heuristic drift is evidence for review, not automatic ground truth. "
        "Normative authority outranks observed implementation in governance decisions.",
    }
    return payload


def write_audit_json(repo: Path, out_path: Path, *, max_contracts: int = 30) -> None:
    payload = run_audit(repo, max_contracts=max_contracts)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
