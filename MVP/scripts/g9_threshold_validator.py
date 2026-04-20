#!/usr/bin/env python3
"""Validate filled G9 score matrices against roadmap §6.9 threshold structure.

Usage:
  python scripts/g9_threshold_validator.py path/to/g9_matrix.json

Exits non-zero if structure is invalid or thresholds fail. Missing scores (null)
produce a report but exit 0 — this supports partial fills during collection.

Graceful degradation ≥ 3.5 applies only to scenarios marked failure_oriented
(roadmap §6.9: "in failure scenarios"), not to every row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CRITERIA = (
    "dramatic_responsiveness",
    "truth_consistency",
    "character_credibility",
    "conflict_continuity",
    "graceful_degradation",
)

# Canonical flags for each fixed scenario id (align with ai_stack/goc_g9_roadmap_scenarios.py).
_CANONICAL_FAILURE_ORIENTED: dict[str, bool] = {
    "goc_roadmap_s1_direct_provocation": False,
    "goc_roadmap_s2_deflection_brevity": False,
    "goc_roadmap_s3_pressure_escalation": False,
    "goc_roadmap_s4_misinterpretation_correction": False,
    "goc_roadmap_s5_primary_failure_fallback": True,
    "goc_roadmap_s6_retrieval_heavy": False,
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_scenarios(
    doc: dict[str, Any],
) -> tuple[list[list[float | None]], list[bool], list[str]]:
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 6:
        raise ValueError("expected exactly 6 scenarios")
    grid: list[list[float | None]] = []
    failure_oriented: list[bool] = []
    errors: list[str] = []
    for i, row in enumerate(scenarios):
        if not isinstance(row, dict):
            errors.append(f"scenario[{i}] not an object")
            grid.append([None] * 5)
            failure_oriented.append(False)
            continue
        sid = row.get("scenario_id")
        if sid not in _CANONICAL_FAILURE_ORIENTED:
            errors.append(f"scenario[{i}] unknown or missing scenario_id")
        fo = row.get("failure_oriented")
        if fo is None:
            fo = _CANONICAL_FAILURE_ORIENTED.get(str(sid), False)
        else:
            fo = bool(fo)
            canon = _CANONICAL_FAILURE_ORIENTED.get(str(sid))
            if canon is not None and fo != canon:
                errors.append(
                    f"{sid}: failure_oriented={fo} conflicts with canonical roadmap mapping"
                )
        scores = row.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"scenario[{i}].scores missing")
            grid.append([None] * 5)
            failure_oriented.append(fo)
            continue
        line: list[float | None] = []
        for c in CRITERIA:
            v = scores.get(c)
            if v is None:
                line.append(None)
            elif isinstance(v, (int, float)):
                fv = float(v)
                if fv < 1.0 or fv > 5.0:
                    errors.append(f"{row.get('scenario_id')}.{c} out of 1..5")
                line.append(fv)
            else:
                errors.append(f"{row.get('scenario_id')}.{c} not numeric")
                line.append(None)
        grid.append(line)
        failure_oriented.append(fo)
    return grid, failure_oriented, errors


def evaluate_thresholds(
    grid: list[list[float | None]],
    failure_oriented: list[bool],
) -> dict[str, Any]:
    """Return threshold results; skip rows/cells that still contain None."""
    complete = all(all(x is not None for x in row) for row in grid)
    if not complete:
        return {"complete": False, "message": "scores incomplete — thresholds not computed"}

    if len(failure_oriented) != 6:
        return {
            "complete": False,
            "message": "internal error: failure_oriented length must be 6",
        }

    if not any(failure_oriented):
        return {
            "complete": False,
            "message": "no failure_oriented scenario — matrix must mark roadmap failure scenario(s)",
        }

    scenario_avgs: list[float] = []
    for row in grid:
        scenario_avgs.append(sum(row) / 5.0)

    crit_avgs: list[float] = []
    for ci, _ in enumerate(CRITERIA):
        crit_avgs.append(sum(grid[si][ci] for si in range(6)) / 6.0)

    min_cell = min(x for row in grid for x in row)
    min_scenario_avg = min(scenario_avgs)
    min_crit_avg = min(crit_avgs)

    deg_idx = list(CRITERIA).index("graceful_degradation")
    deg_scores = [grid[si][deg_idx] for si in range(6) if failure_oriented[si]]
    assert all(s is not None for s in deg_scores)
    min_deg_failure = min(float(s) for s in deg_scores)

    rules = {
        "no_criterion_below_3": min_cell >= 3.0,
        "per_scenario_avg_ge_4": min_scenario_avg >= 4.0,
        "per_criterion_avg_ge_4": min_crit_avg >= 4.0,
        "graceful_degradation_ge_3_5_failure_scenarios": min_deg_failure >= 3.5,
    }
    return {
        "complete": True,
        "min_cell": min_cell,
        "min_scenario_average": min_scenario_avg,
        "min_criterion_average": min_crit_avg,
        "min_graceful_degradation_failure_scenarios": min_deg_failure,
        "failure_oriented_indices_checked": [si for si in range(6) if failure_oriented[si]],
        "rules": rules,
        "pass_all": all(rules.values()),
    }


def enrich_result_with_scenario_ids(
    doc: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    if result.get("complete") and "failure_oriented_indices_checked" in result:
        scenarios = doc.get("scenarios") or []
        idxs = result["failure_oriented_indices_checked"]
        ids = []
        for si in idxs:
            if isinstance(scenarios, list) and si < len(scenarios):
                row = scenarios[si]
                if isinstance(row, dict):
                    ids.append(row.get("scenario_id", f"index_{si}"))
                else:
                    ids.append(f"index_{si}")
            else:
                ids.append(f"index_{si}")
        out = dict(result)
        out["failure_oriented_scenario_ids_checked"] = ids
        return out
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: g9_threshold_validator.py <g9_matrix.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    doc = _load(path)
    try:
        grid, failure_oriented, struct_errors = _parse_scenarios(doc)
    except ValueError as e:
        print("structure:", e, file=sys.stderr)
        return 1
    if struct_errors:
        for e in struct_errors:
            print("structure:", e)
        return 1
    result = evaluate_thresholds(grid, failure_oriented)
    result = enrich_result_with_scenario_ids(doc, result)
    print(json.dumps(result, indent=2))
    if result.get("complete") and result.get("pass_all") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
