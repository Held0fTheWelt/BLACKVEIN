"""Semantic capability and validator-plan projections for ledger consumers.

This module translates turn context into the semantic capability selection,
validator execution plan, and dry-run dispatch report shown in runtime
intelligence diagnostics.
"""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities.capability_selector import (
    CapabilitySelectionResult,
    LastTurnQuality,
    TurnKind,
    TurnSituation,
    derive_turn_situation_from_runtime_context,
    select_capabilities,
    validate_semantic_capability_name,
)
from ai_stack.capabilities.capability_validator_dispatch import (
    ValidatorDispatchMode,
    build_validator_dispatch_report,
    resolve_validator_dispatch_mode,
)
from ai_stack.capabilities.capability_validator_plan import ValidatorExecutionPlan, build_validator_execution_plan
from ai_stack.capabilities.capability_validator_registry import (
    VALIDATOR_REGISTRY_INVENTORY,
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    build_available_semantic_validator_registry,
)

from .constants import *  # Shared aspect names and ADR schema constants.
from .feature_flags import resolve_adr0041_plan_projection_enabled
from .projection_helpers import _record_block, _record_nested_value, _record_reasons
from .records import _json_safe

def build_semantic_capability_selection_projection(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 local selector evidence for runtime intelligence projection."""
    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    payload = selection_result.to_runtime_aspect_projection()[
        ASPECT_CAPABILITY_SELECTION
    ]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)
def build_semantic_validator_execution_plan_projection(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 local validator-plan evidence for runtime projection."""
    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    payload = build_validator_execution_plan(selection_result).to_runtime_projection()[
        "validator_execution_plan"
    ]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)
def build_semantic_validator_dispatch_report_projection(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
    dispatch_mode: ValidatorDispatchMode | str | None = None,
) -> dict[str, Any]:
    """Build ADR-0041 dry-run dispatch evidence for runtime intelligence projection."""
    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    execution_plan = build_validator_execution_plan(selection_result)
    resolved_mode, mode_warnings = resolve_validator_dispatch_mode(explicit_mode=dispatch_mode)
    payload = build_validator_dispatch_report(
        execution_plan,
        mode=resolved_mode,
        feature_flag_enabled=resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED,
    ).to_runtime_projection()["validator_dispatch_report"]
    warnings = [
        *(
            payload.get("warnings")
            if isinstance(payload.get("warnings"), list)
            else []
        ),
        *mode_warnings,
        *derivation_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)
