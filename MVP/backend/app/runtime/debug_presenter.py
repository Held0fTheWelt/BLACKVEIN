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
    # Get latest turn context and history
    short_term = session_state.context_layers.short_term_context
    history = session_state.context_layers.session_history
    degraded_state = session_state.degraded_state

    # Extract degradation markers
    degradation_markers = (
        [marker.value for marker in degraded_state.active_markers]
        if degraded_state and degraded_state.active_markers
        else []
    )

    # If no short_term_context, return minimal valid output
    if not short_term:
        primary = PrimaryDiagnosticOutput(
            summary=DebugSummarySection(
                turn_number=0,
                scene_id=session_state.current_scene_id,
                guard_outcome="unknown",
                scene_changed=False,
                ending_reached=False,
                created_at=datetime.now(),
            ),
            detailed=DebugDetailedSection(
                accepted_delta_target_count=0,
                rejected_delta_target_count=0,
            ),
        )
        return DebugPanelOutput(
            primary_diagnostic=primary,
            recent_pattern_context=[],
            degradation_markers=degradation_markers,
            full_diagnostics=None,  # No short_term_context, so no full diagnostics
        )

    # Build primary diagnostic from short_term_context
    accepted_targets = (
        short_term.accepted_delta_targets
        if hasattr(short_term, "accepted_delta_targets")
        else []
    )
    rejected_targets = (
        short_term.rejected_delta_targets
        if hasattr(short_term, "rejected_delta_targets")
        else []
    )

    primary = PrimaryDiagnosticOutput(
        summary=DebugSummarySection(
            turn_number=short_term.turn_number,
            scene_id=short_term.scene_id,
            guard_outcome=short_term.guard_outcome,
            detected_triggers=short_term.detected_triggers or [],
            scene_changed=short_term.scene_changed,
            prior_scene_id=short_term.prior_scene_id,
            ending_reached=short_term.ending_reached,
            ending_id=short_term.ending_id,
            conflict_pressure=getattr(short_term, "conflict_pressure", None),
            created_at=short_term.created_at,
        ),
        detailed=DebugDetailedSection(
            accepted_delta_target_count=len(accepted_targets),
            rejected_delta_target_count=len(rejected_targets),
            sample_accepted_targets=accepted_targets[:3],
            sample_rejected_targets=rejected_targets[:3],
        ),
    )

    # Extract recent pattern context (last 3-5 turns from history)
    recent_pattern = []
    if history and history.entries:
        # Get last 5 entries (or fewer if not available)
        entries_to_use = (
            history.entries[-5:] if len(history.entries) >= 5 else history.entries
        )
        recent_pattern = [
            RecentPatternIndicator(
                turn_number=entry.turn_number,
                guard_outcome=entry.guard_outcome,
                scene_id=entry.scene_id,
                scene_changed=entry.scene_changed,
                ending_reached=entry.ending_reached,
            )
            for entry in entries_to_use
        ]

    # Build full diagnostics from short_term_context (W3 closure)
    full_diagnostics = None
    if short_term and hasattr(short_term, 'execution_result_full'):
        execution_result = getattr(short_term, 'execution_result_full', None)
        ai_log = getattr(short_term, 'ai_decision_log_full', None)

        full_diagnostics = {
            "raw_llm_output": ai_log.get("raw_output") if isinstance(ai_log, dict) else None,
            "parsed_output": ai_log.get("parsed_output") if isinstance(ai_log, dict) else None,
            "role_diagnostics": {
                "interpreter": ai_log.get("interpreter_output") if isinstance(ai_log, dict) else None,
                "director": ai_log.get("director_output") if isinstance(ai_log, dict) else None,
                "responder": ai_log.get("responder_output") if isinstance(ai_log, dict) else None
            } if ai_log else None,
            "validation_errors": execution_result.get("validation_errors", [])[:5] if isinstance(execution_result, dict) else [],
            "recovery_action": None,
            "tool_loop_summary": ai_log.get("tool_loop_summary") if isinstance(ai_log, dict) else None,
            "tool_call_transcript": (
                ai_log.get("tool_call_transcript", [])[:10] if isinstance(ai_log, dict) else []
            ),
            "tool_influence": ai_log.get("tool_influence") if isinstance(ai_log, dict) else None,
            "preview_diagnostics": ai_log.get("preview_diagnostics") if isinstance(ai_log, dict) else None,
            "supervisor_plan": ai_log.get("supervisor_plan") if isinstance(ai_log, dict) else None,
            "subagent_invocations": (
                ai_log.get("subagent_invocations", [])[:8] if isinstance(ai_log, dict) else []
            ),
            "subagent_results": (
                ai_log.get("subagent_results", [])[:8] if isinstance(ai_log, dict) else []
            ),
            "merge_finalization": (
                ai_log.get("merge_finalization") if isinstance(ai_log, dict) else None
            ),
            "orchestration_budget_summary": (
                ai_log.get("orchestration_budget_summary")
                if isinstance(ai_log, dict)
                else None
            ),
            "agent_budget_status": (
                ai_log.get("subagent_invocations", [])[:8]
                if isinstance(ai_log, dict)
                else []
            ),
            "failover_degradation": (
                ai_log.get("orchestration_failover", [])[:10]
                if isinstance(ai_log, dict)
                else []
            ),
            "cache_usage": (
                ai_log.get("orchestration_cache")
                if isinstance(ai_log, dict)
                else None
            ),
            "tool_audit": (
                ai_log.get("tool_audit", [])[:12]
                if isinstance(ai_log, dict)
                else []
            ),
        }

        # Infer recovery action from degradation markers
        if degraded_state and degraded_state.active_markers:
            markers = [m.value if hasattr(m, 'value') else str(m) for m in degraded_state.active_markers]
            if "FALLBACK_ACTIVE" in markers:
                full_diagnostics["recovery_action"] = "fallback_responder_used"
            elif "REDUCED_CONTEXT_ACTIVE" in markers:
                full_diagnostics["recovery_action"] = "reduced_context_retry"
            elif "RETRY_EXHAUSTED" in markers:
                full_diagnostics["recovery_action"] = "retries_exhausted_fallback"

    return DebugPanelOutput(
        primary_diagnostic=primary,
        recent_pattern_context=recent_pattern,
        degradation_markers=degradation_markers,
        full_diagnostics=full_diagnostics,
    )
