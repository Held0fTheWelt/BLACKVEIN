"""Policy-driven opt-in meta-narrative awareness derivation and validation."""

from __future__ import annotations

from typing import Any

from ai_stack.meta_narrative_awareness_contracts import (
    META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
    META_NARRATIVE_AWARENESS_SCHEMA_VERSION_V2,
    META_NARRATIVE_AWARENESS_TIERS,
    META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED,
    META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED,
    META_NARRATIVE_FAILURE_DIRECT_ADDRESS,
    META_NARRATIVE_FAILURE_EVENT_BUDGET_EXCEEDED,
    META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY,
    META_NARRATIVE_FAILURE_FORBIDDEN_MODE,
    META_NARRATIVE_FAILURE_FOURTH_WALL_SCOPE,
    META_NARRATIVE_FAILURE_NOT_OPTED_IN,
    META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY,
    META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE,
    META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR,
    META_NARRATIVE_FAILURE_UNBOUNDED_REWRITE,
    META_NARRATIVE_FOURTH_WALL_LEVELS,
    META_NARRATIVE_INTENSITIES,
    META_NARRATIVE_TRIGGER_FREQUENCIES,
    MetaNarrativeAwarenessTarget,
    MetaNarrativeAwarenessValidation,
    normalize_meta_narrative_awareness_policy,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _clean_str_list(value: Any, *, lower: bool = False) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if lower:
            text = text.lower()
        if text and text not in out:
            out.append(text)
    return out


def _runtime_policy_meta_narrative_awareness(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("meta_narrative_awareness_policy")
    if isinstance(direct, dict):
        return normalize_meta_narrative_awareness_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("meta_narrative_awareness")
    return normalize_meta_narrative_awareness_policy(
        nested if isinstance(nested, dict) else {}
    )


def _experience_settings(story_runtime_experience: dict[str, Any] | None) -> dict[str, Any]:
    raw = story_runtime_experience if isinstance(story_runtime_experience, dict) else {}
    effective = raw.get("effective") if isinstance(raw.get("effective"), dict) else None
    return effective if isinstance(effective, dict) else raw


def _choice(value: Any, allowed: frozenset[str], fallback: str) -> str:
    text = _text(value).lower()
    return text if text in allowed else fallback


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def _selected_responder_ids(selected_responder_set: list[dict[str, Any]] | None) -> list[str]:
    out: list[str] = []
    for row in selected_responder_set or []:
        if not isinstance(row, dict):
            continue
        actor_id = _text(row.get("actor_id") or row.get("responder_id"))
        if actor_id and actor_id not in out:
            out.append(actor_id)
    return out


def _forbidden_actor_ids(actor_lane_context: dict[str, Any] | None) -> set[str]:
    ctx = actor_lane_context if isinstance(actor_lane_context, dict) else {}
    raw_ids = []
    raw_ids.extend(_as_list(ctx.get("ai_forbidden_actor_ids")))
    raw_ids.append(ctx.get("human_actor_id"))
    raw_ids.append(ctx.get("selected_player_role"))
    return {text for text in (_text(item) for item in raw_ids) if text}


def _source_evidence(
    *,
    current_scene_id: str | None,
    selected_scene_function: str | None,
    social_pressure_target: dict[str, Any] | None,
    dramatic_irony_record: dict[str, Any] | None,
    relationship_state_record: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    memory_ref_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    scene_id = _text(current_scene_id)
    if scene_id:
        evidence.append({"source": "current_scene", "field": "current_scene_id", "value": scene_id})
    scene_function = _text(selected_scene_function)
    if scene_function:
        evidence.append(
            {
                "source": "scene_plan_record",
                "field": "selected_scene_function",
                "value": scene_function,
            }
        )
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    if pressure.get("target_band") or pressure.get("trend"):
        evidence.append(
            {
                "source": "social_pressure_target",
                "field": "target_band",
                "value": pressure.get("target_band"),
                "trend": pressure.get("trend"),
            }
        )
    irony = dramatic_irony_record if isinstance(dramatic_irony_record, dict) else {}
    if irony.get("selected_opportunity_ids"):
        evidence.append(
            {
                "source": "dramatic_irony_record",
                "field": "selected_opportunity_ids",
                "count": len(irony.get("selected_opportunity_ids") or []),
            }
        )
    relationship = (
        relationship_state_record if isinstance(relationship_state_record, dict) else {}
    )
    if relationship.get("pressure_band") or relationship.get("transition_events"):
        evidence.append(
            {
                "source": "relationship_state_record",
                "field": "pressure_band",
                "value": relationship.get("pressure_band"),
                "transition_event_count": len(relationship.get("transition_events") or []),
            }
        )
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    move_type = _text(semantic.get("move_type") or semantic.get("primary_move_type"))
    if move_type:
        evidence.append(
            {"source": "semantic_move_record", "field": "move_type", "value": move_type}
        )
    if memory_ref_ids:
        evidence.append(
            {
                "source": "hierarchical_memory_context",
                "field": "memory_ref_ids",
                "count": len(memory_ref_ids),
            }
        )
    return evidence


def _tier_from_settings(settings: dict[str, Any], *, enabled: bool, intensity: str) -> str:
    raw = _text(settings.get("meta_narrative_awareness_tier")).lower()
    if raw in META_NARRATIVE_AWARENESS_TIERS:
        return raw
    if not enabled:
        return "off"
    if intensity == "full_fourth_wall":
        return "full"
    if intensity == "moderate":
        return "adaptive"
    return "subtle"


def _collect_memory_ref_ids(hierarchical_memory_context: dict[str, Any] | None) -> list[str]:
    ctx = hierarchical_memory_context if isinstance(hierarchical_memory_context, dict) else {}
    refs: list[str] = []

    def add(value: Any) -> None:
        text = _text(value)
        if text and text not in refs:
            refs.append(text)

    for key in (
        "selected_memory_ref_ids",
        "memory_ref_ids",
        "memory_refs",
        "reference_ids",
        "item_ids",
    ):
        for item in _as_list(ctx.get(key)):
            if isinstance(item, dict):
                add(
                    item.get("memory_id")
                    or item.get("item_id")
                    or item.get("id")
                    or item.get("ref_id")
                )
            else:
                add(item)
    for key in ("items", "context_items", "memory_items", "projected_items"):
        for item in _as_list(ctx.get(key)):
            if isinstance(item, dict):
                add(
                    item.get("memory_id")
                    or item.get("item_id")
                    or item.get("id")
                    or item.get("ref_id")
                )
    tiers = ctx.get("tiers")
    if isinstance(tiers, dict):
        for rows in tiers.values():
            for item in _as_list(rows):
                if isinstance(item, dict):
                    add(
                        item.get("memory_id")
                        or item.get("item_id")
                        or item.get("id")
                        or item.get("ref_id")
                    )
    return refs


def _adaptive_signal_codes(
    *,
    social_pressure_target: dict[str, Any] | None,
    dramatic_irony_record: dict[str, Any] | None,
    relationship_state_record: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    memory_ref_ids: list[str],
) -> list[str]:
    codes: list[str] = []
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    if _text(pressure.get("target_band")).lower() in {"high", "critical"}:
        codes.append("meta_narrative_adaptive_social_pressure")
    if _text(pressure.get("trend")).lower() in {"rising", "accelerating"}:
        codes.append("meta_narrative_adaptive_pressure_trend")
    irony = dramatic_irony_record if isinstance(dramatic_irony_record, dict) else {}
    if irony.get("selected_opportunity_ids"):
        codes.append("meta_narrative_adaptive_dramatic_irony")
    relationship = (
        relationship_state_record if isinstance(relationship_state_record, dict) else {}
    )
    if relationship.get("transition_events") or _text(
        relationship.get("pressure_band")
    ).lower() in {"high", "critical"}:
        codes.append("meta_narrative_adaptive_relationship_state")
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    if _text(semantic.get("move_type") or semantic.get("primary_move_type")):
        codes.append("meta_narrative_adaptive_player_move")
    if memory_ref_ids:
        codes.append("meta_narrative_adaptive_memory_context")
    return codes


def derive_meta_narrative_awareness(
    *,
    module_runtime_policy: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
    selected_responder_set: list[dict[str, Any]] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    current_scene_id: str | None = None,
    selected_scene_function: str | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    dramatic_irony_record: dict[str, Any] | None = None,
    relationship_state_record: dict[str, Any] | None = None,
    semantic_move_record: dict[str, Any] | None = None,
    hierarchical_memory_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a bounded meta-narrative awareness target for the current turn."""
    policy = _runtime_policy_meta_narrative_awareness(module_runtime_policy)
    settings = _experience_settings(story_runtime_experience)
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    scene_function = _text(
        selected_scene_function
        or plan.get("selected_scene_function")
        or plan.get("scene_function")
    )
    supported_actor_ids = _clean_str_list(policy.get("characters_with_awareness"))
    configured_actor_ids = _clean_str_list(
        settings.get("meta_narrative_characters_with_awareness")
    )
    allowed_actor_ids = [
        actor_id for actor_id in configured_actor_ids if actor_id in set(supported_actor_ids)
    ]
    forbidden_actor_ids = _forbidden_actor_ids(actor_lane_context)
    responder_ids = _selected_responder_ids(selected_responder_set)
    selected_actor_ids = [
        actor_id
        for actor_id in responder_ids
        if actor_id in set(allowed_actor_ids) and actor_id not in forbidden_actor_ids
    ]
    default_intensity = str(policy.get("default_intensity") or "subtle")
    requested_intensity = _choice(
        settings.get("meta_narrative_awareness_intensity"),
        META_NARRATIVE_INTENSITIES,
        default_intensity,
    )
    allowed_intensities = set(_clean_str_list(policy.get("allowed_intensities"), lower=True))
    intensity = requested_intensity if requested_intensity in allowed_intensities else default_intensity
    default_frequency = str(policy.get("default_trigger_frequency") or "rare")
    requested_frequency = _choice(
        settings.get("meta_narrative_trigger_frequency"),
        META_NARRATIVE_TRIGGER_FREQUENCIES,
        default_frequency,
    )
    allowed_frequencies = set(
        _clean_str_list(policy.get("allowed_trigger_frequencies"), lower=True)
    )
    trigger_frequency = (
        requested_frequency if requested_frequency in allowed_frequencies else default_frequency
    )
    opt_in_enabled = bool(settings.get("meta_narrative_awareness_enabled"))
    policy_enabled = bool(policy.get("enabled"))
    requested_tier = _tier_from_settings(
        settings,
        enabled=opt_in_enabled,
        intensity=requested_intensity,
    )
    allowed_tiers = set(_clean_str_list(policy.get("allowed_awareness_tiers"), lower=True))
    default_tier = _text(policy.get("default_awareness_tier")).lower() or "subtle"
    awareness_tier = requested_tier if requested_tier in allowed_tiers else default_tier
    max_events = int(policy.get("max_events_per_turn") or 0)
    max_direct_addresses = int(policy.get("max_direct_addresses_per_turn") or 0)
    memory_ref_ids = _collect_memory_ref_ids(hierarchical_memory_context)
    max_memory_refs = int(policy.get("max_cross_session_memory_refs") or 0)
    direct_player_address_allowed = bool(
        opt_in_enabled
        and awareness_tier == "full"
        and _as_bool(policy.get("allow_direct_player_address"))
        and _as_bool(settings.get("meta_narrative_allow_direct_player_address"))
        and max_direct_addresses > 0
    )
    narrator_negotiation_allowed = bool(
        opt_in_enabled
        and awareness_tier in {"adaptive", "full"}
        and _as_bool(policy.get("allow_narrator_negotiation"))
        and _as_bool(settings.get("meta_narrative_allow_narrator_negotiation"))
    )
    cross_session_memory_allowed = bool(
        opt_in_enabled
        and awareness_tier in {"adaptive", "full"}
        and _as_bool(policy.get("allow_cross_session_memory"))
        and _as_bool(settings.get("meta_narrative_allow_cross_session_memory"))
        and max_memory_refs > 0
        and memory_ref_ids
    )
    selected_memory_ref_ids = (
        memory_ref_ids[:max_memory_refs] if cross_session_memory_allowed else []
    )
    allowed_modes = _clean_str_list(policy.get("allowed_awareness_modes"), lower=True)
    if not direct_player_address_allowed:
        allowed_modes = [
            mode
            for mode in allowed_modes
            if mode not in {"direct_player_address", "fourth_wall_address"}
        ]
    if not narrator_negotiation_allowed:
        allowed_modes = [
            mode
            for mode in allowed_modes
            if mode not in {"narrator_negotiation", "story_form_negotiation"}
        ]
    if not cross_session_memory_allowed:
        allowed_modes = [
            mode
            for mode in allowed_modes
            if mode not in {"cross_session_memory_reference", "character_self_model"}
        ]
    adaptive_signal_codes = _adaptive_signal_codes(
        social_pressure_target=social_pressure_target,
        dramatic_irony_record=dramatic_irony_record,
        relationship_state_record=relationship_state_record,
        semantic_move_record=semantic_move_record,
        memory_ref_ids=memory_ref_ids,
    )
    rationale_codes: list[str] = []
    if not policy_enabled:
        rationale_codes.append("meta_narrative_policy_disabled")
    if policy_enabled and not opt_in_enabled:
        rationale_codes.append("meta_narrative_session_not_opted_in")
    if opt_in_enabled and requested_intensity != intensity:
        rationale_codes.append("meta_narrative_requested_intensity_clamped")
    if opt_in_enabled and requested_frequency != trigger_frequency:
        rationale_codes.append("meta_narrative_requested_frequency_clamped")
    if opt_in_enabled and requested_tier != awareness_tier:
        rationale_codes.append("meta_narrative_requested_tier_clamped")
    if opt_in_enabled and not configured_actor_ids:
        rationale_codes.append("meta_narrative_no_configured_actor")
    elif opt_in_enabled and not allowed_actor_ids:
        rationale_codes.append("meta_narrative_no_supported_configured_actor")
    if opt_in_enabled and allowed_actor_ids and not selected_actor_ids:
        rationale_codes.append("meta_narrative_no_selected_eligible_actor")
    if (
        opt_in_enabled
        and _as_bool(settings.get("meta_narrative_allow_cross_session_memory"))
        and not selected_memory_ref_ids
    ):
        rationale_codes.append("meta_narrative_no_verified_memory_refs")
    if max_events <= 0:
        rationale_codes.append("meta_narrative_event_budget_zero")

    active = bool(
        policy_enabled
        and opt_in_enabled
        and awareness_tier != "off"
        and selected_actor_ids
        and max_events > 0
    )
    if active:
        rationale_codes.append("meta_narrative_opt_in_target_selected")
    schema_version = (
        META_NARRATIVE_AWARENESS_SCHEMA_VERSION_V2
        if (
            awareness_tier in {"adaptive", "full"}
            or direct_player_address_allowed
            or narrator_negotiation_allowed
            or cross_session_memory_allowed
        )
        else META_NARRATIVE_AWARENESS_SCHEMA_VERSION
    )
    target = MetaNarrativeAwarenessTarget(
        schema_version=schema_version,
        policy_version=str(policy.get("schema_version") or ""),
        policy_enabled=policy_enabled,
        opt_in_enabled=opt_in_enabled,
        active=active,
        awareness_tier=awareness_tier,
        intensity=intensity,
        trigger_frequency=trigger_frequency,
        supported_actor_ids=supported_actor_ids,
        configured_actor_ids=configured_actor_ids,
        selected_actor_ids=selected_actor_ids,
        allowed_awareness_modes=allowed_modes,
        forbidden_awareness_modes=_clean_str_list(
            policy.get("forbidden_awareness_modes"), lower=True
        ),
        allowed_fourth_wall_levels=_clean_str_list(
            policy.get("allowed_fourth_wall_levels"), lower=True
        ),
        max_events_per_turn=max_events,
        max_direct_addresses_per_turn=max_direct_addresses,
        requires_player_consent=bool(policy.get("requires_player_consent", True)),
        allow_player_toggle=bool(policy.get("allow_player_toggle", True)),
        direct_player_address_allowed=direct_player_address_allowed,
        narrator_negotiation_allowed=narrator_negotiation_allowed,
        cross_session_memory_allowed=cross_session_memory_allowed,
        memory_retention_scope=str(
            policy.get("default_memory_retention_scope") or "session"
        ),
        selected_memory_ref_ids=selected_memory_ref_ids,
        adaptive_signal_codes=adaptive_signal_codes,
        model_context_visibility=str(
            policy.get("model_context_visibility") or "bounded_structured_only"
        ),
        commit_impact=str(policy.get("default_commit_impact") or "recover"),
        rationale_codes=rationale_codes,
        source_evidence=_source_evidence(
            current_scene_id=current_scene_id,
            selected_scene_function=scene_function,
            social_pressure_target=social_pressure_target,
            dramatic_irony_record=dramatic_irony_record,
            relationship_state_record=relationship_state_record,
            semantic_move_record=semantic_move_record,
            memory_ref_ids=selected_memory_ref_ids,
        ),
    ).to_dict()
    return {"policy": policy, "target": target}


def compact_meta_narrative_awareness_context(
    target: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return model-visible awareness context without player text or hidden facts."""
    src = target if isinstance(target, dict) else {}
    if not src or not src.get("active"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "awareness_tier": src.get("awareness_tier"),
        "intensity": src.get("intensity"),
        "trigger_frequency": src.get("trigger_frequency"),
        "selected_actor_ids": src.get("selected_actor_ids") or [],
        "allowed_awareness_modes": src.get("allowed_awareness_modes") or [],
        "forbidden_awareness_modes": src.get("forbidden_awareness_modes") or [],
        "allowed_fourth_wall_levels": src.get("allowed_fourth_wall_levels") or [],
        "max_events_per_turn": int(src.get("max_events_per_turn") or 0),
        "max_direct_addresses_per_turn": int(
            src.get("max_direct_addresses_per_turn") or 0
        ),
        "direct_player_address_allowed": bool(
            src.get("direct_player_address_allowed")
        ),
        "narrator_negotiation_allowed": bool(src.get("narrator_negotiation_allowed")),
        "cross_session_memory_allowed": bool(src.get("cross_session_memory_allowed")),
        "selected_memory_ref_ids": src.get("selected_memory_ref_ids") or [],
        "adaptive_signal_codes": src.get("adaptive_signal_codes") or [],
        "requires_player_consent": bool(src.get("requires_player_consent")),
        "model_context_visibility": src.get("model_context_visibility"),
        "structured_event_field": "meta_narrative_awareness_events",
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("meta_narrative_awareness_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def validate_meta_narrative_awareness_realization(
    *,
    meta_narrative_awareness_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structured meta-narrative events against opt-in limits."""
    target = (
        meta_narrative_awareness_target
        if isinstance(meta_narrative_awareness_target, dict)
        else {}
    )
    events = _event_rows(structured_output)
    if not target or not bool(target.get("active")):
        if events:
            return MetaNarrativeAwarenessValidation(
                schema_version=META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
                status="rejected",
                contract_pass=False,
                failure_codes=[META_NARRATIVE_FAILURE_NOT_OPTED_IN],
                feedback_code=META_NARRATIVE_FAILURE_NOT_OPTED_IN,
                target=target,
                actual={
                    "structured_events_present": True,
                    "event_count": len(events),
                    "contract_pass": False,
                    "failure_codes": [META_NARRATIVE_FAILURE_NOT_OPTED_IN],
                },
            ).to_dict()
        return MetaNarrativeAwarenessValidation(
            schema_version=META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            target=target,
            actual={"structured_events_present": False, "event_count": 0},
        ).to_dict()

    selected_actor_ids = set(_clean_str_list(target.get("selected_actor_ids")))
    allowed_modes = set(_clean_str_list(target.get("allowed_awareness_modes"), lower=True))
    forbidden_modes = set(
        _clean_str_list(target.get("forbidden_awareness_modes"), lower=True)
    )
    allowed_fourth_wall_levels = set(
        _clean_str_list(target.get("allowed_fourth_wall_levels"), lower=True)
    ) or {"none", "subtle"}
    selected_memory_ref_ids = set(
        _clean_str_list(target.get("selected_memory_ref_ids"))
    )
    max_events = max(0, int(target.get("max_events_per_turn") or 0))
    max_direct_addresses = max(
        0, int(target.get("max_direct_addresses_per_turn") or 0)
    )
    intensity = _text(target.get("intensity")).lower()
    direct_allowed = bool(target.get("direct_player_address_allowed"))
    narrator_negotiation_allowed = bool(target.get("narrator_negotiation_allowed"))
    cross_session_memory_allowed = bool(target.get("cross_session_memory_allowed"))
    failure_codes: list[str] = []
    realized_actor_ids: list[str] = []
    awareness_modes: list[str] = []
    fourth_wall_levels: list[str] = []
    realized_memory_ref_ids: list[str] = []
    direct_address_count = 0
    if len(events) > max_events:
        failure_codes.append(META_NARRATIVE_FAILURE_EVENT_BUDGET_EXCEEDED)
    for row in events:
        actor_id = _text(row.get("actor_id") or row.get("speaker_id"))
        if actor_id and actor_id not in realized_actor_ids:
            realized_actor_ids.append(actor_id)
        if actor_id not in selected_actor_ids:
            failure_codes.append(META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR)
        mode = _text(row.get("awareness_mode") or row.get("mode")).lower()
        if mode and mode not in awareness_modes:
            awareness_modes.append(mode)
        if not mode or mode not in allowed_modes or mode in forbidden_modes:
            failure_codes.append(META_NARRATIVE_FAILURE_FORBIDDEN_MODE)
        if mode in {"narrator_negotiation", "story_form_negotiation"} and not narrator_negotiation_allowed:
            failure_codes.append(META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED)
        if bool(
            row.get("discloses_system_prompt")
            or row.get("discloses_tool_or_model")
            or row.get("references_model_or_tools")
            or row.get("names_runtime_system")
            or row.get("system_disclosure_absent") is False
        ):
            failure_codes.append(META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE)
        if bool(
            row.get("forces_player_revision")
            or row.get("rewrites_player_intent")
            or row.get("unbounded_rewrite")
            or row.get("claims_player_control")
            or row.get("player_agency_preserved") is False
        ):
            failure_codes.append(META_NARRATIVE_FAILURE_UNBOUNDED_REWRITE)
        fourth_wall_level = _text(row.get("fourth_wall_level")).lower()
        if fourth_wall_level and fourth_wall_level not in fourth_wall_levels:
            fourth_wall_levels.append(fourth_wall_level)
        direct_address = bool(row.get("direct_player_address")) or mode in {
            "direct_player_address",
            "fourth_wall_address",
        } or fourth_wall_level in {"direct", "full", "full_fourth_wall"}
        if direct_address:
            direct_address_count += 1
            if not direct_allowed:
                failure_codes.append(META_NARRATIVE_FAILURE_DIRECT_ADDRESS)
        if fourth_wall_level and fourth_wall_level not in allowed_fourth_wall_levels:
            failure_codes.append(META_NARRATIVE_FAILURE_FOURTH_WALL_SCOPE)
        if intensity == "subtle" and (
            bool(row.get("direct_player_address"))
            or fourth_wall_level in {"direct", "full", "full_fourth_wall"}
        ):
            failure_codes.append(META_NARRATIVE_FAILURE_DIRECT_ADDRESS)
        memory_refs = _clean_str_list(
            row.get("memory_ref_ids")
            or row.get("memory_refs")
            or row.get("cross_session_memory_ref_ids")
        )
        single_memory_ref = _text(row.get("memory_ref_id"))
        if single_memory_ref and single_memory_ref not in memory_refs:
            memory_refs.append(single_memory_ref)
        if memory_refs:
            if not cross_session_memory_allowed:
                failure_codes.append(META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED)
            for ref_id in memory_refs:
                if ref_id not in realized_memory_ref_ids:
                    realized_memory_ref_ids.append(ref_id)
                if ref_id not in selected_memory_ref_ids:
                    failure_codes.append(
                        META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED
                    )
        if mode == "cross_session_memory_reference" and not memory_refs:
            failure_codes.append(META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED)
        if bool(
            row.get("quotes_raw_player_input")
            or row.get("raw_player_text_present")
            or row.get("private_player_data_disclosed")
            or row.get("reveals_private_player_data")
        ):
            failure_codes.append(META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY)
        if bool(
            row.get("invented_memory")
            or row.get("unverified_memory_claim")
            or row.get("false_self_memory")
        ):
            failure_codes.append(META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY)

    if direct_address_count > max_direct_addresses:
        failure_codes.append(META_NARRATIVE_FAILURE_FOURTH_WALL_SCOPE)

    deduped_failures = list(dict.fromkeys(failure_codes))
    actual = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "realized_actor_ids": realized_actor_ids,
        "awareness_modes": awareness_modes,
        "fourth_wall_levels": fourth_wall_levels,
        "direct_address_count": direct_address_count,
        "realized_memory_ref_ids": realized_memory_ref_ids,
        "cross_session_memory_ref_count": len(realized_memory_ref_ids),
        "max_events_per_turn": max_events,
        "max_direct_addresses_per_turn": max_direct_addresses,
        "contract_pass": not deduped_failures,
        "failure_codes": deduped_failures,
    }
    return MetaNarrativeAwarenessValidation(
        schema_version=META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
        status="rejected" if deduped_failures else "approved",
        contract_pass=not deduped_failures,
        failure_codes=deduped_failures,
        feedback_code=deduped_failures[0] if deduped_failures else None,
        target=target,
        actual=actual,
        source_evidence=[
            {
                "source": "structured_output",
                "field": "meta_narrative_awareness_events",
                "present": bool(events),
            }
        ],
    ).to_dict()


def build_meta_narrative_awareness_aspect_record(
    *,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible meta-awareness record."""
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy
        if isinstance(policy, dict)
        else normalize_meta_narrative_awareness_policy(None)
    )
    failure_codes = _clean_str_list(validation_dict.get("failure_codes"))
    validation_status = _text(validation_dict.get("status")).lower()
    applicable = bool(target_dict.get("policy_enabled"))
    if not validation_dict:
        aspect_status = "partial" if target_dict.get("active") else "not_applicable"
        applicable = bool(target_dict.get("active"))
    elif validation_status == "approved":
        aspect_status = "passed"
    elif validation_status == "not_applicable":
        aspect_status = "not_applicable"
        applicable = False
    else:
        aspect_status = "failed"
    actual = (
        dict(validation_dict.get("actual"))
        if isinstance(validation_dict.get("actual"), dict)
        else {}
    )
    actual.update(
        {
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    return {
        "applicable": applicable,
        "status": aspect_status,
        "expected": {
            "schema_version": target_dict.get("schema_version")
            or META_NARRATIVE_AWARENESS_SCHEMA_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "opt_in_required": True,
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "allowed_awareness_tiers": policy_dict.get("allowed_awareness_tiers")
            or [],
            "allowed_intensities": policy_dict.get("allowed_intensities") or [],
            "allowed_trigger_frequencies": policy_dict.get("allowed_trigger_frequencies")
            or [],
            "allowed_awareness_modes": target_dict.get("allowed_awareness_modes")
            or policy_dict.get("allowed_awareness_modes")
            or [],
            "forbidden_awareness_modes": target_dict.get("forbidden_awareness_modes")
            or policy_dict.get("forbidden_awareness_modes")
            or [],
            "allowed_fourth_wall_levels": target_dict.get("allowed_fourth_wall_levels")
            or policy_dict.get("allowed_fourth_wall_levels")
            or [],
            "allow_direct_player_address": bool(
                policy_dict.get("allow_direct_player_address")
            ),
            "allow_narrator_negotiation": bool(
                policy_dict.get("allow_narrator_negotiation")
            ),
            "allow_cross_session_memory": bool(
                policy_dict.get("allow_cross_session_memory")
            ),
        },
        "selected": {
            "active": bool(target_dict.get("active")),
            "opt_in_enabled": bool(target_dict.get("opt_in_enabled")),
            "awareness_tier": target_dict.get("awareness_tier"),
            "intensity": target_dict.get("intensity"),
            "trigger_frequency": target_dict.get("trigger_frequency"),
            "supported_actor_ids": target_dict.get("supported_actor_ids") or [],
            "configured_actor_ids": target_dict.get("configured_actor_ids") or [],
            "selected_actor_ids": target_dict.get("selected_actor_ids") or [],
            "max_events_per_turn": int(target_dict.get("max_events_per_turn") or 0),
            "max_direct_addresses_per_turn": int(
                target_dict.get("max_direct_addresses_per_turn") or 0
            ),
            "direct_player_address_allowed": bool(
                target_dict.get("direct_player_address_allowed")
            ),
            "narrator_negotiation_allowed": bool(
                target_dict.get("narrator_negotiation_allowed")
            ),
            "cross_session_memory_allowed": bool(
                target_dict.get("cross_session_memory_allowed")
            ),
            "memory_retention_scope": target_dict.get("memory_retention_scope"),
            "selected_memory_ref_ids": target_dict.get("selected_memory_ref_ids") or [],
            "adaptive_signal_codes": target_dict.get("adaptive_signal_codes") or [],
            "cooldown_applied": bool(target_dict.get("cooldown_applied")),
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            list(target_dict.get("rationale_codes") or [])
            if isinstance(target_dict.get("rationale_codes"), list)
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
