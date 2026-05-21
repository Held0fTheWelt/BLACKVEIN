"""Projection section builder for `narrative_momentum`."""

from __future__ import annotations

from typing import Any

from ...projection_helpers import _record_reasons

BUILD_NARRATIVE_MOMENTUM_SECTION_PARAMS = (
    "narrative_momentum_actual",
    "narrative_momentum_expected",
    "narrative_momentum_rec",
    "narrative_momentum_selected",
)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_narrative_momentum_section(**values: Any) -> dict[str, Any]:
    narrative_momentum_actual = values['narrative_momentum_actual']
    narrative_momentum_expected = values['narrative_momentum_expected']
    narrative_momentum_rec = values['narrative_momentum_rec']
    narrative_momentum_selected = values['narrative_momentum_selected']
    reasons = _record_reasons(narrative_momentum_rec)
    selected_state = _dict_or_empty(narrative_momentum_selected.get("state"))
    selected_target = _dict_or_empty(narrative_momentum_selected.get("target"))
    return {
        "schema_version": narrative_momentum_expected.get("schema_version")
        or narrative_momentum_selected.get("schema_version")
        or narrative_momentum_actual.get("schema_version"),
        "policy_present": bool(narrative_momentum_expected.get("policy_present")),
        "policy_enabled": bool(narrative_momentum_expected.get("policy_enabled")),
        "commit_impact": narrative_momentum_expected.get("commit_impact"),
        "require_structured_events": bool(narrative_momentum_expected.get("require_structured_events")),
        "target_state": narrative_momentum_selected.get("target_state")
        or selected_target.get("target_state")
        or narrative_momentum_actual.get("target_state"),
        "target_score": float(
            narrative_momentum_selected.get("target_score")
            or selected_target.get("target_score")
            or narrative_momentum_actual.get("target_score")
            or 0.0
        ),
        "current_state": narrative_momentum_actual.get("current_state")
        or selected_state.get("current_state"),
        "current_score": float(
            narrative_momentum_actual.get("current_score")
            or selected_state.get("current_score")
            or 0.0
        ),
        "trend": narrative_momentum_actual.get("trend") or selected_state.get("trend"),
        "velocity": float(narrative_momentum_actual.get("velocity") or 0.0),
        "allowed_next_states": narrative_momentum_selected.get("allowed_next_states")
        or selected_target.get("allowed_next_states")
        or [],
        "requires_forward_motion": bool(
            narrative_momentum_selected.get("requires_forward_motion")
            or selected_target.get("requires_forward_motion")
        ),
        "release_allowed": bool(
            narrative_momentum_selected.get("release_allowed")
            or selected_target.get("release_allowed")
        ),
        "transition_allowed": narrative_momentum_actual.get("transition_allowed"),
        "structured_events_present": bool(narrative_momentum_actual.get("structured_events_present")),
        "event_count": int(narrative_momentum_actual.get("event_count") or 0),
        "progress_event_count": int(narrative_momentum_actual.get("progress_event_count") or 0),
        "stall_turn_count": int(narrative_momentum_actual.get("stall_turn_count") or 0),
        "stall_budget_respected": narrative_momentum_actual.get("stall_budget_respected"),
        "source_refs_valid": narrative_momentum_actual.get("source_refs_valid"),
        "contract_pass": narrative_momentum_actual.get("contract_pass"),
        "failure_codes": narrative_momentum_actual.get("failure_codes") or reasons,
        "failure_reason": narrative_momentum_rec.get("failure_reason") or (reasons[0] if reasons else None),
        "status": narrative_momentum_rec.get("status"),
    }
