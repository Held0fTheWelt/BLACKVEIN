"""Durable relationship-state-machine derivation and validation."""

from __future__ import annotations

import hashlib
from typing import Any

from ai_stack.story_runtime.npc_agency.npc_agency_contracts import dedupe_strings, is_forbidden_actor_id
from ai_stack.relationship_state_contracts import (
    RELATIONSHIP_STATE_FAILURE_CODES,
    RELATIONSHIP_STATE_SCHEMA_VERSION,
    RELATIONSHIP_TRANSITION_CODES,
    RelationshipAxisState,
    RelationshipDynamicsTarget,
    RelationshipPairState,
    RelationshipStateEvidenceRef,
    RelationshipStateRecord,
    RelationshipStateValidation,
    RelationshipTransitionEvent,
    normalize_relationship_state_policy,
)
from ai_stack.runtime_aspect_ledger import make_aspect_record


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return _clean(value).lower()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def _evidence(source: str, field: str, value: Any) -> RelationshipStateEvidenceRef:
    return RelationshipStateEvidenceRef(source=source, field=field, value=value)


def _runtime_policy_relationship_state(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    policy = governance.get("relationship_state_machine")
    if not isinstance(policy, dict):
        policy = (
            raw.get("relationship_state_policy")
            if isinstance(raw.get("relationship_state_policy"), dict)
            else {}
        )
    return normalize_relationship_state_policy(policy)


def relationship_state_fingerprint(record: RelationshipStateRecord) -> str:
    payload = "|".join(
        [
            str(record.turn_number),
            ",".join(record.active_relationship_axis_ids),
            record.dominant_relationship_axis_id or "",
            ";".join(
                f"{row.relationship_id}:{row.tension_score}:{row.trust_score}:{row.alliance_score}:{row.stability_band}"
                for row in record.pair_states
            ),
            ";".join(
                f"{row.transition_id}:{row.transition_code}:{row.relationship_id}"
                for row in record.transition_events
            ),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _canonical_relationships(yaml_slice: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    yslice = yaml_slice if isinstance(yaml_slice, dict) else {}
    rels = yslice.get("relationships") if isinstance(yslice.get("relationships"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for raw_rel_id, row in rels.items():
        if not isinstance(row, dict):
            continue
        rel_id = _clean(row.get("id") or raw_rel_id)
        if not rel_id:
            continue
        axes = row.get("axis_membership") if isinstance(row.get("axis_membership"), list) else []
        out[rel_id] = {
            "relationship_id": rel_id,
            "axis_ids": dedupe_strings(axes),
            "character_ids": _character_ids_for_relationship(rel_id, row),
        }
    return out


def _canonical_axes(yaml_slice: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    yslice = yaml_slice if isinstance(yaml_slice, dict) else {}
    axes = yslice.get("relationship_axes") if isinstance(yslice.get("relationship_axes"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for raw_axis_id, row in axes.items():
        if not isinstance(row, dict):
            continue
        axis_id = _clean(row.get("id") or raw_axis_id)
        if not axis_id:
            continue
        out[axis_id] = {
            "axis_id": axis_id,
            "relationship_ids": dedupe_strings(
                row.get("relationships") if isinstance(row.get("relationships"), list) else []
            ),
        }
    return out


def _character_ids_for_relationship(relationship_id: str, row: dict[str, Any]) -> list[str]:
    raw_chars = row.get("character_ids")
    if isinstance(raw_chars, list):
        return dedupe_strings(raw_chars)[:2]
    return dedupe_strings(
        token
        for token in relationship_id.replace("-", "_").split("_")
        if token and token not in {"and", "vs", "with"}
    )[:2]


def _actor_tokens(actor_id: Any) -> set[str]:
    return {
        token
        for token in _key(actor_id).replace("-", "_").split("_")
        if len(token) > 2 and token not in {"actor", "npc"}
    }


def _relationship_for_actor_pair(
    relationships: dict[str, dict[str, Any]],
    source_actor_id: Any,
    target_actor_id: Any,
) -> str | None:
    source_tokens = _actor_tokens(source_actor_id)
    target_tokens = _actor_tokens(target_actor_id)
    if not source_tokens or not target_tokens:
        return None
    for rel_id, row in relationships.items():
        rel_tokens = set(_actor_tokens(rel_id))
        for char_id in row.get("character_ids") or []:
            rel_tokens.update(_actor_tokens(char_id))
        if source_tokens.intersection(rel_tokens) and target_tokens.intersection(rel_tokens):
            return rel_id
    return None


def _prior_pair_map(prior_relationship_state_record: dict[str, Any] | None) -> tuple[dict[str, RelationshipPairState], str | None]:
    prior = prior_relationship_state_record if isinstance(prior_relationship_state_record, dict) else {}
    if not prior:
        return {}, None
    try:
        model = RelationshipStateRecord.model_validate(prior)
    except Exception:
        return {}, None
    return {row.relationship_id: row for row in model.pair_states}, relationship_state_fingerprint(model)


def _band_for_pair(tension_score: float, trust_score: float, policy: dict[str, Any]) -> str:
    thresholds = policy.get("stability_thresholds") if isinstance(policy.get("stability_thresholds"), dict) else {}
    strained_min = float(thresholds.get("strained_min") or 0.45)
    fractured_min = float(thresholds.get("fractured_min") or 0.72)
    if tension_score >= fractured_min or trust_score <= 0.25:
        return "fractured"
    if tension_score >= strained_min or trust_score <= 0.45:
        return "strained"
    return "stable"


def _trend(current: float, prior: float | None, policy: dict[str, Any]) -> str:
    if prior is None:
        return "stable"
    deadband = float(policy.get("trend_deadband") or 0.04)
    if current - prior > deadband:
        return "rising"
    if prior - current > deadband:
        return "falling"
    return "stable"


def _active_axis_ids(social_state_record: dict[str, Any] | None) -> list[str]:
    social = social_state_record if isinstance(social_state_record, dict) else {}
    return dedupe_strings(
        social.get("active_relationship_axis_ids")
        if isinstance(social.get("active_relationship_axis_ids"), list)
        else []
    )


def _continuity_classes(
    social_state_record: dict[str, Any] | None,
    prior_continuity_impacts: list[dict[str, Any]] | None,
) -> list[str]:
    values: list[Any] = []
    social = social_state_record if isinstance(social_state_record, dict) else {}
    values.extend(
        social.get("prior_continuity_classes")
        if isinstance(social.get("prior_continuity_classes"), list)
        else []
    )
    for row in prior_continuity_impacts if isinstance(prior_continuity_impacts, list) else []:
        if isinstance(row, dict):
            values.append(row.get("class") or row.get("continuity_class"))
    return dedupe_strings(values)


def _social_transition_codes(
    social_state_record: dict[str, Any] | None,
    social_pressure_state: dict[str, Any] | None,
    prior_continuity_impacts: list[dict[str, Any]] | None,
) -> list[str]:
    social = social_state_record if isinstance(social_state_record, dict) else {}
    pressure = social_pressure_state if isinstance(social_pressure_state, dict) else {}
    codes: list[Any] = []
    classes = _continuity_classes(social, prior_continuity_impacts)
    for cls in classes:
        if cls in {"blame_pressure", "repair_attempt", "alliance_shift"}:
            codes.append(cls)
    if _clean(social.get("social_continuity_status")) == "social_state_shifted":
        codes.append("social_state_shifted")
    if _clean(pressure.get("current_band")) == "high" or _clean(social.get("social_risk_band")) == "high":
        codes.append("high_social_pressure")
    if _active_axis_ids(social):
        codes.append("relationship_axis_pressure")
    return dedupe_strings(codes)


def _relationships_for_axes(
    relationships: dict[str, dict[str, Any]],
    axis_ids: list[str],
) -> list[str]:
    if not axis_ids:
        return []
    out: list[str] = []
    axis_set = set(axis_ids)
    for rel_id, row in relationships.items():
        if axis_set.intersection(set(row.get("axis_ids") or [])):
            out.append(rel_id)
    return dedupe_strings(out)


def _npc_edge_relationships(
    relationships: dict[str, dict[str, Any]],
    npc_agency_simulation: dict[str, Any] | None,
) -> list[tuple[str, RelationshipStateEvidenceRef]]:
    simulation = npc_agency_simulation if isinstance(npc_agency_simulation, dict) else {}
    graph = simulation.get("npc_interaction_graph") if isinstance(simulation.get("npc_interaction_graph"), dict) else {}
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    out: list[tuple[str, RelationshipStateEvidenceRef]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        rel_id = _relationship_for_actor_pair(
            relationships,
            edge.get("source_actor_id"),
            edge.get("target_actor_id"),
        )
        if rel_id:
            out.append((rel_id, _evidence("npc_agency_simulation", "npc_interaction_graph.edges", edge.get("edge_type"))))
    return out


def derive_relationship_state(
    *,
    yaml_slice: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    relationship_dynamics_context: dict[str, Any] | None = None,
    npc_agency_simulation: dict[str, Any] | None = None,
    social_pressure_state: dict[str, Any] | None = None,
    prior_relationship_state_record: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
    turn_number: Any = None,
) -> dict[str, Any]:
    """Derive durable relationship state from structured runtime signals."""

    policy = _runtime_policy_relationship_state(module_runtime_policy)
    relationships = _canonical_relationships(yaml_slice)
    axes = _canonical_axes(yaml_slice)
    prior_from_planner = (
        prior_planner_truth.get("relationship_state_record")
        if isinstance(prior_planner_truth, dict) and isinstance(prior_planner_truth.get("relationship_state_record"), dict)
        else None
    )
    prior_pairs, prior_fp = _prior_pair_map(prior_relationship_state_record or prior_from_planner)
    if not relationships and prior_pairs:
        relationships = {
            rel_id: {
                "relationship_id": rel_id,
                "axis_ids": list(row.axis_ids),
                "character_ids": list(row.character_ids),
            }
            for rel_id, row in prior_pairs.items()
        }
    if not relationships:
        return {
            "schema_version": RELATIONSHIP_STATE_SCHEMA_VERSION,
            "policy": policy,
            "state": {},
            "target": {},
            "source_evidence": [],
            "rationale_codes": ["relationship_state_no_canonical_relationships"],
        }

    try:
        turn = int(turn_number or 0)
    except (TypeError, ValueError):
        turn = 0
    max_pairs = int(policy.get("max_tracked_pairs") or 24)
    max_events = int(policy.get("max_transition_events") or 24)
    default_tension = float(policy.get("default_tension_score") or 0.35)
    default_trust = float(policy.get("default_trust_score") or 0.65)
    default_alliance = float(policy.get("default_alliance_score") or 0.2)
    default_dominance = float(policy.get("default_dominance_score") or 0.5)

    active_axis_ids = _active_axis_ids(social_state_record)
    relationship_context = relationship_dynamics_context if isinstance(relationship_dynamics_context, dict) else {}
    active_axis_ids = dedupe_strings(
        active_axis_ids
        + (
            relationship_context.get("active_relationship_axis_ids")
            if isinstance(relationship_context.get("active_relationship_axis_ids"), list)
            else []
        )
    )
    active_relationship_ids = _relationships_for_axes(relationships, active_axis_ids)
    transition_specs: list[tuple[str, str, RelationshipStateEvidenceRef]] = []
    social_codes = _social_transition_codes(
        social_state_record,
        social_pressure_state,
        prior_continuity_impacts,
    )
    if not active_relationship_ids and prior_pairs:
        active_relationship_ids = list(prior_pairs.keys())[:max_pairs]
    if not active_relationship_ids and social_codes:
        active_relationship_ids = list(relationships.keys())[: min(4, max_pairs)]
    for rel_id in active_relationship_ids:
        for code in social_codes:
            transition_specs.append((rel_id, code, _evidence("social_state_record", "relationship_pressure_codes", code)))
    for rel_id, evidence in _npc_edge_relationships(relationships, npc_agency_simulation):
        active_relationship_ids.append(rel_id)
        transition_specs.append((rel_id, "npc_initiative_pressure", evidence))

    active_relationship_ids = dedupe_strings(active_relationship_ids)[:max_pairs]
    if not active_relationship_ids:
        active_relationship_ids = list(relationships.keys())[: min(4, max_pairs)]

    transition_weights = policy.get("transition_weights") if isinstance(policy.get("transition_weights"), dict) else {}
    events: list[RelationshipTransitionEvent] = []
    event_codes_by_rel: dict[str, list[str]] = {}
    deltas_by_rel: dict[str, dict[str, float]] = {}
    for rel_id, code, evidence in transition_specs:
        if rel_id not in active_relationship_ids or code not in transition_weights:
            continue
        deltas = transition_weights.get(code) if isinstance(transition_weights.get(code), dict) else {}
        bucket = deltas_by_rel.setdefault(
            rel_id,
            {"tension_delta": 0.0, "trust_delta": 0.0, "alliance_delta": 0.0, "dominance_delta": 0.0},
        )
        for key in bucket:
            bucket[key] += float(deltas.get(key) or 0.0)
        event_codes_by_rel.setdefault(rel_id, []).append(code)
        event_id = f"{rel_id}:{code}:{turn}:{len(events) + 1}"
        events.append(
            RelationshipTransitionEvent(
                transition_id=event_id,
                turn_number=turn,
                relationship_id=rel_id,
                axis_ids=relationships.get(rel_id, {}).get("axis_ids") or [],
                transition_code=code,
                tension_delta=float(deltas.get("tension_delta") or 0.0),
                trust_delta=float(deltas.get("trust_delta") or 0.0),
                alliance_delta=float(deltas.get("alliance_delta") or 0.0),
                dominance_delta=float(deltas.get("dominance_delta") or 0.0),
                source_evidence=[evidence],
            )
        )
        if len(events) >= max_events:
            break

    pair_states: list[RelationshipPairState] = []
    for rel_id in active_relationship_ids:
        prior = prior_pairs.get(rel_id)
        prior_tension = prior.tension_score if prior else None
        rel = relationships.get(rel_id, {})
        deltas = deltas_by_rel.get(rel_id, {})
        tension = _clamp((prior.tension_score if prior else default_tension) + float(deltas.get("tension_delta") or 0.0))
        trust = _clamp((prior.trust_score if prior else default_trust) + float(deltas.get("trust_delta") or 0.0))
        alliance = _clamp((prior.alliance_score if prior else default_alliance) + float(deltas.get("alliance_delta") or 0.0))
        dominance = _clamp((prior.dominance_score if prior else default_dominance) + float(deltas.get("dominance_delta") or 0.0))
        pair_states.append(
            RelationshipPairState(
                relationship_id=rel_id,
                character_ids=list(rel.get("character_ids") or (prior.character_ids if prior else []))[:2],
                axis_ids=list(rel.get("axis_ids") or (prior.axis_ids if prior else []))[:8],
                tension_score=tension,
                trust_score=trust,
                alliance_score=alliance,
                dominance_score=dominance,
                stability_band=_band_for_pair(tension, trust, policy),  # type: ignore[arg-type]
                trend=_trend(tension, prior_tension, policy),  # type: ignore[arg-type]
                last_transition_codes=dedupe_strings(event_codes_by_rel.get(rel_id, []))[:8],
                last_updated_turn=turn if event_codes_by_rel.get(rel_id) else (prior.last_updated_turn if prior else turn),
            )
        )

    axis_states = _axis_states_from_pairs(
        pair_states=pair_states,
        axes=axes,
        active_axis_ids=active_axis_ids,
        policy=policy,
        max_axes=int(policy.get("max_tracked_axes") or 12),
    )
    if not active_axis_ids:
        active_axis_ids = [row.axis_id for row in axis_states if row.active]
    if not active_axis_ids and axis_states:
        active_axis_ids = [axis_states[0].axis_id]
    dominant_axis_id = active_axis_ids[0] if active_axis_ids else None
    evidence = [
        _evidence("relationship_state_policy", "enabled", policy.get("enabled")),
        _evidence("canonical_relationships", "relationship_count", len(relationships)),
    ]
    social = social_state_record if isinstance(social_state_record, dict) else {}
    if social.get("relationship_pressure_codes"):
        evidence.append(_evidence("social_state_record", "relationship_pressure_codes", social.get("relationship_pressure_codes")))
    if social_pressure_state:
        evidence.append(_evidence("social_pressure_state", "current_band", social_pressure_state.get("current_band")))
    rationale = ["relationship_state_policy_applied"]
    if prior_fp:
        rationale.append("relationship_state_prior_rehydrated")
    if events:
        rationale.append("relationship_state_transition_events")
    record = RelationshipStateRecord(
        turn_number=turn,
        prior_record_fingerprint=prior_fp,
        pair_states=pair_states,
        axis_states=axis_states,
        transition_events=events,
        active_relationship_axis_ids=dedupe_strings(active_axis_ids)[:16],
        dominant_relationship_axis_id=dominant_axis_id,
        source_evidence=evidence[:24],
        rationale_codes=dedupe_strings(rationale),
    )
    target = _target_from_record(record)
    return {
        "schema_version": RELATIONSHIP_STATE_SCHEMA_VERSION,
        "policy": policy,
        "state": record.to_runtime_dict(),
        "target": target.to_runtime_dict(),
        "source_evidence": [row.to_runtime_dict() for row in record.source_evidence],
        "rationale_codes": record.rationale_codes,
    }


def _axis_states_from_pairs(
    *,
    pair_states: list[RelationshipPairState],
    axes: dict[str, dict[str, Any]],
    active_axis_ids: list[str],
    policy: dict[str, Any],
    max_axes: int,
) -> list[RelationshipAxisState]:
    by_axis: dict[str, list[RelationshipPairState]] = {}
    for pair in pair_states:
        for axis_id in pair.axis_ids:
            by_axis.setdefault(axis_id, []).append(pair)
    out: list[RelationshipAxisState] = []
    for axis_id, rows in by_axis.items():
        if not rows:
            continue
        tension = _clamp(sum(row.tension_score for row in rows) / len(rows))
        trust = _clamp(sum(row.trust_score for row in rows) / len(rows))
        transition_codes = dedupe_strings(
            code for row in rows for code in row.last_transition_codes
        )
        out.append(
            RelationshipAxisState(
                axis_id=axis_id,
                relationship_ids=dedupe_strings(row.relationship_id for row in rows)[:16],
                tension_score=tension,
                stability_band=_band_for_pair(tension, trust, policy),  # type: ignore[arg-type]
                trend=_trend(tension, None, policy),  # type: ignore[arg-type]
                active=axis_id in active_axis_ids or bool(transition_codes),
                last_transition_codes=transition_codes[:8],
            )
        )
    for axis_id in active_axis_ids:
        if axis_id not in {row.axis_id for row in out} and axis_id in axes:
            out.append(
                RelationshipAxisState(
                    axis_id=axis_id,
                    relationship_ids=[],
                    tension_score=0.0,
                    stability_band="stable",
                    trend="stable",
                    active=True,
                )
            )
    return sorted(out, key=lambda row: (not row.active, -row.tension_score, row.axis_id))[:max_axes]


def _target_from_record(record: RelationshipStateRecord) -> RelationshipDynamicsTarget:
    active_pairs = sorted(
        record.pair_states,
        key=lambda row: (-row.tension_score, row.relationship_id),
    )
    selected_pairs = active_pairs[:4]
    selected_axes = record.active_relationship_axis_ids[:4] or [
        row.axis_id for row in record.axis_states if row.active
    ][:4]
    transition_codes = dedupe_strings(
        code for event in record.transition_events for code in [event.transition_code]
    )
    band = "stable"
    if any(row.stability_band == "fractured" for row in selected_pairs):
        band = "fractured"
    elif any(row.stability_band == "strained" for row in selected_pairs):
        band = "strained"
    return RelationshipDynamicsTarget(
        target_axis_ids=selected_axes,
        target_relationship_ids=[row.relationship_id for row in selected_pairs],
        required_transition_codes=transition_codes[:6],
        pressure_band=band,  # type: ignore[arg-type]
        requires_visible_relationship_beat=band in {"strained", "fractured"} or bool(transition_codes),
        source_evidence=record.source_evidence[:12],
        rationale_codes=dedupe_strings(
            [
                "relationship_state_target_from_durable_state",
                *("relationship_state_transition_target" for _ in transition_codes[:1]),
            ]
        ),
    )


def validate_relationship_state_realization(
    *,
    relationship_state_record: dict[str, Any] | None,
    relationship_dynamics_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate relationship state using schema and structured event fields only."""

    if not isinstance(relationship_state_record, dict) and not isinstance(relationship_dynamics_target, dict):
        return RelationshipStateValidation(
            status="not_applicable",
            contract_pass=True,
            actual={"reason": "relationship_state_missing"},
        ).to_runtime_dict()
    policy = _runtime_policy_relationship_state(module_runtime_policy)
    failure_codes: list[str] = []
    try:
        record = RelationshipStateRecord.model_validate(relationship_state_record or {})
    except Exception:
        return RelationshipStateValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["relationship_state_missing"],
            target=relationship_dynamics_target if isinstance(relationship_dynamics_target, dict) else {},
            actual={"reason": "invalid_relationship_state_record"},
        ).to_runtime_dict()
    try:
        target = RelationshipDynamicsTarget.model_validate(relationship_dynamics_target or {})
    except Exception:
        return RelationshipStateValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["relationship_target_missing"],
            target=relationship_dynamics_target if isinstance(relationship_dynamics_target, dict) else {},
            actual={"reason": "invalid_relationship_dynamics_target"},
        ).to_runtime_dict()
    pair_ids = {row.relationship_id for row in record.pair_states}
    axis_ids = {row.axis_id for row in record.axis_states}
    for pair in record.pair_states:
        if not (0.0 <= pair.tension_score <= 1.0 and 0.0 <= pair.trust_score <= 1.0):
            failure_codes.append("relationship_pair_score_out_of_bounds")
    for axis in record.axis_states:
        if not (0.0 <= axis.tension_score <= 1.0):
            failure_codes.append("relationship_axis_score_out_of_bounds")
    if any(rel_id not in pair_ids for rel_id in target.target_relationship_ids):
        failure_codes.append("relationship_unknown_target_relationship")
    if any(axis_id not in axis_ids for axis_id in target.target_axis_ids):
        failure_codes.append("relationship_unknown_target_axis")
    allowed_codes = set(policy.get("allowed_transition_codes") or RELATIONSHIP_TRANSITION_CODES)
    if any(code not in allowed_codes for code in target.required_transition_codes):
        failure_codes.append("relationship_unknown_transition_code")
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("relationship_dynamics_events") if isinstance(structured.get("relationship_dynamics_events"), list) else []
    for event in events:
        if not isinstance(event, dict):
            continue
        if _clean(event.get("transition_code")) and _clean(event.get("transition_code")) not in allowed_codes:
            failure_codes.append("relationship_unknown_transition_code")
        for actor_key in ("source_actor_id", "target_actor_id", "actor_id"):
            actor_id = event.get(actor_key)
            if actor_id and is_forbidden_actor_id(actor_id, actor_lane_context=actor_lane_context):
                failure_codes.append("relationship_event_actor_lane_violation")
    failure_codes = [
        code
        for code in dict.fromkeys(failure_codes)
        if code in RELATIONSHIP_STATE_FAILURE_CODES
    ]
    return RelationshipStateValidation(
        status="approved" if not failure_codes else "rejected",
        contract_pass=not failure_codes,
        failure_codes=failure_codes,
        target=target.to_runtime_dict(),
        actual={
            "pair_count": len(record.pair_states),
            "axis_count": len(record.axis_states),
            "transition_event_count": len(record.transition_events),
            "structured_relationship_event_count": len(events),
            "validated_from_schema_and_actor_lane": True,
        },
        source_evidence=record.source_evidence[:8],
    ).to_runtime_dict()


def build_relationship_state_aspect_record(
    *,
    state_record: dict[str, Any] | None,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    state_dict = state_record if isinstance(state_record, dict) else {}
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    failure_codes = [
        str(code)
        for code in (validation_dict.get("failure_codes") or [])
        if str(code).strip()
    ]
    validation_status = _key(validation_dict.get("status"))
    applicable = bool(state_dict or target_dict)
    if not validation_dict:
        aspect_status = "partial" if applicable else "not_applicable"
    elif validation_status == "approved":
        aspect_status = "passed"
    elif validation_status == "not_applicable":
        aspect_status = "not_applicable"
        applicable = False
    elif validation_status == "degraded":
        aspect_status = "partial"
    else:
        aspect_status = "failed"
    actual = (
        dict(validation_dict.get("actual"))
        if isinstance(validation_dict.get("actual"), dict)
        else {}
    )
    actual.update(
        {
            "pair_count": len(state_dict.get("pair_states") or []),
            "axis_count": len(state_dict.get("axis_states") or []),
            "transition_event_count": len(state_dict.get("transition_events") or []),
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    return make_aspect_record(
        applicable=applicable,
        status=aspect_status,
        expected={
            "schema_version": state_dict.get("schema_version") or target_dict.get("schema_version"),
            "policy_present": bool(policy),
            "policy_enabled": bool((policy or {}).get("enabled")),
            "durable_prior_supported": True,
            "validation_uses_schema_and_actor_lane": True,
        },
        selected={
            "state": state_dict,
            "target": target_dict,
            "target_axis_ids": target_dict.get("target_axis_ids") or [],
            "target_relationship_ids": target_dict.get("target_relationship_ids") or [],
            "pressure_band": target_dict.get("pressure_band"),
            "requires_visible_relationship_beat": target_dict.get("requires_visible_relationship_beat"),
        },
        actual=actual,
        reasons=failure_codes or (["relationship_state_target_selected"] if target_dict and not validation_dict else []),
        source=source or ("runtime" if not validation_dict else "validator"),
        failure_class="recoverable_dramatic_failure" if failure_codes else None,
        failure_reason=failure_codes[0] if failure_codes else None,
    )
