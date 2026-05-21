"""Langfuse verify source segment: normalized_evidence_core.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            local_only = bool(score_metadata.get("local_only")) or proof_level == "local_only" or evidence_scope == "local_langfuse"
            live_or_staging = score_metadata.get("live_or_staging_evidence")
            entry = {
                "value": value,
                "category": category,
                "reasoning": comment or None,
                "local_only": local_only,
            }
            if proof_level:
                entry["proof_level"] = proof_level
            if evidence_scope:
                entry["evidence_scope"] = evidence_scope
            if live_or_staging is not None:
                entry["live_or_staging_evidence"] = bool(live_or_staging)
            judge[name] = entry
        else:
            if name in det:
                continue
            det[name] = value
    return det, judge


def _extract_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = raw_trace.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


# ---------------------------------------------------------------------------
# WoS evidence extraction helpers
# ---------------------------------------------------------------------------

def _coerce_dict_or_json(value: Any) -> dict[str, Any]:
    """Return dict from value; parse JSON if it's a string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return {}


def _get_observations(raw_trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Return observations list, normalising each entry to a plain dict."""
    raw_obs = raw_trace.get("observations") or []
    result: list[dict[str, Any]] = []
    for o in raw_obs:
        if isinstance(o, dict):
            result.append(o)
        elif hasattr(o, "model_dump"):
            try:
                d = o.model_dump()
                if isinstance(d, dict):
                    result.append(d)
            except Exception:
                pass
    return result


def _find_observation_by_name(
    observations: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    for obs in observations:
        if obs.get("name") == name:
            return obs
'''
