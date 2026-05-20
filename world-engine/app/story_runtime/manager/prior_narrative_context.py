from __future__ import annotations

from ._deps import *

def _prior_narrative_momentum_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed narrative-momentum state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("narrative_momentum_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_genre_awareness_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed genre-awareness state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("genre_awareness_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_symbolic_object_resonance_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed symbolic-object-resonance state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("symbolic_object_resonance_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None

def _prior_narrative_thread_state_from_session(
    session: "StorySession",
    *,
    graph_threads: list[dict[str, Any]] | None,
    graph_summary: str | None,
) -> dict[str, Any] | None:
    """Project committed session thread continuity into graph director input."""
    metrics = thread_continuity_metrics(session.narrative_threads)
    if metrics.get("thread_count", 0) <= 0 and not graph_summary and not graph_threads:
        return None
    return {
        "feedback_contract": "narrative_thread_feedback.v1",
        "source": "session.narrative_threads",
        "thread_count": metrics.get("thread_count", 0),
        "dominant_thread_kind": metrics.get("dominant_thread_kind"),
        "thread_pressure_level": metrics.get("thread_pressure_level", 0),
        "thread_pressure_summary": graph_summary or "",
        "active_threads": list(graph_threads or []),
    }

def _compact_context_str(value: Any, *, max_chars: int = 220) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if not text:
        return None
    return text[:max_chars].rstrip()

def _compact_context_list(value: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _compact_context_str(str(item), max_chars=80)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
