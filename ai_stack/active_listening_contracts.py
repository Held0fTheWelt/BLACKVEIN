"""Bounded active-listening contracts for Pi34 local runtime evidence.

The functions in this module derive structured evidence from existing runtime
surfaces. They do not run an LLM, store raw player input, mutate story truth, or
change commit/readiness gates.
"""

from __future__ import annotations

from typing import Any

from story_runtime_core.player_input_intent_contract import (
    is_action_like_player_input_kind,
    is_known_player_input_kind,
    is_non_story_control_player_input_kind,
    is_perception_like_player_input_kind,
    is_speech_like_player_input_kind,
    normalize_player_input_kind,
    player_input_kind_family,
)


BROAD_NLU_LISTENING_SCHEMA_VERSION = "broad_nlu_listening.v1"
CONVERSATIONAL_MEMORY_SCHEMA_VERSION = "conversational_memory.v1"
PROMPT_AUTHORITY_SCHEMA_VERSION = "prompt_authority.v1"

LOCAL_PROOF_LEVEL = "local_only"
LOCAL_EVIDENCE_SCOPE = "local_runtime_projection"

_RECORD_VERSION = "runtime_aspect_record.v1"


def _text(value: Any, *, max_chars: int = 160) -> str:
    return str(value or "").strip()[:max_chars]


def _unique_texts(values: Any, *, max_items: int = 8) -> list[str]:
    rows = values if isinstance(values, list) else [values]
    out: list[str] = []
    for raw in rows:
        text = _text(raw)
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _record(
    *,
    applicable: bool,
    status: str,
    expected: dict[str, Any] | None = None,
    selected: dict[str, Any] | None = None,
    actual: dict[str, Any] | None = None,
    reasons: list[str] | None = None,
    source: str = "runtime",
    failure_class: str | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "applicable": bool(applicable),
        "status": status,
        "expected": expected or {},
        "selected": selected or {},
        "actual": actual or {},
        "reasons": [str(reason) for reason in (reasons or []) if str(reason).strip()],
        "source": source,
        "record_version": _RECORD_VERSION,
        "failure_class": failure_class,
        "failure_reason": failure_reason,
    }


def _primary_discourse_act(
    *,
    kind: str,
    player_input_kind: str,
    intent: str,
    ambiguity: str,
) -> str:
    if is_non_story_control_player_input_kind(player_input_kind) or kind == "meta":
        return "meta_control"
    if kind == "explicit_command":
        return "explicit_command"
    if player_input_kind == "question" or intent == "question_utterance":
        return "question"
    if "withheld_response_or_silence" in intent or "silence" in intent:
        return "withheld_or_silence"
    if is_perception_like_player_input_kind(player_input_kind):
        return "perception_request"
    if player_input_kind == "wait_or_observe":
        return "wait_or_observe"
    if player_input_kind_family(player_input_kind) == "mixed" or kind == "mixed":
        return "mixed_action_speech"
    if is_action_like_player_input_kind(player_input_kind):
        return "action_request"
    if is_speech_like_player_input_kind(player_input_kind):
        return "speech_act"
    if ambiguity or kind in {"ambiguous", "unclear"}:
        return "ambiguous_player_intent"
    return "unspecified_player_intent"


def _response_expectation(interpreted_input: dict[str, Any]) -> str:
    narrator = bool(interpreted_input.get("narrator_response_expected"))
    npc = bool(interpreted_input.get("npc_response_expected"))
    if narrator and npc:
        return "narrator_and_npc_response"
    if narrator:
        return "narrator_response"
    if npc:
        return "npc_response"
    return "no_story_response_expected"


