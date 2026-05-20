"""Shared AI turn recovery state mutations.

Kept separate from recovery path orchestration so fallback helpers can reuse
decision-log and degraded-marker writes without forming import cycles.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.runtime.runtime_models import AIDecisionLog, DegradedMarker, SessionState


def store_decision_log(session: SessionState, log: AIDecisionLog) -> None:
    if "ai_decision_logs" not in session.metadata:
        session.metadata["ai_decision_logs"] = []
    session.metadata["ai_decision_logs"].append(log)


def activate_degraded_marker(session: SessionState, marker: DegradedMarker) -> None:
    if marker not in session.degraded_state.active_markers:
        session.degraded_state.active_markers.add(marker)
        session.degraded_state.marker_timestamps[marker] = datetime.now(timezone.utc)
    if not session.degraded_state.is_degraded:
        session.degraded_state.is_degraded = True
        session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = datetime.now(timezone.utc)
