"""W3.5.1 Debug Panel Presenter.

Transforms session diagnostics (ShortTermTurnContext, SessionHistory, DegradedSessionState)
into a bounded, presenter-ready output for UI rendering.

Presenter Function:
    present_debug_panel(session_state: SessionState) -> DebugPanelOutput

Output Model:
    DebugPanelOutput
    - primary_diagnostic: Latest turn diagnostics (from ShortTermTurnContext)
      - summary: Turn health (guard outcome, scene info, triggers, pressure)
      - detailed: Delta target counts and samples
    - recent_pattern_context: Last 3-5 turn patterns (from SessionHistory)
    - degradation_markers: Active recovery markers (from DegradedSessionState)

Canonical Sources:
    - Latest turn: ShortTermTurnContext (W2.3.1)
    - Recent turns: SessionHistory.HistoryEntry (W2.3.2)
    - Degradation: DegradedSessionState (W2.5.7)

Determinism & Graceful Degradation:
    - Pure function: no side effects, no randomness
    - Deterministic filtering/sorting by turn_number and created_at
    - Graceful: returns valid output with empty/None fields if data missing

Limitations (W3.5.1):
    - Does not include TurnExecutionResult fields (validation, failure reasons, timing)
    - Does not include AIDecisionLog fields (raw output, role diagnostics, notes)
    - Those require separate persistence design (W3.5.2+)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.runtime_models import SessionState, DegradedMarker


class DebugSummarySection(BaseModel):
    """Summary diagnostics for latest turn derived from ShortTermTurnContext."""

    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str] = Field(default_factory=list)
    scene_changed: bool
    prior_scene_id: Optional[str] = None
    ending_reached: bool
    ending_id: Optional[str] = None
    conflict_pressure: Optional[float] = None
    created_at: datetime


class DebugDetailedSection(BaseModel):
    """Detailed diagnostics for latest turn derived from ShortTermTurnContext."""

    accepted_delta_target_count: int
    rejected_delta_target_count: int
    sample_accepted_targets: list[str] = Field(default_factory=list)
    sample_rejected_targets: list[str] = Field(default_factory=list)


class PrimaryDiagnosticOutput(BaseModel):
    """Typed wrapper for primary (latest turn) diagnostics."""

    summary: DebugSummarySection
    detailed: DebugDetailedSection


class RecentPatternIndicator(BaseModel):
    """Compressed pattern from recent turn derived from HistoryEntry."""

    turn_number: int
    guard_outcome: str
    scene_id: str
    scene_changed: bool
    ending_reached: bool


class DebugPanelOutput(BaseModel):
    """Complete debug panel presenter output, ready for template rendering."""

    primary_diagnostic: PrimaryDiagnosticOutput
    recent_pattern_context: list[RecentPatternIndicator]  # last 3-5 turns
    degradation_markers: list[str]  # active DegradedSessionState markers
    full_diagnostics: dict | None = None  # W3 closure: full LLM pipeline visibility


def present_debug_panel(session_state: SessionState) -> DebugPanelOutput:
    """
    Derive bounded diagnostic view from session's latest ShortTermTurnContext and recent HistoryEntry records.

    Targets the latest turn (from ShortTermTurnContext) as primary diagnostic object.
    Includes recent-pattern context from last 3-5 HistoryEntry records (from SessionHistory).

    Args:
        session_state: Current SessionState with context_layers.short_term_context,
                      context_layers.session_history, and degraded_state

    Returns:
        DebugPanelOutput with primary_diagnostic (latest) + recent_pattern_context + degradation_markers

    Determinism:
        - No randomness, no side effects
        - Filtering deterministic (by turn_number, by created_at)
        - Graceful degradation: returns valid output with None values if data missing

    Limitation (W3.5.1):
        - Does not include TurnExecutionResult fields (validation outcomes, failure reasons, timing)
        - Does not include AIDecisionLog fields (raw output, role diagnostics, guard notes)
        - TurnExecutionResult and AIDecisionLog are not persisted in SessionState
        - Deferred to W3.5.2 pending storage design for richer diagnostics
    """
    from app.runtime import debug_presenter_sections as dps

    short_term = session_state.context_layers.short_term_context
    history = session_state.context_layers.session_history
    degraded_state = session_state.degraded_state
    degradation_markers = dps.degradation_marker_values(session_state)

    if not short_term:
        return dps.empty_short_term_panel_output(session_state, degradation_markers)

    primary = dps.primary_diagnostic_from_short_term(short_term)
    recent_pattern = dps.recent_pattern_from_history(history)
    full_diagnostics = dps.full_diagnostics_from_short_term(short_term, degraded_state)

    return DebugPanelOutput(
        primary_diagnostic=primary,
        recent_pattern_context=recent_pattern,
        degradation_markers=degradation_markers,
        full_diagnostics=full_diagnostics,
    )
