"""Runtime aspect validation orchestration for the LangGraph executor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ai_stack.capabilities.runtime_dramatic_capabilities import build_capability_selection_record
from ai_stack.dramatic_irony_runtime import (
    build_dramatic_irony_aspect_record,
    validate_dramatic_irony_realization,
)
from ai_stack.expectation_variation_engine import (
    build_expectation_variation_aspect_record,
    validate_expectation_variation_realization,
)
from ai_stack.genre_awareness_engine import (
    build_genre_awareness_aspect_record,
    validate_genre_awareness_realization,
)
from ai_stack.god_of_carnage_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.improvisational_coherence_engine import (
    build_improvisational_coherence_aspect_record,
    validate_improvisational_coherence_realization,
)
from ai_stack.information_disclosure_engine import validate_information_disclosure_realization
from ai_stack.meta_narrative_awareness_engine import (
    build_meta_narrative_awareness_aspect_record,
    validate_meta_narrative_awareness_realization,
)
from ai_stack.narrative_momentum_engine import (
    build_narrative_momentum_aspect_record,
    validate_narrative_momentum_realization,
)
from ai_stack.pacing_rhythm_engine import validate_pacing_rhythm_realization
from ai_stack.relationship_state_engine import (
    build_relationship_state_aspect_record,
    validate_relationship_state_realization,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_EXPECTATION_VARIATION,
    ASPECT_GENRE_AWARENESS,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_META_NARRATIVE_AWARENESS,
    ASPECT_NARRATIVE_MOMENTUM,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_PACING_RHYTHM,
    ASPECT_RELATIONSHIP_STATE,
    ASPECT_SCENE_ENERGY,
    ASPECT_SENSORY_CONTEXT,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_SYMBOLIC_OBJECT_RESONANCE,
    ASPECT_TEMPORAL_CONTROL,
    ASPECT_TONAL_CONSISTENCY,
    ASPECT_VALIDATION,
    ASPECT_VOICE_CONSISTENCY,
    make_aspect_record,
    set_aspect_record,
)
from ai_stack.scene_energy_engine import validate_scene_energy_realization
from ai_stack.sensory_context_engine import validate_sensory_context_realization
from ai_stack.social_pressure_engine import validate_social_pressure_metric
from ai_stack.story_runtime.dramatic_effect.dramatic_effect_gate import build_evaluation_context_from_runtime_state
from ai_stack.story_runtime.director.capabilities_manager.director_capability_manager import (
    executable_capabilities_from_manager_plan,
)
from ai_stack.story_runtime.npc_agency.npc_agency_realization import validate_npc_initiative_realization
from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import run_validation_seam
from ai_stack.symbolic_object_resonance_engine import (
    build_symbolic_object_resonance_aspect_record,
    validate_symbolic_object_resonance_realization,
)
from ai_stack.temporal_control_engine import (
    build_temporal_control_aspect_record,
    validate_temporal_control_realization,
)
from ai_stack.tonal_consistency_engine import (
    build_tonal_consistency_aspect_record,
    validate_tonal_consistency_realization,
)


ValidationHook = Callable[..., Any]


@dataclass(frozen=True)
class RuntimeAspectValidationHooks:
    actor_lane_validation: ValidationHook
    build_authority_aspect_records: ValidationHook
    dramatic_quality_rejection_locked: ValidationHook
    structured_output_from_generation: ValidationHook
    runtime_governance_section: ValidationHook
    voice_consistency_validation: ValidationHook
    voice_aspect_record: ValidationHook
    voice_semantic_failure_present: ValidationHook
    scene_energy_aspect_record: ValidationHook
    pacing_rhythm_aspect_record: ValidationHook
    sensory_context_aspect_record: ValidationHook
    social_pressure_aspect_record: ValidationHook
    information_disclosure_aspect_record: ValidationHook
    npc_agency_plan_from_state: ValidationHook
    npc_agency_aspect_record: ValidationHook


@dataclass
class _RuntimeAspectBuild:
    state: Any
    generation: dict[str, Any]
    proposed_state_effects: list[dict[str, Any]]
    hooks: RuntimeAspectValidationHooks
    outcome: dict[str, Any]
    dramatic_rejection_locked: bool
    actor_lane_validation: dict[str, Any]
    ledger: dict[str, Any]
    structured_output: dict[str, Any]
    narrator_authority: dict[str, Any]
    npc_authority: dict[str, Any]
    capability_selection: dict[str, Any] = field(default_factory=dict)
    cap_violation: dict[str, Any] = field(default_factory=dict)
    cap_missing_first: Any = None
    validations: dict[str, Any] = field(default_factory=dict)
    failures: dict[str, Any] = field(default_factory=dict)


def build_runtime_aspect_validation(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    outcome: dict[str, Any],
    hooks: RuntimeAspectValidationHooks,
) -> dict[str, Any]:
    """Evaluate runtime authority/capability aspects as validation inputs."""
    ctx = _initial_context(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
        outcome=outcome,
        hooks=hooks,
    )
    _capture_runtime_validations(ctx)
    _capture_capability_selection(ctx)
    _collect_failure_records(ctx)
    _apply_outcome_failures(ctx)
    _capture_validation_aspect(ctx)
    return _result(ctx)


def _initial_context(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    outcome: dict[str, Any],
    hooks: RuntimeAspectValidationHooks,
) -> _RuntimeAspectBuild:
    next_outcome = dict(outcome or {})
    actor_lane = hooks.actor_lane_validation(state, generation)
    if actor_lane.get("status") == "rejected" and next_outcome.get("status") == "approved":
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": actor_lane.get("reason") or "actor_lane_validation_rejected",
            "actor_lane_validation": actor_lane,
        }
    else:
        next_outcome = {**next_outcome, "actor_lane_validation": actor_lane}

    narrator, npc = hooks.build_authority_aspect_records(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
    )
    ledger = state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {}
    ledger = set_aspect_record(ledger, ASPECT_NARRATOR_AUTHORITY, narrator)
    ledger = set_aspect_record(ledger, ASPECT_NPC_AUTHORITY, npc)
    structured = hooks.structured_output_from_generation(generation)
    ctx = _RuntimeAspectBuild(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
        hooks=hooks,
        outcome=next_outcome,
        dramatic_rejection_locked=bool(hooks.dramatic_quality_rejection_locked(next_outcome)),
        actor_lane_validation=actor_lane,
        ledger=ledger,
        structured_output=structured,
        narrator_authority=narrator,
        npc_authority=npc,
    )
    voice_validation = hooks.voice_consistency_validation(state=state, generation=generation)
    ctx.validations["voice_consistency"] = voice_validation
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_VOICE_CONSISTENCY,
        hooks.voice_aspect_record(voice_validation),
    )
    return ctx


def _capture_runtime_validations(ctx: _RuntimeAspectBuild) -> None:
    _capture_scene_energy(ctx)
    _capture_pacing_rhythm(ctx)
    _capture_temporal_control(ctx)
    _capture_improvisational_coherence(ctx)
    _capture_social_pressure(ctx)
    _capture_tonal_consistency(ctx)
    _capture_relationship_state(ctx)
    _capture_genre_awareness(ctx)
    _capture_symbolic_object(ctx)
    _capture_sensory_context(ctx)
    _capture_information_disclosure(ctx)
    _capture_dramatic_irony(ctx)
    _capture_expectation_variation(ctx)
    _capture_narrative_momentum(ctx)
    _capture_meta_narrative(ctx)
    _capture_npc_agency(ctx)


def _state_dict(ctx: _RuntimeAspectBuild, key: str) -> dict[str, Any] | None:
    value = ctx.state.get(key)
    return value if isinstance(value, dict) else None


def _state_dict_or_empty(ctx: _RuntimeAspectBuild, key: str) -> dict[str, Any]:
    return _state_dict(ctx, key) or {}


def _record_validation(
    ctx: _RuntimeAspectBuild,
    key: str,
    aspect_id: str,
    validation: Any,
    aspect_record: dict[str, Any],
    *,
    outcome_key: str | None = None,
) -> None:
    ctx.validations[key] = validation
    ctx.ledger = set_aspect_record(ctx.ledger, aspect_id, aspect_record)
    ctx.outcome = {**ctx.outcome, outcome_key or f"{key}_validation": validation}


def _capture_scene_energy(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "scene_energy_target")
    transition = _state_dict(ctx, "scene_energy_transition")
    validation = validate_scene_energy_realization(
        scene_energy_target=target,
        scene_energy_transition=transition,
        structured_output=ctx.structured_output,
        scene_plan_record=_state_dict(ctx, "scene_plan_record"),
    )
    _record_validation(
        ctx,
        "scene_energy",
        ASPECT_SCENE_ENERGY,
        validation,
        ctx.hooks.scene_energy_aspect_record(target=target, transition=transition, validation=validation),
    )


def _capture_pacing_rhythm(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "pacing_rhythm_state")
    target = _state_dict(ctx, "pacing_rhythm_target")
    validation = validate_pacing_rhythm_realization(
        pacing_rhythm_target=target,
        pacing_rhythm_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "pacing_rhythm",
        ASPECT_PACING_RHYTHM,
        validation,
        ctx.hooks.pacing_rhythm_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )


def _capture_temporal_control(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "temporal_control_target")
    state_record = _state_dict(ctx, "temporal_control_state")
    validation = validate_temporal_control_realization(
        temporal_control_target=target,
        temporal_control_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "temporal_control",
        ASPECT_TEMPORAL_CONTROL,
        validation,
        build_temporal_control_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )


def _capture_improvisational_coherence(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "improvisational_coherence_target")
    validation = validate_improvisational_coherence_realization(
        improvisational_coherence_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "improvisational_coherence",
        ASPECT_IMPROVISATIONAL_COHERENCE,
        validation,
        build_improvisational_coherence_aspect_record(
            target=target,
            validation=validation,
            source="validator",
        ),
    )


def _capture_social_pressure(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "social_pressure_state")
    target = _state_dict(ctx, "social_pressure_target")
    validation = validate_social_pressure_metric(
        social_pressure_target=target,
        social_pressure_state=state_record,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    policy = ctx.hooks.runtime_governance_section(ctx.state, "social_pressure")
    _record_validation(
        ctx,
        "social_pressure",
        ASPECT_SOCIAL_PRESSURE,
        validation,
        ctx.hooks.social_pressure_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
            policy=policy,
        ),
    )


def _capture_tonal_consistency(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "tonal_consistency_target")
    policy = ctx.hooks.runtime_governance_section(ctx.state, "tonal_consistency")
    validation = validate_tonal_consistency_realization(
        tonal_consistency_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "tonal_consistency",
        ASPECT_TONAL_CONSISTENCY,
        validation,
        build_tonal_consistency_aspect_record(
            target=target,
            validation=validation,
            policy=policy,
            source="validator",
        ),
    )


def _capture_relationship_state(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "relationship_state_record")
    target = _state_dict(ctx, "relationship_dynamics_target")
    validation = validate_relationship_state_realization(
        relationship_state_record=state_record,
        relationship_dynamics_target=target,
        structured_output=ctx.structured_output,
        actor_lane_context=_state_dict(ctx, "actor_lane_context"),
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    _record_validation(
        ctx,
        "relationship_state",
        ASPECT_RELATIONSHIP_STATE,
        validation,
        build_relationship_state_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )


def _capture_genre_awareness(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "genre_awareness_target")
    state_record = _state_dict(ctx, "genre_awareness_state")
    validation = validate_genre_awareness_realization(
        genre_awareness_target=target,
        genre_awareness_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "genre_awareness",
        ASPECT_GENRE_AWARENESS,
        validation,
        build_genre_awareness_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )


def _capture_symbolic_object(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "symbolic_object_resonance_target")
    state_record = _state_dict(ctx, "symbolic_object_resonance_state")
    validation = validate_symbolic_object_resonance_realization(
        symbolic_object_resonance_target=target,
        symbolic_object_resonance_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "symbolic_object_resonance",
        ASPECT_SYMBOLIC_OBJECT_RESONANCE,
        validation,
        build_symbolic_object_resonance_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )


def _capture_sensory_context(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "sensory_context_state")
    target = _state_dict(ctx, "sensory_context_target")
    validation = validate_sensory_context_realization(
        sensory_context_target=target,
        sensory_context_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "sensory_context",
        ASPECT_SENSORY_CONTEXT,
        validation,
        ctx.hooks.sensory_context_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )


def _capture_information_disclosure(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "information_disclosure_target")
    validation = validate_information_disclosure_realization(
        information_disclosure_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "information_disclosure",
        ASPECT_INFORMATION_DISCLOSURE,
        validation,
        ctx.hooks.information_disclosure_aspect_record(target=target, validation=validation),
    )


def _capture_dramatic_irony(ctx: _RuntimeAspectBuild) -> None:
    record = _state_dict(ctx, "dramatic_irony_record")
    validation = validate_dramatic_irony_realization(
        record=record,
        generation=ctx.generation,
        proposed_state_effects=ctx.proposed_state_effects,
    )
    _record_validation(
        ctx,
        "dramatic_irony",
        ASPECT_DRAMATIC_IRONY,
        validation,
        build_dramatic_irony_aspect_record(
            record=record,
            validation=validation,
            source="validator",
        ),
    )


def _capture_expectation_variation(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "expectation_variation_target")
    state_record = _state_dict(ctx, "expectation_variation_state")
    validation = validate_expectation_variation_realization(
        expectation_variation_target=target,
        expectation_variation_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "expectation_variation",
        ASPECT_EXPECTATION_VARIATION,
        validation,
        build_expectation_variation_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )


def _capture_narrative_momentum(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "narrative_momentum_target")
    state_record = _state_dict(ctx, "narrative_momentum_state")
    validation = validate_narrative_momentum_realization(
        narrative_momentum_target=target,
        narrative_momentum_state=state_record,
        structured_output=ctx.structured_output,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    policy = ctx.hooks.runtime_governance_section(ctx.state, "narrative_momentum")
    _record_validation(
        ctx,
        "narrative_momentum",
        ASPECT_NARRATIVE_MOMENTUM,
        validation,
        build_narrative_momentum_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            policy=policy,
            source="validator",
        ),
    )


def _capture_meta_narrative(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "meta_narrative_awareness_target")
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "meta_narrative_awareness",
        ASPECT_META_NARRATIVE_AWARENESS,
        validation,
        build_meta_narrative_awareness_aspect_record(
            target=target,
            validation=validation,
            source="validator",
        ),
    )


def _capture_npc_agency(ctx: _RuntimeAspectBuild) -> None:
    plan = ctx.hooks.npc_agency_plan_from_state(ctx.state)
    actor_lane_context = _state_dict(ctx, "actor_lane_context")
    validation = (
        validate_npc_initiative_realization(
            plan,
            ctx.structured_output,
            actor_lane_context=actor_lane_context,
            strict_required=True,
        )
        if isinstance(plan, dict)
        else None
    )
    ctx.validations["npc_initiative"] = validation
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_NPC_AGENCY,
        ctx.hooks.npc_agency_aspect_record(validation),
    )
    if isinstance(validation, dict):
        ctx.outcome = {**ctx.outcome, "npc_initiative_validation": validation}


def _capture_capability_selection(ctx: _RuntimeAspectBuild) -> None:
    selection = build_capability_selection_record(
        interpreted_input=_state_dict_or_empty(ctx, "interpreted_input"),
        player_action_frame=_state_dict_or_empty(ctx, "player_action_frame"),
        affordance_resolution=_state_dict_or_empty(ctx, "affordance_resolution"),
        narrator_authority=ctx.narrator_authority,
        npc_authority=ctx.npc_authority,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    scene_plan = _state_dict_or_empty(ctx, "scene_plan_record")
    manager_plan = scene_plan.get("capability_manager_plan")
    if isinstance(manager_plan, dict) and manager_plan.get("run_only_selected_capabilities"):
        _apply_director_capability_plan(
            selection,
            manager_plan,
            narrator_authority=ctx.narrator_authority,
            npc_authority=ctx.npc_authority,
        )
    ctx.capability_selection = selection
    ctx.cap_violation, ctx.cap_missing_first, cap_reason = _capability_status_bits(selection)
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_CAPABILITY_SELECTION,
        _capability_selection_aspect_record(ctx, cap_reason),
    )


def _apply_director_capability_plan(
    selection: dict[str, Any],
    manager_plan: dict[str, Any],
    *,
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
) -> None:
    manager_caps = list(executable_capabilities_from_manager_plan(manager_plan))
    for key in ("requested_capabilities", "selected_capabilities"):
        selection[key] = _append_unique_text(selection.get(key), manager_caps)
    required = _append_required_manager_caps(
        selection.get("required_capabilities"),
        manager_plan.get("required_capabilities"),
        manager_caps,
    )
    selection["required_capabilities"] = required
    selection["director_capability_manager_plan"] = manager_plan
    selection["director_capability_dispatch_audit"] = manager_plan.get("capability_dispatch_audit")
    selection["suppressed_capabilities"] = _clean_text_list(manager_plan.get("suppressed_capabilities"))
    realized = _infer_realized_manager_capabilities(
        selection.get("realized_capabilities"),
        manager_caps,
        narrator_authority=narrator_authority,
        npc_authority=npc_authority,
    )
    selection["realized_capabilities"] = realized
    missing_required = [cap for cap in required if cap not in set(realized)]
    selection["missing_required_capabilities"] = missing_required
    if selection.get("violations"):
        selection["status"] = "failed"
    elif missing_required:
        selection["status"] = "partial"
    else:
        selection["status"] = "passed"


def _append_unique_text(existing: Any, values: list[Any]) -> list[Any]:
    out = list(existing) if isinstance(existing, list) else []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _append_required_manager_caps(existing: Any, requested: Any, manager_caps: list[Any]) -> list[Any]:
    out = list(existing) if isinstance(existing, list) else []
    for value in requested or []:
        text = str(value or "").strip()
        if text and text in manager_caps and text not in out:
            out.append(text)
    return out


def _clean_text_list(values: Any) -> list[str]:
    return [text for text in (str(value or "").strip() for value in values or []) if text]


def _infer_realized_manager_capabilities(
    existing: Any,
    manager_caps: list[Any],
    *,
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
) -> list[Any]:
    realized = list(existing) if isinstance(existing, list) else []
    narrator_actual = narrator_authority.get("actual") if isinstance(narrator_authority.get("actual"), dict) else {}
    npc_actual = npc_authority.get("actual") if isinstance(npc_authority.get("actual"), dict) else {}
    narrator_present = bool(narrator_actual.get("narrator_block_present") or narrator_actual.get("consequence_realized"))
    npc_spoken = int(npc_actual.get("spoken_line_count") or 0) > 0
    npc_action = int(npc_actual.get("action_line_count") or 0) > 0
    for cap in manager_caps:
        text = str(cap or "").strip()
        if not text or text in realized:
            continue
        if text.startswith("narrator.") and narrator_present:
            realized.append(text)
        elif text in {"npc.social_reaction.optional", "npc.direct_answer.allowed"} and npc_spoken:
            realized.append(text)
        elif text == "npc.action_gesture.optional" and npc_action:
            realized.append(text)
    return realized


def _capability_status_bits(selection: dict[str, Any]) -> tuple[dict[str, Any], Any, str]:
    violations = selection.get("violations")
    violation = violations[0] if isinstance(violations, list) and violations else {}
    missing = selection.get("missing_required_capabilities")
    missing_first = missing[0] if isinstance(missing, list) and missing else None
    reason = (
        str(violation.get("reason") or violation.get("capability"))
        if isinstance(violation, dict) and violation
        else f"missing_required_capability:{missing_first}"
        if missing_first
        else ""
    )
    return (violation if isinstance(violation, dict) else {}, missing_first, reason)


def _capability_selection_aspect_record(ctx: _RuntimeAspectBuild, cap_reason: str) -> dict[str, Any]:
    status = str(ctx.capability_selection.get("status") or "missing").strip()
    cap_violation = ctx.cap_violation
    cap_missing = ctx.cap_missing_first
    return make_aspect_record(
        applicable=True,
        status=status if status in {"passed", "failed", "partial"} else "missing",
        expected={
            "blocked_capabilities": ctx.capability_selection.get("blocked_capabilities"),
            "required_capabilities": ctx.capability_selection.get("required_capabilities"),
            "selected_capabilities_must_be_realized_or_marked_missing": True,
            "director_capability_manager_plan": ctx.capability_selection.get("director_capability_manager_plan"),
        },
        selected={
            "requested_capabilities": ctx.capability_selection.get("requested_capabilities"),
            "selected_capabilities": ctx.capability_selection.get("selected_capabilities"),
            "blocked_capabilities": ctx.capability_selection.get("blocked_capabilities"),
            "required_capabilities": ctx.capability_selection.get("required_capabilities"),
            "suppressed_capabilities": ctx.capability_selection.get("suppressed_capabilities"),
        },
        actual={
            "realized_capabilities": ctx.capability_selection.get("realized_capabilities"),
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities"),
            "violations": ctx.capability_selection.get("violations"),
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities"),
            "forbidden_capability_realized": bool(cap_violation),
        },
        reasons=[cap_reason] if cap_reason else [],
        source="runtime",
        failure_class="hard_contract_failure" if cap_violation else "recoverable_contract_gap" if cap_missing else None,
        failure_reason=(
            str(cap_violation.get("reason") or "forbidden_capability_realized")
            if cap_violation
            else "capability_missing_required"
            if cap_missing
            else None
        ),
        offending_actor_id=cap_violation.get("offending_actor_id") if cap_violation else None,
        selected_capability=cap_missing,
        realized_capability=cap_violation.get("capability") if cap_violation else None,
    )


def _collect_failure_records(ctx: _RuntimeAspectBuild) -> None:
    ctx.failures["authority_failure"] = _authority_failure(ctx)
    ctx.failures["capability_failure"] = _capability_failure(ctx)
    for key, default, reason_key, codes_key, output_codes_key in _DRAMATIC_FAILURE_SPECS:
        ctx.failures[f"{key}_failure"] = _dramatic_failure(
            ctx.validations.get(key),
            default,
            reason_key=reason_key,
            codes_key=codes_key,
            output_codes_key=output_codes_key,
        )
    ctx.failures["npc_agency_failure"] = _npc_agency_failure(ctx.validations.get("npc_initiative"))


def _authority_failure(ctx: _RuntimeAspectBuild) -> dict[str, Any] | None:
    if ctx.npc_authority.get("status") == "failed":
        return ctx.npc_authority
    if ctx.narrator_authority.get("status") == "failed":
        return ctx.narrator_authority
    return None


def _capability_failure(ctx: _RuntimeAspectBuild) -> dict[str, Any] | None:
    if ctx.cap_violation:
        return {
            "failure_reason": str(ctx.cap_violation.get("reason") or "forbidden_capability_realized"),
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities") or [],
            "offending_actor_id": ctx.cap_violation.get("offending_actor_id"),
        }
    if ctx.cap_missing_first:
        return {
            "failure_reason": "capability_missing_required",
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities") or [],
            "selected_capability": ctx.cap_missing_first,
        }
    return None


def _dramatic_failure(
    validation: Any,
    default_reason: str,
    *,
    reason_key: str | None = "feedback_code",
    codes_key: str = "failure_codes",
    output_codes_key: str = "failure_codes",
) -> dict[str, Any] | None:
    if not isinstance(validation, dict):
        return None
    if str(validation.get("status") or "").strip().lower() != "rejected":
        return None
    codes = [str(code) for code in (validation.get(codes_key) or []) if str(code).strip()]
    reason = str(validation.get(reason_key) or "").strip() if reason_key else ""
    return {
        "failure_reason": reason or (codes[0] if codes else default_reason),
        output_codes_key: codes,
        "failure_class": "recoverable_dramatic_failure",
    }


def _npc_agency_failure(validation: Any) -> dict[str, Any] | None:
    if not isinstance(validation, dict):
        return None
    if str(validation.get("status") or "").strip().lower() == "approved":
        return None
    codes = [str(code) for code in (validation.get("error_codes") or []) if str(code).strip()]
    forbidden = bool(validation.get("forbidden_planned_actor_ids") or validation.get("forbidden_realized_actor_ids"))
    return {
        "failure_reason": str(
            validation.get("feedback_code") or (codes[0] if codes else "npc_initiative_validation_failed")
        ),
        "error_codes": codes,
        "missing_required_actor_ids": validation.get("missing_required_actor_ids") or [],
        "forbidden_planned_actor_ids": validation.get("forbidden_planned_actor_ids") or [],
        "forbidden_realized_actor_ids": validation.get("forbidden_realized_actor_ids") or [],
        "failure_class": "hard_contract_failure" if forbidden else "recoverable_dramatic_failure",
    }


_DRAMATIC_FAILURE_SPECS = (
    ("scene_energy", "scene_energy_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("pacing_rhythm", "pacing_rhythm_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("temporal_control", "temporal_control_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "improvisational_coherence",
        "improvisational_coherence_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("social_pressure", "social_pressure_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("tonal_consistency", "tonal_consistency_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    ("relationship_state", "relationship_state_validation_failed", None, "failure_codes", "failure_codes"),
    ("genre_awareness", "genre_awareness_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "symbolic_object_resonance",
        "symbolic_object_resonance_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("sensory_context", "sensory_context_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "information_disclosure",
        "information_disclosure_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("dramatic_irony", "dramatic_irony_validation_failed", "feedback_code", "violation_codes", "violation_codes"),
    (
        "expectation_variation",
        "expectation_variation_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
    ("narrative_momentum", "narrative_momentum_validation_failed", "feedback_code", "failure_codes", "failure_codes"),
    (
        "meta_narrative_awareness",
        "meta_narrative_awareness_validation_failed",
        "feedback_code",
        "failure_codes",
        "failure_codes",
    ),
)


def _apply_outcome_failures(ctx: _RuntimeAspectBuild) -> None:
    if _apply_authority_failure(ctx):
        return
    if _apply_capability_failure(ctx):
        return
    if _apply_voice_failure(ctx):
        return
    if _apply_npc_agency_failure(ctx):
        return
    for spec in _OUTCOME_FAILURE_SPECS:
        failure_key, lane, contract_key, default_reason, skip_when_locked = spec
        if skip_when_locked and ctx.dramatic_rejection_locked:
            continue
        if _apply_generic_failure(ctx, failure_key, lane, contract_key, default_reason):
            return
    ctx.outcome = {**ctx.outcome, "voice_consistency_validation": ctx.validations["voice_consistency"]}


def _outcome_is_approved(ctx: _RuntimeAspectBuild) -> bool:
    return str(ctx.outcome.get("status") or "").strip().lower() == "approved"


def _apply_authority_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("authority_failure")
    if not isinstance(failure, dict):
        return False
    reason = str(failure.get("failure_reason") or (failure.get("reasons") or ["authority_contract_violation"])[0])
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "runtime_aspect_ledger_authority_v1",
        "authority_contract_violation": True,
        "failure_class": "hard_contract_failure",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "runtime_aspect_failure": {
            "aspect_status": failure.get("status"),
            "failure_reason": reason,
            "offending_actor_id": failure.get("offending_actor_id"),
            "offending_block_id": failure.get("offending_block_id"),
            "expected_owner": failure.get("expected_owner"),
            "actual_owner": failure.get("actual_owner"),
            "missing_field": failure.get("missing_field"),
        },
    }
    if isinstance(ctx.failures.get("capability_failure"), dict):
        ctx.outcome["capability_failure"] = ctx.failures["capability_failure"]
    return True


def _apply_capability_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("capability_failure")
    if not isinstance(failure, dict):
        return False
    reason = str(failure.get("failure_reason") or "capability_missing_required")
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "runtime_aspect_ledger_capability_v1",
        "capability_contract_violation": bool(ctx.cap_violation),
        "failure_class": "hard_contract_failure" if ctx.cap_violation else "recoverable_contract_gap",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "capability_failure": failure,
    }
    return True


def _apply_voice_failure(ctx: _RuntimeAspectBuild) -> bool:
    voice_validation = ctx.validations["voice_consistency"]
    if voice_validation.get("status") != "rejected" or not _outcome_is_approved(ctx):
        return False
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": "voice_consistency_drift",
        "error_code": "voice_consistency_drift",
        "validator_lane": "runtime_voice_consistency_v2"
        if ctx.hooks.voice_semantic_failure_present(voice_validation)
        else "runtime_voice_consistency_v1",
        "voice_consistency_validation": voice_validation,
        "voice_consistency_contract_violation": True,
        "failure_class": "recoverable_dramatic_failure",
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
    }
    return True


def _apply_npc_agency_failure(ctx: _RuntimeAspectBuild) -> bool:
    failure = ctx.failures.get("npc_agency_failure")
    if not isinstance(failure, dict) or ctx.dramatic_rejection_locked or not _outcome_is_approved(ctx):
        return False
    reason = str(failure.get("failure_reason") or "npc_initiative_validation_failed")
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": "npc_initiative_validation_v1",
        "npc_agency_contract_violation": True,
        "failure_class": failure.get("failure_class"),
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        "npc_agency_failure": failure,
    }
    return True


def _apply_generic_failure(
    ctx: _RuntimeAspectBuild,
    failure_key: str,
    validator_lane: str,
    contract_key: str,
    default_reason: str,
) -> bool:
    failure = ctx.failures.get(failure_key)
    if not isinstance(failure, dict) or not _outcome_is_approved(ctx):
        return False
    reason = str(failure.get("failure_reason") or default_reason)
    ctx.outcome = {
        **ctx.outcome,
        "status": "rejected",
        "reason": reason,
        "error_code": reason,
        "validator_lane": validator_lane,
        contract_key: True,
        "failure_class": failure.get("failure_class"),
        "hard_boundary_failure": False,
        "recoverable_rejection": True,
        failure_key: failure,
    }
    return True


_OUTCOME_FAILURE_SPECS = (
    ("dramatic_irony_failure", "dramatic_irony_validation_v1", "dramatic_irony_contract_violation", "dramatic_irony_validation_failed", False),
    (
        "expectation_variation_failure",
        "expectation_variation_validation_v1",
        "expectation_variation_contract_violation",
        "expectation_variation_validation_failed",
        False,
    ),
    (
        "narrative_momentum_failure",
        "narrative_momentum_validation_v1",
        "narrative_momentum_contract_violation",
        "narrative_momentum_validation_failed",
        False,
    ),
    (
        "meta_narrative_awareness_failure",
        "meta_narrative_awareness_validation_v1",
        "meta_narrative_awareness_contract_violation",
        "meta_narrative_awareness_validation_failed",
        False,
    ),
    ("scene_energy_failure", "scene_energy_validation_v1", "scene_energy_contract_violation", "scene_energy_validation_failed", True),
    ("pacing_rhythm_failure", "pacing_rhythm_validation_v1", "pacing_rhythm_contract_violation", "pacing_rhythm_validation_failed", False),
    (
        "temporal_control_failure",
        "temporal_control_validation_v1",
        "temporal_control_contract_violation",
        "temporal_control_validation_failed",
        False,
    ),
    (
        "improvisational_coherence_failure",
        "improvisational_coherence_validation_v1",
        "improvisational_coherence_contract_violation",
        "improvisational_coherence_validation_failed",
        False,
    ),
    ("social_pressure_failure", "social_pressure_validation_v1", "social_pressure_contract_violation", "social_pressure_validation_failed", False),
    (
        "tonal_consistency_failure",
        "tonal_consistency_validation_v1",
        "tonal_consistency_contract_violation",
        "tonal_consistency_validation_failed",
        False,
    ),
    (
        "relationship_state_failure",
        "relationship_state_validation_v1",
        "relationship_state_contract_violation",
        "relationship_state_validation_failed",
        False,
    ),
    ("genre_awareness_failure", "genre_awareness_validation_v1", "genre_awareness_contract_violation", "genre_awareness_validation_failed", False),
    (
        "symbolic_object_resonance_failure",
        "symbolic_object_resonance_validation_v1",
        "symbolic_object_resonance_contract_violation",
        "symbolic_object_resonance_validation_failed",
        False,
    ),
    ("sensory_context_failure", "sensory_context_validation_v1", "sensory_context_contract_violation", "sensory_context_validation_failed", False),
    (
        "information_disclosure_failure",
        "information_disclosure_validation_v1",
        "information_disclosure_contract_violation",
        "information_disclosure_validation_failed",
        False,
    ),
)


def _capture_validation_aspect(ctx: _RuntimeAspectBuild) -> None:
    validation_failed = str(ctx.outcome.get("status") or "").strip().lower() != "approved"
    authority_failure = ctx.failures.get("authority_failure")
    capability_failure = ctx.failures.get("capability_failure")
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed" if validation_failed else "passed",
            expected={"validation_consumes_runtime_aspect_ledger": True},
            actual=_validation_aspect_actual(ctx),
            reasons=[str(ctx.outcome.get("reason"))] if validation_failed and ctx.outcome.get("reason") else [],
            source="validator",
            failure_class=ctx.outcome.get("failure_class") if validation_failed else None,
            failure_reason=str(ctx.outcome.get("reason")) if validation_failed and ctx.outcome.get("reason") else None,
            offending_actor_id=_first_failure_value(authority_failure, capability_failure, "offending_actor_id"),
            offending_block_id=authority_failure.get("offending_block_id") if isinstance(authority_failure, dict) else None,
            expected_owner=authority_failure.get("expected_owner") if isinstance(authority_failure, dict) else None,
            actual_owner=authority_failure.get("actual_owner") if isinstance(authority_failure, dict) else None,
            missing_field=authority_failure.get("missing_field") if isinstance(authority_failure, dict) else None,
        ),
    )


def _first_failure_value(first: Any, second: Any, key: str) -> Any:
    if isinstance(first, dict) and first.get(key) is not None:
        return first.get(key)
    if isinstance(second, dict):
        return second.get(key)
    return None


def _validation_aspect_actual(ctx: _RuntimeAspectBuild) -> dict[str, Any]:
    voice = ctx.validations["voice_consistency"]
    actual = {
        "validation_status": ctx.outcome.get("status"),
        "reason": ctx.outcome.get("reason"),
        "validator_lane": ctx.outcome.get("validator_lane"),
        "authority_contract_violation": bool(ctx.outcome.get("authority_contract_violation")),
        "capability_contract_violation": bool(ctx.outcome.get("capability_contract_violation")),
        "voice_consistency_contract_violation": bool(ctx.outcome.get("voice_consistency_contract_violation")),
        "voice_consistency_status": voice.get("status"),
        "voice_consistency_reason": voice.get("reason"),
        "recoverable_rejection": bool(ctx.outcome.get("recoverable_rejection")),
        "hard_boundary_failure": bool(ctx.outcome.get("hard_boundary_failure")),
    }
    for validation_key, status_key, contract_key in _VALIDATION_STATUS_FIELDS:
        validation = ctx.validations.get(validation_key)
        actual[status_key] = validation.get("status") if isinstance(validation, dict) else None
        actual[contract_key] = bool(ctx.outcome.get(contract_key))
    return actual


_VALIDATION_STATUS_FIELDS = (
    ("scene_energy", "scene_energy_validation_status", "scene_energy_contract_violation"),
    ("pacing_rhythm", "pacing_rhythm_validation_status", "pacing_rhythm_contract_violation"),
    ("temporal_control", "temporal_control_validation_status", "temporal_control_contract_violation"),
    (
        "improvisational_coherence",
        "improvisational_coherence_validation_status",
        "improvisational_coherence_contract_violation",
    ),
    ("social_pressure", "social_pressure_validation_status", "social_pressure_contract_violation"),
    ("tonal_consistency", "tonal_consistency_validation_status", "tonal_consistency_contract_violation"),
    ("relationship_state", "relationship_state_validation_status", "relationship_state_contract_violation"),
    ("genre_awareness", "genre_awareness_validation_status", "genre_awareness_contract_violation"),
    (
        "symbolic_object_resonance",
        "symbolic_object_resonance_validation_status",
        "symbolic_object_resonance_contract_violation",
    ),
    ("sensory_context", "sensory_context_validation_status", "sensory_context_contract_violation"),
    ("information_disclosure", "information_disclosure_validation_status", "information_disclosure_contract_violation"),
    ("dramatic_irony", "dramatic_irony_validation_status", "dramatic_irony_contract_violation"),
    ("expectation_variation", "expectation_variation_validation_status", "expectation_variation_contract_violation"),
    ("narrative_momentum", "narrative_momentum_validation_status", "narrative_momentum_contract_violation"),
    (
        "meta_narrative_awareness",
        "meta_narrative_awareness_validation_status",
        "meta_narrative_awareness_contract_violation",
    ),
    ("npc_initiative", "npc_initiative_validation_status", "npc_agency_contract_violation"),
)


def _result(ctx: _RuntimeAspectBuild) -> dict[str, Any]:
    return {
        "outcome": ctx.outcome,
        "actor_lane_validation": ctx.actor_lane_validation,
        "turn_aspect_ledger": ctx.ledger,
        "narrator_authority": ctx.narrator_authority,
        "npc_authority": ctx.npc_authority,
        "capability_selection": ctx.capability_selection,
        "voice_consistency_validation": ctx.validations.get("voice_consistency"),
        "scene_energy_validation": ctx.validations.get("scene_energy"),
        "pacing_rhythm_validation": ctx.validations.get("pacing_rhythm"),
        "temporal_control_validation": ctx.validations.get("temporal_control"),
        "improvisational_coherence_validation": ctx.validations.get("improvisational_coherence"),
        "social_pressure_validation": ctx.validations.get("social_pressure"),
        "tonal_consistency_validation": ctx.validations.get("tonal_consistency"),
        "relationship_state_validation": ctx.validations.get("relationship_state"),
        "genre_awareness_validation": ctx.validations.get("genre_awareness"),
        "symbolic_object_resonance_validation": ctx.validations.get("symbolic_object_resonance"),
        "sensory_context_validation": ctx.validations.get("sensory_context"),
        "information_disclosure_validation": ctx.validations.get("information_disclosure"),
        "dramatic_irony_validation": ctx.validations.get("dramatic_irony"),
        "expectation_variation_validation": ctx.validations.get("expectation_variation"),
        "narrative_momentum_validation": ctx.validations.get("narrative_momentum"),
        "meta_narrative_awareness_validation": ctx.validations.get("meta_narrative_awareness"),
        "npc_initiative_validation": ctx.validations.get("npc_initiative"),
        "authority_failure": ctx.failures.get("authority_failure"),
        "capability_failure": ctx.failures.get("capability_failure"),
        "scene_energy_failure": ctx.failures.get("scene_energy_failure"),
        "temporal_control_failure": ctx.failures.get("temporal_control_failure"),
        "improvisational_coherence_failure": ctx.failures.get("improvisational_coherence_failure"),
        "social_pressure_failure": ctx.failures.get("social_pressure_failure"),
        "tonal_consistency_failure": ctx.failures.get("tonal_consistency_failure"),
        "relationship_state_failure": ctx.failures.get("relationship_state_failure"),
        "genre_awareness_failure": ctx.failures.get("genre_awareness_failure"),
        "symbolic_object_resonance_failure": ctx.failures.get("symbolic_object_resonance_failure"),
        "sensory_context_failure": ctx.failures.get("sensory_context_failure"),
        "information_disclosure_failure": ctx.failures.get("information_disclosure_failure"),
        "dramatic_irony_failure": ctx.failures.get("dramatic_irony_failure"),
        "expectation_variation_failure": ctx.failures.get("expectation_variation_failure"),
        "narrative_momentum_failure": ctx.failures.get("narrative_momentum_failure"),
        "meta_narrative_awareness_failure": ctx.failures.get("meta_narrative_awareness_failure"),
        "npc_agency_failure": ctx.failures.get("npc_agency_failure"),
    }


def run_runtime_validation_seam(
    *,
    state: Any,
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    silence_brevity_decision: dict[str, Any],
    actor_lane_validation: ValidationHook,
) -> dict[str, Any]:
    narr = extract_proposed_narrative_text(proposed_state_effects)
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    lane_validation = actor_lane_validation(state, generation)
    actor_lane_summary = {
        "spoken_line_count": len(structured.get("spoken_lines") or []),
        "action_line_count": len(structured.get("action_lines") or []),
        "initiative_event_count": len(structured.get("initiative_events") or []),
        "actor_lane_status": str(lane_validation.get("status") or "not_evaluated").strip().lower(),
    }
    eval_ctx = build_evaluation_context_from_runtime_state(
        module_id=str(state.get("module_id") or ""),
        proposed_narrative=narr,
        selected_scene_function=str(state.get("selected_scene_function") or "establish_pressure"),
        pacing_mode=str(state.get("pacing_mode") or "standard"),
        silence_brevity_decision=dict(silence_brevity_decision),
        semantic_move_record=_dict_or_none(state.get("semantic_move_record")),
        social_state_record=_dict_or_none(state.get("social_state_record")),
        character_mind_records=_list_or_empty(state.get("character_mind_records")),
        scene_plan_record=_dict_or_none(state.get("scene_plan_record")),
        prior_continuity_impacts=_list_or_empty(state.get("prior_continuity_impacts")),
        selected_responder_set=_list_or_empty(state.get("selected_responder_set")),
        dramatic_irony_record=_dict_or_none(state.get("dramatic_irony_record")),
        actor_lane_summary=actor_lane_summary,
    )
    return run_validation_seam(
        module_id=state.get("module_id") or "",
        proposed_state_effects=proposed_state_effects,
        generation=generation if isinstance(generation, dict) else {},
        evaluation_context=eval_ctx,
        actor_lane_summary=actor_lane_summary,
        actor_lane_context=_dict_or_none(state.get("actor_lane_context")),
        story_runtime_experience=_dict_or_none(state.get("story_runtime_experience")),
        interpreted_input=_dict_or_none(state.get("interpreted_input")),
        raw_player_input=str(state.get("player_input") or "").strip() or None,
        player_action_frame=_dict_or_none(state.get("player_action_frame")),
        affordance_resolution=_dict_or_none(state.get("affordance_resolution")),
        opening_scene_sequence=_dict_or_none(state.get("opening_scene_sequence")),
        hard_forbidden_rules=_dict_or_none(state.get("hard_forbidden_rules")),
        turn_input_class=state.get("turn_input_class") if isinstance(state.get("turn_input_class"), str) else None,
        scene_plan_record=_dict_or_none(state.get("scene_plan_record")),
        current_scene_id=state.get("current_scene_id") if isinstance(state.get("current_scene_id"), str) else None,
        w5_latest_snapshot=state.get("w5_latest_snapshot"),
    )


def build_validation_retry_feedback(
    *,
    outcome: dict[str, Any],
    decision: Any,
    actor_lane_validation: dict[str, Any],
    attempt_index: int,
) -> dict[str, Any]:
    feedback = {
        "codes": list(decision.feedback_codes),
        "attempt_index": attempt_index,
        "trigger_source": _retry_trigger_source(outcome),
        "validation_status_before_retry": outcome.get("status"),
        "failure_reason_before_retry": str(outcome.get("reason") or "").strip(),
        "actor_lane_status_before_retry": actor_lane_validation.get("status")
        if isinstance(actor_lane_validation, dict)
        else None,
    }
    for outcome_key, feedback_key in _RETRY_FAILURE_FIELDS:
        feedback[feedback_key] = _dict_copy_or_none(outcome.get(outcome_key))
    return feedback


def build_retry_attempt_record_update(
    *,
    validation_feedback: dict[str, Any],
    outcome: dict[str, Any],
    context_synthesis_retry: dict[str, Any],
) -> dict[str, Any]:
    update = {key: validation_feedback.get(key) for key in _ATTEMPT_RECORD_FEEDBACK_KEYS}
    update.update(
        {
            "validation_status_after_retry": outcome.get("status"),
            "failure_reason_after_retry": outcome.get("reason"),
            "context_synthesis_retry": context_synthesis_retry,
            "resolved_failure": (
                str(outcome.get("status") or "").strip().lower() == "approved"
                or (
                    bool(validation_feedback.get("failure_reason_before_retry"))
                    and str(outcome.get("reason") or "").strip()
                    != str(validation_feedback.get("failure_reason_before_retry") or "")
                )
            ),
        }
    )
    return update


def copy_validation_eval_to_update(update: dict[str, Any], validation_eval: dict[str, Any]) -> None:
    for key in _VALIDATION_EVAL_UPDATE_KEYS:
        value = validation_eval.get(key)
        if isinstance(value, dict):
            update[key] = value
    dramatic_irony = validation_eval.get("dramatic_irony_validation")
    if isinstance(dramatic_irony, dict) and isinstance(dramatic_irony.get("record"), dict):
        update["dramatic_irony_record"] = dramatic_irony["record"]


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _dict_copy_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, dict) else None


def _list_or_empty(value: Any) -> list[Any]:
    return list(value or []) if isinstance(value, list) else []


def _retry_trigger_source(outcome: dict[str, Any]) -> str:
    for key, source in _RETRY_TRIGGER_SOURCES:
        if isinstance(outcome.get(key), dict):
            return source
    return "validation"


_RETRY_TRIGGER_SOURCES = (
    ("runtime_aspect_failure", "runtime_aspect"),
    ("capability_failure", "capability"),
    ("scene_energy_failure", "scene_energy"),
    ("pacing_rhythm_failure", "pacing_rhythm"),
    ("temporal_control_failure", "temporal_control"),
    ("improvisational_coherence_failure", "improvisational_coherence"),
    ("social_pressure_failure", "social_pressure"),
    ("tonal_consistency_failure", "tonal_consistency"),
    ("genre_awareness_failure", "genre_awareness"),
    ("sensory_context_failure", "sensory_context"),
    ("information_disclosure_failure", "information_disclosure"),
    ("dramatic_irony_failure", "dramatic_irony"),
    ("expectation_variation_failure", "expectation_variation"),
    ("narrative_momentum_failure", "narrative_momentum"),
    ("meta_narrative_awareness_failure", "meta_narrative_awareness"),
)


_RETRY_FAILURE_FIELDS = tuple(
    (outcome_key, f"{outcome_key}_before_retry")
    for outcome_key, _ in _RETRY_TRIGGER_SOURCES
)


_ATTEMPT_RECORD_FEEDBACK_KEYS = (
    "trigger_source",
    "failure_reason_before_retry",
    "runtime_aspect_failure_before_retry",
    "capability_failure_before_retry",
    "scene_energy_failure_before_retry",
    "pacing_rhythm_failure_before_retry",
    "temporal_control_failure_before_retry",
    "improvisational_coherence_failure_before_retry",
    "social_pressure_failure_before_retry",
    "tonal_consistency_failure_before_retry",
    "genre_awareness_failure_before_retry",
    "sensory_context_failure_before_retry",
    "information_disclosure_failure_before_retry",
    "dramatic_irony_failure_before_retry",
    "expectation_variation_failure_before_retry",
    "narrative_momentum_failure_before_retry",
    "meta_narrative_awareness_failure_before_retry",
)


_VALIDATION_EVAL_UPDATE_KEYS = (
    "voice_consistency_validation",
    "scene_energy_validation",
    "pacing_rhythm_validation",
    "temporal_control_validation",
    "improvisational_coherence_validation",
    "social_pressure_validation",
    "tonal_consistency_validation",
    "relationship_state_validation",
    "genre_awareness_validation",
    "symbolic_object_resonance_validation",
    "sensory_context_validation",
    "information_disclosure_validation",
    "dramatic_irony_validation",
    "expectation_variation_validation",
    "narrative_momentum_validation",
    "meta_narrative_awareness_validation",
    "npc_initiative_validation",
)
