"""Runtime builders and validators for Pi16 dramatic irony."""

from __future__ import annotations

import re
from typing import Any

from ai_stack.dramatic_irony_contracts import (
    DRAMATIC_IRONY_REALIZATION_NOT_EVALUATED,
    DRAMATIC_IRONY_REALIZATION_REALIZED,
    DRAMATIC_IRONY_REALIZATION_REJECTED,
    DRAMATIC_IRONY_REALIZATION_SELECTED_ONLY,
    DRAMATIC_IRONY_SCHEMA_VERSION,
    DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
    DRAMATIC_IRONY_STATUS_NO_OPPORTUNITY,
    DRAMATIC_IRONY_STATUS_NOT_APPLICABLE,
    DRAMATIC_IRONY_STATUS_SELECTED,
    DRAMATIC_IRONY_SURFACE_DIRECT_REVEAL,
    DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
    DRAMATIC_IRONY_VIOLATION_FORBIDDEN_SURFACE_MODE,
    DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO,
    DramaticIronyOpportunity,
    DramaticIronyRealization,
    DramaticIronyRecord,
    KnowledgeFact,
    normalize_dramatic_irony_policy,
)
from ai_stack.story_runtime.npc_agency.npc_agency_contracts import (
    canonical_actor_id,
    coerce_dict_rows,
    dedupe_strings,
    forbidden_actor_ids_from_context,
    npc_actor_ids_from_context,
)


DIRECT_HIDDEN_INTENT_VIOLATION = "forbidden_omniscient_hidden_intent_reveal"
DRAMATIC_IRONY_CONTRACT_VIOLATION = "dramatic_irony_contract_violation"

_DIRECT_REVEAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:secretly|privately|in\s+truth|actually|really|heimlich|insgeheim)\b"
        r".{0,96}\b(?:want|wants|plan|plans|intend|intends|motive|agenda|absicht|motiv|plant)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:hidden|secret|private|true|real|versteckt|geheim|wahr)\s+"
        r"(?:intent|intention|motive|plan|agenda|absicht|motiv)\b",
        re.IGNORECASE,
    ),
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return dedupe_strings(list(value))
    cleaned = _clean_text(value)
    return [cleaned] if cleaned else []


