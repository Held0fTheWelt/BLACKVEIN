"""Conflict-Panel-Helfer (DS-046) — flache Extraktion aus ``build_conflict_panel_from_session``."""

from __future__ import annotations

from typing import Any

from app.runtime.runtime_models import SessionState
from app.runtime.scene_presenter import ConflictTrendSignal


def resolve_conflict_pressure(session_state: SessionState) -> Any:
    current_pressure = None
    if session_state.context_layers and session_state.context_layers.short_term_context:
        current_pressure = session_state.context_layers.short_term_context.conflict_pressure
    if current_pressure is None and session_state.canonical_state:
        conflict_state = session_state.canonical_state.get("conflict_state", {})
        if isinstance(conflict_state, dict):
            current_pressure = conflict_state.get("pressure")
    return current_pressure


def pressure_to_escalation_status(current_pressure: Any) -> str:
    if current_pressure is None:
        return "unknown"
    if current_pressure <= 33:
        return "low"
    if current_pressure <= 66:
        return "medium"
    return "high"


def build_recent_trend_signal(session_state: SessionState) -> ConflictTrendSignal | None:
    if not session_state.context_layers:
        return None
    if not (
        session_state.context_layers.progression_summary or session_state.context_layers.relationship_axis_context
    ):
        return None
    signal = None
    source_basis: list[str] = []

    if session_state.context_layers.progression_summary:
        outcomes = session_state.context_layers.progression_summary.most_recent_guard_outcomes
        if outcomes:
            rejections = outcomes.count("rejected")
            acceptances = outcomes.count("accepted")
            if rejections > acceptances:
                signal = "escalating"
                source_basis.append("guard_outcomes")

    if session_state.context_layers.relationship_axis_context:
        rel_ctx = session_state.context_layers.relationship_axis_context
        if rel_ctx.has_escalation_markers:
            if signal != "escalating":
                signal = "escalating"
            source_basis.append("relationship_tension")
        elif signal is None:
            if rel_ctx.overall_stability_signal == "de-escalating":
                signal = "de-escalating"
                source_basis.append("stability_signal")
            elif rel_ctx.overall_stability_signal == "stable":
                signal = "stable"
                source_basis.append("stability_signal")

    if signal is None:
        signal = "uncertain"
    if not source_basis and signal == "uncertain":
        return None
    return ConflictTrendSignal(signal=signal, source_basis=source_basis)


def resolve_turning_point_risk(session_state: SessionState) -> bool | None:
    if not session_state.context_layers or not session_state.context_layers.relationship_axis_context:
        return None
    return session_state.context_layers.relationship_axis_context.has_escalation_markers
