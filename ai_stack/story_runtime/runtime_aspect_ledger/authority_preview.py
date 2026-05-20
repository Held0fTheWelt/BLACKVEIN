"""ADR-0041 validation-authority projections and dispatch sidecars.

These routines compare the canonical validation seam with ADR-0041 validator
plans. They expose drift, preview, and plan-enforced runtime sidecars without
turning the sidecar into commit authority.
"""

from __future__ import annotations

from typing import Any, Callable

from ai_stack.capabilities.capability_selector import validate_semantic_capability_name
from ai_stack.capabilities.capability_validator_dispatch import (
    ValidatorDispatchMode,
    ValidatorRegistry,
    build_validator_dispatch_report,
    resolve_validator_dispatch_mode,
)
from ai_stack.capabilities.capability_validator_plan import (
    build_validator_execution_plan,
    prepend_goc_seam_mirror_plan_entries,
)
from ai_stack.capabilities.capability_validator_registry import (
    TURN_CLASS_DEGRADED_OR_FALLBACK_TURN,
    TURN_CLASS_NPC_CONFLICT_TURN,
    TURN_CLASS_NORMAL_PLAYER_TURN,
    TURN_CLASS_OPENING_SCENE,
    TURN_CLASS_RECOVERY_TURN,
    TURN_CLASS_SYSTEM_TRANSITION,
    build_degraded_or_fallback_enforced_semantic_validator_registry,
    build_npc_conflict_enforced_semantic_validator_registry,
    build_opening_enforced_semantic_validator_registry,
    build_player_turn_enforced_semantic_validator_registry,
    build_recovery_turn_enforced_semantic_validator_registry,
    build_system_transition_enforced_semantic_validator_registry,
    goc_seam_mirror_plan_validator_ids_for_turn_class,
)
from ai_stack.story_runtime.turn.validation_authority_bridge import (
    build_readiness_aggregation_decision,
    build_readiness_co_authority_enforcement,
    build_readiness_co_authority_preview,
    build_validation_authority_bridge,
    build_validation_co_authority_decision,
)

from .capability_projection import (
    _infer_adr0041_turn_class_from_situation,
    _select_semantic_capabilities_from_runtime_context,
    build_semantic_validator_dispatch_report_projection,
)
from .constants import (
    ADR0041_DRIFT_ADR_STRICTER,
    ADR0041_DRIFT_ALIGNED,
    ADR0041_DRIFT_CONFLICTING_RESULT,
    ADR0041_DRIFT_MISSING_CONTEXT,
    ADR0041_DRIFT_SEAM_STRICTER,
    ADR0041_DRIFT_UNAVAILABLE_VALIDATOR,
    ADR0041_HARNESS_PLAN_ENFORCED_REQUIRES_REGISTRY_WARNING,
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
    ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
    GOC_TURN_VALIDATION_SEAM_SYMBOL,
)
from .feature_flags import (
    resolve_adr0041_readiness_co_authority_preview_enabled,
    resolve_adr0041_scoped_co_authority_enabled,
    resolve_adr0041_scoped_readiness_aggregation_enabled,
    resolve_adr0041_scoped_readiness_enforcement_enabled,
)
from .records import _json_safe

def adr0041_validator_registry_for_turn_class(turn_class_key: str) -> dict[str, Any]:
    """Return semantic validator callables scoped to one ADR-0041 turn class."""
    key = str(turn_class_key or "").strip()
    if key == TURN_CLASS_OPENING_SCENE:
        return dict(build_opening_enforced_semantic_validator_registry())
    if key == TURN_CLASS_NORMAL_PLAYER_TURN:
        return dict(build_player_turn_enforced_semantic_validator_registry())
    if key == TURN_CLASS_NPC_CONFLICT_TURN:
        return dict(build_npc_conflict_enforced_semantic_validator_registry())
    if key == TURN_CLASS_RECOVERY_TURN:
        return dict(build_recovery_turn_enforced_semantic_validator_registry())
    if key == TURN_CLASS_SYSTEM_TRANSITION:
        return dict(build_system_transition_enforced_semantic_validator_registry())
    if key == TURN_CLASS_DEGRADED_OR_FALLBACK_TURN:
        return dict(build_degraded_or_fallback_enforced_semantic_validator_registry())
    return {}