def _actor_id_from_row(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    return canonical_actor_id(
        row.get("actor_id")
        or row.get("responder_id")
        or row.get("runtime_actor_id")
        or row.get("character_key")
    )


def _actor_ids_from_context(
    *,
    actor_lane_context: dict[str, Any] | None,
    selected_responder_set: list[Any] | None,
    character_mind_records: list[Any] | None,
    npc_agency_simulation: dict[str, Any] | None,
) -> list[str]:
    ctx = actor_lane_context if isinstance(actor_lane_context, dict) else {}
    forbidden = forbidden_actor_ids_from_context(ctx)
    raw_ids: list[Any] = []
    raw_ids.extend(npc_actor_ids_from_context(ctx))
    for row in selected_responder_set or []:
        raw_ids.append(_actor_id_from_row(row))
    for row in character_mind_records or []:
        raw_ids.append(_actor_id_from_row(row))
    sim = npc_agency_simulation if isinstance(npc_agency_simulation, dict) else {}
    raw_ids.extend(sim.get("candidate_actor_ids") or [])
    raw_ids.extend(sim.get("ordered_actor_ids") or [])

    out: list[str] = []
    for raw_actor_id in raw_ids:
        actor_id = canonical_actor_id(raw_actor_id)
        if not actor_id or actor_id in out:
            continue
        aliases = {actor_id.lower()}
        if aliases.intersection(forbidden):
            continue
        out.append(actor_id)
    return out


def _module_dramatic_irony_policy(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    module_policy = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = module_policy.get("dramatic_irony_policy")
    if isinstance(direct, dict):
        return normalize_dramatic_irony_policy(direct)
    runtime_governance = (
        module_policy.get("runtime_governance_policy")
        if isinstance(module_policy.get("runtime_governance_policy"), dict)
        else {}
    )
    return normalize_dramatic_irony_policy(
        runtime_governance.get("dramatic_irony")
        if isinstance(runtime_governance.get("dramatic_irony"), dict)
        else None
    )


def _risk_band(
    *,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
) -> str:
    social = social_state_record if isinstance(social_state_record, dict) else {}
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    for key in ("social_risk_band", "scene_risk_band", "risk_band"):
        value = _clean_text(social.get(key) or semantic.get(key)).lower()
        if value in {"low", "moderate", "elevated", "high"}:
            return "high" if value == "elevated" else value
    pressure = _clean_text(social.get("scene_pressure_state") or semantic.get("pressure_tactic")).lower()
    if pressure in {"high", "volatile", "escalating", "threat"}:
        return "high"
    if pressure:
        return "moderate"
    return "low"


def _scene_relevance(
    *,
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
) -> str:
    scene_function = _clean_text(selected_scene_function)
    risk = _risk_band(
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
    )
    if scene_function in {"escalate_conflict", "redirect_blame", "probe_motive", "scene_pivot"}:
        return "high"
    if risk in {"high", "moderate"}:
        return risk
    return "moderate" if scene_function else "low"


def _fact_summary_from_private_plan(row: dict[str, Any]) -> str:
    intent = _clean_text(row.get("intent")) or "maintain_scene_pressure"
    scope = _clean_text(row.get("requirement_scope"))
    target = canonical_actor_id(row.get("target_actor_id"))
    parts = [f"intent:{intent}"]
    if scope:
        parts.append(f"scope:{scope}")
    if target:
        parts.append(f"target:{target}")
    return ";".join(parts)


def _knowledge_facts_from_npc_private_plans(
    *,
    npc_agency_simulation: dict[str, Any] | None,
    actor_ids: list[str],
) -> list[KnowledgeFact]:
    sim = npc_agency_simulation if isinstance(npc_agency_simulation, dict) else {}
    private_plans = coerce_dict_rows(sim.get("npc_private_plans"))
    conflict = (
        sim.get("npc_plan_conflict_resolution")
        if isinstance(sim.get("npc_plan_conflict_resolution"), dict)
        else {}
    )
    selected_private_plan_ids = dedupe_strings(conflict.get("selected_private_plan_ids") or [])
    if not selected_private_plan_ids:
        return []
    selected_id_set = set(selected_private_plan_ids)
    facts: list[KnowledgeFact] = []
    for row in private_plans:
        private_plan_id = _clean_text(row.get("private_plan_id"))
        if not private_plan_id or private_plan_id not in selected_id_set:
            continue
        actor_id = canonical_actor_id(row.get("actor_id"))
        if not actor_id:
            continue
        unknown_to_actor_ids = [candidate for candidate in actor_ids if candidate != actor_id]
        if not unknown_to_actor_ids:
            continue
        fact_id = f"npc_private_plan:{private_plan_id}"
        facts.append(
            KnowledgeFact(
                fact_id=fact_id,
                summary=_fact_summary_from_private_plan(row),
                source=DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
                truth_status="runtime_planner_selected",
                visible_to_player=True,
                known_by_actor_ids=[actor_id],
                unknown_to_actor_ids=unknown_to_actor_ids,
                relevance_tags=_clean_list(
                    [
                        row.get("intent"),
                        row.get("requirement_scope"),
                        row.get("visible_resolution_policy"),
                    ]
                ),
                provenance={
                    "source_schema_version": row.get("schema_version"),
                    "private_plan_id": private_plan_id,
                    "source_intention_thread_ids": list(
                        row.get("source_intention_thread_ids") or []
                    ),
                    "visibility": row.get("private_plan_visibility"),
                },
            )
        )
    return facts


def _source_evidence(
    *,
    fact: KnowledgeFact,
    selected_scene_function: str | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    current_scene_id: str | None,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = [
        {"source": "knowledge_fact", "fact_id": fact.fact_id, "fact_source": fact.source}
    ]
    scene_id = _clean_text(current_scene_id)
    if scene_id:
        evidence.append({"source": "current_scene", "value": scene_id})
    scene_function = _clean_text(selected_scene_function)
    if scene_function:
        evidence.append({"source": "selected_scene_function", "value": scene_function})
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    move_type = _clean_text(semantic.get("move_type") or semantic.get("primary_move_type"))
    if move_type:
        evidence.append({"source": "semantic_move_record", "field": "move_type", "value": move_type})
    social = social_state_record if isinstance(social_state_record, dict) else {}
    risk = _clean_text(social.get("social_risk_band") or social.get("scene_pressure_state"))
    if risk:
        evidence.append({"source": "social_state_record", "field": "risk_or_pressure", "value": risk})
    return evidence


def build_dramatic_irony_record(
    *,
    module_runtime_policy: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    selected_responder_set: list[Any] | None = None,
    character_mind_records: list[Any] | None = None,
    social_state_record: dict[str, Any] | None = None,
    semantic_move_record: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    npc_agency_simulation: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    current_scene_id: str | None = None,
    selected_scene_function: str | None = None,
) -> dict[str, Any]:
    """Build a bounded Pi16 record from planner-owned runtime facts."""
    del scene_plan_record, prior_planner_truth
    policy = _module_dramatic_irony_policy(module_runtime_policy)
    if not policy.get("enabled"):
        return DramaticIronyRecord(
            policy=policy,
            status=DRAMATIC_IRONY_STATUS_NOT_APPLICABLE,
            rationale_codes=["dramatic_irony_policy_disabled"],
        ).to_runtime_dict()

    actor_ids = _actor_ids_from_context(
        actor_lane_context=actor_lane_context,
        selected_responder_set=selected_responder_set,
        character_mind_records=character_mind_records,
        npc_agency_simulation=npc_agency_simulation,
    )
    if not actor_ids:
        return DramaticIronyRecord(
            policy=policy,
            status=DRAMATIC_IRONY_STATUS_NO_OPPORTUNITY,
            rationale_codes=["no_ai_actor_scope"],
        ).to_runtime_dict()

    allowed_sources = set(_clean_list(policy.get("allowed_sources")))
    allowed_surface_modes = _clean_list(policy.get("allowed_surface_modes")) or [
        DRAMATIC_IRONY_SURFACE_MISREAD_REACTION
    ]
    facts = [
        fact
        for fact in _knowledge_facts_from_npc_private_plans(
            npc_agency_simulation=npc_agency_simulation,
            actor_ids=actor_ids,
        )
        if fact.source in allowed_sources
    ]
    risk = _risk_band(
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
    )
    relevance = _scene_relevance(
        selected_scene_function=selected_scene_function,
        semantic_move_record=semantic_move_record,
        social_state_record=social_state_record,
    )
    opportunities: list[DramaticIronyOpportunity] = []
    for fact in facts:
        for ignorant_actor_id in fact.unknown_to_actor_ids:
            opportunity_id = f"{fact.fact_id}:unknown_to:{ignorant_actor_id}"
            opportunities.append(
                DramaticIronyOpportunity(
                    opportunity_id=opportunity_id,
                    fact_id=fact.fact_id,
                    ignorant_actor_id=ignorant_actor_id,
                    scene_relevance=relevance,
                    risk_band=risk,
                    allowed_surface_mode=allowed_surface_modes[0],
                    source_evidence=_source_evidence(
                        fact=fact,
                        selected_scene_function=selected_scene_function,
                        semantic_move_record=semantic_move_record,
                        social_state_record=social_state_record,
                        current_scene_id=current_scene_id,
                    ),
                    rationale_codes=[
                        "player_audience_knows_selected_runtime_fact",
                        "ignorant_actor_in_ai_scope",
                        "surface_mode_bounded",
                    ],
                )
            )
    max_opportunities = int(policy.get("max_opportunities") or 1)
    selected_opportunity_ids = [row.opportunity_id for row in opportunities[:max_opportunities]]
    status = (
        DRAMATIC_IRONY_STATUS_SELECTED
        if selected_opportunity_ids
        else DRAMATIC_IRONY_STATUS_NO_OPPORTUNITY
    )
    rationale_codes = ["dramatic_irony_opportunity_selected"] if selected_opportunity_ids else [
        "no_knowledge_asymmetry_available"
    ]
    return DramaticIronyRecord(
        policy=policy,
        facts=facts,
        opportunities=opportunities,
        selected_opportunity_ids=selected_opportunity_ids,
        status=status,
        rationale_codes=rationale_codes,
    ).to_runtime_dict()


def compact_dramatic_irony_context(record: dict[str, Any] | None) -> dict[str, Any]:
    """Return model-visible Pi16 context without exposing direct hidden prose."""
    src = record if isinstance(record, dict) else {}
    policy = normalize_dramatic_irony_policy(src.get("policy") if isinstance(src.get("policy"), dict) else None)
    selected_id_list = _clean_list(src.get("selected_opportunity_ids"))
    selected_ids = set(selected_id_list)
    opportunities = [
        row
        for row in coerce_dict_rows(src.get("opportunities"))
        if str(row.get("opportunity_id") or "") in selected_ids
    ]
    return {
        "schema_version": src.get("schema_version") or DRAMATIC_IRONY_SCHEMA_VERSION,
        "status": src.get("status") or DRAMATIC_IRONY_STATUS_NOT_APPLICABLE,
        "model_context_visibility": policy.get("model_context_visibility"),
        "allowed_surface_modes": policy.get("allowed_surface_modes") or [],
        "selected_opportunity_ids": selected_id_list,
        "opportunities": [
            {
                "opportunity_id": row.get("opportunity_id"),
                "ignorant_actor_id": row.get("ignorant_actor_id"),
                "scene_relevance": row.get("scene_relevance"),
                "risk_band": row.get("risk_band"),
                "allowed_surface_mode": row.get("allowed_surface_mode"),
                "knowledge_gap_class": "actor_does_not_know_planner_selected_fact",
            }
            for row in opportunities
        ],
        "surface_rule": "Use subtext, behavior, or misread reactions; do not state hidden intent directly.",
    }


def _structured_output_from_generation(generation: dict[str, Any] | None) -> dict[str, Any]:
    gen = generation if isinstance(generation, dict) else {}
    meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    return structured


def _text_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        parts: list[str] = []
        for key in (
            "text",
            "content",
            "line",
            "dialogue",
            "utterance",
            "description",
            "summary",
            "narrative_response",
        ):
            parts.extend(_text_from_value(value.get(key)))
        return parts
    if isinstance(value, list):
        parts: list[str] = []
        for row in value:
            parts.extend(_text_from_value(row))
        return parts
    return []


def _generation_text(
    *,
    generation: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None,
) -> str:
    gen = generation if isinstance(generation, dict) else {}
    structured = _structured_output_from_generation(gen)
    parts: list[str] = []
    for key in ("content", "model_raw_text", "text"):
        parts.extend(_text_from_value(gen.get(key)))
    for key in (
        "narrative_response",
        "narration_summary",
        "spoken_lines",
        "action_lines",
        "initiative_events",
        "state_effects",
    ):
        parts.extend(_text_from_value(structured.get(key)))
    for effect in proposed_state_effects or []:
        parts.extend(_text_from_value(effect))
    return "\n".join(part for part in parts if part).strip()


def _detect_direct_hidden_intent_reveal(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in _DIRECT_REVEAL_PATTERNS)


_DIRECT_REVEAL_VERBS: frozenset[str] = frozenset(
    {
        "want",
        "wants",
        "plan",
        "plans",
        "planned",
        "planning",
        "intend",
        "intends",
        "intended",
        "intention",
        "intent",
        "motive",
        "agenda",
        "absicht",
        "motiv",
        "plant",
    }
)


def _normalized_text(value: Any) -> str:
    text = _clean_text(value).replace("_", " ").replace("-", " ").lower()
    return re.sub(r"[^a-z0-9äöüß]+", " ", text).strip()


def _tokens(value: Any) -> set[str]:
    return {token for token in _normalized_text(value).split() if len(token) > 1}


def _mentions_actor(text_norm: str, actor_id: Any) -> bool:
    actor_norm = _normalized_text(actor_id)
    return bool(actor_norm and f" {actor_norm} " in f" {text_norm} ")


def _summary_parts(summary: Any) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in _clean_text(summary).split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        key_text = _clean_text(key)
        value_text = _clean_text(value)
        if key_text and value_text:
            parts[key_text] = value_text
    return parts


def _selected_fact_ids(record: dict[str, Any]) -> set[str]:
    selected_ids = set(_clean_list(record.get("selected_opportunity_ids")))
    return {
        str(row.get("fact_id") or "")
        for row in coerce_dict_rows(record.get("opportunities"))
        if str(row.get("opportunity_id") or "") in selected_ids
        and str(row.get("fact_id") or "")
    }


def _detect_hidden_fact_echo(record: dict[str, Any], text: str) -> bool:
    if not text:
        return False
    text_norm = _normalized_text(text)
    text_tokens = _tokens(text)
    if not text_tokens.intersection(_DIRECT_REVEAL_VERBS):
        return False
    selected_fact_ids = _selected_fact_ids(record)
    for fact in coerce_dict_rows(record.get("facts")):
        fact_id = str(fact.get("fact_id") or "")
        if fact_id not in selected_fact_ids:
            continue
        if not any(_mentions_actor(text_norm, actor_id) for actor_id in fact.get("known_by_actor_ids") or []):
            continue
        parts = _summary_parts(fact.get("summary"))
        intent_tokens = _tokens(parts.get("intent"))
        if intent_tokens and len(text_tokens.intersection(intent_tokens)) >= min(2, len(intent_tokens)):
            return True
    return False


def _candidate_opportunity_ids(structured_output: dict[str, Any]) -> list[str]:
    raw_ids: list[Any] = []
    for key in ("dramatic_irony_opportunity_ids", "dramatic_irony_refs"):
        raw_ids.extend(structured_output.get(key) or [])
    for key in ("initiative_events", "spoken_lines", "action_lines"):
        for row in coerce_dict_rows(structured_output.get(key)):
            raw_ids.extend(row.get("dramatic_irony_opportunity_ids") or [])
            raw_ids.extend(row.get("dramatic_irony_refs") or [])
    return dedupe_strings(raw_ids)


def _surface_modes_by_opportunity(structured_output: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    ids = _candidate_opportunity_ids(structured_output)
    default_mode = _clean_text(
        structured_output.get("dramatic_irony_surface_mode")
        or structured_output.get("dramatic_irony_mode")
    )
    if default_mode:
        for opportunity_id in ids:
            out.setdefault(opportunity_id, default_mode)
    modes = structured_output.get("dramatic_irony_surface_modes")
    if isinstance(modes, dict):
        for opportunity_id, mode in modes.items():
            oid = _clean_text(opportunity_id)
            mode_text = _clean_text(mode)
            if oid and mode_text:
                out[oid] = mode_text
    for key in ("initiative_events", "spoken_lines", "action_lines"):
        for row in coerce_dict_rows(structured_output.get(key)):
            row_mode = _clean_text(
                row.get("dramatic_irony_surface_mode")
                or row.get("surface_mode")
                or row.get("allowed_surface_mode")
            )
            if not row_mode:
                continue
            for opportunity_id in dedupe_strings(
                (row.get("dramatic_irony_opportunity_ids") or [])
                + (row.get("dramatic_irony_refs") or [])
            ):
                out[opportunity_id] = row_mode
    return out


def _realization_evidence(
    *,
    record: dict[str, Any],
    structured_output: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    selected_ids = set(_clean_list(record.get("selected_opportunity_ids")))
    if not selected_ids:
        return {
            "realized_ids": [],
            "invalid_surface_mode_ids": [],
            "visible_anchor_refs": [],
            "surface_modes": {},
        }
    candidate_ids = [value for value in _candidate_opportunity_ids(structured_output) if value in selected_ids]
    surface_modes = _surface_modes_by_opportunity(structured_output)
    policy = normalize_dramatic_irony_policy(record.get("policy") if isinstance(record.get("policy"), dict) else None)
    allowed_modes = set(_clean_list(policy.get("allowed_surface_modes")))
    forbidden_modes = set(_clean_list(policy.get("forbidden_surface_modes")))
    visible_anchor_present = bool(_clean_text(text))
    realized_ids: list[str] = []
    invalid_surface_mode_ids: list[str] = []
    for opportunity_id in candidate_ids:
        mode = _clean_text(surface_modes.get(opportunity_id))
        if mode in forbidden_modes or (mode and allowed_modes and mode not in allowed_modes):
            invalid_surface_mode_ids.append(opportunity_id)
            continue
        if policy.get("require_structured_realization") and not mode:
            invalid_surface_mode_ids.append(opportunity_id)
            continue
        if visible_anchor_present:
            realized_ids.append(opportunity_id)
    anchor_refs = _clean_list(structured_output.get("dramatic_irony_visible_text_refs")) or realized_ids
    return {
        "realized_ids": dedupe_strings(realized_ids),
        "invalid_surface_mode_ids": dedupe_strings(invalid_surface_mode_ids),
        "visible_anchor_refs": dedupe_strings(anchor_refs),
        "surface_modes": surface_modes,
    }


def validate_dramatic_irony_realization(
    *,
    record: dict[str, Any] | None,
    generation: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate that selected Pi16 opportunities do not become omniscient reveal."""
    src = record if isinstance(record, dict) else {}
    policy = normalize_dramatic_irony_policy(src.get("policy") if isinstance(src.get("policy"), dict) else None)
    selected_ids = _clean_list(src.get("selected_opportunity_ids"))
    structured = _structured_output_from_generation(generation)
    text = _generation_text(generation=generation, proposed_state_effects=proposed_state_effects)
    violation_codes: list[str] = []
    leak_blocked = False
    if selected_ids and not policy.get("direct_reveal_allowed"):
        if _detect_direct_hidden_intent_reveal(text):
            violation_codes.append(DIRECT_HIDDEN_INTENT_VIOLATION)
            leak_blocked = True
        if policy.get("hidden_fact_echo_check") and _detect_hidden_fact_echo(src, text):
            violation_codes.append(DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO)
            leak_blocked = True
    evidence = _realization_evidence(record=src, structured_output=structured, text=text)
    realized_ids = evidence["realized_ids"]
    invalid_surface_mode_ids = evidence["invalid_surface_mode_ids"]
    if invalid_surface_mode_ids:
        violation_codes.append(DRAMATIC_IRONY_VIOLATION_FORBIDDEN_SURFACE_MODE)
    violation_codes = dedupe_strings(violation_codes)
    if violation_codes:
        realization_status = DRAMATIC_IRONY_REALIZATION_REJECTED
    elif realized_ids:
        realization_status = DRAMATIC_IRONY_REALIZATION_REALIZED
    elif selected_ids:
        realization_status = DRAMATIC_IRONY_REALIZATION_SELECTED_ONLY
    else:
        realization_status = DRAMATIC_IRONY_REALIZATION_NOT_EVALUATED
    surface_mode = None
    for opportunity_id in realized_ids:
        mode = _clean_text(evidence["surface_modes"].get(opportunity_id))
        if mode:
            surface_mode = mode
            break
    realization = DramaticIronyRealization(
        status=realization_status,
        selected_opportunity_id=selected_ids[0] if selected_ids else None,
        realized_opportunity_ids=realized_ids,
        surface_mode=DRAMATIC_IRONY_SURFACE_DIRECT_REVEAL
        if violation_codes
        else surface_mode or DRAMATIC_IRONY_SURFACE_MISREAD_REACTION
        if realized_ids
        else None,
        visible_text_refs=realized_ids,
        visible_anchor_refs=evidence["visible_anchor_refs"],
        violation_codes=violation_codes,
        leak_blocked=leak_blocked,
        contract_pass=not violation_codes,
        surface_mode_contract_pass=not invalid_surface_mode_ids,
        hidden_fact_echo_absent=DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO not in violation_codes,
        unused_selected_opportunity_ids=[
            opportunity_id for opportunity_id in selected_ids if opportunity_id not in realized_ids
        ],
    ).model_dump(mode="json")
    updated_record = dict(src)
    updated_record["realization"] = realization
    return {
        "status": "rejected" if violation_codes else "approved",
        "feedback_code": violation_codes[0] if violation_codes else None,
        "contract_pass": not violation_codes,
        "violation_codes": violation_codes,
        "leak_blocked": leak_blocked,
        "selected_opportunity_ids": selected_ids,
        "realized_opportunity_ids": realized_ids,
        "visible_anchor_refs": evidence["visible_anchor_refs"],
        "realization_status": realization_status,
        "surface_mode_contract_pass": not invalid_surface_mode_ids,
        "hidden_fact_echo_absent": DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO not in violation_codes,
        "record": updated_record,
    }


def build_dramatic_irony_aspect_record(
    *,
    record: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible Pi16 aspect record."""
    src = record if isinstance(record, dict) else {}
    validation_src = validation if isinstance(validation, dict) else {}
    policy = normalize_dramatic_irony_policy(src.get("policy") if isinstance(src.get("policy"), dict) else None)
    record_present = bool(src)
    opportunities = coerce_dict_rows(src.get("opportunities"))
    facts = coerce_dict_rows(src.get("facts"))
    selected_ids = _clean_list(src.get("selected_opportunity_ids"))
    selected_fact_ids = dedupe_strings(
        [
            row.get("fact_id")
            for row in opportunities
            if str(row.get("opportunity_id") or "") in set(selected_ids)
        ]
    )
    violation_codes = _clean_list(validation_src.get("violation_codes"))
    status = "failed" if violation_codes else "passed"
    applicable = bool(policy.get("enabled") and record_present)
    if not applicable:
        status = "not_applicable"
    reasons = violation_codes or _clean_list(src.get("rationale_codes"))
    return {
        "applicable": applicable,
        "status": status,
        "expected": {
            "schema_version": DRAMATIC_IRONY_SCHEMA_VERSION,
            "policy_present": record_present,
            "policy_enabled": bool(policy.get("enabled")),
            "allowed_sources": policy.get("allowed_sources") or [],
            "allowed_surface_modes": policy.get("allowed_surface_modes") or [],
            "direct_reveal_allowed": bool(policy.get("direct_reveal_allowed")),
        },
        "selected": {
            "selected_opportunity_ids": selected_ids,
            "selected_fact_ids": selected_fact_ids,
        },
        "actual": {
            "status": src.get("status"),
            "fact_count": len(facts),
            "opportunity_count": len(opportunities),
            "selected_opportunity_count": len(selected_ids),
            "realization_status": validation_src.get("realization_status"),
            "realized_opportunity_ids": validation_src.get("realized_opportunity_ids") or [],
            "visible_anchor_refs": validation_src.get("visible_anchor_refs") or [],
            "leak_blocked": bool(validation_src.get("leak_blocked")),
            "violation_codes": violation_codes,
            "contract_pass": not violation_codes,
            "surface_mode_contract_pass": (
                validation_src.get("surface_mode_contract_pass")
                if "surface_mode_contract_pass" in validation_src
                else not violation_codes
            ),
            "hidden_fact_echo_absent": (
                validation_src.get("hidden_fact_echo_absent")
                if "hidden_fact_echo_absent" in validation_src
                else DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO not in violation_codes
            ),
        },
        "reasons": reasons,
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if violation_codes else None,
        "failure_reason": violation_codes[0] if violation_codes else None,
    }
