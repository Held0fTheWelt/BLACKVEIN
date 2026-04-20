#!/usr/bin/env python3
"""
Compute G9B per-cell score deltas from two frozen goc_g9_experience_score_matrix_v1 JSON files.

Delta semantics: score_a_minus_score_b (Evaluator A minus Evaluator B) per roadmap G9B discipline.
Exits non-zero on structural mismatch or missing scores.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_matrix(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def compute_delta(
    matrix_a: dict[str, Any], matrix_b: dict[str, Any]
) -> tuple[dict[str, dict[str, int]], list[str]]:
    if matrix_a.get("audit_run_id") != matrix_b.get("audit_run_id"):
        raise ValueError("audit_run_id mismatch between matrices")
    crit_a = matrix_a.get("criteria")
    crit_b = matrix_b.get("criteria")
    if crit_a != crit_b:
        raise ValueError("criteria list mismatch")
    scenarios_a = matrix_a.get("scenarios") or []
    scenarios_b = matrix_b.get("scenarios") or []
    if len(scenarios_a) != len(scenarios_b):
        raise ValueError("scenario count mismatch")
    per_cell: dict[str, dict[str, int]] = {}
    disagreements: list[str] = []
    criteria = list(crit_a or [])
    for sa, sb in zip(scenarios_a, scenarios_b, strict=True):
        sid_a = sa.get("scenario_id")
        sid_b = sb.get("scenario_id")
        if sid_a != sid_b:
            raise ValueError(f"scenario_id order mismatch: {sid_a!r} vs {sid_b!r}")
        scores_a = sa.get("scores") or {}
        scores_b = sb.get("scores") or {}
        per_cell[sid_a] = {}
        for c in criteria:
            if c not in scores_a or c not in scores_b:
                raise ValueError(f"missing score for {sid_a}/{c}")
            va, vb = scores_a[c], scores_b[c]
            if not isinstance(va, int) or not isinstance(vb, int):
                raise ValueError(f"non-integer score for {sid_a}/{c}")
            d = va - vb
            per_cell[sid_a][c] = d
            if d != 0:
                disagreements.append(f"{sid_a}:{c}")
    return per_cell, disagreements


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("matrix_a", type=Path, help="Evaluator A matrix JSON")
    p.add_argument("matrix_b", type=Path, help="Evaluator B matrix JSON")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write full g9b_score_delta_record JSON to this path",
    )
    p.add_argument(
        "--evaluator-a-id",
        default="",
        help="Override evaluator_a_id (default: from matrix A)",
    )
    p.add_argument(
        "--evaluator-b-id",
        default="",
        help="Override evaluator_b_id (default: from matrix B)",
    )
    p.add_argument("--raw-sheet-a-ref", required=True)
    p.add_argument("--raw-sheet-b-ref", required=True)
    p.add_argument(
        "--roadmap-reference",
        default="docs/ROADMAP_MVP_GoC.md section 6.10",
    )
    args = p.parse_args()
    ma = _load_matrix(args.matrix_a)
    mb = _load_matrix(args.matrix_b)
    try:
        per_cell, disagreements = compute_delta(ma, mb)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    audit_run_id = ma["audit_run_id"]
    eid_a = args.evaluator_a_id or ma.get("evaluator_id", "")
    eid_b = args.evaluator_b_id or mb.get("evaluator_id", "")
    record: dict[str, Any] = {
        "schema": "goc_g9b_score_delta_record_v1",
        "roadmap_reference": args.roadmap_reference,
        "audit_run_id": audit_run_id,
        "not_applicable_level_a": False,
        "evaluator_a_id": eid_a,
        "evaluator_b_id": eid_b,
        "raw_sheet_a_ref": args.raw_sheet_a_ref,
        "raw_sheet_b_ref": args.raw_sheet_b_ref,
        "per_cell_delta": per_cell,
        "disagreement_summary": {
            "nonzero_cell_count": len(disagreements),
            "nonzero_cells": disagreements,
            "semantics": "score_a_minus_score_b; nonzero entries are inter-evaluator score differences only",
        },
        "note": (
            "Per-cell delta is score_a minus score_b from the frozen matrix files named in "
            "raw_sheet_a_ref / raw_sheet_b_ref (pointer chain to g9_experience_score_matrix*.json). "
            "Full grid preserved; disagreement_summary is additive, not a substitute."
        ),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    else:
        json.dump(record, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
