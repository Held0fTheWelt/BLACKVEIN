"""Sensory-context derivation and structured validation."""

from __future__ import annotations

from typing import Any

from ai_stack.sensory_context_contracts import (
    SENSORY_CONTEXT_FAILURE_CODES,
    SENSORY_CONTEXT_INTENSITIES,
    SENSORY_CONTEXT_LAYER_KINDS,
    SENSORY_CONTEXT_SCHEMA_VERSION,
    SensoryContextEvidenceRef,
    SensoryContextLayer,
    SensoryContextState,
    SensoryContextTarget,
    SensoryContextValidation,
    normalize_sensory_context_policy,
)


_DEFAULT_MOOD_BY_SCENE_ENERGY: dict[str, str] = {
    "low": "opening",
    "contained": "mid_tension",
    "rising": "mid_tension",
    "volatile": "late_breakdown",
    "collapsed": "late_breakdown",
}

_DEFAULT_MOOD_BY_SCENE_FUNCTION: dict[str, str] = {
    "establish_pressure": "opening",
    "repair_or_stabilize": "mid_tension",
    "withhold_or_evade": "mid_tension",
    "escalate_conflict": "late_breakdown",
    "redirect_blame": "mid_tension",
    "probe_motive": "mid_tension",
    "reveal_surface": "mid_tension",
    "scene_pivot": "mid_tension",
}

_DEFAULT_INTENSITY_BY_PRESSURE_BAND: dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "moderate": "medium",
    "high": "high",
}