def derive_broad_nlu_listening(
    *,
    interpreted_input: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive structured local NLU/listening evidence without raw text."""
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    entities = interp.get("entities") if isinstance(interp.get("entities"), dict) else {}
    kind = normalize_player_input_kind(interp.get("kind"))
    player_input_kind = normalize_player_input_kind(
        interp.get("player_input_kind") or interp.get("input_kind") or kind
    )
    intent = _text(interp.get("intent")).lower()
    ambiguity = _text(interp.get("ambiguity")).lower()
    confidence_raw = interp.get("confidence")
    try:
        confidence = max(0.0, min(1.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 0.0

    target_refs = _unique_texts(
        [
            entities.get("target_actor_id"),
            entities.get("target_actor"),
            interp.get("target_actor_id"),
            semantic.get("target_actor_hint"),
        ],
        max_items=6,
    )
    object_refs = _unique_texts(
        [
            entities.get("object_id"),
            entities.get("object"),
            interp.get("object_id"),
            interp.get("location_id"),
        ],
        max_items=6,
    )
    source_refs = [
        "interpreted_input.kind",
        "interpreted_input.player_input_kind",
        "interpreted_input.confidence",
    ]
    if semantic:
        source_refs.append("semantic_move_record")
    if target_refs:
        source_refs.append("interpreted_input.entities.target")
    if object_refs:
        source_refs.append("interpreted_input.entities.object")

    repair_prompt_recommended = bool(
        ambiguity
        or kind in {"ambiguous", "unclear"}
        or player_input_kind in {"ambiguous", "unclear"}
        or confidence < 0.52
    )
    ambiguity_codes = _unique_texts(
        [
            ambiguity,
            "unknown_player_input_kind"
            if player_input_kind and not is_known_player_input_kind(player_input_kind)
            else None,
        ],
        max_items=6,
    )
    return {
        "schema_version": BROAD_NLU_LISTENING_SCHEMA_VERSION,
        "primary_discourse_act": _primary_discourse_act(
            kind=kind,
            player_input_kind=player_input_kind,
            intent=intent,
            ambiguity=ambiguity,
        ),
        "kind": kind,
        "player_input_kind": player_input_kind,
        "intent": intent or None,
        "confidence": confidence,
        "ambiguity_codes": ambiguity_codes,
        "repair_prompt_recommended": repair_prompt_recommended,
        "response_expectation": _response_expectation(interp),
        "target_actor_refs": target_refs,
        "object_refs": object_refs,
        "semantic_move_type": _text(semantic.get("move_type")) or None,
        "ranked_move_candidate_count": len(
            semantic.get("ranked_move_candidates")
            if isinstance(semantic.get("ranked_move_candidates"), list)
            else []
        ),
        "raw_player_input_included": False,
        "source_refs": source_refs,
        "proof_level": LOCAL_PROOF_LEVEL,
        "evidence_scope": LOCAL_EVIDENCE_SCOPE,
        "live_or_staging_evidence": False,
    }


def build_broad_nlu_listening_aspect_record(
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = evidence if isinstance(evidence, dict) else {}
    applicable = bool(payload)
    failure_reasons: list[str] = []
    if applicable and payload.get("raw_player_input_included"):
        failure_reasons.append("raw_player_input_must_not_be_in_broad_nlu_evidence")
    if applicable and not payload.get("player_input_kind"):
        failure_reasons.append("player_input_kind_missing")
    return _record(
        applicable=applicable,
        status="failed" if failure_reasons else "passed" if applicable else "missing",
        expected={
            "schema_version": BROAD_NLU_LISTENING_SCHEMA_VERSION,
            "semantic_taxonomy_required": True,
            "raw_player_input_forbidden": True,
        },
        selected={
            "primary_discourse_act": payload.get("primary_discourse_act"),
            "target_actor_refs": payload.get("target_actor_refs") or [],
            "object_refs": payload.get("object_refs") or [],
            "source_refs": payload.get("source_refs") or [],
        },
        actual={
            "player_input_kind": payload.get("player_input_kind"),
            "confidence": payload.get("confidence"),
            "ambiguity_codes": payload.get("ambiguity_codes") or [],
            "repair_prompt_recommended": bool(payload.get("repair_prompt_recommended")),
            "response_expectation": payload.get("response_expectation"),
            "raw_player_input_included": bool(payload.get("raw_player_input_included")),
            "contract_pass": not failure_reasons,
        },
        reasons=failure_reasons,
        failure_class="hard_contract_failure" if failure_reasons else None,
        failure_reason=failure_reasons[0] if failure_reasons else None,
    )


def derive_conversational_memory_context(
    *,
    hierarchical_memory_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build memory continuity evidence from bounded committed memory context."""
    memory = hierarchical_memory_context if isinstance(hierarchical_memory_context, dict) else {}
    projected_tiers = memory.get("projected_tiers") if isinstance(memory.get("projected_tiers"), dict) else {}
    selected_refs: list[str] = []
    selected_tiers: list[str] = []
    for tier_id, rows in projected_tiers.items():
        if not isinstance(rows, list):
            continue
        tier_text = _text(tier_id)
        if rows and tier_text:
            selected_tiers.append(tier_text)
        for row in rows:
            if not isinstance(row, dict):
                continue
            ref = _text(row.get("item_id")) or _text(row.get("source_canonical_turn_id"))
            if ref and ref not in selected_refs:
                selected_refs.append(ref)
            if len(selected_refs) >= 12:
                break
    context_line_count = len(memory.get("context_lines") if isinstance(memory.get("context_lines"), list) else [])
    return {
        "schema_version": CONVERSATIONAL_MEMORY_SCHEMA_VERSION,
        "memory_present": bool(memory.get("memory_present")),
        "bounded": bool(memory.get("bounded")),
        "item_count": int(memory.get("item_count") or 0),
        "available_item_count": int(memory.get("available_item_count") or 0),
        "omitted_item_count": int(memory.get("omitted_item_count") or 0),
        "context_line_count": context_line_count,
        "selected_tiers": selected_tiers,
        "selected_memory_ref_ids": selected_refs,
        "committed_turn_refs_only": True,
        "raw_player_input_included": False,
        "raw_prompt_included": False,
        "source_refs": ["hierarchical_memory_context"],
        "proof_level": LOCAL_PROOF_LEVEL,
        "evidence_scope": LOCAL_EVIDENCE_SCOPE,
        "live_or_staging_evidence": False,
    }


def build_conversational_memory_aspect_record(
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = evidence if isinstance(evidence, dict) else {}
    applicable = bool(payload)
    failure_reasons: list[str] = []
    if applicable and payload.get("raw_player_input_included"):
        failure_reasons.append("raw_player_input_must_not_be_in_conversational_memory")
    if applicable and payload.get("raw_prompt_included"):
        failure_reasons.append("raw_prompt_must_not_be_in_conversational_memory")
    if applicable and payload.get("memory_present") and not payload.get("bounded"):
        failure_reasons.append("memory_context_must_be_bounded")
    return _record(
        applicable=applicable,
        status="failed" if failure_reasons else "passed" if applicable else "missing",
        expected={
            "schema_version": CONVERSATIONAL_MEMORY_SCHEMA_VERSION,
            "committed_turn_refs_only": True,
            "raw_player_input_forbidden": True,
            "raw_prompt_forbidden": True,
        },
        selected={
            "selected_tiers": payload.get("selected_tiers") or [],
            "selected_memory_ref_ids": payload.get("selected_memory_ref_ids") or [],
            "source_refs": payload.get("source_refs") or [],
        },
        actual={
            "memory_present": bool(payload.get("memory_present")),
            "bounded": bool(payload.get("bounded")),
            "context_line_count": int(payload.get("context_line_count") or 0),
            "raw_player_input_included": bool(payload.get("raw_player_input_included")),
            "raw_prompt_included": bool(payload.get("raw_prompt_included")),
            "contract_pass": not failure_reasons,
        },
        reasons=failure_reasons,
        failure_class="hard_contract_failure" if failure_reasons else None,
        failure_reason=failure_reasons[0] if failure_reasons else None,
    )


def build_prompt_authority_packet(
    *,
    capability_selection: dict[str, Any] | None,
    broad_nlu_listening: dict[str, Any] | None,
    conversational_memory: dict[str, Any] | None,
    dramatic_generation_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Declare which structured fields may act as model-visible authority."""
    selection = capability_selection if isinstance(capability_selection, dict) else {}
    broad = broad_nlu_listening if isinstance(broad_nlu_listening, dict) else {}
    memory = conversational_memory if isinstance(conversational_memory, dict) else {}
    packet = dramatic_generation_packet if isinstance(dramatic_generation_packet, dict) else {}
    selected_caps = _unique_texts(selection.get("selected") or [], max_items=16)
    observed_caps = _unique_texts(selection.get("observed_only") or [], max_items=16)
    sections = [
        "actor_lane_boundary",
        "player_intent_surface",
        "semantic_interpretation",
        "broad_nlu_listening",
    ]
    if memory:
        sections.append("conversational_memory")
    if packet.get("npc_agency_plan"):
        sections.append("npc_agency_plan")
    if packet.get("relationship_state"):
        sections.append("relationship_state")
    source_refs = [
        "interpreted_input",
        "semantic_move_record",
        "runtime_intelligence_projection.capability_selection",
    ]
    if memory:
        source_refs.append("hierarchical_memory_context")
    if packet:
        source_refs.append("dramatic_generation_packet")
    return {
        "schema_version": PROMPT_AUTHORITY_SCHEMA_VERSION,
        "authority_mode": "model_visible_generation_constraints",
        "selected_capabilities": selected_caps,
        "observed_capabilities": observed_caps,
        "authoritative_sections": sections,
        "source_refs": source_refs,
        "broad_nlu_discourse_act": broad.get("primary_discourse_act"),
        "broad_nlu_response_expectation": broad.get("response_expectation"),
        "selected_memory_ref_ids": memory.get("selected_memory_ref_ids") or [],
        "forbidden_inferences": [
            "raw_player_input_as_memory_truth",
            "unverified_memory_claim",
            "prompt_or_tool_disclosure",
            "generated_prose_as_validator_oracle",
            "npc_reclassification_of_player_turn",
        ],
        "prompt_authority_applied_to_packet": True,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "validation_outcome_changed": False,
        "proof_level": LOCAL_PROOF_LEVEL,
        "evidence_scope": LOCAL_EVIDENCE_SCOPE,
        "live_or_staging_evidence": False,
    }


def build_prompt_authority_aspect_record(
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = evidence if isinstance(evidence, dict) else {}
    applicable = bool(payload)
    failure_reasons: list[str] = []
    if applicable and payload.get("commit_gate_changed"):
        failure_reasons.append("prompt_authority_must_not_change_commit_gate")
    if applicable and payload.get("validation_outcome_changed"):
        failure_reasons.append("prompt_authority_must_not_change_validation_outcome")
    if applicable and not payload.get("source_refs"):
        failure_reasons.append("prompt_authority_source_refs_missing")
    return _record(
        applicable=applicable,
        status="failed" if failure_reasons else "passed" if applicable else "missing",
        expected={
            "schema_version": PROMPT_AUTHORITY_SCHEMA_VERSION,
            "source_refs_required": True,
            "commit_gate_changed": False,
            "validation_outcome_changed": False,
        },
        selected={
            "authoritative_sections": payload.get("authoritative_sections") or [],
            "source_refs": payload.get("source_refs") or [],
            "selected_capabilities": payload.get("selected_capabilities") or [],
            "selected_memory_ref_ids": payload.get("selected_memory_ref_ids") or [],
        },
        actual={
            "authority_mode": payload.get("authority_mode"),
            "prompt_authority_applied_to_packet": bool(
                payload.get("prompt_authority_applied_to_packet")
            ),
            "commit_gate_changed": bool(payload.get("commit_gate_changed")),
            "readiness_gate_changed": bool(payload.get("readiness_gate_changed")),
            "validation_outcome_changed": bool(payload.get("validation_outcome_changed")),
            "contract_pass": not failure_reasons,
        },
        reasons=failure_reasons,
        failure_class="hard_contract_failure" if failure_reasons else None,
        failure_reason=failure_reasons[0] if failure_reasons else None,
    )
