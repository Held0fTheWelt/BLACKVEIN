"""Scene-energy derivation and structural validation.

The engine is contract-first: module policy and structured runtime records are
the oracle. Generated prose is never used as an assertion target.
"""

from __future__ import annotations

from typing import Any

from ai_stack.scene_energy_contracts import (
    SCENE_ENERGY_DENSITIES,
    SCENE_ENERGY_FAILURE_CODES,
    SCENE_ENERGY_LEVELS,
    SCENE_ENERGY_PRESSURE_VECTORS,
    SCENE_ENERGY_SCHEMA_VERSION,
    SCENE_ENERGY_TEMPOS,
    SCENE_ENERGY_TRANSITIONS,
    SCENE_ENERGY_VOLATILITIES,
    SceneEnergyEvidenceRef,
    SceneEnergyTarget,
    SceneEnergyTransition,
    SceneEnergyValidation,
    normalize_scene_energy_policy,
)


_DEFAULT_SCENE_FUNCTION_PROFILES: dict[str, dict[str, Any]] = {
    "establish_pressure": {
        "energy_level": "contained",
        "pressure_vector": "social",
        "tempo": "standard",
        "density": "focused",
        "volatility": "stable",
        "target_transition": "hold",
        "minimum_actor_response_count": 1,
    },
    "escalate_conflict": {
        "energy_level": "rising",
        "pressure_vector": "rupture",
        "tempo": "accelerating",
        "density": "layered",
        "volatility": "unstable",
        "target_transition": "rise",
        "minimum_actor_response_count": 2,
    },
    "redirect_blame": {
        "energy_level": "rising",
        "pressure_vector": "social",
        "tempo": "accelerating",
        "density": "layered",
        "volatility": "unstable",
        "target_transition": "rise",
        "minimum_actor_response_count": 2,
    },
    "probe_motive": {
        "energy_level": "contained",
        "pressure_vector": "moral",
        "tempo": "compressed",
        "density": "focused",
        "volatility": "unstable",
        "target_transition": "hold",
        "minimum_actor_response_count": 1,
    },
    "repair_or_stabilize": {
        "energy_level": "contained",
        "pressure_vector": "repair",
        "tempo": "compressed",
        "density": "focused",
        "volatility": "stable",
        "target_transition": "deescalate",
        "minimum_actor_response_count": 1,
    },
    "withhold_or_evade": {
        "energy_level": "contained",
        "pressure_vector": "evasive",
        "tempo": "still",
        "density": "sparse",
        "volatility": "unstable",
        "target_transition": "hold",
        "minimum_actor_response_count": 0,
    },
    "reveal_surface": {
        "energy_level": "rising",
        "pressure_vector": "exposure",
        "tempo": "standard",
        "density": "focused",
        "volatility": "unstable",
        "target_transition": "rise",
        "minimum_actor_response_count": 1,
    },
    "scene_pivot": {
        "energy_level": "contained",
        "pressure_vector": "social",
        "tempo": "compressed",
        "density": "focused",
        "volatility": "stable",
        "target_transition": "pivot",
        "minimum_actor_response_count": 1,
    },
}