def _select_semantic_capabilities_from_runtime_context(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> tuple[Any, tuple[str, ...]]:
    situation, derivation_warnings = derive_turn_situation_from_runtime_context(
        turn_kind=turn_kind,
        turn_number=turn_number,
        raw_player_input=raw_player_input,
        input_kind=input_kind,
        active_actor=active_actor,
        npc_decision_required=npc_decision_required,
        action_resolution_required=action_resolution_required,
        visible_projection_required=visible_projection_required,
        canonical_scene_seed=canonical_scene_seed,
        non_lexical_input_present=non_lexical_input_present,
        knowledge_gap_present=knowledge_gap_present,
        world_state_change_requested=world_state_change_requested,
    )
    return select_capabilities(situation), derivation_warnings
def _infer_adr0041_turn_class_from_situation(situation: TurnSituation) -> tuple[str, dict[str, Any]]:
    """Map selector TurnSituation to ADR-0041 drift-guard turn class labels."""
    tk = situation.turn_kind
    tk_val = tk.value if isinstance(tk, TurnKind) else str(tk)
    hints: dict[str, Any] = {
        "situation_turn_kind": tk_val,
        "npc_decision_required": bool(situation.npc_decision_required),
        "player_input_present": bool(situation.player_input_present),
        "last_turn_quality": (
            situation.last_turn_quality.value
            if isinstance(situation.last_turn_quality, LastTurnQuality)
            else str(situation.last_turn_quality)
        ),
    }
    if tk is TurnKind.OPENING:
        return TURN_CLASS_OPENING_SCENE, hints
    if tk is TurnKind.NPC_TURN and situation.npc_decision_required:
        return TURN_CLASS_NPC_CONFLICT_TURN, hints
    if tk is TurnKind.PLAYER_INPUT:
        return TURN_CLASS_NORMAL_PLAYER_TURN, hints
    if tk is TurnKind.RECOVERY:
        if situation.last_turn_quality is LastTurnQuality.FALLBACK:
            return TURN_CLASS_DEGRADED_OR_FALLBACK_TURN, hints
        return TURN_CLASS_RECOVERY_TURN, hints
    if tk is TurnKind.SYSTEM_TRANSITION:
        return TURN_CLASS_SYSTEM_TRANSITION, hints
    if situation.last_turn_quality is LastTurnQuality.FALLBACK:
        return TURN_CLASS_DEGRADED_OR_FALLBACK_TURN, hints
    return TURN_CLASS_SYSTEM_TRANSITION, hints
def _build_adr0041_plan_projection_sibling(
    *,
    selection_result: CapabilitySelectionResult,
    execution_plan: ValidatorExecutionPlan,
    dispatch_report: dict[str, Any],
    flag_warnings: tuple[str, ...],
    derivation_warnings: tuple[str, ...],
) -> dict[str, Any]:
    """Sibling projection-only envelope (never executes validators or seams)."""
    situation = selection_result.situation
    turn_class_key, turn_class_hints = _infer_adr0041_turn_class_from_situation(situation)

    avail = build_available_semantic_validator_registry()
    avail_keys = frozenset(avail.keys())
    inventory_safe = {
        row.validator_id: row.safe_for_local_plan_enforced for row in VALIDATOR_REGISTRY_INVENTORY
    }

    planned_validators = list(execution_plan.validators_to_run)
    planned_observers = list(execution_plan.observer_diagnostics)

    would_execute_local_sorted = sorted(vid for vid in planned_validators if vid in avail_keys)
    blocked_missing_registry_sorted = sorted(vid for vid in planned_validators if vid not in avail_keys)
    inventory_marked_unsafe = sorted(
        vid for vid in planned_validators if vid in inventory_safe and not inventory_safe[vid]
    )

    registry_availability: dict[str, dict[str, Any]] = {}
    for vid in sorted(set(planned_validators) | set(planned_observers)):
        registry_availability[vid] = {
            "adapter_registered_for_local_dispatch": vid in avail_keys,
            "inventory_marks_safe_for_local_plan_enforced": bool(inventory_safe.get(vid)),
        }

    consciously_not_executed = {
        "validators_skipped_by_plan_budget_or_exclusion": list(dispatch_report.get("validators_would_skip") or []),
        "judges_disallowed_by_plan": list(dispatch_report.get("judges_would_be_disallowed") or []),
        "observer_diagnostics_planned_only_non_blocking": list(dispatch_report.get("diagnostics_would_run") or []),
        "note": (
            "Dry-run projection does not invoke validators or judges; skipped/disallowed rows reflect "
            "plan semantics only."
        ),
    }

    drift = {
        "production_validation_seam_symbol": GOC_TURN_VALIDATION_SEAM_SYMBOL,
        "adr0041_dispatch_projection_symbol": (
            "ai_stack.story_runtime.runtime_aspect_ledger.build_semantic_validator_dispatch_report_projection"
        ),
        "relationship_note": (
            "run_validation_seam enforces GoC proposal seams (actor lane, transcript shell caps, "
            "hard-forbidden runtime, opening coverage, dramatic-effect gate). ADR-0041 plan projection "
            "enumerates semantic capability-linked validator contracts for local planning only; it does not "
            "replace or reorder run_validation_seam."
        ),
        "validation_seam_contract_surfaces": [
            "actor_lane_human_ai_boundary",
            "npc_lane_transcript_shell_blob_cap",
            "authoritative_action_resolution_surface_waiver",
            "non_goc_module_vertical_slice_waiver",
            "generation_success_gate",
            "proposal_effect_wellformedness_gate",
            "hard_forbidden_runtime_detection",
            "opening_event_coverage_gate",
            "dramatic_effect_gate",
        ],
        "adr0041_planned_local_validator_contract_ids": planned_validators,
    }

    dr_warnings_list = dispatch_report.get("warnings")
    dispatch_warnings: tuple[str, ...] = ()
    if isinstance(dr_warnings_list, list):
        dispatch_warnings = tuple(str(item).strip() for item in dr_warnings_list if str(item).strip())

    warn_seen: list[str] = []
    for bucket in (
        flag_warnings,
        derivation_warnings,
        dispatch_warnings,
        execution_plan.warnings,
        selection_result.warnings,
    ):
        for w in bucket:
            text = str(w).strip()
            if text and text not in warn_seen:
                warn_seen.append(text)

    payload: dict[str, Any] = {
        "schema_version": ADR0041_PLAN_PROJECTION_SCHEMA_VERSION,
        "adr0041_plan_projection_enabled": True,
        "proof_level": "local_only",
        "evidence_scope": dispatch_report.get("evidence_scope"),
        "live_or_staging_evidence": False,
        "execution_changed": False,
        "actually_executed": [],
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "judge_execution_changed": False,
        "selected_turn_class": turn_class_key,
        "turn_class_hints": turn_class_hints,
        "capabilities": {
            "enforced": list(selection_result.enforced),
            "observed": list(selection_result.observed),
            "excluded": list(selection_result.excluded),
            "judged": list(selection_result.judged),
        },
        "planned_local_validator_ids": planned_validators,
        "planned_observer_diagnostic_ids": planned_observers,
        "registry_availability_by_id": registry_availability,
        "would_execute_local_validators_if_plan_enforced_with_inventory_adapters": would_execute_local_sorted,
        "validators_unavailable_per_dispatch_report": list(dispatch_report.get("validators_unavailable") or []),
        "unavailable_local_adapters_for_planned_validators": blocked_missing_registry_sorted,
        "blocked_by_missing_registry_or_context": blocked_missing_registry_sorted,
        "inventory_marks_unsafe_for_local_plan_enforced": inventory_marked_unsafe,
        "consciously_not_executed": consciously_not_executed,
        "validator_dispatch_report_echo": {
            "mode": dispatch_report.get("mode"),
            "execution_changed": dispatch_report.get("execution_changed"),
            "actually_executed": dispatch_report.get("actually_executed"),
            "feature_flag_enabled": dispatch_report.get("feature_flag_enabled"),
        },
        "seam_vs_plan_projection_drift_visibility": drift,
        "warnings": warn_seen,
    }
    return _json_safe(payload)
