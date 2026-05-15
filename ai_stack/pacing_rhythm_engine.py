"""Pacing-rhythm derivation and structured validation."""

from __future__ import annotations

from typing import Any

from ai_stack.pacing_rhythm_contracts import (
    PACING_RHYTHM_CADENCES,
    PACING_RHYTHM_FAILURE_CODES,
    PACING_RHYTHM_RESPONSE_SHAPES,
    PACING_RHYTHM_SCHEMA_VERSION,
    PACING_RHYTHM_TEMPO_ARCS,
    PACING_RHYTHM_TURN_CHANGE_POLICIES,
    PacingRhythmEvidenceRef,
    PacingRhythmState,
    PacingRhythmTarget,
    PacingRhythmValidation,
    normalize_pacing_rhythm_policy,
)


_DEFAULT_CADENCE_PROFILES: dict[str, dict[str, Any]] = {
    "breathe": {
        "tempo_arc": "still",
        "response_shape": "pause",
        "turn_change_policy": "silence_or_action_only",
        "min_visible_blocks": 0,
        "max_visible_blocks": 3,
        "min_actor_turns": 0,
        "max_actor_turns": 1,
        "requires_pause": True,
    },
    "hold": {
        "tempo_arc": "standard",
        "response_shape": "single_beat",
        "turn_change_policy": "allow_hold",
        "min_visible_blocks": 1,
        "max_visible_blocks": 6,
        "min_actor_turns": 0,
        "max_actor_turns": 3,
    },
    "press": {
        "tempo_arc": "accelerating",
        "response_shape": "exchange",
        "turn_change_policy": "prefer_actor_turn_change",
        "min_visible_blocks": 1,
        "max_visible_blocks": 6,
        "min_actor_turns": 1,
        "max_actor_turns": 4,
    },
    "release": {
        "tempo_arc": "releasing",
        "response_shape": "single_beat",
        "turn_change_policy": "allow_hold",
        "min_visible_blocks": 1,
        "max_visible_blocks": 5,
        "min_actor_turns": 0,
        "max_actor_turns": 2,
    },
    "pivot": {
        "tempo_arc": "compressed",
        "response_shape": "exchange",
        "turn_change_policy": "prefer_actor_turn_change",
        "min_visible_blocks": 1,
        "max_visible_blocks": 6,
        "min_actor_turns": 1,
        "max_actor_turns": 3,
    },
    "interrupt": {
        "tempo_arc": "accelerating",
        "response_shape": "multi_reaction",
        "turn_change_policy": "require_actor_turn_change",
        "min_visible_blocks": 2,
        "max_visible_blocks": 8,
        "min_actor_turns": 2,
        "max_actor_turns": 4,
    },
}

_PACING_TO_CADENCE: dict[str, str] = {
    "thin_edge": "breathe",
    "compressed": "press",
    "containment": "pivot",
    "multi_pressure": "interrupt",
    "standard": "hold",
}

