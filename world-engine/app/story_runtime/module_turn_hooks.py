"""Per-module execute_turn hooks — keeps StoryRuntimeManager.execute_turn readable."""

from __future__ import annotations

from typing import Any

GOD_OF_CARNAGE_MODULE_ID = "god_of_carnage"


def goc_host_experience_template(runtime_projection: Any) -> dict[str, Any] | None:
    """Build host_experience_template dict for GoC graph input, or None."""
    if not isinstance(runtime_projection, dict):
        return None
    tid = runtime_projection.get("experience_template_id") or runtime_projection.get("seed_template_id")
    tit = runtime_projection.get("experience_template_title")
    if tid is None and tit is None:
        return None
    return {
        "template_id": str(tid) if tid is not None else None,
        "title": str(tit) if tit is not None else None,
    }


def goc_prior_continuity_for_graph(session_module_id: str, session_prior: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Return prior continuity list for turn_graph when module is GoC, else None."""
    if session_module_id != GOD_OF_CARNAGE_MODULE_ID:
        return None
    return session_prior


def goc_append_continuity_impacts(
    session_module_id: str,
    prior: list[dict[str, Any]],
    graph_state: dict[str, Any],
    *,
    max_tail: int = 12,
) -> None:
    """Append continuity impacts from graph_state into ``prior``, then bound length (GoC only)."""
    if session_module_id != GOD_OF_CARNAGE_MODULE_ID:
        return
    ci = graph_state.get("continuity_impacts")
    if not isinstance(ci, list):
        return
    for item in ci:
        if isinstance(item, dict):
            prior.append(item)
    if len(prior) > max_tail:
        prior[:] = prior[-max_tail:]