_DEFAULT_PACING_PROFILES: dict[str, dict[str, Any]] = {
    "thin_edge": {
        "tempo": "still",
        "density": "sparse",
        "target_transition": "hold",
        "maximum_visible_density_count": 4,
    },
    "compressed": {
        "tempo": "compressed",
        "density": "focused",
        "maximum_visible_density_count": 5,
    },
    "containment": {
        "energy_level": "contained",
        "target_transition": "pivot",
        "maximum_visible_density_count": 6,
    },
    "multi_pressure": {
        "energy_level": "volatile",
        "density": "layered",
        "volatility": "breaking",
        "target_transition": "rise",
        "minimum_actor_response_count": 2,
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _evidence(source: str, field: str, value: Any) -> SceneEnergyEvidenceRef:
    return SceneEnergyEvidenceRef(source=source, field=field, value=value)


def _runtime_policy_scene_energy(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    policy = governance.get("scene_energy")
    if not isinstance(policy, dict):
        policy = raw.get("scene_energy_policy") if isinstance(raw.get("scene_energy_policy"), dict) else {}
    return normalize_scene_energy_policy(policy)


def _profile_value(
    profile: dict[str, Any],
    key: str,
    allowed: frozenset[str],
    default: str,
) -> str:
    value = _clean_text(profile.get(key))
    return value if value in allowed else default


def _profile_int(profile: dict[str, Any], key: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(profile.get(key))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _overlay_profile(
    base: dict[str, Any],
    overlay: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(base)
    if isinstance(overlay, dict):
        for key, value in overlay.items():
            if value is not None:
                out[str(key)] = value
    return out


def _selected_actor_ids(responders: list[dict[str, Any]] | None) -> list[str]:
    out: list[str] = []
    for row in responders or []:
        if not isinstance(row, dict):
            continue
        actor_id = _clean_text(row.get("actor_id") or row.get("responder_id"))
        if actor_id and actor_id not in out:
            out.append(actor_id)
    return out


def _npc_required_actor_ids(npc_agency_simulation: dict[str, Any] | None) -> list[str]:
    sim = npc_agency_simulation if isinstance(npc_agency_simulation, dict) else {}
    for key in ("required_actor_ids", "planned_actor_ids", "selected_private_plan_actor_ids"):
        values = sim.get(key)
        if not isinstance(values, list):
            continue
        out = [_clean_text(value) for value in values if _clean_text(value)]
        if out:
            return list(dict.fromkeys(out))
    return []


def _prior_energy_level(prior_planner_truth: dict[str, Any] | None) -> str | None:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    value = _clean_text(prior.get("scene_energy_level") or prior.get("prior_scene_energy_level"))
    return value if value in SCENE_ENERGY_LEVELS else None


def _has_prior_pressure(
    *,
    prior_planner_truth: dict[str, Any] | None,
    prior_continuity_impacts: list[dict[str, Any]] | None,
    social_state_record: dict[str, Any] | None,
) -> bool:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    if prior.get("carry_forward_tension_notes"):
        return True
    if prior_continuity_impacts:
        return True
    pressure_shift = _clean_text(social.get("social_pressure_shift")).lower()
    if pressure_shift in {"rising", "escalating", "volatile", "compressed"}:
        return True
    return False


def _phase_forbidden_transitions(
    *,
    policy: dict[str, Any],
    scene_plan_record: dict[str, Any] | None,
) -> list[str]:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    phase_policy = plan.get("phase_policy_applied") if isinstance(plan.get("phase_policy_applied"), dict) else {}
    phase_id = _clean_text(phase_policy.get("phase_id") or plan.get("phase_id"))
    limits = policy.get("phase_limits") if isinstance(policy.get("phase_limits"), dict) else {}
    phase_limit = limits.get(phase_id) if phase_id else None
    raw = phase_limit.get("forbidden_transitions") if isinstance(phase_limit, dict) else []
    if not isinstance(raw, list):
        return []
    return [item for item in (_clean_text(value) for value in raw) if item in SCENE_ENERGY_TRANSITIONS]


def derive_scene_energy(
    *,
    scene_plan_record: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None = None,
    social_state_record: dict[str, Any] | None = None,
    pacing_mode: str | None = None,
    silence_brevity_decision: dict[str, Any] | None = None,
    selected_responder_set: list[dict[str, Any]] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    npc_agency_simulation: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a scene-energy target from policy and structured state."""

    policy = _runtime_policy_scene_energy(module_runtime_policy)
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    scene_function = _clean_text(
        plan.get("selected_scene_function") or semantic.get("scene_function") or "establish_pressure"
    )
    pacing = _clean_text(pacing_mode or plan.get("pacing_mode") or "standard") or "standard"
    policy_profiles = policy.get("scene_function_profiles")
    policy_profile = (
        policy_profiles.get(scene_function)
        if isinstance(policy_profiles, dict) and isinstance(policy_profiles.get(scene_function), dict)
        else None
    )
    profile = _overlay_profile(
        _DEFAULT_SCENE_FUNCTION_PROFILES.get(
            scene_function,
            _DEFAULT_SCENE_FUNCTION_PROFILES["establish_pressure"],
        ),
        policy_profile,
    )
    policy_pacing = policy.get("pacing_profiles")
    pacing_overlay = _DEFAULT_PACING_PROFILES.get(pacing, {})
    policy_pacing_overlay = (
        policy_pacing.get(pacing)
        if isinstance(policy_pacing, dict) and isinstance(policy_pacing.get(pacing), dict)
        else None
    )
    profile = _overlay_profile(profile, pacing_overlay)
    profile = _overlay_profile(profile, policy_pacing_overlay)

    evidence = [
        _evidence("scene_plan_record", "selected_scene_function", scene_function),
        _evidence("scene_plan_record", "pacing_mode", pacing),
    ]
    rationale_codes = ["scene_energy_scene_function_profile", "scene_energy_pacing_profile"]

    prior_pressure = _has_prior_pressure(
        prior_planner_truth=prior_planner_truth,
        prior_continuity_impacts=prior_continuity_impacts,
        social_state_record=social_state_record,
    )
    if prior_pressure:
        rationale_codes.append("scene_energy_prior_pressure_present")
        evidence.append(_evidence("prior_runtime_state", "pressure_present", True))

    selected_actor_ids = _selected_actor_ids(selected_responder_set)
    required_actor_ids = _npc_required_actor_ids(npc_agency_simulation)
    if selected_actor_ids:
        evidence.append(_evidence("selected_responder_set", "actor_ids", selected_actor_ids))
    if required_actor_ids:
        rationale_codes.append("scene_energy_npc_required_actor_pressure")
        evidence.append(_evidence("npc_agency_simulation", "required_actor_ids", required_actor_ids))

    min_actor_count = _profile_int(
        profile,
        "minimum_actor_response_count",
        1 if prior_pressure else 0,
        minimum=0,
        maximum=4,
    )
    if prior_pressure and selected_actor_ids and min_actor_count == 0:
        min_actor_count = 1
    if required_actor_ids:
        min_actor_count = max(min_actor_count, min(len(required_actor_ids), 2))
    if selected_actor_ids:
        min_actor_count = min(min_actor_count, len(selected_actor_ids))
    else:
        min_actor_count = 0

    max_density = _profile_int(
        profile,
        "maximum_visible_density_count",
        _profile_int(policy, "default_maximum_visible_density_count", 8, minimum=1, maximum=12),
        minimum=1,
        maximum=12,
    )
    forbidden_transitions = _phase_forbidden_transitions(
        policy=policy,
        scene_plan_record=scene_plan_record,
    )
    target_transition = _profile_value(profile, "target_transition", SCENE_ENERGY_TRANSITIONS, "hold")
    if silence_brevity_decision and isinstance(silence_brevity_decision, dict):
        mode = _clean_text(silence_brevity_decision.get("mode") or silence_brevity_decision.get("brevity_mode"))
        if mode:
            evidence.append(_evidence("silence_brevity_decision", "mode", mode))
    target = SceneEnergyTarget(
        energy_level=_profile_value(profile, "energy_level", SCENE_ENERGY_LEVELS, "contained"),
        pressure_vector=_profile_value(profile, "pressure_vector", SCENE_ENERGY_PRESSURE_VECTORS, "social"),
        tempo=_profile_value(profile, "tempo", SCENE_ENERGY_TEMPOS, "standard"),
        density=_profile_value(profile, "density", SCENE_ENERGY_DENSITIES, "focused"),
        volatility=_profile_value(profile, "volatility", SCENE_ENERGY_VOLATILITIES, "stable"),
        target_transition=target_transition,
        minimum_actor_response_count=min_actor_count,
        maximum_visible_density_count=max_density,
        forbidden_transitions=forbidden_transitions,
        source_evidence=evidence,
        rationale_codes=rationale_codes,
    )
    allowed = target_transition not in forbidden_transitions
    transition = SceneEnergyTransition(
        from_energy_level=_prior_energy_level(prior_planner_truth),
        to_energy_level=target.energy_level,
        transition_intent=target.target_transition,
        allowed=allowed,
        reason_codes=[] if allowed else ["scene_energy_forbidden_escalation"],
    )
    return {
        "schema_version": SCENE_ENERGY_SCHEMA_VERSION,
        "policy": policy,
        "target": target.to_runtime_dict(),
        "transition": transition.to_runtime_dict(),
        "source_evidence": [row.to_runtime_dict() for row in evidence],
        "rationale_codes": list(rationale_codes),
    }


def _structured_rows(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _line_actor_id(row: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(row, dict):
        return ""
    for key in keys:
        actor_id = _clean_text(row.get(key))
        if actor_id:
            return actor_id
    return ""


def _actor_response_ids(structured_output: dict[str, Any] | None) -> list[str]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    out: list[str] = []
    for row in _structured_rows(structured.get("spoken_lines")):
        actor_id = _line_actor_id(row, ("speaker_id", "actor_id", "responder_id"))
        if actor_id and actor_id not in out:
            out.append(actor_id)
    for row in _structured_rows(structured.get("action_lines")):
        actor_id = _line_actor_id(row, ("actor_id", "speaker_id", "responder_id"))
        if actor_id and actor_id not in out:
            out.append(actor_id)
    return out


def _visible_density_count(structured_output: dict[str, Any] | None) -> int:
    structured = structured_output if isinstance(structured_output, dict) else {}
    count = 0
    for key in ("spoken_lines", "action_lines", "initiative_events", "state_effects"):
        count += len(_structured_rows(structured.get(key)))
    for key in (
        "narration_summary",
        "narrative_response",
        "gm_response",
        "consequence_summary",
        "visible_output",
    ):
        if _clean_text(structured.get(key)):
            count += 1
    return count


def validate_scene_energy_realization(
    *,
    scene_energy_target: dict[str, Any] | None,
    scene_energy_transition: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate realization with structured counts and contract fields only."""

    if not isinstance(scene_energy_target, dict):
        return SceneEnergyValidation(
            status="not_applicable",
            contract_pass=True,
            target={},
            actual={"reason": "scene_energy_target_missing"},
        ).to_runtime_dict()
    try:
        target = SceneEnergyTarget.model_validate(scene_energy_target)
    except Exception:
        return SceneEnergyValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["scene_energy_transition_mismatch"],
            feedback_code="scene_energy_transition_mismatch",
            target=scene_energy_target,
            actual={"reason": "invalid_scene_energy_target"},
        ).to_runtime_dict()
    transition_raw = scene_energy_transition if isinstance(scene_energy_transition, dict) else {}
    try:
        transition = SceneEnergyTransition.model_validate(
            transition_raw
            or {
                "to_energy_level": target.energy_level,
                "transition_intent": target.target_transition,
                "allowed": target.target_transition not in target.forbidden_transitions,
            }
        )
    except Exception:
        transition = SceneEnergyTransition(
            to_energy_level=target.energy_level,
            transition_intent=target.target_transition,
            allowed=False,
            reason_codes=["scene_energy_transition_mismatch"],
        )
    actor_ids = _actor_response_ids(structured_output)
    density_count = _visible_density_count(structured_output)
    failure_codes: list[str] = []
    if target.target_transition in target.forbidden_transitions or transition.allowed is False:
        failure_codes.append("scene_energy_forbidden_escalation")
    if transition.transition_intent != target.target_transition or transition.to_energy_level != target.energy_level:
        failure_codes.append("scene_energy_transition_mismatch")
    if len(actor_ids) < target.minimum_actor_response_count:
        failure_codes.append("scene_energy_missing_required_pressure")
    if density_count == 0 and target.energy_level not in {"low", "collapsed"}:
        failure_codes.append("scene_energy_empty_fluency")
    if density_count > target.maximum_visible_density_count:
        failure_codes.append("scene_energy_overloaded_output")

    failure_codes = [
        code for code in dict.fromkeys(failure_codes) if code in SCENE_ENERGY_FAILURE_CODES
    ]
    actual = {
        "actual_actor_response_count": len(actor_ids),
        "actual_actor_ids": actor_ids,
        "visible_density_count": density_count,
        "selected_scene_function": (
            scene_plan_record.get("selected_scene_function")
            if isinstance(scene_plan_record, dict)
            else None
        ),
        "transition_allowed": bool(transition.allowed),
    }
    return SceneEnergyValidation(
        status="approved" if not failure_codes else "rejected",
        contract_pass=not failure_codes,
        failure_codes=failure_codes,
        feedback_code=failure_codes[0] if failure_codes else None,
        target=target.to_runtime_dict(),
        actual=actual,
        source_evidence=[
            _evidence("structured_output", "actor_response_count", len(actor_ids)),
            _evidence("structured_output", "visible_density_count", density_count),
        ],
    ).to_runtime_dict()
