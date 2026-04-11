"""Conflict panel mapping steps (DS-035) — extracted from ``scene_presenter``."""

from __future__ import annotations

from app.runtime.runtime_models import SessionState
from app.runtime.scene_presenter import ConflictPanelOutput
from app.runtime.scene_presenter_conflict_helpers import (
    build_recent_trend_signal,
    pressure_to_escalation_status,
    resolve_conflict_pressure,
    resolve_turning_point_risk,
)


def build_conflict_panel_from_session(session_state: SessionState) -> ConflictPanelOutput:
    """Map canonical session data to conflict panel output (implementation body)."""
    current_pressure = resolve_conflict_pressure(session_state)
    current_escalation_status = pressure_to_escalation_status(current_pressure)
    recent_trend = build_recent_trend_signal(session_state)
    turning_point_risk = resolve_turning_point_risk(session_state)
    return ConflictPanelOutput(
        current_pressure=current_pressure,
        current_escalation_status=current_escalation_status,
        recent_trend=recent_trend,
        turning_point_risk=turning_point_risk,
    )
