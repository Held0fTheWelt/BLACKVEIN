"""Langfuse verify source segment: normalized_evidence_scores.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    return None


def _parse_status_tokens(status_message: str) -> dict[str, str]:
    """Parse 'key=value ...' tokens from a Langfuse statusMessage string."""
    result: dict[str, str] = {}
    for m in re.finditer(r"(\w+)=([^\s]+)", str(status_message or "")):
        result[m.group(1).lower()] = m.group(2).strip()
    return result


def _first_score_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    """Return metadata from the first score row that has a non-empty metadata dict.

    All scores in a trace share the same ``score_metadata_base`` (session_id,
    selected_player_role, human_actor_id, final_adapter, quality_class, etc.)
    so any score entry is an equally valid source.
    """
    for row in (raw_trace.get("scores") or []):
        if not isinstance(row, dict):
            continue
        meta = _coerce_dict_or_json(row.get("metadata"))
        if meta:
            return meta
    return {}


def _is_opening_trace(raw_trace: dict[str, Any]) -> bool:
    """Return True when this trace is a turn-0 (opening) trace.

    Detection order (first match wins):
    1. trace.name == "world-engine.session.create"
    2. Any score row has metadata.turn_number == 0
    3. trace.metadata.turn_number == 0
    """
    trace_name = str(raw_trace.get("name") or "").strip()
    if trace_name == "world-engine.session.create":
        return True
    for row in (raw_trace.get("scores") or []):
        if not isinstance(row, dict):
            continue
        row_meta = _coerce_dict_or_json(row.get("metadata"))
        try:
            if int(row_meta.get("turn_number", -1)) == 0:
                return True
        except (TypeError, ValueError):
            pass
    top_meta = _extract_metadata(raw_trace)
    try:
        if int(top_meta.get("turn_number", -1)) == 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _live_opening_value(
    det_scores: dict[str, Any],
    raw_trace: dict[str, Any],
) -> float | str:
    """Return live_opening_contract_pass as float, or "not_applicable" for turn-1+ traces.

    Rules:
    - Score present (0.0 or 1.0) → return as float regardless of turn.
    - Score absent on opening trace (turn 0) → 0.0 (missing = gate fail).
    - Score absent on non-opening trace (turn 1+) → "not_applicable".
    """
    val = det_scores.get("live_opening_contract_pass")
    if val is not None:
        return float(val)
    if _is_opening_trace(raw_trace):
        return 0.0
'''
