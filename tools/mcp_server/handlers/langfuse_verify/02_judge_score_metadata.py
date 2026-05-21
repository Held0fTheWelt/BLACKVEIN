"""Langfuse verify source segment: judge_score_metadata.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
def _extract_scores(raw_trace: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    score_rows = raw_trace.get("scores")
    if isinstance(score_rows, list):
        for row in score_rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            out[name] = row.get("value")
    return out


def _is_judge_score(name: str) -> bool:
    return name.endswith("_judge")


def _extract_judge_category_from_row(row: dict[str, Any]) -> str | None:
    """Resolve categorical label from Langfuse score row metadata (API shape varies)."""
    row_meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    for key in (
        "category",
        "label",
        "selectedCategory",
        "selected_category",
        "valueCategory",
        "value_category",
    ):
        if key not in row_meta:
            continue
        v = row_meta.get(key)
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    cats = row_meta.get("categories")
    if isinstance(cats, list):
        non_empty = [str(c).strip() for c in cats if str(c).strip()]
        if len(non_empty) == 1:
            return non_empty[0]
    if isinstance(cats, str) and cats.strip():
        return cats.strip()
    matched = row_meta.get("matched_categories")
    if isinstance(matched, list) and len(matched) == 1:
        s = str(matched[0]).strip()
        if s:
            return s
    return None


def _normalize_judge_category_for_issue_check(judge_name: str, category: str | None) -> str | None:
    """Map legacy evaluator labels to current rubric tokens (case-insensitive)."""
    mapped = _normalize_judge_category_label(judge_name, category)
    if not mapped:
        return None
    return str(mapped).strip()


def _judge_category_triggers_issue(judge_name: str, category: str | None) -> bool:
    if not category:
        return False
    normalized = _normalize_judge_category_for_issue_check(judge_name, category)
    if not normalized:
        return False
    low = normalized.strip().lower()
    spec = _WOS_JUDGE_ISSUE_CATEGORIES.get(judge_name)
    if spec is not None:
        return low in spec
'''