def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _evidence(source: str, field: str, value: Any) -> SensoryContextEvidenceRef:
    return SensoryContextEvidenceRef(source=source, field=field, value=value)


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _runtime_policy_sensory_context(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    policy = governance.get("sensory_context")
    if not isinstance(policy, dict):
        policy = raw.get("sensory_context_policy") if isinstance(raw.get("sensory_context_policy"), dict) else {}
    return normalize_sensory_context_policy(policy)


def _locale_language(session_output_language: str | None) -> str:
    value = _clean_text(session_output_language).lower()
    return value[:2] if value else "de"


def _scene_affordances(scene_affordances: dict[str, Any] | None) -> dict[str, Any]:
    raw = scene_affordances if isinstance(scene_affordances, dict) else {}
    nested = raw.get("scene_affordances")
    return nested if isinstance(nested, dict) else raw


def _location_rows(scene_affordances: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    affordances = _scene_affordances(scene_affordances)
    return {
        _clean_text(row.get("id")): row
        for row in (affordances.get("locations") if isinstance(affordances.get("locations"), list) else [])
        if isinstance(row, dict) and _clean_text(row.get("id"))
    }


def _resolve_location_id_from_scene(
    scene_id: str,
    scene_affordances: dict[str, Any] | None,
) -> str | None:
    """Map a scene or alias id to the canonical location id declared in affordances."""

    scene = _clean_text(scene_id).lower()
    if not scene:
        return None
    for row in _location_rows(scene_affordances).values():
        location_id = _clean_text(row.get("id"))
        if not location_id:
            continue
        if scene == location_id.lower():
            return location_id
        aliases = row.get("aliases")
        if not isinstance(aliases, list):
            continue
        alias_set = {_clean_text(alias).lower() for alias in aliases if _clean_text(alias)}
        if scene in alias_set:
            return location_id
    return None


def _object_rows(scene_affordances: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    affordances = _scene_affordances(scene_affordances)
    return {
        _clean_text(row.get("id")): row
        for row in (affordances.get("objects") if isinstance(affordances.get("objects"), list) else [])
        if isinstance(row, dict) and _clean_text(row.get("id"))
    }


def _target_id(player_action_frame: dict[str, Any] | None) -> str | None:
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    target = frame.get("resolved_target") if isinstance(frame.get("resolved_target"), dict) else {}
    value = _clean_text(
        target.get("target_id")
        or target.get("object_id")
        or target.get("location_id")
        or target.get("canonical_name")
    )
    return value or None


def _action_kind(player_action_frame: dict[str, Any] | None) -> str:
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    return _clean_text(frame.get("action_kind") or frame.get("verb")).lower()


def _current_location_id(
    *,
    current_scene_id: str | None,
    scene_affordances: dict[str, Any] | None,
    local_context_transition: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> str | None:
    transition = local_context_transition if isinstance(local_context_transition, dict) else {}
    for key in ("to_area", "current_area", "from_area"):
        value = _clean_text(transition.get(key))
        if value:
            return value
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    prior_state = prior.get("sensory_context_state") if isinstance(prior.get("sensory_context_state"), dict) else {}
    value = _clean_text(prior_state.get("location_id"))
    if value:
        return value
    resolved = _resolve_location_id_from_scene(_clean_text(current_scene_id), scene_affordances)
    if resolved:
        return resolved
    affordances = _scene_affordances(scene_affordances)
    return _clean_text(affordances.get("current_area")) or None


def _mood_key(
    *,
    policy: dict[str, Any],
    scene_plan_record: dict[str, Any] | None,
    scene_energy_target: dict[str, Any] | None,
) -> str:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    target = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    by_function = policy.get("mood_by_scene_function")
    if not isinstance(by_function, dict):
        by_function = {}
    by_energy = policy.get("mood_by_scene_energy")
    if not isinstance(by_energy, dict):
        by_energy = {}
    scene_function = _clean_text(plan.get("selected_scene_function"))
    energy = _clean_text(target.get("energy_level"))
    return (
        _clean_text(by_function.get(scene_function))
        or _DEFAULT_MOOD_BY_SCENE_FUNCTION.get(scene_function)
        or _clean_text(by_energy.get(energy))
        or _DEFAULT_MOOD_BY_SCENE_ENERGY.get(energy)
        or "mid_tension"
    )


def _intensity(
    *,
    policy: dict[str, Any],
    scene_energy_target: dict[str, Any] | None,
    social_pressure_target: dict[str, Any] | None,
) -> str:
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    by_band = policy.get("intensity_by_pressure_band")
    if not isinstance(by_band, dict):
        by_band = {}
    band = _clean_text(pressure.get("target_band") or pressure.get("current_band")).lower()
    value = _clean_text(by_band.get(band) or _DEFAULT_INTENSITY_BY_PRESSURE_BAND.get(band))
    if value in SENSORY_CONTEXT_INTENSITIES:
        return value
    energy = _clean_text((scene_energy_target or {}).get("energy_level")).lower()
    if energy in {"volatile", "collapsed"}:
        return "high"
    if energy in {"low"}:
        return "low"
    return "medium"


def _palette_text(
    narrator_sensory_palette: dict[str, Any] | None,
    *path: str,
) -> str | None:
    node: Any = narrator_sensory_palette if isinstance(narrator_sensory_palette, dict) else {}
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    value = _clean_text(node)
    return value or None


def _palette_ref(
    narrator_sensory_palette: dict[str, Any] | None,
    *path: str,
) -> dict[str, Any] | None:
    node: Any = narrator_sensory_palette if isinstance(narrator_sensory_palette, dict) else {}
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, dict) else None


def _palette_ref_source(ref: dict[str, Any] | None, fallback: str) -> str:
    row = ref if isinstance(ref, dict) else {}
    source = _clean_text(row.get("source"))
    fields = row.get("fields")
    if source:
        if isinstance(fields, list):
            clean_fields = [_clean_text(item) for item in fields if _clean_text(item)]
            if clean_fields:
                return f"{source}#{','.join(clean_fields)}"
        return source
    return fallback


def _source_kind_from_ref(source_ref: str, fallback: str) -> str:
    if source_ref.startswith("locations/"):
        return "locations"
    if source_ref.startswith("objects/"):
        return "objects"
    return fallback


def _localized_detail(row: dict[str, Any], field: str, locale: str) -> str | None:
    detail_map = row.get(field) if isinstance(row.get(field), dict) else {}
    value = detail_map.get(locale) or detail_map.get("de") or detail_map.get("en")
    text = _clean_text(value)
    return text or None


def _layer(
    *,
    layer_id: str,
    layer_kind: str,
    source: str,
    source_field: str,
    source_ref: str,
    text: str | None,
    locale: str | None = None,
    required: bool = True,
) -> SensoryContextLayer | None:
    if not layer_id or layer_kind not in SENSORY_CONTEXT_LAYER_KINDS:
        return None
    return SensoryContextLayer(
        layer_id=layer_id,
        layer_kind=layer_kind,  # type: ignore[arg-type]
        source=source,
        source_field=source_field,
        source_ref=source_ref,
        text=text,
        locale=locale,
        required=required,
    )


def _prior_layer_ids(prior_planner_truth: dict[str, Any] | None) -> list[str]:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    prior_state = prior.get("sensory_context_state")
    if isinstance(prior_state, dict):
        raw = prior_state.get("current_layer_ids") or prior_state.get("prior_layer_ids")
        if isinstance(raw, list):
            return [_clean_text(item) for item in raw if _clean_text(item)][:8]
    return []


def derive_sensory_context(
    *,
    scene_plan_record: dict[str, Any] | None,
    current_scene_id: str | None = None,
    player_action_frame: dict[str, Any] | None = None,
    local_context_transition: dict[str, Any] | None = None,
    narrator_sensory_palette: dict[str, Any] | None = None,
    scene_affordances: dict[str, Any] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
    session_output_language: str | None = None,
) -> dict[str, Any]:
    """Derive bounded sensory target from policy and authored source fields."""

    policy = _runtime_policy_sensory_context(module_runtime_policy)
    if not bool(policy.get("enabled")):
        return {
            "schema_version": SENSORY_CONTEXT_SCHEMA_VERSION,
            "policy": policy,
            "state": {},
            "target": {},
            "source_evidence": [],
            "rationale_codes": ["sensory_context_policy_disabled"],
        }

    locale = _locale_language(session_output_language)
    location_id = _current_location_id(
        current_scene_id=current_scene_id,
        scene_affordances=scene_affordances,
        local_context_transition=local_context_transition,
        prior_planner_truth=prior_planner_truth,
    )
    action_kind = _action_kind(player_action_frame)
    target_id = _target_id(player_action_frame)
    objects = _object_rows(scene_affordances)
    locations = _location_rows(scene_affordances)
    object_id = target_id if target_id in objects and action_kind in {"look_at", "perception", "inspect"} else None
    mood = _mood_key(
        policy=policy,
        scene_plan_record=scene_plan_record,
        scene_energy_target=scene_energy_target,
    )
    intensity = _intensity(
        policy=policy,
        scene_energy_target=scene_energy_target,
        social_pressure_target=social_pressure_target,
    )
    evidence: list[SensoryContextEvidenceRef] = []
    rationale: list[str] = []
    selected: list[SensoryContextLayer] = []

    if mood:
        mood_text = _palette_text(narrator_sensory_palette, "global_mood", mood)
        mood_layer = _layer(
            layer_id=f"mood:{mood}",
            layer_kind="mood",
            source="narrator_sensory_palette",
            source_field=f"global_mood.{mood}",
            source_ref=f"narrator_sensory_palette.global_mood.{mood}",
            text=mood_text,
            locale=None,
            required=False,
        )
        if mood_layer:
            selected.append(mood_layer)
            evidence.append(_evidence("narrator_sensory_palette", f"global_mood.{mood}", bool(mood_text)))
            rationale.append("sensory_context_mood_from_scene_state")

    if location_id:
        room_text = _palette_text(narrator_sensory_palette, "rooms", location_id, "ambient")
        room_ref = _palette_ref(narrator_sensory_palette, "rooms", location_id, "ambient_ref")
        room_source_ref = _palette_ref_source(
            room_ref,
            f"narrator_sensory_palette.rooms.{location_id}.ambient",
        )
        room_layer = _layer(
            layer_id=f"room:{location_id}:ambient",
            layer_kind="room_ambient",
            source=_source_kind_from_ref(room_source_ref, "narrator_sensory_palette") if room_ref else "narrator_sensory_palette",
            source_field=f"rooms.{location_id}.ambient_ref" if room_ref else f"rooms.{location_id}.ambient",
            source_ref=room_source_ref,
            text=room_text,
            locale=None,
            required=True,
        )
        if room_layer:
            selected.append(room_layer)
            evidence.append(_evidence(room_layer.source, room_layer.source_field, bool(room_text or room_ref)))
            rationale.append("sensory_context_room_ambient")
        loc_row = locations.get(location_id)
        if isinstance(loc_row, dict):
            entry_text = _localized_detail(loc_row, "entry_sensory_detail", locale)
            entry_source_ref = _clean_text(loc_row.get("entry_sensory_source_ref")) or (
                f"scene_affordances.locations.{location_id}.entry_sensory_detail"
            )
            entry_layer = _layer(
                layer_id=f"location:{location_id}:entry",
                layer_kind="location_entry",
                source=_source_kind_from_ref(entry_source_ref, "scene_affordances"),
                source_field=f"locations.{location_id}.entry_sensory_source_ref",
                source_ref=entry_source_ref,
                text=entry_text,
                locale=locale,
                required=bool(local_context_transition),
            )
            if entry_layer:
                selected.append(entry_layer)
                evidence.append(_evidence(entry_layer.source, entry_layer.source_field, bool(entry_text)))
                rationale.append("sensory_context_location_entry")

    if object_id:
        object_text = _palette_text(narrator_sensory_palette, "objects", object_id, "glance")
        object_ref = _palette_ref(narrator_sensory_palette, "objects", object_id, "glance_ref")
        object_source_ref = _palette_ref_source(
            object_ref,
            f"narrator_sensory_palette.objects.{object_id}.glance",
        )
        obj_layer = _layer(
            layer_id=f"object:{object_id}:glance",
            layer_kind="object_perception",
            source=_source_kind_from_ref(object_source_ref, "narrator_sensory_palette") if object_ref else "narrator_sensory_palette",
            source_field=f"objects.{object_id}.glance_ref" if object_ref else f"objects.{object_id}.glance",
            source_ref=object_source_ref,
            text=object_text,
            locale=None,
            required=True,
        )
        if obj_layer:
            selected.append(obj_layer)
            evidence.append(_evidence(obj_layer.source, obj_layer.source_field, bool(object_text or object_ref)))
            rationale.append("sensory_context_object_focus")
        obj_row = objects.get(object_id)
        if isinstance(obj_row, dict):
            perception_text = _localized_detail(obj_row, "perception_detail", locale)
            perception_source_ref = _clean_text(obj_row.get("perception_source_ref")) or (
                f"scene_affordances.objects.{object_id}.perception_detail"
            )
            perception_layer = _layer(
                layer_id=f"object:{object_id}:perception",
                layer_kind="object_perception",
                source=_source_kind_from_ref(perception_source_ref, "scene_affordances"),
                source_field=f"objects.{object_id}.perception_source_ref",
                source_ref=perception_source_ref,
                text=perception_text,
                locale=locale,
                required=True,
            )
            if perception_layer:
                selected.append(perception_layer)
                evidence.append(_evidence(perception_layer.source, perception_layer.source_field, bool(perception_text)))
                rationale.append("sensory_context_object_perception")

    min_layers = _bounded_int(policy.get("min_layers_per_turn"), 1, minimum=0, maximum=8)
    max_layers = _bounded_int(policy.get("max_layers_per_turn"), 3, minimum=1, maximum=8)
    if intensity == "low":
        max_layers = min(max_layers, 2)
    elif intensity == "high":
        min_layers = max(min_layers, 2)
    required_layers = [layer for layer in selected if layer.required]
    ordered = required_layers + [layer for layer in selected if layer.layer_id not in {r.layer_id for r in required_layers}]
    selected_layers = ordered[:max_layers]
    if len(selected_layers) < min_layers:
        selected_layers = ordered[: max(min_layers, len(selected_layers))]
    layer_ids = [layer.layer_id for layer in selected_layers]
    prior_layers = _prior_layer_ids(prior_planner_truth)
    repeated = len(set(layer_ids).intersection(prior_layers))
    target = SensoryContextTarget(
        intensity=intensity,  # type: ignore[arg-type]
        location_id=location_id,
        object_id=object_id,
        mood_key=mood,
        selected_layers=selected_layers,
        required_layer_ids=[layer.layer_id for layer in selected_layers if layer.required],
        min_layers_per_turn=min_layers,
        max_layers_per_turn=max_layers,
        require_structured_events=bool(policy.get("require_structured_events", True)),
        source_evidence=evidence,
        rationale_codes=list(dict.fromkeys(rationale)),
    )
    state = SensoryContextState(
        current_layer_ids=layer_ids,
        prior_layer_ids=prior_layers,
        repeated_layer_count=repeated,
        location_id=location_id,
        object_id=object_id,
        mood_key=mood,
        intensity=intensity,  # type: ignore[arg-type]
        source_evidence=evidence,
    )
    return {
        "schema_version": SENSORY_CONTEXT_SCHEMA_VERSION,
        "policy": policy,
        "state": state.to_runtime_dict(),
        "target": target.to_runtime_dict(),
        "source_evidence": [row.to_runtime_dict() for row in evidence],
        "rationale_codes": list(dict.fromkeys(rationale)),
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("sensory_context_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _selected_layer_refs(target: SensoryContextTarget) -> dict[str, str]:
    return {layer.layer_id: layer.source_ref for layer in target.selected_layers}


def validate_sensory_context_realization(
    *,
    sensory_context_target: dict[str, Any] | None,
    sensory_context_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate sensory realization using structured events only."""

    if not isinstance(sensory_context_target, dict) or not sensory_context_target:
        return SensoryContextValidation(
            status="not_applicable",
            contract_pass=True,
            actual={"reason": "sensory_context_target_missing"},
        ).to_runtime_dict()
    try:
        target = SensoryContextTarget.model_validate(sensory_context_target)
    except Exception:
        return SensoryContextValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["sensory_context_target_mismatch"],
            feedback_code="sensory_context_target_mismatch",
            target=sensory_context_target,
            actual={"reason": "invalid_sensory_context_target"},
        ).to_runtime_dict()

    events = _event_rows(structured_output)
    selected_refs = _selected_layer_refs(target)
    selected_ids = set(selected_refs)
    event_ids = [_clean_text(row.get("layer_id")) for row in events if _clean_text(row.get("layer_id"))]
    failure_codes: list[str] = []
    if target.require_structured_events and not events and target.selected_layers:
        failure_codes.append("sensory_context_structured_event_missing")
    for required_id in target.required_layer_ids:
        if required_id not in event_ids:
            failure_codes.append("sensory_context_missing_required_layer")
            break
    for row in events:
        layer_id = _clean_text(row.get("layer_id"))
        if layer_id and layer_id not in selected_ids:
            failure_codes.append("sensory_context_unselected_layer")
            break
        source_ref = _clean_text(row.get("source_ref"))
        if layer_id and source_ref and selected_refs.get(layer_id) != source_ref:
            failure_codes.append("sensory_context_source_ref_mismatch")
            break
    if len(events) > target.max_layers_per_turn:
        failure_codes.append("sensory_context_layer_budget_exceeded")
    failure_codes = [code for code in dict.fromkeys(failure_codes) if code in SENSORY_CONTEXT_FAILURE_CODES]
    state = sensory_context_state if isinstance(sensory_context_state, dict) else {}
    status = "approved" if not failure_codes else "rejected"
    return SensoryContextValidation(
        status=status,  # type: ignore[arg-type]
        contract_pass=not failure_codes,
        failure_codes=failure_codes,
        feedback_code=failure_codes[0] if failure_codes else None,
        target=target.to_runtime_dict(),
        actual={
            "event_count": len(events),
            "realized_layer_ids": event_ids[:8],
            "required_layer_ids": target.required_layer_ids,
            "selected_layer_ids": list(selected_ids),
            "repeated_layer_count": int(state.get("repeated_layer_count") or 0),
        },
        source_evidence=[
            _evidence("structured_output", "sensory_context_events", bool(events)),
        ],
    ).to_runtime_dict()