_TRANSITION_TO_CADENCE: dict[str, str] = {
    "hold": "hold",
    "rise": "press",
    "release": "release",
    "deescalate": "release",
    "pivot": "pivot",
    "interrupt": "interrupt",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _evidence(source: str, field: str, value: Any) -> PacingRhythmEvidenceRef:
    return PacingRhythmEvidenceRef(source=source, field=field, value=value)


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _overlay(base: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(base)
    if isinstance(overlay, dict):
        for key, value in overlay.items():
            if value is not None:
                out[str(key)] = value
    return out


def _profile_value(profile: dict[str, Any], key: str, allowed: frozenset[str], default: str) -> str:
    value = _clean_text(profile.get(key))
    return value if value in allowed else default


def _runtime_policy_pacing_rhythm(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    policy = governance.get("pacing_rhythm")
    if not isinstance(policy, dict):
        policy = raw.get("pacing_rhythm_policy") if isinstance(raw.get("pacing_rhythm_policy"), dict) else {}
    return normalize_pacing_rhythm_policy(policy)


def _prior_cadences(
    prior_pacing_rhythm_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> list[str]:
    state = prior_pacing_rhythm_state if isinstance(prior_pacing_rhythm_state, dict) else {}
    raw = state.get("recent_cadences")
    out = [
        str(item).strip()
        for item in (raw if isinstance(raw, list) else [])
        if str(item).strip() in PACING_RHYTHM_CADENCES
    ]
    current = _clean_text(state.get("current_cadence"))
    if current in PACING_RHYTHM_CADENCES and (not out or out[-1] != current):
        out.append(current)
    if out:
        return out[-6:]
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    prior_rhythm = prior.get("pacing_rhythm_state")
    if isinstance(prior_rhythm, dict):
        return _prior_cadences(prior_rhythm, None)
    return []


def _selected_beat_id(scene_plan_record: dict[str, Any] | None) -> str | None:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    selected = plan.get("selected_beat")
    if isinstance(selected, dict):
        beat_id = _clean_text(selected.get("id") or selected.get("selected_beat_id"))
        if beat_id:
            return beat_id
    beat_id = _clean_text(plan.get("selected_beat_id") or plan.get("beat_id"))
    return beat_id or None


def _silence_mode(silence_brevity_decision: dict[str, Any] | None) -> str:
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    return _clean_text(silence.get("mode") or silence.get("brevity_mode"))


def _silence_blocks_forced_speech(silence_brevity_decision: dict[str, Any] | None) -> bool:
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    return bool(silence.get("blocks_forced_speech")) or _silence_mode(silence) == "withheld"


def _cadence_from_inputs(
    *,
    pacing_mode: str,
    scene_energy_target: dict[str, Any],
    silence_brevity_decision: dict[str, Any] | None,
) -> tuple[str, list[PacingRhythmEvidenceRef], list[str]]:
    evidence: list[PacingRhythmEvidenceRef] = []
    rationale: list[str] = []
    silence_mode = _silence_mode(silence_brevity_decision)
    if silence_mode == "withheld":
        evidence.append(_evidence("silence_brevity_decision", "mode", silence_mode))
        return "breathe", evidence, ["pacing_rhythm_silence_withheld"]
    transition = _clean_text(scene_energy_target.get("target_transition"))
    cadence = _TRANSITION_TO_CADENCE.get(transition)
    if cadence:
        evidence.append(_evidence("scene_energy_target", "target_transition", transition))
        rationale.append("pacing_rhythm_scene_energy_transition")
    pacing_cadence = _PACING_TO_CADENCE.get(pacing_mode)
    if pacing_cadence:
        evidence.append(_evidence("scene_plan_record", "pacing_mode", pacing_mode))
        rationale.append("pacing_rhythm_pacing_profile")
    if pacing_mode == "thin_edge" and silence_mode == "brief":
        return "breathe", evidence, rationale + ["pacing_rhythm_brief_thin_edge"]
    return pacing_cadence or cadence or "hold", evidence, rationale or ["pacing_rhythm_default_hold"]


def derive_pacing_rhythm(
    *,
    scene_plan_record: dict[str, Any] | None,
    pacing_mode: str | None = None,
    silence_brevity_decision: dict[str, Any] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    selected_responder_set: list[dict[str, Any]] | None = None,
    prior_pacing_rhythm_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    prior_dramatic_signature: dict[str, Any] | None = None,
    prior_narrative_thread_state: dict[str, Any] | None = None,
    prior_callback_web_state: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a bounded rhythm state and target from structured runtime state."""

    policy = _runtime_policy_pacing_rhythm(module_runtime_policy)
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    target_energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    pacing = _clean_text(pacing_mode or plan.get("pacing_mode") or "standard") or "standard"
    cadence, evidence, rationale = _cadence_from_inputs(
        pacing_mode=pacing,
        scene_energy_target=target_energy,
        silence_brevity_decision=silence_brevity_decision,
    )

    prior_cads = _prior_cadences(prior_pacing_rhythm_state, prior_planner_truth)
    prior_cadence = prior_cads[-1] if prior_cads else None
    repeated_count = 1
    if prior_cadence == cadence:
        repeated_count += sum(1 for item in reversed(prior_cads[:-1]) if item == cadence)
    max_repeated = int(policy.get("max_repeated_cadence_count") or 2)
    release_due = cadence in {"press", "interrupt"} and repeated_count >= max_repeated
    if release_due and _clean_text(target_energy.get("target_transition")) not in {"rise", "interrupt"}:
        cadence = "release"
        rationale.append("pacing_rhythm_release_after_repetition")

    thread_pressure = 0
    thread_state = prior_narrative_thread_state if isinstance(prior_narrative_thread_state, dict) else {}
    try:
        thread_pressure = int(thread_state.get("thread_pressure_level") or 0)
    except (TypeError, ValueError):
        thread_pressure = 0
    callback_state = prior_callback_web_state if isinstance(prior_callback_web_state, dict) else {}
    if callback_state.get("selected_edge_id") and cadence == "hold" and thread_pressure >= 2:
        cadence = "press"
        rationale.append("pacing_rhythm_callback_thread_pressure")

    policy_profiles = policy.get("cadence_profiles") if isinstance(policy.get("cadence_profiles"), dict) else {}
    pacing_profiles = policy.get("pacing_mode_profiles") if isinstance(policy.get("pacing_mode_profiles"), dict) else {}
    scene_profiles = policy.get("scene_function_profiles") if isinstance(policy.get("scene_function_profiles"), dict) else {}
    scene_function = _clean_text(plan.get("selected_scene_function"))
    profile = _DEFAULT_CADENCE_PROFILES.get(cadence, _DEFAULT_CADENCE_PROFILES["hold"])
    profile = _overlay(profile, policy_profiles.get(cadence) if isinstance(policy_profiles, dict) else None)
    profile = _overlay(profile, pacing_profiles.get(pacing) if isinstance(pacing_profiles, dict) else None)
    profile = _overlay(profile, scene_profiles.get(scene_function) if scene_function else None)

    if _silence_blocks_forced_speech(silence_brevity_decision):
        profile = _overlay(
            profile,
            {
                "turn_change_policy": "silence_or_action_only",
                "requires_pause": True,
                "blocks_forced_speech": True,
                "min_actor_turns": 0,
                "max_actor_turns": min(1, _bounded_int(profile.get("max_actor_turns"), 1, minimum=0, maximum=4)),
            },
        )
        rationale.append("pacing_rhythm_forced_speech_block")

    responders = selected_responder_set if isinstance(selected_responder_set, list) else []
    responder_count = len([row for row in responders if isinstance(row, dict)])
    min_actor_turns = _bounded_int(profile.get("min_actor_turns"), 0, minimum=0, maximum=4)
    if profile.get("turn_change_policy") == "require_actor_turn_change" and responder_count >= 2:
        min_actor_turns = max(min_actor_turns, 2)
    max_blocks_default = int(policy.get("default_max_visible_blocks") or 6)
    max_visible_blocks = _bounded_int(profile.get("max_visible_blocks"), max_blocks_default, minimum=1, maximum=12)
    min_visible_blocks = _bounded_int(profile.get("min_visible_blocks"), 1, minimum=0, maximum=max_visible_blocks)

    state = PacingRhythmState(
        current_cadence=cadence,  # type: ignore[arg-type]
        prior_cadence=prior_cadence,  # type: ignore[arg-type]
        recent_cadences=(prior_cads + [cadence])[-6:],  # type: ignore[list-item]
        repeated_cadence_count=repeated_count,
        pressure_streak=(
            repeated_count
            if cadence in {"press", "interrupt"}
            else max(0, thread_pressure)
        ),
        release_due=release_due,
        pause_obligation_active=bool(profile.get("requires_pause")),
        last_pacing_mode=pacing,
        last_scene_function=scene_function or None,
        last_beat_id=_selected_beat_id(plan)
        or _clean_text((prior_dramatic_signature or {}).get("prior_beat_id"))
        or None,
        source_evidence=evidence,
    )
    target = PacingRhythmTarget(
        cadence=cadence,  # type: ignore[arg-type]
        tempo_arc=_profile_value(profile, "tempo_arc", PACING_RHYTHM_TEMPO_ARCS, "standard"),  # type: ignore[arg-type]
        response_shape=_profile_value(profile, "response_shape", PACING_RHYTHM_RESPONSE_SHAPES, "single_beat"),  # type: ignore[arg-type]
        turn_change_policy=_profile_value(
            profile,
            "turn_change_policy",
            PACING_RHYTHM_TURN_CHANGE_POLICIES,
            "allow_hold",
        ),  # type: ignore[arg-type]
        min_visible_blocks=min_visible_blocks,
        max_visible_blocks=max_visible_blocks,
        min_actor_turns=min_actor_turns,
        max_actor_turns=_bounded_int(profile.get("max_actor_turns"), 4, minimum=0, maximum=4),
        requires_pause=bool(profile.get("requires_pause", False)),
        blocks_forced_speech=bool(profile.get("blocks_forced_speech", False)),
        release_due_after_turn=release_due,
        source_evidence=evidence,
        rationale_codes=list(dict.fromkeys(rationale)),
    )
    return {
        "schema_version": PACING_RHYTHM_SCHEMA_VERSION,
        "policy": policy,
        "state": state.to_runtime_dict(),
        "target": target.to_runtime_dict(),
        "source_evidence": [row.to_runtime_dict() for row in evidence],
        "rationale_codes": list(dict.fromkeys(rationale)),
    }


def _structured_rows(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _row_actor_id(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    for key in ("speaker_id", "actor_id", "responder_id"):
        actor_id = _clean_text(row.get(key))
        if actor_id:
            return actor_id
    return ""


def _actor_turn_ids(structured_output: dict[str, Any] | None) -> list[str]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    out: list[str] = []
    for key in ("spoken_lines", "action_lines"):
        for row in _structured_rows(structured.get(key)):
            actor_id = _row_actor_id(row)
            if actor_id:
                out.append(actor_id)
    return out


def _visible_block_count(structured_output: dict[str, Any] | None) -> int:
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


def validate_pacing_rhythm_realization(
    *,
    pacing_rhythm_target: dict[str, Any] | None,
    pacing_rhythm_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate rhythm realization using structured output only."""

    if not isinstance(pacing_rhythm_target, dict):
        return PacingRhythmValidation(
            status="not_applicable",
            contract_pass=True,
            actual={"reason": "pacing_rhythm_target_missing"},
        ).to_runtime_dict()
    try:
        target = PacingRhythmTarget.model_validate(pacing_rhythm_target)
    except Exception:
        return PacingRhythmValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["pacing_rhythm_target_mismatch"],
            feedback_code="pacing_rhythm_target_mismatch",
            target=pacing_rhythm_target,
            actual={"reason": "invalid_pacing_rhythm_target"},
        ).to_runtime_dict()

    visible_count = _visible_block_count(structured_output)
    actor_turn_ids = _actor_turn_ids(structured_output)
    unique_actor_turn_count = len(dict.fromkeys(actor_turn_ids))
    spoken_count = len(_structured_rows((structured_output or {}).get("spoken_lines")))
    failure_codes: list[str] = []
    if visible_count < target.min_visible_blocks:
        failure_codes.append("pacing_rhythm_underrealized_cadence")
    if visible_count > target.max_visible_blocks:
        failure_codes.append("pacing_rhythm_visible_density_exceeded")
    if unique_actor_turn_count < target.min_actor_turns:
        failure_codes.append("pacing_rhythm_required_turn_change_missing")
    if target.requires_pause and visible_count > target.max_visible_blocks:
        failure_codes.append("pacing_rhythm_pause_obligation_lost")
    if target.blocks_forced_speech and spoken_count > 0:
        failure_codes.append("pacing_rhythm_forced_speech_violation")
    state = pacing_rhythm_state if isinstance(pacing_rhythm_state, dict) else {}
    repeated_count = _bounded_int(state.get("repeated_cadence_count"), 0, minimum=0, maximum=6)
    release_due = bool(state.get("release_due"))
    if release_due and target.cadence not in {"release", "breathe"}:
        failure_codes.append("pacing_rhythm_flat_repetition")
    failure_codes = [code for code in dict.fromkeys(failure_codes) if code in PACING_RHYTHM_FAILURE_CODES]
    status = "approved" if not failure_codes else "rejected"
    return PacingRhythmValidation(
        status=status,  # type: ignore[arg-type]
        contract_pass=not failure_codes,
        failure_codes=failure_codes,
        feedback_code=failure_codes[0] if failure_codes else None,
        target=target.to_runtime_dict(),
        actual={
            "visible_block_count": visible_count,
            "actor_turn_count": unique_actor_turn_count,
            "actor_turn_ids": actor_turn_ids[:8],
            "spoken_line_count": spoken_count,
            "repeated_cadence_count": repeated_count,
            "release_due": release_due,
        },
    ).to_runtime_dict()