def classify_adr0041_validation_authority_drift(
    *,
    validator_dispatch_report: dict[str, Any],
    validation_seam_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify disagreement between ``run_validation_seam`` and ADR-0041 local enforcement."""
    would_run_raw = list(validator_dispatch_report.get("validators_would_run") or [])
    would_run: list[str] = []
    for item in would_run_raw:
        text = str(item or "").strip()
        if not text:
            continue
        would_run.append(validate_semantic_capability_name(text))
    would_run_set = frozenset(would_run)

    unavailable_raw = list(validator_dispatch_report.get("validators_unavailable") or [])
    unavailable: set[str] = set()
    for item in unavailable_raw:
        text = str(item or "").strip()
        if not text:
            continue
        unavailable.add(validate_semantic_capability_name(text))

    seam = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    seam_ok = str(seam.get("status") or "").strip().lower() == "approved"

    entries = validator_dispatch_report.get("entries") or []
    evidences: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            evidences.append(ev)

    planned_unavailable = would_run_set & unavailable
    notes: list[str] = []
    classification: str

    if would_run_set and planned_unavailable == would_run_set:
        classification = ADR0041_DRIFT_MISSING_CONTEXT
        notes.append("all_planned_enforced_validators_unavailable")
    elif planned_unavailable and planned_unavailable != would_run_set:
        classification = ADR0041_DRIFT_UNAVAILABLE_VALIDATOR
        notes.append("partial_planned_enforced_unavailable")
    elif not evidences:
        classification = ADR0041_DRIFT_ALIGNED
        notes.append("no_local_execution_evidence_rows")
    else:
        any_fail = any(not bool(e.get("passed")) for e in evidences)
        all_pass = all(bool(e.get("passed")) for e in evidences)

        if seam_ok and any_fail:
            classification = ADR0041_DRIFT_ADR_STRICTER
        elif not seam_ok and all_pass:
            classification = ADR0041_DRIFT_SEAM_STRICTER
        elif not seam_ok and any_fail:
            classification = ADR0041_DRIFT_CONFLICTING_RESULT
            notes.append("seam_rejected_and_adr_local_failures_present")
        else:
            classification = ADR0041_DRIFT_ALIGNED

    return {
        "classification": classification,
        "notes": notes,
        "validation_seam_status": seam.get("status"),
        "validation_seam_reason": seam.get("reason"),
        "planned_enforced_count": len(would_run_set),
        "unavailable_planned_count": len(planned_unavailable),
        "executed_evidence_count": len(evidences),
    }
def build_adr0041_validation_authority_preview(
    *,
    validator_dispatch_report: dict[str, Any],
    validation_seam_summary: dict[str, Any] | None,
    selected_turn_class: str,
) -> dict[str, Any]:
    """Structured preview: ADR-0041 routing/evidence vs seam (never commit/readiness authority)."""
    seam_dict = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    drift = classify_adr0041_validation_authority_drift(
        validator_dispatch_report=validator_dispatch_report,
        validation_seam_summary=seam_dict,
    )
    executed_ids = list(validator_dispatch_report.get("actually_executed") or [])
    unavailable = list(validator_dispatch_report.get("validators_unavailable") or [])
    would_run = list(validator_dispatch_report.get("validators_would_run") or [])

    entries = validator_dispatch_report.get("entries") or []
    evidences: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            evidences.append(ev)
    failed_ids = sorted({str(e.get("validator_id") or "") for e in evidences if not e.get("passed")} - {""})
    passed_ids = sorted({str(e.get("validator_id") or "") for e in evidences if e.get("passed")} - {""})

    return _json_safe(
        {
            "schema_version": ADR0041_VALIDATION_AUTHORITY_PREVIEW_SCHEMA_VERSION,
            "authority_mode": "plan_enforced_local_routing_preview",
            "selected_turn_class": str(selected_turn_class or "").strip(),
            "enforced_validators_planned": would_run,
            "executed_validators": executed_ids,
            "unavailable_validators": unavailable,
            "pass_fail_summary": {
                "all_executed_passed": bool(evidences) and not failed_ids,
                "failed_validator_ids": failed_ids,
                "passed_validator_ids": passed_ids,
            },
            "drift_vs_validation_seam": drift,
            "canonical_commitment_seam": GOC_TURN_VALIDATION_SEAM_SYMBOL,
            "affects_commit": False,
            "affects_readiness": False,
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
        }
    )
def _build_adr0041_plan_enforced_runtime_projection_dispatch(
    *,
    capability_context: dict[str, Any],
    graph_bundle: dict[str, Any],
    dispatch_mode_warnings: tuple[str, ...],
    registry_for_turn_class: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Plan-enforced dispatch report for runtime_intelligence (graph runtime path only)."""
    selection_for_sidecar, sidecar_deriv_warnings = _select_semantic_capabilities_from_runtime_context(
        **capability_context
    )
    turn_class_key, turn_class_hints = _infer_adr0041_turn_class_from_situation(
        selection_for_sidecar.situation
    )
    execution_plan_sidecar = build_validator_execution_plan(selection_for_sidecar)
    execution_plan_sidecar = prepend_goc_seam_mirror_plan_entries(
        execution_plan_sidecar,
        seam_mirror_validator_ids=goc_seam_mirror_plan_validator_ids_for_turn_class(turn_class_key),
    )
    registry_sidecar = (
        registry_for_turn_class or adr0041_validator_registry_for_turn_class
    )(turn_class_key)
    dispatch_ctx_raw = graph_bundle.get("dispatch_context")
    dispatch_ctx: dict[str, Any] = (
        dict(dispatch_ctx_raw) if isinstance(dispatch_ctx_raw, dict) else {}
    )

    report_obj = build_validator_dispatch_report(
        execution_plan_sidecar,
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry_sidecar,
        dispatch_context=dispatch_ctx,
        feature_flag_enabled=True,
    )
    semantic_validator_dispatch_report = report_obj.to_runtime_projection()["validator_dispatch_report"]
    seam_summary = graph_bundle.get("validation_seam_summary")
    visibility: dict[str, Any] = {
        "canonical_commitment_seam": GOC_TURN_VALIDATION_SEAM_SYMBOL,
        "adr0041_runtime_sidecar": (
            "ai_stack.story_runtime.runtime_aspect_ledger / ADR-0041 plan_enforced local validators"
        ),
        "relationship_note": (
            "run_validation_seam remains the canonical commitment seam for validation_outcome; "
            "ADR-0041 performs plan-enforced local validator routing by turn class; "
            "see adr0041_authority_preview / validation_authority_preview (projection) for drift classification."
        ),
        "validation_seam_status": seam_summary.get("status") if isinstance(seam_summary, dict) else None,
        "validation_seam_reason": seam_summary.get("reason") if isinstance(seam_summary, dict) else None,
        "plan_enforced_actually_executed": list(
            semantic_validator_dispatch_report.get("actually_executed") or []
        ),
        "plan_enforced_validators_unavailable": list(
            semantic_validator_dispatch_report.get("validators_unavailable") or []
        ),
        "selected_turn_class": turn_class_key,
    }
    semantic_validator_dispatch_report["run_validation_seam_outcome_echo"] = (
        _json_safe(seam_summary) if isinstance(seam_summary, dict) else {}
    )
    semantic_validator_dispatch_report["adr0041_selected_turn_class"] = turn_class_key
    semantic_validator_dispatch_report["adr0041_turn_class_hints"] = _json_safe(turn_class_hints)
    semantic_validator_dispatch_report["seam_vs_adr0041_sidecar_drift_visibility"] = _json_safe(
        visibility
    )
    preview = build_adr0041_validation_authority_preview(
        validator_dispatch_report=semantic_validator_dispatch_report,
        validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
        selected_turn_class=turn_class_key,
    )
    semantic_validator_dispatch_report["adr0041_authority_preview"] = preview
    bridge = build_validation_authority_bridge(
        validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
        validator_dispatch_report=semantic_validator_dispatch_report,
        validation_authority_preview=preview,
        selected_turn_class=turn_class_key,
    )
    semantic_validator_dispatch_report["validation_authority_bridge"] = _json_safe(bridge)
    co_authority_enabled, co_authority_warnings = resolve_adr0041_scoped_co_authority_enabled()
    co_authority_decision: dict[str, Any] | None = None
    if co_authority_enabled:
        co_authority_decision = build_validation_co_authority_decision(
            validation_authority_bridge=bridge,
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            feature_flag_name=ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        if isinstance(co_authority_decision, dict):
            semantic_validator_dispatch_report["validation_co_authority_decision"] = _json_safe(
                co_authority_decision
            )
    readiness_preview_enabled, readiness_preview_warnings = (
        resolve_adr0041_readiness_co_authority_preview_enabled()
    )
    if readiness_preview_enabled:
        readiness_preview = build_readiness_co_authority_preview(
            validation_authority_bridge=bridge,
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            validation_co_authority_decision=co_authority_decision,
            feature_flag_name=ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        semantic_validator_dispatch_report["readiness_co_authority_preview"] = _json_safe(
            readiness_preview
        )
    enforcement_enabled, enforcement_warnings = (
        resolve_adr0041_scoped_readiness_enforcement_enabled()
    )
    if enforcement_enabled:
        readiness_enforcement = build_readiness_co_authority_enforcement(
            readiness_co_authority_preview=(
                semantic_validator_dispatch_report.get("readiness_co_authority_preview")
                if isinstance(semantic_validator_dispatch_report.get("readiness_co_authority_preview"), dict)
                else None
            ),
            validator_dispatch_report=semantic_validator_dispatch_report,
            selected_turn_class=turn_class_key,
            feature_flag_name=ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
            feature_flag_enabled=True,
        )
        semantic_validator_dispatch_report["readiness_co_authority_enforcement"] = _json_safe(
            readiness_enforcement
        )
    aggregation_enabled, aggregation_warnings = (
        resolve_adr0041_scoped_readiness_aggregation_enabled()
    )
    prereq_aggregation = (
        co_authority_enabled
        and readiness_preview_enabled
        and enforcement_enabled
    )
    policy_for_agg = semantic_validator_dispatch_report.get("readiness_co_authority_enforcement")
    if aggregation_enabled:
        if prereq_aggregation and isinstance(policy_for_agg, dict):
            semantic_validator_dispatch_report["readiness_aggregation_decision"] = _json_safe(
                build_readiness_aggregation_decision(
                    validation_seam_summary=seam_summary if isinstance(seam_summary, dict) else {},
                    readiness_policy_input=policy_for_agg,
                )
            )
        elif not prereq_aggregation:
            merged_pre = semantic_validator_dispatch_report.get("warnings")
            merged_list = list(merged_pre) if isinstance(merged_pre, list) else []
            msg = (
                "ADR-0041 scoped readiness aggregation skipped: prerequisite flags "
                "(scoped co-authority, readiness preview, enforcement) not all enabled."
            )
            if msg not in merged_list:
                merged_list.append(msg)
            semantic_validator_dispatch_report["warnings"] = merged_list
        else:
            merged_pre = semantic_validator_dispatch_report.get("warnings")
            merged_list = list(merged_pre) if isinstance(merged_pre, list) else []
            msg = (
                "ADR-0041 scoped readiness aggregation skipped: readiness policy input missing "
                "(enable scoped readiness enforcement to emit enforcement payload)."
            )
            if msg not in merged_list:
                merged_list.append(msg)
            semantic_validator_dispatch_report["warnings"] = merged_list
    extra_warnings = [
        *dispatch_mode_warnings,
        *sidecar_deriv_warnings,
        *co_authority_warnings,
        *readiness_preview_warnings,
        *enforcement_warnings,
        *aggregation_warnings,
    ]
    existing_warnings = semantic_validator_dispatch_report.get("warnings")
    merged: list[str] = list(existing_warnings) if isinstance(existing_warnings, list) else []
    for w in extra_warnings:
        t = str(w).strip()
        if t and t not in merged:
            merged.append(t)
    semantic_validator_dispatch_report["warnings"] = merged
    return _json_safe(semantic_validator_dispatch_report)
def build_adr0041_validator_dispatch_harness_report(
    *,
    harness_allow_plan_enforced_local_dispatch: bool = False,
    validator_registry: ValidatorRegistry | None = None,
    dispatch_context: dict[str, Any] | None = None,
    dispatch_mode: ValidatorDispatchMode | str | None = None,
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
    """Explicit ADR-0041 harness for plan-enforced local validator dispatch (tests only).

    When ``harness_allow_plan_enforced_local_dispatch`` is false, behavior matches
    ``build_semantic_validator_dispatch_report_projection`` (registry ignored).
    When true, ``plan_enforced`` runs registered validators only if an explicit
    registry mapping is supplied; missing registry fails closed to ``dry_run``.
    Production ledger normalization continues to use dry-run projection only.
    """
    cap_kw: dict[str, Any] = {
        "turn_kind": turn_kind,
        "turn_number": turn_number,
        "raw_player_input": raw_player_input,
        "input_kind": input_kind,
        "active_actor": active_actor,
        "npc_decision_required": npc_decision_required,
        "action_resolution_required": action_resolution_required,
        "visible_projection_required": visible_projection_required,
        "canonical_scene_seed": canonical_scene_seed,
        "non_lexical_input_present": non_lexical_input_present,
        "knowledge_gap_present": knowledge_gap_present,
        "world_state_change_requested": world_state_change_requested,
    }

    if not harness_allow_plan_enforced_local_dispatch:
        return build_semantic_validator_dispatch_report_projection(
            **cap_kw,
            dispatch_mode=dispatch_mode,
        )

    selection_result, derivation_warnings = _select_semantic_capabilities_from_runtime_context(**cap_kw)
    execution_plan = build_validator_execution_plan(selection_result)
    resolved_mode, mode_warnings = resolve_validator_dispatch_mode(explicit_mode=dispatch_mode)
    harness_warnings: list[str] = []

    if resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED and validator_registry is None:
        resolved_mode = ValidatorDispatchMode.DRY_RUN
        harness_warnings.append(ADR0041_HARNESS_PLAN_ENFORCED_REQUIRES_REGISTRY_WARNING)

    registry_arg: ValidatorRegistry = validator_registry if validator_registry is not None else {}

    report_obj = build_validator_dispatch_report(
        execution_plan,
        mode=resolved_mode,
        validator_registry=registry_arg,
        dispatch_context=dispatch_context or {},
        feature_flag_enabled=(resolved_mode is ValidatorDispatchMode.PLAN_ENFORCED),
    )
    payload = report_obj.to_runtime_projection()["validator_dispatch_report"]
    warnings = [
        *(payload.get("warnings") if isinstance(payload.get("warnings"), list) else []),
        *mode_warnings,
        *derivation_warnings,
        *harness_warnings,
    ]
    payload["warnings"] = [str(warning) for warning in warnings if str(warning).strip()]
    return _json_safe(payload)
