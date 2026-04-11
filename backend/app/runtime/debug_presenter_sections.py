"""Section builders for ``present_debug_panel`` (debug_presenter.py)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.runtime.debug_presenter import (
    DebugDetailedSection,
    DebugPanelOutput,
    DebugSummarySection,
    PrimaryDiagnosticOutput,
    RecentPatternIndicator,
)
from app.runtime.runtime_models import SessionState


def degradation_marker_values(session_state: SessionState) -> list[str]:
    degraded_state = session_state.degraded_state
    if degraded_state and degraded_state.active_markers:
        return [marker.value for marker in degraded_state.active_markers]
    return []


def empty_short_term_panel_output(
    session_state: SessionState, degradation_markers: list[str]
) -> DebugPanelOutput:
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
        full_diagnostics=None,
    )


def primary_diagnostic_from_short_term(short_term: Any) -> PrimaryDiagnosticOutput:
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
    return PrimaryDiagnosticOutput(
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


def recent_pattern_from_history(history: Any) -> list[RecentPatternIndicator]:
    if not history or not history.entries:
        return []
    entries_to_use = (
        history.entries[-5:] if len(history.entries) >= 5 else history.entries
    )
    return [
        RecentPatternIndicator(
            turn_number=entry.turn_number,
            guard_outcome=entry.guard_outcome,
            scene_id=entry.scene_id,
            scene_changed=entry.scene_changed,
            ending_reached=entry.ending_reached,
        )
        for entry in entries_to_use
    ]


def full_diagnostics_from_short_term(
    short_term: Any, degraded_state: Any
) -> dict[str, Any] | None:
    if not short_term or not hasattr(short_term, "execution_result_full"):
        return None
    execution_result = getattr(short_term, "execution_result_full", None)
    ai_log = getattr(short_term, "ai_decision_log_full", None)

    full_diagnostics: dict[str, Any] = {
        "raw_llm_output": ai_log.get("raw_output") if isinstance(ai_log, dict) else None,
        "parsed_output": ai_log.get("parsed_output") if isinstance(ai_log, dict) else None,
        "role_diagnostics": {
            "interpreter": ai_log.get("interpreter_output") if isinstance(ai_log, dict) else None,
            "director": ai_log.get("director_output") if isinstance(ai_log, dict) else None,
            "responder": ai_log.get("responder_output") if isinstance(ai_log, dict) else None,
        }
        if ai_log
        else None,
        "validation_errors": execution_result.get("validation_errors", [])[:5]
        if isinstance(execution_result, dict)
        else [],
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
            ai_log.get("orchestration_budget_summary") if isinstance(ai_log, dict) else None
        ),
        "agent_budget_status": (
            ai_log.get("subagent_invocations", [])[:8] if isinstance(ai_log, dict) else []
        ),
        "failover_degradation": (
            ai_log.get("orchestration_failover", [])[:10] if isinstance(ai_log, dict) else []
        ),
        "cache_usage": (
            ai_log.get("orchestration_cache") if isinstance(ai_log, dict) else None
        ),
        "tool_audit": (
            ai_log.get("tool_audit", [])[:12] if isinstance(ai_log, dict) else []
        ),
    }

    if degraded_state and degraded_state.active_markers:
        markers = [
            m.value if hasattr(m, "value") else str(m) for m in degraded_state.active_markers
        ]
        if "FALLBACK_ACTIVE" in markers:
            full_diagnostics["recovery_action"] = "fallback_responder_used"
        elif "REDUCED_CONTEXT_ACTIVE" in markers:
            full_diagnostics["recovery_action"] = "reduced_context_retry"
        elif "RETRY_EXHAUSTED" in markers:
            full_diagnostics["recovery_action"] = "retries_exhausted_fallback"

    return full_diagnostics
