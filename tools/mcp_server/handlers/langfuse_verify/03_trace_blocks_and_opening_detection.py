"""Langfuse verify source segment: trace_blocks_and_opening_detection.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    return low in JUDGE_ISSUE_ALIAS_TOKENS


def _judge_score_coverage_gaps(*, is_opening: bool, judge_scores: dict[str, Any]) -> list[dict[str, Any]]:
    expected = (
        _judge_names_for_scope("opening_generation")
        if is_opening
        else _judge_names_for_scope("turn_generation")
    )
    present = {str(k) for k in judge_scores if str(k).endswith("_judge")}
    gaps: list[dict[str, Any]] = []
    for name in expected:
        if name not in present:
            gaps.append(
                {
                    "evaluator": name,
                    "gap_kind": "missing_score_row",
                    "note": (
                        "Observability / evaluator coverage gap — not a deterministic runtime failure. "
                        "Attach or backfill Langfuse scores if this rubric should be tracked."
                    ),
                }
            )
    return gaps


def _evaluator_column_metadata() -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for jname, col_key in _MATRIX_JUDGE_COLUMN_KEYS.items():
        spec = _get_categorical_evaluator_spec(jname)
        if spec is None:
            continue
        meta[col_key] = {
            "evaluator": jname,
            "evaluator_group": spec.evaluator_group,
            "qualitative_only": spec.qualitative_only,
            "runtime_gate": spec.runtime_gate,
            "suggested_repair_area": spec.repair_card,
        }
    return meta


def _extract_scores_split(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split trace scores into (deterministic_gates, judge_scores).

    Deduplicates by name (first occurrence wins). Judge scores carry
    category and reasoning extracted from score row metadata/comment.
    """
    det: dict[str, Any] = {}
    judge: dict[str, Any] = {}
    trace_metadata = _extract_metadata(raw_trace)
    score_rows = raw_trace.get("scores")
    if not isinstance(score_rows, list):
        return det, judge
    for row in score_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        value = row.get("value")
        if _is_judge_score(name):
            if name in judge:
                continue
            comment = str(row.get("comment") or "").strip()
            category = _extract_judge_category_from_row(row)
            row_metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            score_metadata = {**trace_metadata, **row_metadata}
            proof_level = str(score_metadata.get("proof_level") or "").strip() or None
            evidence_scope = str(score_metadata.get("evidence_scope") or "").strip() or None
'''
