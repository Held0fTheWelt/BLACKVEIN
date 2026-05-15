"""
``ai_stack/langgraph_runtime_executor.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger(__name__)

from ai_stack.langgraph_imports import END, StateGraph

from story_runtime_core.adapters import BaseModelAdapter
from story_runtime_core.model_registry import ModelRegistry, RoutingPolicy
from story_runtime_core.player_input_intent_contract import (
    SPEECH_PROJECTION_KINDS,
    is_action_like_player_input_kind,
    is_mixed_player_input_kind,
    is_narrator_only_player_input_kind,
    is_non_story_control_player_input_kind,
    is_perception_like_player_input_kind,
    is_speech_like_player_input_kind,
    player_input_kind_family,
)
from ai_stack.capabilities import CapabilityRegistry
from ai_stack.story_runtime_playability import (
    build_rewrite_instruction,
    decide_playability_recovery,
    degrade_validation_outcome,
)
from ai_stack.rag import ContextPackAssembler, ContextRetriever
from ai_stack.rag_retrieval_dtos import (
    RetrievalRequest,
    RuntimeRetrievalConfig,
    filter_retrieval_result_by_min_score,
)
from ai_stack.rag_types import RetrievalDomain
from ai_stack.retrieval_governance_summary import attach_retrieval_governance_summary
from ai_stack.context_synthesis_engine import (
    build_context_synthesis_bundle,
    build_context_synthesis_error_bundle,
    context_synthesis_prompt_lines,
    summarize_context_synthesis_for_diagnostics,
)
from ai_stack.operational_profile import build_operational_cost_hints_for_runtime_graph
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    ADAPTER_INVOCATION_META_CONTROL,
    ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    RAW_FALLBACK_BYPASS_NOTE,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_IMPROVISATIONAL_COHERENCE,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_INPUT,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SCENE_ENERGY,
    ASPECT_SOCIAL_PRESSURE,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)
from ai_stack.dramatic_irony_runtime import (
    build_dramatic_irony_aspect_record,
    build_dramatic_irony_record,
    compact_dramatic_irony_context,
    validate_dramatic_irony_realization,
)
from ai_stack.beat_lifecycle_contracts import phase_beat_candidates, select_beat_candidate
from ai_stack.dramatic_capability_contracts import (
    AI_CONTROLLED_HUMAN_ACTOR_REASON,
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON,
    NPC_ALLOWED_PRESSURE_VERBS,
    NPC_COERCIVE_ACTION_TYPES,
    NPC_COERCIVE_CONTROL_VERBS,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_EXECUTED_PLAYER_ACTION_REASON,
    NPC_NARRATED_PLAYER_PERCEPTION_REASON,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_LOCATION_TRANSITION_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.environment_state_contracts import (
    apply_action_to_environment_state,
    build_environment_generation_context,
    build_environment_model,
    build_environment_render_context,
    normalize_environment_state,
)
from ai_stack.runtime_dramatic_capabilities import build_capability_selection_record
from ai_stack.version import AI_STACK_SEMANTIC_VERSION, RUNTIME_TURN_GRAPH_VERSION
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID, canonicalize_goc_actor_id
from ai_stack.goc_frozen_vocab import expand_goc_actor_id_aliases
from ai_stack.goc_roadmap_semantic_surface import ROUTING_LABELS
from ai_stack.goc_yaml_authority import (
    detect_builtin_yaml_title_conflict,
    goc_character_profile_snippet,
    load_goc_canonical_module_yaml,
    load_goc_yaml_slice_bundle,
    scene_guidance_snippets,
)
from ai_stack.goc_knowledge_runtime_gates import (
    build_opening_scene_plan_metadata,
    build_runtime_knowledge_contract,
    knowledge_contract_prompt_lines,
)
from ai_stack.npc_agency_contracts import (
    NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS,
    NPC_AGENCY_CLOSURE_CLOSED_STATUS,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    npc_actor_ids_from_context,
)
from ai_stack.npc_agency_planner import build_npc_agency_plan, build_npc_agency_simulation
from ai_stack.npc_agency_realization import validate_npc_initiative_realization
from ai_stack.information_disclosure_engine import (
    derive_information_disclosure,
    validate_information_disclosure_realization,
)
from ai_stack.improvisational_coherence_engine import (
    build_improvisational_coherence_aspect_record,
    compact_improvisational_coherence_context,
    derive_improvisational_coherence,
    validate_improvisational_coherence_realization,
)
from ai_stack.pacing_rhythm_engine import (
    derive_pacing_rhythm,
    validate_pacing_rhythm_realization,
)
from ai_stack.social_pressure_engine import (
    derive_social_pressure,
    validate_social_pressure_metric,
)
from ai_stack.scene_energy_engine import derive_scene_energy, validate_scene_energy_realization
from ai_stack.goc_scene_identity import GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY
from ai_stack.character_mind_goc import build_character_mind_records_for_goc
from ai_stack.character_voice_goc import build_character_voice_profiles_for_goc
from ai_stack.character_voice_validation import validate_voice_consistency
from ai_stack.scene_director_goc import (
    build_pacing_and_silence,
    build_responder_and_function,
    build_scene_assessment,
    prior_continuity_classes,
)
from ai_stack.scene_plan_contract import ScenePlanRecord
from ai_stack.semantic_move_contract import SemanticMoveRecord
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move, semantic_move_fingerprint
from ai_stack.social_state_contract import SocialStateRecord
from ai_stack.social_state_goc import build_social_state_record, social_state_fingerprint
from ai_stack.dramatic_effect_gate import build_evaluation_context_from_runtime_state
from ai_stack.goc_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.goc_turn_seams import (
    build_diagnostics_refs,
    build_goc_continuity_impacts_on_commit,
    repro_metadata_complete,
    run_commit_seam,
    run_validation_seam,
    run_visible_render,
    strip_director_overwrites_from_structured_output,
    structured_output_to_proposed_effects,
)
from ai_stack.langgraph_runtime_state import (
    STORY_RUNTIME_ROUTING_POLICY_ID,
    STORY_RUNTIME_ROUTING_POLICY_VERSION,
    RuntimeTurnState,
)
from ai_stack.langgraph_runtime_tracking import _dist_version, _track
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str
from ai_stack.langgraph_synthetic_action_resolution import build_synthetic_generation_for_action_resolution
from ai_stack.player_action_resolution import resolve_player_action
from story_runtime_core.content_locale import (
    classify_player_input_from_rules,
    default_player_intent_commit_flags,
    load_session_language_model_directive,
)


def _runtime_profile_id_from_host_template(host_experience_template: dict[str, Any] | None) -> str | None:
    """Resolve a runtime profile id from host-provided module metadata."""
    if not isinstance(host_experience_template, dict):
        return None
    for key in ("runtime_profile_id", "template_id", "experience_template_id", "seed_template_id"):
        text = str(host_experience_template.get(key) or "").strip()
        if text:
            return text
    return None


def _session_language_directive_for_model(state: RuntimeTurnState) -> str:
    """Bind model output to ``session_output_language`` for non-opening turns (opening prompt already binds)."""
    if str(state.get("turn_input_class") or "").strip().lower() == "opening":
        return ""
    lang = str(state.get("session_output_language") or "de").strip().lower()[:2] or "de"
    mid = str(state.get("module_id") or "").strip()
    if not mid:
        return ""
    return load_session_language_model_directive(module_id=mid, lang=lang, content_modules_root=None)


def _prune_out_of_scope_actor_lanes(
    generation: dict[str, Any], out_of_scope_actors: list[str]
) -> dict[str, str]:
    """Prune out-of-scope actors from spoken_lines and action_lines in structured output.

    Returns a dict with pruning stats for telemetry.
    """
    if not out_of_scope_actors:
        return {"spoken_lines_pruned": 0, "action_lines_pruned": 0}

    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    if not structured:
        return {"spoken_lines_pruned": 0, "action_lines_pruned": 0}

    out_of_scope_set = set(out_of_scope_actors)
    spoken_lines_pruned = 0
    action_lines_pruned = 0

    spoken_lines = structured.get("spoken_lines")
    if isinstance(spoken_lines, list):
        filtered = []
        for row in spoken_lines:
            if isinstance(row, dict):
                speaker_id = row.get("speaker_id")
                if isinstance(speaker_id, str) and speaker_id.strip() in out_of_scope_set:
                    spoken_lines_pruned += 1
                    continue
            filtered.append(row)
        structured["spoken_lines"] = filtered

    action_lines = structured.get("action_lines")
    if isinstance(action_lines, list):
        filtered = []
        for row in action_lines:
            if isinstance(row, dict):
                actor_id = row.get("actor_id")
                if isinstance(actor_id, str) and actor_id.strip() in out_of_scope_set:
                    action_lines_pruned += 1
                    continue
            filtered.append(row)
        structured["action_lines"] = filtered

    return {"spoken_lines_pruned": spoken_lines_pruned, "action_lines_pruned": action_lines_pruned}


def _reconcile_model_responders(
    state: "RuntimeTurnState", generation: dict[str, Any]
) -> dict[str, Any]:
    """Check the model's proposed responders against the director's scope.

    The model may propose a ``responder_id`` and/or a list of
    ``responder_actor_ids`` in its structured output. The director's
    ``selected_responder_set`` is the authoritative scope for the scene.
    This helper computes the intersection, records the actors the model
    introduced that were out of scope, and picks the final effective
    responder — preferring the model's claim when it was in scope and
    otherwise falling back to the director's first responder.

    The returned dict lives on the runtime state as
    ``responder_reconciliation`` and is surfaced on the governance surface
    so operators can audit when and why a model responder claim was
    dropped.
    """
    selected = state.get("selected_responder_set")
    selected_list = selected if isinstance(selected, list) else []
    director_actor_ids: list[str] = []
    for row in selected_list:
        if isinstance(row, dict):
            aid = row.get("actor_id") or row.get("responder_id")
            if isinstance(aid, str) and aid.strip():
                director_actor_ids.append(aid.strip())
    director_scope = set(director_actor_ids)

    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}

    model_primary_raw = structured.get("primary_responder_id") or structured.get("responder_id")
    model_primary = model_primary_raw.strip() if isinstance(model_primary_raw, str) else ""

    model_scope_raw = structured.get("secondary_responder_ids")
    if not isinstance(model_scope_raw, list):
        model_scope_raw = structured.get("responder_actor_ids")
    model_scope: list[str] = []
    if isinstance(model_scope_raw, list):
        for value in model_scope_raw:
            if isinstance(value, str) and value.strip():
                model_scope.append(value.strip())
    if model_primary and model_primary not in model_scope:
        model_scope.append(model_primary)

    in_scope: list[str] = []
    out_of_scope: list[str] = []
    for actor in model_scope:
        if not director_scope or actor in director_scope:
            if actor not in in_scope:
                in_scope.append(actor)
        else:
            if actor not in out_of_scope:
                out_of_scope.append(actor)

    if model_primary and model_primary in in_scope:
        effective_primary = model_primary
        reconciliation_outcome = "model_responder_accepted"
    elif director_actor_ids:
        effective_primary = director_actor_ids[0]
        if model_primary and model_primary not in director_scope:
            reconciliation_outcome = "model_responder_out_of_scope_dropped"
        elif model_primary:
            reconciliation_outcome = "model_responder_missing_from_director_scope"
        else:
            reconciliation_outcome = "director_primary_responder_used"
    else:
        effective_primary = model_primary or ""
        reconciliation_outcome = (
            "no_director_scope_available"
            if not model_primary
            else "no_director_scope_accepting_model_responder"
        )

    return {
        "outcome": reconciliation_outcome,
        "director_responder_scope": director_actor_ids,
        "model_proposed_responder_id": model_primary or None,
        "model_proposed_responder_scope": model_scope,
        "effective_responder_id": effective_primary or None,
        "effective_responder_scope": in_scope,
        "dropped_out_of_scope_actors": out_of_scope,
        "dropped_out_of_scope_count": len(out_of_scope),
    }


_ALLOWED_INITIATIVE_EVENT_TYPES = {"interrupt", "escalate", "withdraw", "deflect", "counter", "seize"}


def _actor_lane_validation(
    state: "RuntimeTurnState",
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Validate actor-lane legality without flattening actor-level structure."""
    selected = state.get("selected_responder_set")
    selected_list = selected if isinstance(selected, list) else []
    director_actor_ids: list[str] = []
    for row in selected_list:
        if isinstance(row, dict):
            aid = row.get("actor_id") or row.get("responder_id")
            if isinstance(aid, str) and aid.strip():
                director_actor_ids.append(aid.strip())

    mind_records = state.get("character_mind_records")
    if isinstance(mind_records, list):
        for row in mind_records:
            if isinstance(row, dict):
                aid = row.get("runtime_actor_id") or row.get("character_key")
                if isinstance(aid, str) and aid.strip():
                    director_actor_ids.append(aid.strip())

    allowed_actor_ids = sorted({aid for aid in director_actor_ids if aid})
    allowed_scope: set[str] = set()
    for aid in allowed_actor_ids:
        allowed_scope.update(expand_goc_actor_id_aliases(aid))
    allowed_scope.update(allowed_actor_ids)

    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    if not structured:
        has_selected_responders = bool(allowed_actor_ids)
        reason = (
            "no_structured_actor_output_with_selected_responders"
            if has_selected_responders
            else "no_structured_actor_output"
        )
        return {
            "status": "approved",
            "reason": reason,
            "allowed_actor_ids": allowed_actor_ids,
            "illegal_actor_ids": [],
            "invalid_initiative_types": [],
            "scene_function_compatibility": "not_evaluated",
            "checked_fields": [],
        }

    checked_fields: list[str] = []
    illegal_actor_ids: list[str] = []
    invalid_initiative_types: list[str] = []
    scene_mismatch_reasons: list[str] = []

    def _record_illegal_actor(actor_id: str) -> None:
        aid = str(actor_id or "").strip()
        if not aid:
            return
        if aid not in illegal_actor_ids:
            illegal_actor_ids.append(aid)

    def _actor_is_legal(actor_id: str) -> bool:
        aid = str(actor_id or "").strip()
        if not aid:
            return True
        if not allowed_scope:
            return True
        return aid in allowed_scope

    primary_responder = structured.get("primary_responder_id") or structured.get("responder_id")
    if isinstance(primary_responder, str) and primary_responder.strip():
        checked_fields.append("primary_responder_id")
        if not _actor_is_legal(primary_responder):
            _record_illegal_actor(primary_responder)

    secondary_ids = structured.get("secondary_responder_ids")
    if isinstance(secondary_ids, list):
        checked_fields.append("secondary_responder_ids")
        for value in secondary_ids:
            if isinstance(value, str) and value.strip() and not _actor_is_legal(value):
                _record_illegal_actor(value)

    spoken_lines = structured.get("spoken_lines")
    if isinstance(spoken_lines, list):
        checked_fields.append("spoken_lines")
        for row in spoken_lines:
            if not isinstance(row, dict):
                continue
            speaker_id = row.get("speaker_id")
            if isinstance(speaker_id, str) and speaker_id.strip() and not _actor_is_legal(speaker_id):
                _record_illegal_actor(speaker_id)

    action_lines = structured.get("action_lines")
    if isinstance(action_lines, list):
        checked_fields.append("action_lines")
        for row in action_lines:
            if not isinstance(row, dict):
                continue
            actor_id = row.get("actor_id")
            if isinstance(actor_id, str) and actor_id.strip() and not _actor_is_legal(actor_id):
                _record_illegal_actor(actor_id)

    initiative_events = structured.get("initiative_events")
    if isinstance(initiative_events, list):
        checked_fields.append("initiative_events")
        for row in initiative_events:
            if not isinstance(row, dict):
                continue
            actor_id = row.get("actor_id")
            event_type_raw = row.get("type")
            event_type = str(event_type_raw).strip().lower() if isinstance(event_type_raw, str) else ""
            if isinstance(actor_id, str) and actor_id.strip() and not _actor_is_legal(actor_id):
                _record_illegal_actor(actor_id)
            if event_type and event_type not in _ALLOWED_INITIATIVE_EVENT_TYPES:
                if event_type not in invalid_initiative_types:
                    invalid_initiative_types.append(event_type)

            scene_fn = str(state.get("selected_scene_function") or "").strip()
            if scene_fn == "withhold_or_evade" and event_type in {"interrupt", "escalate", "counter"}:
                scene_mismatch_reasons.append(
                    f"scene_function={scene_fn} incompatible_with_initiative_type={event_type}"
                )

    prior_impacts = state.get("prior_continuity_impacts")
    continuity_flags: list[str] = []
    if isinstance(prior_impacts, list):
        for item in prior_impacts:
            if not isinstance(item, dict):
                continue
            cls = str(item.get("class") or item.get("continuity_class") or "").strip()
            if cls and cls not in continuity_flags:
                continuity_flags.append(cls)

    scene_compatibility = "compatible"
    if scene_mismatch_reasons:
        scene_compatibility = "mismatch"

    continuity_compatibility = "compatible"
    if "repair_attempt" in continuity_flags and any(
        isinstance(row, dict) and str(row.get("type") or "").strip().lower() in {"interrupt", "counter"}
        for row in (initiative_events if isinstance(initiative_events, list) else [])
    ):
        continuity_compatibility = "warning_repair_tension_interrupt_mix"

    if illegal_actor_ids:
        return {
            "status": "rejected",
            "reason": "actor_lane_illegal_actor",
            "allowed_actor_ids": allowed_actor_ids,
            "illegal_actor_ids": illegal_actor_ids,
            "invalid_initiative_types": invalid_initiative_types,
            "scene_function_compatibility": scene_compatibility,
            "scene_function_mismatch_reasons": scene_mismatch_reasons,
            "continuity_classes": continuity_flags,
            "continuity_compatibility": continuity_compatibility,
            "checked_fields": checked_fields,
        }
    if invalid_initiative_types:
        return {
            "status": "rejected",
            "reason": "actor_lane_invalid_initiative_type",
            "allowed_actor_ids": allowed_actor_ids,
            "illegal_actor_ids": illegal_actor_ids,
            "invalid_initiative_types": invalid_initiative_types,
            "scene_function_compatibility": scene_compatibility,
            "scene_function_mismatch_reasons": scene_mismatch_reasons,
            "continuity_classes": continuity_flags,
            "continuity_compatibility": continuity_compatibility,
            "checked_fields": checked_fields,
        }
    if scene_mismatch_reasons:
        return {
            "status": "rejected",
            "reason": "actor_lane_scene_function_mismatch",
            "allowed_actor_ids": allowed_actor_ids,
            "illegal_actor_ids": illegal_actor_ids,
            "invalid_initiative_types": invalid_initiative_types,
            "scene_function_compatibility": scene_compatibility,
            "scene_function_mismatch_reasons": scene_mismatch_reasons,
            "continuity_classes": continuity_flags,
            "continuity_compatibility": continuity_compatibility,
            "checked_fields": checked_fields,
        }
    return {
        "status": "approved",
        "reason": "actor_lane_legal",
        "allowed_actor_ids": allowed_actor_ids,
        "illegal_actor_ids": illegal_actor_ids,
        "invalid_initiative_types": invalid_initiative_types,
        "scene_function_compatibility": scene_compatibility,
        "scene_function_mismatch_reasons": scene_mismatch_reasons,
        "continuity_classes": continuity_flags,
        "continuity_compatibility": continuity_compatibility,
        "checked_fields": checked_fields,
    }


def _structured_output_from_generation(generation: dict[str, Any]) -> dict[str, Any]:
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output")
    return structured if isinstance(structured, dict) else {}


def _row_text(row: dict[str, Any]) -> str:
    return str(
        row.get("text")
        or row.get("line")
        or row.get("body")
        or row.get("description")
        or ""
    ).strip()


def _actor_alias_scope(actor_id: str | None) -> set[str]:
    aid = str(actor_id or "").strip()
    if not aid:
        return set()
    out = set(expand_goc_actor_id_aliases(aid))
    canon = canonicalize_goc_actor_id(aid)
    if canon:
        out.update(expand_goc_actor_id_aliases(canon))
        out.add(canon)
    out.add(aid)
    return {x for x in out if x}


def _actor_in_scope(actor_id: str | None, scope: set[str]) -> bool:
    aid = str(actor_id or "").strip()
    if not aid:
        return False
    return aid in scope or (canonicalize_goc_actor_id(aid) or aid) in scope


def _normalized_word_set(text: str) -> set[str]:
    return {
        item
        for item in re.split(r"[^a-zA-ZÀ-ÿ0-9_]+", str(text or "").lower())
        if len(item) >= 3
    }


def _authority_text_matches_player_action(text: str, frame: dict[str, Any]) -> bool:
    """Generic overlap check: action ontology verb/target, not fixture phrases."""
    blob = str(text or "").strip().lower()
    if not blob:
        return False
    target_query = str(frame.get("target_query") or "").strip()
    target_id = str(frame.get("resolved_target_id") or "").strip()
    target_hit = False
    for candidate in (target_query, target_id):
        if candidate and candidate.lower() in blob:
            target_hit = True
            break
    verb = str(frame.get("verb") or "").strip().lower()
    verb_markers = {
        "move_to": {"go", "geht", "gehen", "tritt", "betritt", "moves", "walks"},
        "look_at": {"look", "looks", "schau", "schaut", "blick", "blickt", "sieht"},
        "listen_to": {"listen", "listens", "hoer", "hoert", "hört", "lauscht"},
        "take": {"take", "takes", "nimmt", "nehme", "nimm"},
        "activate": {"activate", "activates", "schaltet", "schalte", "macht"},
        "deactivate": {"deactivate", "deactivates", "schaltet", "schalte", "macht"},
        "open": {"open", "opens", "oeffnet", "öffnet", "oeffne", "öffne"},
        "place": {"place", "places", "legt", "lege", "stellt", "stelle"},
        "stand_up": {"stand", "stands", "steht"},
    }.get(verb, {verb} if verb else set())
    words = _normalized_word_set(blob)
    verb_hit = bool(words.intersection(verb_markers))
    if target_query or target_id:
        return target_hit and (verb_hit or len(_normalized_word_set(target_query).intersection(words)) >= 1)
    raw_words = _normalized_word_set(str(frame.get("source_text") or ""))
    return verb_hit and len(raw_words.intersection(words)) >= 2


def _npc_action_controls_human_actor(row: dict[str, Any], human_scope: set[str]) -> bool:
    """Return True for structured NPC coercion targeting the player-owned actor."""
    target_values: list[Any] = [
        row.get("target_actor_id"),
        row.get("target_actor"),
        row.get("target_id"),
    ]
    target_actor_ids = row.get("target_actor_ids")
    if isinstance(target_actor_ids, list):
        target_values.extend(target_actor_ids)
    target_ids = row.get("target_ids")
    if isinstance(target_ids, list):
        target_values.extend(target_ids)
    if not any(_actor_in_scope(str(value or ""), human_scope) for value in target_values):
        return False

    for key in ("coercion_type", "action_type"):
        value = str(row.get(key) or "").strip().lower()
        if value in NPC_COERCIVE_ACTION_TYPES:
            return True

    words = _normalized_word_set(_row_text(row))
    if words.intersection(NPC_ALLOWED_PRESSURE_VERBS):
        return False
    return bool(words.intersection(NPC_COERCIVE_CONTROL_VERBS))


def _build_authority_aspect_records(
    *,
    state: "RuntimeTurnState",
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    structured = _structured_output_from_generation(generation)
    interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    frame = state.get("player_action_frame") if isinstance(state.get("player_action_frame"), dict) else {}
    aff = state.get("affordance_resolution") if isinstance(state.get("affordance_resolution"), dict) else {}
    module_policy = state.get("module_runtime_policy") if isinstance(state.get("module_runtime_policy"), dict) else {}
    authority_policy = (
        module_policy.get("authority_policy")
        if isinstance(module_policy.get("authority_policy"), dict)
        else {}
    )
    capability_policy = (
        module_policy.get("capability_policy")
        if isinstance(module_policy.get("capability_policy"), dict)
        else {}
    )
    turn_number = int(state.get("turn_number") or 0)
    player_input_kind = str(frame.get("player_input_kind") or interp.get("player_input_kind") or "").strip().lower()
    narrator_required = bool(frame.get("narrator_response_expected") or interp.get("narrator_response_expected"))
    if is_narrator_only_player_input_kind(player_input_kind) or is_mixed_player_input_kind(player_input_kind):
        narrator_required = True
    if str(aff.get("requires_narrator") or "").strip().lower() == "true":
        narrator_required = True
    narrative_text = "\n".join(
        part
        for part in (
            narration_summary_to_plain_str(structured.get("narration_summary")),
            str(structured.get("narrative_response") or "").strip(),
            extract_proposed_narrative_text(proposed_state_effects),
        )
        if str(part or "").strip()
    ).strip()
    narrator_present = bool(narrative_text)
    if turn_number <= 0 and narrator_present:
        narrator_required = True
    narrator_status = "passed"
    narrator_failure_reason = None
    if narrator_required and not narrator_present:
        narrator_status = "failed"
        narrator_failure_reason = "narrator_required_missing"
    narrator_record = make_aspect_record(
        applicable=bool(narrator_required or narrator_present),
        status=narrator_status if (narrator_required or narrator_present) else "not_applicable",
        expected={
            "required": bool(narrator_required),
            "expected_owner": "narrator" if narrator_required else None,
            "reason": "player_action_or_perception_consequence"
            if is_narrator_only_player_input_kind(player_input_kind) or is_mixed_player_input_kind(player_input_kind)
            else "opening_or_optional_narration"
            if narrator_required
            else None,
            "required_capabilities": [
                NARRATOR_PERCEPTION_RESULT_DESCRIBE
                if is_perception_like_player_input_kind(player_input_kind)
                else NARRATOR_LOCATION_TRANSITION_DESCRIBE
                if str(frame.get("action_kind") or "").strip().lower() == "movement"
                else NARRATOR_OBJECT_STATE_DESCRIBE
                if str(frame.get("action_kind") or "").strip().lower() == "object_interaction"
                else NARRATOR_ACTION_CONSEQUENCE_DESCRIBE
            ]
            if narrator_required
            else [],
            "authority_policy_source": "module_runtime_policy"
            if authority_policy
            else "runtime_default",
        },
        actual={
            "actual_owner": "narrator" if narrator_present else None,
            "narrator_block_present": narrator_present,
            "consequence_realized": narrator_present if narrator_required else None,
            "narrative_text_present": narrator_present,
        },
        reasons=[] if narrator_failure_reason is None else [narrator_failure_reason],
        source="runtime",
        failure_class=None if narrator_failure_reason is None else "hard_contract_failure",
        failure_reason=narrator_failure_reason,
        expected_owner="narrator" if narrator_required else None,
        actual_owner="narrator" if narrator_present else None,
        missing_field="narration_summary" if narrator_failure_reason else None,
    )

    actor_lane_ctx = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
    human_scope = _actor_alias_scope(
        str(actor_lane_ctx.get("human_actor_id") or actor_lane_ctx.get("selected_player_role") or "").strip()
    )
    npc_scope: set[str] = set()
    for raw_actor_id in actor_lane_ctx.get("npc_actor_ids") or []:
        npc_scope.update(_actor_alias_scope(str(raw_actor_id or "").strip()))
    spoken_rows = [row for row in structured.get("spoken_lines") or [] if isinstance(row, dict)]
    action_rows = [row for row in structured.get("action_lines") or [] if isinstance(row, dict)]
    offending_actor_id = None
    offending_block_id = None
    failure_reason = None

    for row in spoken_rows:
        sid = str(row.get("speaker_id") or "").strip()
        if _actor_in_scope(sid, human_scope):
            offending_actor_id = sid
            offending_block_id = str(row.get("id") or row.get("block_id") or "")
            failure_reason = AI_CONTROLLED_HUMAN_ACTOR_REASON
            break
        if is_perception_like_player_input_kind(player_input_kind) and not _actor_in_scope(sid, human_scope):
            if _authority_text_matches_player_action(_row_text(row), frame):
                offending_actor_id = sid or None
                offending_block_id = str(row.get("id") or row.get("block_id") or "")
                failure_reason = NPC_NARRATED_PLAYER_PERCEPTION_REASON
                break
    if failure_reason is None:
        for row in action_rows:
            aid = str(row.get("actor_id") or "").strip()
            if _actor_in_scope(aid, human_scope):
                offending_actor_id = aid
                offending_block_id = str(row.get("id") or row.get("block_id") or "")
                failure_reason = AI_CONTROLLED_HUMAN_ACTOR_REASON
                break
            if not _actor_in_scope(aid, human_scope) and _npc_action_controls_human_actor(row, human_scope):
                offending_actor_id = aid or None
                offending_block_id = str(row.get("id") or row.get("block_id") or "")
                failure_reason = NPC_ACTION_CONTROLS_HUMAN_ACTOR_REASON
                break
            if _actor_in_scope(aid, npc_scope) and (
                is_action_like_player_input_kind(player_input_kind)
                or is_perception_like_player_input_kind(player_input_kind)
                or is_mixed_player_input_kind(player_input_kind)
            ):
                if _authority_text_matches_player_action(_row_text(row), frame):
                    offending_actor_id = aid
                    offending_block_id = str(row.get("id") or row.get("block_id") or "")
                    failure_reason = (
                        NPC_NARRATED_PLAYER_PERCEPTION_REASON
                        if is_perception_like_player_input_kind(player_input_kind)
                        else NPC_EXECUTED_PLAYER_ACTION_REASON
                    )
                    break
    npc_status = "failed" if failure_reason else "passed"
    actual_npc_actors: list[str] = []
    for row in spoken_rows:
        sid = str(row.get("speaker_id") or "").strip()
        if sid and sid not in actual_npc_actors:
            actual_npc_actors.append(sid)
    for row in action_rows:
        aid = str(row.get("actor_id") or "").strip()
        if aid and aid not in actual_npc_actors:
            actual_npc_actors.append(aid)
    policy_name = "direct_response" if is_speech_like_player_input_kind(player_input_kind) else "optional_social_reaction"
    if not spoken_rows and not action_rows and not bool(interp.get("npc_response_expected")):
        policy_name = "none"
    forbidden_caps = [
        str(item).strip()
        for item in (capability_policy.get("forbidden") if isinstance(capability_policy.get("forbidden"), list) else [])
        if str(item).strip()
    ]
    npc_record = make_aspect_record(
        applicable=True,
        status=npc_status,
        expected={
            "policy": policy_name,
            "allowed_actors": sorted(npc_scope),
            "allowed_capabilities": [
                NPC_SOCIAL_REACTION_OPTIONAL,
                NPC_DIRECT_ANSWER_ALLOWED,
                NPC_ACTION_GESTURE_OPTIONAL,
            ],
            "forbidden_capabilities": forbidden_caps,
            "authority_policy_source": "module_runtime_policy"
            if authority_policy
            else "runtime_default",
        },
        actual={
            "spoken_line_count": len(spoken_rows),
            "action_line_count": len(action_rows),
            "actual_actors": actual_npc_actors,
            "npc_takeover_detected": bool(failure_reason),
            "offending_actor_id": offending_actor_id,
            "offending_block_id": offending_block_id or None,
        },
        reasons=[] if failure_reason is None else [failure_reason],
        source="runtime",
        failure_class=None if failure_reason is None else "hard_contract_failure",
        failure_reason=failure_reason,
        offending_actor_id=offending_actor_id,
        offending_block_id=offending_block_id or None,
        expected_owner="narrator" if failure_reason == NPC_NARRATED_PLAYER_PERCEPTION_REASON else None,
        actual_owner="npc" if failure_reason else None,
    )
    return narrator_record, npc_record


def _voice_validation_mode_from_state(state: "RuntimeTurnState") -> str:
    raw = str(
        state.get("validation_execution_mode")
        or state.get("validation_mode")
        or "schema_plus_semantic"
    ).strip().lower()
    if raw not in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}:
        return "schema_plus_semantic"
    return raw


def _voice_profiles_from_state(state: "RuntimeTurnState") -> list[dict[str, Any]]:
    profiles = state.get("character_voice_profiles")
    if isinstance(profiles, list) and profiles:
        return [row for row in profiles if isinstance(row, dict)]
    if str(state.get("module_id") or "") != GOC_MODULE_ID:
        return []
    yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
    if yslice is None:
        try:
            yslice = load_goc_yaml_slice_bundle()
        except Exception:
            yslice = None
    active_keys: list[str] = []
    minds = state.get("character_mind_records") if isinstance(state.get("character_mind_records"), list) else []
    for row in minds:
        if not isinstance(row, dict):
            continue
        key = str(row.get("character_key") or "").strip()
        if key and key not in active_keys:
            active_keys.append(key)
    if not active_keys:
        active_keys = _derive_active_character_keys(
            yaml_slice=yslice,
            primary_responder=(
                state.get("selected_responder_set", [{}])[0]
                if isinstance(state.get("selected_responder_set"), list)
                and state.get("selected_responder_set")
                and isinstance(state.get("selected_responder_set", [None])[0], dict)
                else {}
            ),
            module_id=str(state.get("module_id") or ""),
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
    return [
        profile.to_runtime_dict()
        for profile in build_character_voice_profiles_for_goc(
            yaml_slice=yslice,
            active_character_keys=active_keys,
            current_scene_id=str(state.get("current_scene_id") or ""),
            module_id=str(state.get("module_id") or ""),
        )
    ]


def _voice_consistency_validation(
    *,
    state: "RuntimeTurnState",
    generation: dict[str, Any],
) -> dict[str, Any]:
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
    result = validate_voice_consistency(
        structured_output=structured,
        voice_profiles=_voice_profiles_from_state(state),
        validation_mode=_voice_validation_mode_from_state(state),
    )
    return result.to_runtime_dict()


def _voice_aspect_record(result: dict[str, Any]) -> dict[str, Any]:
    status = str(result.get("status") or "not_applicable").strip().lower()
    findings = result.get("findings") if isinstance(result.get("findings"), list) else []
    blocking = result.get("blocking_findings") if isinstance(result.get("blocking_findings"), list) else []
    policy_sources = result.get("policy_sources") if isinstance(result.get("policy_sources"), list) else []
    semantic_classifications = (
        result.get("semantic_classifications")
        if isinstance(result.get("semantic_classifications"), list)
        else []
    )
    marker_policy_present = "character_voice.voice_consistency.forbidden_language_markers" in policy_sources
    semantic_policy_present = "character_voice.voice_consistency.semantic_classification" in policy_sources
    drift_counts: dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        drift_class = str(finding.get("drift_class") or "").strip()
        if drift_class:
            drift_counts[drift_class] = drift_counts.get(drift_class, 0) + 1
    applicable = status != "not_applicable"
    aspect_status = "not_applicable"
    if status == "rejected":
        aspect_status = "failed"
    elif status == "approved" and findings:
        aspect_status = "partial"
    elif status == "approved":
        aspect_status = "passed"
    first_blocking = blocking[0] if blocking and isinstance(blocking[0], dict) else {}
    first_finding = findings[0] if findings and isinstance(findings[0], dict) else {}
    failure_reason = "voice_consistency_drift" if status == "rejected" else None
    return make_aspect_record(
        applicable=applicable,
        status=aspect_status,
        expected={
            "policy_present": bool(result.get("policy_sources")),
            "validation_mode": result.get("validation_mode"),
            "profiles_required_for_spoken_lines": True,
            "forbidden_language_markers_enforced": marker_policy_present,
            "semantic_classification_enabled": semantic_policy_present,
        },
        actual={
            "validation_status": status,
            "reason": result.get("reason"),
            "profiles_checked": int(result.get("profiles_checked") or 0),
            "spoken_line_count": int(result.get("spoken_line_count") or 0),
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "drift_class_counts": drift_counts,
            "findings": findings[:6],
            "semantic_classification_count": len(semantic_classifications),
            "semantic_classifications": semantic_classifications[:4],
            "semantic_cross_actor_confusion_count": drift_counts.get(
                "cross_actor_voice_confusion", 0
            ),
            "semantic_mixed_signature_count": drift_counts.get(
                "mixed_voice_signature", 0
            ),
            "semantic_ambiguous_signature_count": drift_counts.get(
                "ambiguous_voice_signature", 0
            ),
            "semantic_weak_alignment_count": drift_counts.get(
                "weak_profile_alignment", 0
            ),
        },
        reasons=[failure_reason] if failure_reason else [],
        source="validator",
        failure_class="recoverable_dramatic_failure" if failure_reason else None,
        failure_reason=failure_reason,
        offending_actor_id=str(first_blocking.get("speaker_id") or first_finding.get("speaker_id") or "").strip() or None,
        actual_owner=str(first_blocking.get("actual_source_actor_id") or "").strip() or None,
        expected_owner=str(first_blocking.get("expected_profile_actor_id") or "").strip() or None,
    )


def _voice_semantic_failure_present(result: dict[str, Any]) -> bool:
    blocking = result.get("blocking_findings") if isinstance(result.get("blocking_findings"), list) else []
    for finding in blocking:
        if not isinstance(finding, dict):
            continue
        if str(finding.get("policy_source") or "") == (
            "character_voice.voice_consistency.semantic_classification"
        ):
            return True
    return False


def _scene_energy_aspect_record(
    *,
    target: dict[str, Any] | None,
    transition: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_dict = target if isinstance(target, dict) else {}
    transition_dict = transition if isinstance(transition, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    failure_codes = [
        str(code)
        for code in (validation_dict.get("failure_codes") or [])
        if str(code).strip()
    ]
    validation_status = str(validation_dict.get("status") or "").strip().lower()
    applicable = bool(target_dict)
    if not validation_dict:
        aspect_status = "partial" if applicable else "not_applicable"
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
            "transition_allowed": transition_dict.get("allowed"),
        }
    )
    selected = {
        "target": target_dict,
        "transition": transition_dict,
        "energy_level": target_dict.get("energy_level"),
        "pressure_vector": target_dict.get("pressure_vector"),
        "tempo": target_dict.get("tempo"),
        "density": target_dict.get("density"),
        "volatility": target_dict.get("volatility"),
        "target_transition": target_dict.get("target_transition"),
        "minimum_actor_response_count": target_dict.get("minimum_actor_response_count"),
    }
    return make_aspect_record(
        applicable=applicable,
        status=aspect_status,
        expected={
            "schema_version": target_dict.get("schema_version"),
            "policy_present": bool(policy),
            "policy_enabled": bool((policy or {}).get("enabled")),
            "validation_uses_structured_counts": True,
        },
        selected=selected,
        actual=actual,
        reasons=failure_codes or (["scene_energy_target_selected"] if target_dict and not validation_dict else []),
        source="runtime" if not validation_dict else "validator",
        failure_class="recoverable_dramatic_failure" if failure_codes else None,
        failure_reason=failure_codes[0] if failure_codes else None,
    )


def _pacing_rhythm_aspect_record(
    *,
    state_record: dict[str, Any] | None,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state_dict = state_record if isinstance(state_record, dict) else {}
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    failure_codes = [
        str(code)
        for code in (validation_dict.get("failure_codes") or [])
        if str(code).strip()
    ]
    validation_status = str(validation_dict.get("status") or "").strip().lower()
    applicable = bool(target_dict)
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
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    selected = {
        "state": state_dict,
        "target": target_dict,
        "cadence": target_dict.get("cadence"),
        "tempo_arc": target_dict.get("tempo_arc"),
        "response_shape": target_dict.get("response_shape"),
        "turn_change_policy": target_dict.get("turn_change_policy"),
        "min_visible_blocks": target_dict.get("min_visible_blocks"),
        "max_visible_blocks": target_dict.get("max_visible_blocks"),
        "requires_pause": target_dict.get("requires_pause"),
        "blocks_forced_speech": target_dict.get("blocks_forced_speech"),
    }
    return make_aspect_record(
        applicable=applicable,
        status=aspect_status,
        expected={
            "schema_version": target_dict.get("schema_version"),
            "policy_present": bool(policy),
            "policy_enabled": bool((policy or {}).get("enabled")),
            "validation_uses_structured_counts": True,
        },
        selected=selected,
        actual=actual,
        reasons=failure_codes or (["pacing_rhythm_target_selected"] if target_dict and not validation_dict else []),
        source="runtime" if not validation_dict else "validator",
        failure_class="recoverable_dramatic_failure" if failure_codes else None,
        failure_reason=failure_codes[0] if failure_codes else None,
    )


def _social_pressure_aspect_record(
    *,
    state_record: dict[str, Any] | None,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state_dict = state_record if isinstance(state_record, dict) else {}
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    failure_codes = [
        str(code)
        for code in (validation_dict.get("failure_codes") or [])
        if str(code).strip()
    ]
    validation_status = str(validation_dict.get("status") or "").strip().lower()
    applicable = bool(target_dict)
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
            "current_score": state_dict.get("current_score") or target_dict.get("target_score"),
            "current_band": state_dict.get("current_band") or target_dict.get("target_band"),
            "trend": state_dict.get("trend") or target_dict.get("trend"),
            "velocity": state_dict.get("velocity"),
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    selected = {
        "state": state_dict,
        "target": target_dict,
        "target_score": target_dict.get("target_score"),
        "target_band": target_dict.get("target_band"),
        "trend": target_dict.get("trend"),
        "pressure_floor": target_dict.get("pressure_floor"),
        "requires_visible_pressure": target_dict.get("requires_visible_pressure"),
        "release_allowed": target_dict.get("release_allowed"),
    }
    return make_aspect_record(
        applicable=applicable,
        status=aspect_status,
        expected={
            "schema_version": target_dict.get("schema_version"),
            "policy_present": bool(policy),
            "policy_enabled": bool((policy or {}).get("enabled")),
            "validation_uses_policy_thresholds": True,
        },
        selected=selected,
        actual=actual,
        reasons=failure_codes or (["social_pressure_target_selected"] if target_dict and not validation_dict else []),
        source="runtime" if not validation_dict else "validator",
        failure_class="recoverable_dramatic_failure" if failure_codes else None,
        failure_reason=failure_codes[0] if failure_codes else None,
    )


def _information_disclosure_aspect_record(
    *,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = policy if isinstance(policy, dict) else {}
    failure_codes = [
        str(code)
        for code in (validation_dict.get("failure_codes") or [])
        if str(code).strip()
    ]
    validation_status = str(validation_dict.get("status") or "").strip().lower()
    policy_present = bool(policy_dict.get("units") or target_dict.get("policy_enabled"))
    if not validation_dict:
        aspect_status = "partial" if target_dict.get("policy_enabled") else "not_applicable"
    elif validation_status == "approved":
        aspect_status = "passed"
    elif validation_status == "not_applicable":
        aspect_status = "not_applicable"
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
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    return make_aspect_record(
        applicable=policy_present or bool(target_dict.get("policy_enabled")),
        status=aspect_status,
        expected={
            "schema_version": target_dict.get("schema_version"),
            "policy_present": policy_present,
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "commit_impact": target_dict.get("commit_impact"),
            "require_structured_events": bool(target_dict.get("require_structured_events")),
            "max_visible_units_per_turn": int(target_dict.get("max_visible_units_per_turn") or 0),
        },
        selected={
            "selected_unit_ids": target_dict.get("selected_unit_ids") or [],
            "allowed_unit_ids": target_dict.get("allowed_unit_ids") or [],
            "withheld_unit_ids": target_dict.get("withheld_unit_ids") or [],
            "forbidden_unit_ids": target_dict.get("forbidden_unit_ids") or [],
            "selected_units": target_dict.get("selected_units") or [],
            "disclosure_mode": target_dict.get("disclosure_mode"),
        },
        actual=actual,
        reasons=failure_codes
        or (["information_disclosure_target_selected"] if target_dict.get("selected_unit_ids") and not validation_dict else []),
        source="runtime" if not validation_dict else "validator",
        failure_class="recoverable_dramatic_failure" if failure_codes else None,
        failure_reason=failure_codes[0] if failure_codes else None,
    )


def _npc_agency_plan_from_state(state: "RuntimeTurnState") -> dict[str, Any] | None:
    packet = (
        state.get("dramatic_generation_packet")
        if isinstance(state.get("dramatic_generation_packet"), dict)
        else {}
    )
    simulation = (
        packet.get("npc_agency_simulation")
        if isinstance(packet.get("npc_agency_simulation"), dict)
        else None
    )
    if simulation:
        return simulation
    direct_simulation = state.get("npc_agency_simulation")
    if isinstance(direct_simulation, dict) and direct_simulation:
        return direct_simulation
    plan = packet.get("npc_agency_plan") if isinstance(packet.get("npc_agency_plan"), dict) else None
    if plan:
        return plan
    direct = state.get("npc_agency_plan")
    return direct if isinstance(direct, dict) and direct else None


def _npc_agency_aspect_record(validation: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(validation, dict):
        return make_aspect_record(
            applicable=False,
            status="not_applicable",
            expected={"npc_agency_plan_present": False},
            actual={},
            source="validator",
        )

    status = str(validation.get("status") or "not_applicable").strip().lower()
    if status == "approved":
        aspect_status = "passed"
    elif status == "degraded":
        aspect_status = "partial"
    elif status == "rejected":
        aspect_status = "failed"
    else:
        aspect_status = "missing"

    realization = (
        validation.get("npc_initiative_realization_v1")
        if isinstance(validation.get("npc_initiative_realization_v1"), dict)
        else {}
    )
    plan = (
        validation.get("npc_agency_plan")
        if isinstance(validation.get("npc_agency_plan"), dict)
        else {}
    )
    simulation = (
        validation.get("npc_agency_simulation")
        if isinstance(validation.get("npc_agency_simulation"), dict)
        else {}
    )
    long_horizon_state = (
        simulation.get("npc_long_horizon_state")
        if isinstance(simulation.get("npc_long_horizon_state"), dict)
        else {}
    )
    private_plan_conflict = (
        simulation.get("npc_plan_conflict_resolution")
        if isinstance(simulation.get("npc_plan_conflict_resolution"), dict)
        else {}
    )
    intention_threads = (
        long_horizon_state.get("intention_threads")
        if isinstance(long_horizon_state.get("intention_threads"), list)
        else []
    )
    error_codes = [str(code) for code in (validation.get("error_codes") or []) if str(code).strip()]
    feedback_code = str(validation.get("feedback_code") or "").strip() or None
    forbidden = bool(validation.get("forbidden_planned_actor_ids") or validation.get("forbidden_realized_actor_ids"))
    failed = aspect_status == "failed"
    not_full = (
        bool(validation.get("not_full_multi_agent_simulation"))
        if "not_full_multi_agent_simulation" in validation
        else bool(plan.get("not_full_multi_agent_simulation"))
    )
    return make_aspect_record(
        applicable=True,
        status=aspect_status,
        expected={
            "npc_agency_plan_present": True,
            "contract_status": validation.get("contract_status") or plan.get("contract_status"),
            "not_full_multi_agent_simulation": not_full,
            "independent_planning_expected": bool(simulation),
            "candidate_actor_ids": simulation.get("candidate_actor_ids") or [],
            "required_actor_ids": realization.get("required_actor_ids") or plan.get("required_actor_ids") or [],
            "minimum_secondary_initiatives_required": plan.get("minimum_secondary_initiatives_required"),
            "long_horizon_state_present": bool(long_horizon_state),
            "private_plan_resolution_present": bool(
                private_plan_conflict.get("selected_private_plan_ids")
            ),
            "selected_private_plan_ids": private_plan_conflict.get("selected_private_plan_ids") or [],
        },
        selected={
            "primary_responder_id": plan.get("primary_responder_id"),
            "secondary_responder_ids": plan.get("secondary_responder_ids") or [],
            "selected_private_plan_ids": validation.get("selected_private_plan_ids") or [],
            "selected_private_plan_actor_ids": validation.get("selected_private_plan_actor_ids") or [],
        },
        actual={
            "validation_status": status,
            "planned_actor_ids": realization.get("planned_actor_ids") or [],
            "realized_actor_ids": validation.get("realized_actor_ids") or [],
            "missing_required_actor_ids": validation.get("missing_required_actor_ids") or [],
            "forbidden_planned_actor_ids": validation.get("forbidden_planned_actor_ids") or [],
            "forbidden_realized_actor_ids": validation.get("forbidden_realized_actor_ids") or [],
            "error_codes": error_codes,
            "multi_npc_initiative_realized": bool(realization.get("multi_npc_initiative_realized")),
            "independent_planning_used": bool(validation.get("independent_planning_used")),
            "planner_scope": simulation.get("planner_scope") or plan.get("planner_scope"),
            "candidate_actor_ids": simulation.get("candidate_actor_ids") or [],
            "long_horizon_state_present": bool(long_horizon_state),
            "intention_threads_active": len(intention_threads),
            "private_plan_resolution_present": bool(validation.get("private_plan_resolution_present")),
            "private_plan_visibility_respected": bool(
                validation.get("private_plan_visibility_respected")
            ),
            "selected_private_plan_ids": validation.get("selected_private_plan_ids") or [],
            "selected_private_plan_actor_ids": validation.get("selected_private_plan_actor_ids") or [],
            "withheld_private_plan_ids": validation.get("withheld_private_plan_ids") or [],
            "selected_private_plan_source_intention_thread_ids": validation.get(
                "selected_private_plan_source_intention_thread_ids"
            )
            or [],
            "unrealized_selected_private_plan_actor_ids": validation.get(
                "unrealized_selected_private_plan_actor_ids"
            )
            or [],
            "carry_forward_actor_ids": simulation.get("carry_forward_actor_ids") or [],
            "closure_status": NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS
            if validation.get("missing_required_actor_ids")
            else NPC_AGENCY_CLOSURE_CLOSED_STATUS,
            "not_full_multi_agent_simulation": not_full,
            "contract_status": validation.get("contract_status") or realization.get("contract_status"),
        },
        reasons=error_codes,
        source="validator",
        failure_class=(
            "hard_contract_failure"
            if failed and forbidden
            else "recoverable_dramatic_failure"
            if failed
            else None
        ),
        failure_reason=feedback_code if failed else None,
    )


def _build_runtime_aspect_validation(
    *,
    state: "RuntimeTurnState",
    generation: dict[str, Any],
    proposed_state_effects: list[dict[str, Any]],
    outcome: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate runtime authority/capability aspects as validation inputs."""
    next_outcome = dict(outcome or {})
    actor_lane_validation = _actor_lane_validation(state, generation)
    if (
        actor_lane_validation.get("status") == "rejected"
        and next_outcome.get("status") == "approved"
    ):
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": actor_lane_validation.get("reason") or "actor_lane_validation_rejected",
            "actor_lane_validation": actor_lane_validation,
        }
    else:
        next_outcome = {
            **next_outcome,
            "actor_lane_validation": actor_lane_validation,
        }

    narrator_authority, npc_authority = _build_authority_aspect_records(
        state=state,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
    )
    authority_ledger = set_aspect_record(
        state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
        ASPECT_NARRATOR_AUTHORITY,
        narrator_authority,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_NPC_AUTHORITY,
        npc_authority,
    )
    voice_validation = _voice_consistency_validation(state=state, generation=generation)
    voice_record = _voice_aspect_record(voice_validation)
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_VOICE_CONSISTENCY,
        voice_record,
    )
    structured_output = _structured_output_from_generation(generation)
    scene_energy_validation = validate_scene_energy_realization(
        scene_energy_target=state.get("scene_energy_target")
        if isinstance(state.get("scene_energy_target"), dict)
        else None,
        scene_energy_transition=state.get("scene_energy_transition")
        if isinstance(state.get("scene_energy_transition"), dict)
        else None,
        structured_output=structured_output,
        scene_plan_record=state.get("scene_plan_record")
        if isinstance(state.get("scene_plan_record"), dict)
        else None,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_SCENE_ENERGY,
        _scene_energy_aspect_record(
            target=state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else None,
            transition=state.get("scene_energy_transition")
            if isinstance(state.get("scene_energy_transition"), dict)
            else None,
            validation=scene_energy_validation,
        ),
    )
    next_outcome = {
        **next_outcome,
        "scene_energy_validation": scene_energy_validation,
    }
    pacing_rhythm_validation = validate_pacing_rhythm_realization(
        pacing_rhythm_target=state.get("pacing_rhythm_target")
        if isinstance(state.get("pacing_rhythm_target"), dict)
        else None,
        pacing_rhythm_state=state.get("pacing_rhythm_state")
        if isinstance(state.get("pacing_rhythm_state"), dict)
        else None,
        structured_output=structured_output,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_PACING_RHYTHM,
        _pacing_rhythm_aspect_record(
            state_record=state.get("pacing_rhythm_state")
            if isinstance(state.get("pacing_rhythm_state"), dict)
            else None,
            target=state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else None,
            validation=pacing_rhythm_validation,
        ),
    )
    next_outcome = {
        **next_outcome,
        "pacing_rhythm_validation": pacing_rhythm_validation,
    }
    improvisational_validation = validate_improvisational_coherence_realization(
        improvisational_coherence_target=state.get("improvisational_coherence_target")
        if isinstance(state.get("improvisational_coherence_target"), dict)
        else None,
        structured_output=structured_output,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_IMPROVISATIONAL_COHERENCE,
        build_improvisational_coherence_aspect_record(
            target=state.get("improvisational_coherence_target")
            if isinstance(state.get("improvisational_coherence_target"), dict)
            else None,
            validation=improvisational_validation,
            source="validator",
        ),
    )
    next_outcome = {
        **next_outcome,
        "improvisational_coherence_validation": improvisational_validation,
    }
    social_pressure_validation = validate_social_pressure_metric(
        social_pressure_target=state.get("social_pressure_target")
        if isinstance(state.get("social_pressure_target"), dict)
        else None,
        social_pressure_state=state.get("social_pressure_state")
        if isinstance(state.get("social_pressure_state"), dict)
        else None,
        module_runtime_policy=state.get("module_runtime_policy")
        if isinstance(state.get("module_runtime_policy"), dict)
        else None,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_SOCIAL_PRESSURE,
        _social_pressure_aspect_record(
            state_record=state.get("social_pressure_state")
            if isinstance(state.get("social_pressure_state"), dict)
            else None,
            target=state.get("social_pressure_target")
            if isinstance(state.get("social_pressure_target"), dict)
            else None,
            validation=social_pressure_validation,
        ),
    )
    next_outcome = {
        **next_outcome,
        "social_pressure_validation": social_pressure_validation,
    }
    information_disclosure_validation = validate_information_disclosure_realization(
        information_disclosure_target=state.get("information_disclosure_target")
        if isinstance(state.get("information_disclosure_target"), dict)
        else None,
        structured_output=structured_output,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_INFORMATION_DISCLOSURE,
        _information_disclosure_aspect_record(
            target=state.get("information_disclosure_target")
            if isinstance(state.get("information_disclosure_target"), dict)
            else None,
            validation=information_disclosure_validation,
        ),
    )
    next_outcome = {
        **next_outcome,
        "information_disclosure_validation": information_disclosure_validation,
    }
    dramatic_irony_validation = validate_dramatic_irony_realization(
        record=state.get("dramatic_irony_record")
        if isinstance(state.get("dramatic_irony_record"), dict)
        else None,
        generation=generation,
        proposed_state_effects=proposed_state_effects,
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_DRAMATIC_IRONY,
        build_dramatic_irony_aspect_record(
            record=state.get("dramatic_irony_record")
            if isinstance(state.get("dramatic_irony_record"), dict)
            else None,
            validation=dramatic_irony_validation,
            source="validator",
        ),
    )
    next_outcome = {
        **next_outcome,
        "dramatic_irony_validation": dramatic_irony_validation,
    }
    npc_agency_plan = _npc_agency_plan_from_state(state)
    actor_lane_context = (
        state.get("actor_lane_context")
        if isinstance(state.get("actor_lane_context"), dict)
        else None
    )
    npc_initiative_validation = (
        validate_npc_initiative_realization(
            npc_agency_plan,
            structured_output,
            actor_lane_context=actor_lane_context,
            strict_required=True,
        )
        if isinstance(npc_agency_plan, dict)
        else None
    )
    npc_agency_record = _npc_agency_aspect_record(npc_initiative_validation)
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_NPC_AGENCY,
        npc_agency_record,
    )
    if isinstance(npc_initiative_validation, dict):
        next_outcome = {
            **next_outcome,
            "npc_initiative_validation": npc_initiative_validation,
        }
    capability_selection = build_capability_selection_record(
        interpreted_input=state.get("interpreted_input")
        if isinstance(state.get("interpreted_input"), dict)
        else {},
        player_action_frame=state.get("player_action_frame")
        if isinstance(state.get("player_action_frame"), dict)
        else {},
        affordance_resolution=state.get("affordance_resolution")
        if isinstance(state.get("affordance_resolution"), dict)
        else {},
        narrator_authority=narrator_authority,
        npc_authority=npc_authority,
        module_runtime_policy=state.get("module_runtime_policy")
        if isinstance(state.get("module_runtime_policy"), dict)
        else None,
    )
    cap_violations = capability_selection.get("violations")
    cap_violation = cap_violations[0] if isinstance(cap_violations, list) and cap_violations else {}
    cap_missing = capability_selection.get("missing_required_capabilities")
    cap_missing_first = cap_missing[0] if isinstance(cap_missing, list) and cap_missing else None
    capability_status = str(capability_selection.get("status") or "missing").strip()
    cap_reason = (
        str(cap_violation.get("reason") or cap_violation.get("capability"))
        if isinstance(cap_violation, dict) and cap_violation
        else f"missing_required_capability:{cap_missing_first}"
        if cap_missing_first
        else ""
    )
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_CAPABILITY_SELECTION,
        make_aspect_record(
            applicable=True,
            status=capability_status if capability_status in {"passed", "failed", "partial"} else "missing",
            expected={
                "blocked_capabilities": capability_selection.get("blocked_capabilities"),
                "required_capabilities": capability_selection.get("required_capabilities"),
                "selected_capabilities_must_be_realized_or_marked_missing": True,
            },
            selected={
                "requested_capabilities": capability_selection.get("requested_capabilities"),
                "selected_capabilities": capability_selection.get("selected_capabilities"),
                "blocked_capabilities": capability_selection.get("blocked_capabilities"),
                "required_capabilities": capability_selection.get("required_capabilities"),
            },
            actual={
                "realized_capabilities": capability_selection.get("realized_capabilities"),
                "violated_capabilities": capability_selection.get("violated_capabilities"),
                "violations": capability_selection.get("violations"),
                "missing_required_capabilities": capability_selection.get("missing_required_capabilities"),
                "forbidden_capability_realized": bool(cap_violation),
            },
            reasons=[cap_reason] if cap_reason else [],
            source="runtime",
            failure_class="hard_contract_failure"
            if cap_violation
            else "recoverable_contract_gap"
            if cap_missing_first
            else None,
            failure_reason=(
                str(cap_violation.get("reason") or "forbidden_capability_realized")
                if isinstance(cap_violation, dict) and cap_violation
                else "capability_missing_required"
                if cap_missing_first
                else None
            ),
            offending_actor_id=cap_violation.get("offending_actor_id")
            if isinstance(cap_violation, dict)
            else None,
            selected_capability=cap_missing_first,
            realized_capability=cap_violation.get("capability")
            if isinstance(cap_violation, dict)
            else None,
        ),
    )

    authority_failure = None
    if npc_authority.get("status") == "failed":
        authority_failure = npc_authority
    elif narrator_authority.get("status") == "failed":
        authority_failure = narrator_authority

    capability_failure = None
    if isinstance(cap_violation, dict) and cap_violation:
        capability_failure = {
            "failure_reason": str(cap_violation.get("reason") or "forbidden_capability_realized"),
            "violated_capabilities": capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": capability_selection.get("missing_required_capabilities") or [],
            "offending_actor_id": cap_violation.get("offending_actor_id"),
        }
    elif cap_missing_first:
        capability_failure = {
            "failure_reason": "capability_missing_required",
            "violated_capabilities": capability_selection.get("violated_capabilities") or [],
            "missing_required_capabilities": capability_selection.get("missing_required_capabilities") or [],
            "selected_capability": cap_missing_first,
        }
    scene_energy_failure = None
    if (
        isinstance(scene_energy_validation, dict)
        and str(scene_energy_validation.get("status") or "").strip().lower() == "rejected"
    ):
        scene_energy_codes = [
            str(code)
            for code in (scene_energy_validation.get("failure_codes") or [])
            if str(code).strip()
        ]
        scene_energy_failure = {
            "failure_reason": str(
                scene_energy_validation.get("feedback_code")
                or (scene_energy_codes[0] if scene_energy_codes else "scene_energy_validation_failed")
            ),
            "failure_codes": scene_energy_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    pacing_rhythm_failure = None
    if (
        isinstance(pacing_rhythm_validation, dict)
        and str(pacing_rhythm_validation.get("status") or "").strip().lower() == "rejected"
    ):
        rhythm_codes = [
            str(code)
            for code in (pacing_rhythm_validation.get("failure_codes") or [])
            if str(code).strip()
        ]
        pacing_rhythm_failure = {
            "failure_reason": str(
                pacing_rhythm_validation.get("feedback_code")
                or (rhythm_codes[0] if rhythm_codes else "pacing_rhythm_validation_failed")
            ),
            "failure_codes": rhythm_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    improvisational_failure = None
    if (
        isinstance(improvisational_validation, dict)
        and str(improvisational_validation.get("status") or "").strip().lower() == "rejected"
    ):
        improv_codes = [
            str(code)
            for code in (improvisational_validation.get("failure_codes") or [])
            if str(code).strip()
        ]
        improvisational_failure = {
            "failure_reason": str(
                improvisational_validation.get("feedback_code")
                or (
                    improv_codes[0]
                    if improv_codes
                    else "improvisational_coherence_validation_failed"
                )
            ),
            "failure_codes": improv_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    social_pressure_failure = None
    if (
        isinstance(social_pressure_validation, dict)
        and str(social_pressure_validation.get("status") or "").strip().lower() == "rejected"
    ):
        pressure_codes = [
            str(code)
            for code in (social_pressure_validation.get("failure_codes") or [])
            if str(code).strip()
        ]
        social_pressure_failure = {
            "failure_reason": str(
                social_pressure_validation.get("feedback_code")
                or (pressure_codes[0] if pressure_codes else "social_pressure_validation_failed")
            ),
            "failure_codes": pressure_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    information_disclosure_failure = None
    if (
        isinstance(information_disclosure_validation, dict)
        and str(information_disclosure_validation.get("status") or "").strip().lower() == "rejected"
    ):
        disclosure_codes = [
            str(code)
            for code in (information_disclosure_validation.get("failure_codes") or [])
            if str(code).strip()
        ]
        information_disclosure_failure = {
            "failure_reason": str(
                information_disclosure_validation.get("feedback_code")
                or (
                    disclosure_codes[0]
                    if disclosure_codes
                    else "information_disclosure_validation_failed"
                )
            ),
            "failure_codes": disclosure_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    dramatic_irony_failure = None
    if (
        isinstance(dramatic_irony_validation, dict)
        and str(dramatic_irony_validation.get("status") or "").strip().lower() == "rejected"
    ):
        irony_codes = [
            str(code)
            for code in (dramatic_irony_validation.get("violation_codes") or [])
            if str(code).strip()
        ]
        dramatic_irony_failure = {
            "failure_reason": str(
                dramatic_irony_validation.get("feedback_code")
                or (irony_codes[0] if irony_codes else "dramatic_irony_validation_failed")
            ),
            "violation_codes": irony_codes,
            "failure_class": "recoverable_dramatic_failure",
        }
    npc_agency_failure = None
    if (
        isinstance(npc_initiative_validation, dict)
        and str(npc_initiative_validation.get("status") or "").strip().lower() != "approved"
    ):
        npc_error_codes = [
            str(code)
            for code in (npc_initiative_validation.get("error_codes") or [])
            if str(code).strip()
        ]
        forbidden_npc_agency = bool(
            npc_initiative_validation.get("forbidden_planned_actor_ids")
            or npc_initiative_validation.get("forbidden_realized_actor_ids")
        )
        npc_agency_failure = {
            "failure_reason": str(
                npc_initiative_validation.get("feedback_code")
                or (npc_error_codes[0] if npc_error_codes else "npc_initiative_validation_failed")
            ),
            "error_codes": npc_error_codes,
            "missing_required_actor_ids": npc_initiative_validation.get("missing_required_actor_ids") or [],
            "forbidden_planned_actor_ids": npc_initiative_validation.get("forbidden_planned_actor_ids") or [],
            "forbidden_realized_actor_ids": npc_initiative_validation.get("forbidden_realized_actor_ids") or [],
            "failure_class": "hard_contract_failure"
            if forbidden_npc_agency
            else "recoverable_dramatic_failure",
        }

    if authority_failure is not None:
        failure_reason = str(
            authority_failure.get("failure_reason")
            or (authority_failure.get("reasons") or ["authority_contract_violation"])[0]
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "runtime_aspect_ledger_authority_v1",
            "authority_contract_violation": True,
            "failure_class": "hard_contract_failure",
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "runtime_aspect_failure": {
                "aspect_status": authority_failure.get("status"),
                "failure_reason": failure_reason,
                "offending_actor_id": authority_failure.get("offending_actor_id"),
                "offending_block_id": authority_failure.get("offending_block_id"),
                "expected_owner": authority_failure.get("expected_owner"),
                "actual_owner": authority_failure.get("actual_owner"),
                "missing_field": authority_failure.get("missing_field"),
            },
        }
        if capability_failure is not None:
            next_outcome["capability_failure"] = capability_failure
    elif capability_failure is not None:
        failure_reason = str(capability_failure.get("failure_reason") or "capability_missing_required")
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "runtime_aspect_ledger_capability_v1",
            "capability_contract_violation": bool(cap_violation),
            "failure_class": "hard_contract_failure" if cap_violation else "recoverable_contract_gap",
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "capability_failure": capability_failure,
        }
    elif (
        voice_validation.get("status") == "rejected"
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": "voice_consistency_drift",
            "error_code": "voice_consistency_drift",
            "validator_lane": "runtime_voice_consistency_v2"
            if _voice_semantic_failure_present(voice_validation)
            else "runtime_voice_consistency_v1",
            "voice_consistency_validation": voice_validation,
            "voice_consistency_contract_violation": True,
            "failure_class": "recoverable_dramatic_failure",
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
        }
    elif npc_agency_failure is not None:
        failure_reason = str(npc_agency_failure.get("failure_reason") or "npc_initiative_validation_failed")
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "npc_initiative_validation_v1",
            "npc_agency_contract_violation": True,
            "failure_class": npc_agency_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "npc_agency_failure": npc_agency_failure,
        }
    elif (
        dramatic_irony_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(
            dramatic_irony_failure.get("failure_reason")
            or "dramatic_irony_validation_failed"
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "dramatic_irony_validation_v1",
            "dramatic_irony_contract_violation": True,
            "failure_class": dramatic_irony_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "dramatic_irony_failure": dramatic_irony_failure,
        }
    elif (
        scene_energy_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(scene_energy_failure.get("failure_reason") or "scene_energy_validation_failed")
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "scene_energy_validation_v1",
            "scene_energy_contract_violation": True,
            "failure_class": scene_energy_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "scene_energy_failure": scene_energy_failure,
        }
    elif (
        pacing_rhythm_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(
            pacing_rhythm_failure.get("failure_reason")
            or "pacing_rhythm_validation_failed"
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "pacing_rhythm_validation_v1",
            "pacing_rhythm_contract_violation": True,
            "failure_class": pacing_rhythm_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "pacing_rhythm_failure": pacing_rhythm_failure,
        }
    elif (
        improvisational_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(
            improvisational_failure.get("failure_reason")
            or "improvisational_coherence_validation_failed"
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "improvisational_coherence_validation_v1",
            "improvisational_coherence_contract_violation": True,
            "failure_class": improvisational_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "improvisational_coherence_failure": improvisational_failure,
        }
    elif (
        social_pressure_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(
            social_pressure_failure.get("failure_reason")
            or "social_pressure_validation_failed"
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "social_pressure_validation_v1",
            "social_pressure_contract_violation": True,
            "failure_class": social_pressure_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "social_pressure_failure": social_pressure_failure,
        }
    elif (
        information_disclosure_failure is not None
        and str(next_outcome.get("status") or "").strip().lower() == "approved"
    ):
        failure_reason = str(
            information_disclosure_failure.get("failure_reason")
            or "information_disclosure_validation_failed"
        )
        next_outcome = {
            **next_outcome,
            "status": "rejected",
            "reason": failure_reason,
            "error_code": failure_reason,
            "validator_lane": "information_disclosure_validation_v1",
            "information_disclosure_contract_violation": True,
            "failure_class": information_disclosure_failure.get("failure_class"),
            "hard_boundary_failure": False,
            "recoverable_rejection": True,
            "information_disclosure_failure": information_disclosure_failure,
        }
    else:
        next_outcome = {
            **next_outcome,
            "voice_consistency_validation": voice_validation,
        }

    validation_failed = str(next_outcome.get("status") or "").strip().lower() != "approved"
    authority_ledger = set_aspect_record(
        authority_ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed" if validation_failed else "passed",
            expected={"validation_consumes_runtime_aspect_ledger": True},
            actual={
                "validation_status": next_outcome.get("status"),
                "reason": next_outcome.get("reason"),
                "validator_lane": next_outcome.get("validator_lane"),
                "authority_contract_violation": bool(next_outcome.get("authority_contract_violation")),
                "capability_contract_violation": bool(next_outcome.get("capability_contract_violation")),
                "voice_consistency_contract_violation": bool(next_outcome.get("voice_consistency_contract_violation")),
                "voice_consistency_status": voice_validation.get("status"),
                "voice_consistency_reason": voice_validation.get("reason"),
                "scene_energy_validation_status": (
                    scene_energy_validation.get("status")
                    if isinstance(scene_energy_validation, dict)
                    else None
                ),
                "scene_energy_contract_violation": bool(next_outcome.get("scene_energy_contract_violation")),
                "pacing_rhythm_validation_status": (
                    pacing_rhythm_validation.get("status")
                    if isinstance(pacing_rhythm_validation, dict)
                    else None
                ),
                "pacing_rhythm_contract_violation": bool(
                    next_outcome.get("pacing_rhythm_contract_violation")
                ),
                "improvisational_coherence_validation_status": (
                    improvisational_validation.get("status")
                    if isinstance(improvisational_validation, dict)
                    else None
                ),
                "improvisational_coherence_contract_violation": bool(
                    next_outcome.get("improvisational_coherence_contract_violation")
                ),
                "social_pressure_validation_status": (
                    social_pressure_validation.get("status")
                    if isinstance(social_pressure_validation, dict)
                    else None
                ),
                "social_pressure_contract_violation": bool(
                    next_outcome.get("social_pressure_contract_violation")
                ),
                "information_disclosure_validation_status": (
                    information_disclosure_validation.get("status")
                    if isinstance(information_disclosure_validation, dict)
                    else None
                ),
                "information_disclosure_contract_violation": bool(
                    next_outcome.get("information_disclosure_contract_violation")
                ),
                "dramatic_irony_validation_status": (
                    dramatic_irony_validation.get("status")
                    if isinstance(dramatic_irony_validation, dict)
                    else None
                ),
                "dramatic_irony_contract_violation": bool(
                    next_outcome.get("dramatic_irony_contract_violation")
                ),
                "npc_initiative_validation_status": (
                    npc_initiative_validation.get("status")
                    if isinstance(npc_initiative_validation, dict)
                    else None
                ),
                "npc_agency_contract_violation": bool(next_outcome.get("npc_agency_contract_violation")),
                "recoverable_rejection": bool(next_outcome.get("recoverable_rejection")),
                "hard_boundary_failure": bool(next_outcome.get("hard_boundary_failure")),
            },
            reasons=[str(next_outcome.get("reason"))] if validation_failed and next_outcome.get("reason") else [],
            source="validator",
            failure_class=next_outcome.get("failure_class") if validation_failed else None,
            failure_reason=str(next_outcome.get("reason")) if validation_failed and next_outcome.get("reason") else None,
            offending_actor_id=(
                authority_failure.get("offending_actor_id")
                if isinstance(authority_failure, dict)
                else capability_failure.get("offending_actor_id")
                if isinstance(capability_failure, dict)
                else None
            ),
            offending_block_id=(
                authority_failure.get("offending_block_id")
                if isinstance(authority_failure, dict)
                else None
            ),
            expected_owner=(
                authority_failure.get("expected_owner")
                if isinstance(authority_failure, dict)
                else None
            ),
            actual_owner=(
                authority_failure.get("actual_owner")
                if isinstance(authority_failure, dict)
                else None
            ),
            missing_field=(
                authority_failure.get("missing_field")
                if isinstance(authority_failure, dict)
                else None
            ),
        ),
    )
    return {
        "outcome": next_outcome,
        "actor_lane_validation": actor_lane_validation,
        "turn_aspect_ledger": authority_ledger,
        "narrator_authority": narrator_authority,
        "npc_authority": npc_authority,
        "capability_selection": capability_selection,
        "voice_consistency_validation": voice_validation,
        "scene_energy_validation": scene_energy_validation,
        "pacing_rhythm_validation": pacing_rhythm_validation,
        "improvisational_coherence_validation": improvisational_validation,
        "social_pressure_validation": social_pressure_validation,
        "information_disclosure_validation": information_disclosure_validation,
        "dramatic_irony_validation": dramatic_irony_validation,
        "npc_initiative_validation": npc_initiative_validation,
        "authority_failure": authority_failure,
        "capability_failure": capability_failure,
        "scene_energy_failure": scene_energy_failure,
        "improvisational_coherence_failure": improvisational_failure,
        "social_pressure_failure": social_pressure_failure,
        "information_disclosure_failure": information_disclosure_failure,
        "dramatic_irony_failure": dramatic_irony_failure,
        "npc_agency_failure": npc_agency_failure,
    }


def _has_usable_narrative_effect(proposed_effects: list[dict[str, Any]]) -> bool:
    """Return True when proposed effects already include non-empty narrative prose."""
    for effect in proposed_effects:
        if not isinstance(effect, dict):
            continue
        desc = str(effect.get("description") or "").strip()
        if not desc:
            continue
        effect_type = str(effect.get("effect_type") or "").strip().lower()
        if effect_type.startswith("narrative") or effect_type in {"opening", "scene", "story"}:
            return True
    return False


def _build_actor_lane_opening_narration(
    *,
    state: "RuntimeTurnState",
    structured_output: dict[str, Any],
) -> str:
    """Synthesize opening narration from approved actor lanes when narration is missing."""
    actor_lane_ctx = (
        state.get("actor_lane_context")
        if isinstance(state.get("actor_lane_context"), dict)
        else {}
    )
    human_actor = str(
        actor_lane_ctx.get("selected_player_role")
        or actor_lane_ctx.get("human_actor_id")
        or "the player"
    ).strip()
    role_label = human_actor.replace("_", " ").strip().title() if human_actor else "The player"

    first_spoken = ""
    spoken = structured_output.get("spoken_lines")
    if isinstance(spoken, list):
        for row in spoken:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or row.get("line") or "").strip()
            speaker = str(row.get("speaker_id") or "").strip().replace("_", " ").title()
            if text:
                first_spoken = f"{speaker} breaks the silence: {text}" if speaker else text
                break

    first_action = ""
    action = structured_output.get("action_lines")
    if isinstance(action, list):
        for row in action:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or row.get("line") or "").strip()
            actor = str(row.get("actor_id") or "").strip().replace("_", " ").title()
            if text:
                first_action = f"{actor} {text}" if actor else text
                break

    policy = state.get("module_runtime_policy") if isinstance(state.get("module_runtime_policy"), dict) else {}
    opening_policy = policy.get("opening_policy") if isinstance(policy.get("opening_policy"), dict) else {}
    opening_contract = (
        opening_policy.get("opening_contract")
        if isinstance(opening_policy.get("opening_contract"), dict)
        else {}
    )
    must_establish = [
        str(item).replace("_", " ").strip()
        for item in (opening_contract.get("must_establish") or [])
        if str(item).strip()
    ][:4]
    events = opening_policy.get("narrative_events") if isinstance(opening_policy.get("narrative_events"), list) else []
    event_labels = [
        str(event.get("title") or event.get("narrative_function") or event.get("id") or "").strip()
        for event in events
        if isinstance(event, dict)
    ][:3]
    intro_parts = event_labels or must_establish
    narrator_intro = (
        "The opening establishes " + ", ".join(intro_parts) + "."
        if intro_parts
        else "The opening establishes the module's starting situation."
    )
    role_anchor = f"You are {role_label}. The scene leaves your next action open."
    location_model = policy.get("location_model") if isinstance(policy.get("location_model"), dict) else {}
    anchor_area = str(location_model.get("narrative_anchor_area_id") or "").strip()
    location_details = location_model.get("locations") if isinstance(location_model.get("locations"), dict) else {}
    anchor_detail = (
        location_details.get(anchor_area)
        if anchor_area and isinstance(location_details.get(anchor_area), dict)
        else {}
    )
    location_label = str(anchor_detail.get("name") or anchor_detail.get("id") or anchor_area or "the starting location").strip()
    scene_setup = f"The visible scene settles into {location_label} with the playable situation in view."
    if first_spoken or first_action:
        lane_projection = " ".join([x for x in (first_spoken, first_action) if x]).strip()
        scene_setup = f"{scene_setup} {lane_projection}".strip()
    return f"{narrator_intro}\n\n{role_anchor}\n\n{scene_setup}"


def _runtime_governance_policy_from_state(state: "RuntimeTurnState") -> dict[str, Any]:
    policy = state.get("module_runtime_policy") if isinstance(state.get("module_runtime_policy"), dict) else {}
    governance = (
        policy.get("runtime_governance_policy")
        if isinstance(policy.get("runtime_governance_policy"), dict)
        else {}
    )
    return governance if isinstance(governance, dict) else {}


def _runtime_governance_section(state: "RuntimeTurnState", section: str) -> dict[str, Any]:
    governance = _runtime_governance_policy_from_state(state)
    value = governance.get(section)
    return value if isinstance(value, dict) else {}


def _runtime_governance_hook_enabled(state: "RuntimeTurnState", hook_id: str) -> bool:
    continuity = _runtime_governance_section(state, "continuity")
    hooks = continuity.get("hooks") if isinstance(continuity.get("hooks"), list) else []
    return hook_id in {str(item).strip() for item in hooks if str(item).strip()}


def _derive_active_character_keys(
    *,
    yaml_slice: dict[str, Any] | None,
    primary_responder: dict[str, Any],
    module_id: str,
    module_runtime_policy: dict[str, Any] | None = None,
) -> list[str]:
    """Compute the active cast for character-mind construction from module data.

    Resolution is data-driven: keys declared in ``yaml_slice.characters`` are
    preferred. They are reordered so the primary responder's key — matched
    either by direct key equality or by actor_id substring — comes first. When
    no YAML characters block is present, the neutral ModuleRuntimePolicy actor
    roster supplies the cast.
    """
    chars_block: dict[str, Any] = {}
    if isinstance(yaml_slice, dict) and isinstance(yaml_slice.get("characters"), dict):
        chars_block = yaml_slice["characters"]

    yaml_keys = [
        str(k).lower().strip()
        for k in chars_block.keys()
        if isinstance(k, str) and str(k).strip()
    ]
    if not yaml_keys:
        policy = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
        roster = policy.get("actor_roster") if isinstance(policy.get("actor_roster"), dict) else {}
        yaml_keys = [
            str(value.get("id") or key).lower().strip()
            for key, value in roster.items()
            if str(key).strip() and isinstance(value, dict)
        ]
        if not yaml_keys:
            yaml_keys = [
                str(key).lower().strip()
                for key in roster.keys()
                if str(key).strip()
            ]
    if not yaml_keys:
        return []

    primary_actor_id = ""
    primary_key = ""
    if isinstance(primary_responder, dict):
        primary_actor_id = str(primary_responder.get("actor_id") or "").lower()
        raw_key = primary_responder.get("character_key") or primary_responder.get("key")
        if isinstance(raw_key, str):
            primary_key = raw_key.lower().strip()

    first: str | None = None
    if primary_key and primary_key in yaml_keys:
        first = primary_key
    elif primary_actor_id:
        for k in yaml_keys:
            if k and k in primary_actor_id:
                first = k
                break

    if first is None:
        return yaml_keys

    ordered = [first] + [k for k in yaml_keys if k != first]
    return ordered


_RETRIEVAL_CONTINUITY_QUERY_CONTRACT = "runtime_retrieval_continuity_query.v1"


def _bounded_retrieval_token(value: Any, *, max_chars: int = 80) -> str | None:
    if isinstance(value, dict):
        for key in (
            "actor_id",
            "responder_id",
            "character_key",
            "thread_kind",
            "status",
            "resolution_hint",
            "class",
            "continuity_class",
        ):
            token = _bounded_retrieval_token(value.get(key), max_chars=max_chars)
            if token:
                return token
        return None
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    text = " ".join(text.split())
    if not text:
        return None
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text


def _collect_retrieval_tokens(*values: Any, max_chars: int = 80) -> list[str]:
    tokens: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item)
            return
        token = _bounded_retrieval_token(value, max_chars=max_chars)
        if token and token not in tokens:
            tokens.append(token)

    for value in values:
        visit(value)
    return tokens


def _retrieval_continuity_query_context(state: RuntimeTurnState) -> tuple[str, dict[str, Any]]:
    """Project committed continuity signals into bounded retrieval query terms."""
    lines: list[str] = []
    sources: set[str] = set()
    signal: dict[str, Any] = {
        "contract": _RETRIEVAL_CONTINUITY_QUERY_CONTRACT,
        "attached": False,
        "sources": [],
    }

    def add_line(label: str, source: str, *values: Any) -> None:
        tokens = _collect_retrieval_tokens(*values)
        if not tokens:
            return
        lines.append(f"{label}: {' '.join(tokens[:8])}")
        existing = signal.get(label)
        if not isinstance(existing, list):
            existing = []
        for token in tokens[:8]:
            if token not in existing:
                existing.append(token)
        signal[label] = existing
        sources.add(source)

    prior_planner = state.get("prior_planner_truth")
    if not isinstance(prior_planner, dict):
        prior_planner = {}
    prior_scene_assessment = prior_planner.get("scene_assessment_core")
    if not isinstance(prior_scene_assessment, dict):
        prior_scene_assessment = {}
    prior_social_summary = prior_planner.get("social_state_summary")
    if not isinstance(prior_social_summary, dict):
        prior_social_summary = {}

    actor_prec_tokens: list[Any] = [
        prior_planner.get("primary_responder_id"),
        prior_planner.get("responder_id"),
        prior_planner.get("secondary_responder_ids"),
        prior_planner.get("responder_scope"),
        prior_planner.get("last_actor_outcome_summary"),
        prior_planner.get("realized_secondary_responder_ids"),
        prior_planner.get("interruption_actor_id"),
    ]
    spoken_summaries = prior_planner.get("spoken_actor_summaries")
    if isinstance(spoken_summaries, list):
        for summary in spoken_summaries:
            if isinstance(summary, dict):
                actor_prec_tokens.append(f"spoke:{summary.get('actor_id')}")
    action_summaries = prior_planner.get("action_actor_summaries")
    if isinstance(action_summaries, list):
        for summary in action_summaries:
            if isinstance(summary, dict):
                actor_prec_tokens.append(f"acted:{summary.get('actor_id')}")
    add_line(
        "actor_precedents",
        "prior_planner_truth",
        *actor_prec_tokens,
    )
    add_line(
        "responder_precedents",
        "prior_planner_truth",
        prior_planner.get("responder_id"),
        prior_planner.get("responder_scope"),
    )
    add_line(
        "function_type_precedents",
        "prior_planner_truth",
        prior_planner.get("function_type"),
        prior_planner.get("selected_scene_function"),
    )
    add_line(
        "social_outcome_precedents",
        "prior_planner_truth",
        prior_planner.get("social_outcome"),
        prior_planner.get("dramatic_direction"),
        prior_planner.get("initiative_summary"),
        prior_planner.get("social_pressure_shift"),
        prior_planner.get("initiative_seizer_id"),
        prior_planner.get("initiative_loser_id"),
        prior_planner.get("initiative_pressure_label"),
    )
    add_line(
        "initiative_precedents",
        "prior_planner_truth",
        prior_planner.get("initiative_seizer_id"),
        prior_planner.get("initiative_loser_id"),
        prior_planner.get("initiative_pressure_label"),
        prior_planner.get("carry_forward_tension_notes"),
    )

    prior_dramatic = state.get("prior_dramatic_signature")
    if not isinstance(prior_dramatic, dict):
        prior_dramatic = {}
    add_line(
        "beat_precedents",
        "prior_dramatic_signature",
        prior_dramatic.get("prior_beat_id"),
        prior_dramatic.get("prior_beat_advancement_reason"),
    )
    add_line(
        "pacing_precedents",
        "prior_dramatic_signature",
        prior_dramatic.get("prior_pacing_mode"),
        prior_planner.get("pacing_mode"),
        prior_planner.get("silence_mode"),
    )

    prior_social = state.get("prior_social_state_record")
    if not isinstance(prior_social, dict):
        prior_social = {}
    add_line(
        "continuity_pressure_context",
        "committed_continuity_truth",
        prior_dramatic.get("prior_pressure_state"),
        prior_scene_assessment.get("pressure_state"),
        prior_social.get("scene_pressure_state"),
        prior_social.get("social_risk_band"),
        prior_social.get("responder_asymmetry_code"),
        prior_social.get("prior_continuity_classes"),
        prior_social_summary.get("social_risk_band"),
        prior_social_summary.get("responder_asymmetry_code"),
        prior_planner.get("continuity_impacts"),
        state.get("prior_continuity_impacts"),
        prior_planner.get("carry_forward_tension_notes"),
    )

    prior_thread = state.get("prior_narrative_thread_state")
    if not isinstance(prior_thread, dict):
        prior_thread = {}
    active_threads = prior_thread.get("active_threads")
    thread_pressure_label: str | None = None
    try:
        thread_pressure_level = int(prior_thread.get("thread_pressure_level") or 0)
        if thread_pressure_level >= 3:
            thread_pressure_label = "thread_pressure_high"
        elif thread_pressure_level > 0:
            thread_pressure_label = "thread_pressure_active"
    except Exception:
        thread_pressure_label = None
    thread_actor_values: list[Any] = []
    thread_precedent_values: list[Any] = [
        prior_thread.get("dominant_thread_kind"),
        thread_pressure_label,
    ]
    if isinstance(active_threads, list):
        for thread in active_threads:
            if not isinstance(thread, dict):
                continue
            thread_actor_values.append(thread.get("related_entities"))
            thread_precedent_values.extend(
                [
                    thread.get("thread_kind"),
                    thread.get("status"),
                    thread.get("resolution_hint"),
                ]
            )
    add_line("actor_precedents", "prior_narrative_thread_state", thread_actor_values)
    add_line("narrative_thread_precedents", "prior_narrative_thread_state", thread_precedent_values)
    add_line(
        "continuity_pressure_context",
        "prior_narrative_thread_state",
        prior_thread.get("dominant_thread_kind"),
        thread_pressure_label,
    )

    prior_callback = state.get("prior_callback_web_state")
    if not isinstance(prior_callback, dict):
        prior_callback = {}
    callback_edges = (
        prior_callback.get("edges") if isinstance(prior_callback.get("edges"), list) else []
    )
    callback_values: list[Any] = [
        prior_callback.get("selected_callback_kind"),
        prior_callback.get("selected_continuity_classes"),
        prior_callback.get("selected_thread_ids"),
    ]
    for edge in callback_edges[:4]:
        if not isinstance(edge, dict):
            continue
        callback_values.extend(
            [
                edge.get("callback_kind"),
                edge.get("continuity_classes"),
                edge.get("thread_ids"),
            ]
        )
    add_line("narrative_thread_precedents", "prior_callback_web_state", callback_values)
    add_line("continuity_pressure_context", "prior_callback_web_state", callback_values)

    prior_cascade = state.get("prior_consequence_cascade_state")
    if not isinstance(prior_cascade, dict):
        prior_cascade = {}
    cascade_items = (
        prior_cascade.get("items") if isinstance(prior_cascade.get("items"), list) else []
    )
    cascade_values: list[Any] = [
        prior_cascade.get("selected_consequence_ids"),
        prior_cascade.get("selected_continuity_classes"),
        prior_cascade.get("selected_statuses"),
    ]
    for item in cascade_items[:5]:
        if not isinstance(item, dict):
            continue
        cascade_values.extend(
            [
                item.get("consequence_id"),
                item.get("continuity_class"),
                item.get("status"),
                item.get("thread_ids"),
            ]
        )
    add_line("narrative_thread_precedents", "prior_consequence_cascade_state", cascade_values)
    add_line("continuity_pressure_context", "prior_consequence_cascade_state", cascade_values)

    memory_context = state.get("hierarchical_memory_context")
    if isinstance(memory_context, dict):
        tiers = memory_context.get("tiers") if isinstance(memory_context.get("tiers"), dict) else {}
        memory_values: list[Any] = []
        if isinstance(tiers, dict):
            for tier_id, rows in tiers.items():
                if not isinstance(rows, list):
                    continue
                for row in rows[:4]:
                    if not isinstance(row, dict):
                        continue
                    memory_values.extend(
                        [
                            tier_id,
                            row.get("summary"),
                            row.get("tags"),
                            row.get("actor_ids"),
                            row.get("location_ids"),
                            row.get("capability_ids"),
                            row.get("beat_id"),
                        ]
                    )
        add_line("hierarchical_memory_context", "hierarchical_memory", memory_values)

    if not lines:
        return "", signal
    signal["attached"] = True
    signal["sources"] = sorted(sources)
    return "continuity_retrieval_context:\n" + "\n".join(lines), signal


def _attach_retrieval_continuity_signal(
    retrieval: dict[str, Any],
    query_signal: dict[str, Any],
) -> None:
    if not query_signal.get("attached"):
        return
    retrieval["continuity_query_signal"] = query_signal
    notes = retrieval.get("ranking_notes")
    if not isinstance(notes, list):
        notes = []
        retrieval["ranking_notes"] = notes
    if "retrieval_continuity_query=attached" not in notes:
        notes.append("retrieval_continuity_query=attached")


def _invoke_runtime_adapter_with_langchain(**kwargs: Any) -> Any:
    """Load LangChain integration only when a graph node actually invokes an adapter.

    Keeping this import lazy lets ``ai_stack.langgraph_runtime`` (and test collection)
    succeed in slim images or CI slices that ship LangGraph but omit optional
    ``langchain_core`` / ``langchain`` extras.
    """
    from ai_stack.langchain_integration import invoke_runtime_adapter_with_langchain

    return invoke_runtime_adapter_with_langchain(**kwargs)


def _extract_realized_actor_order_from_output(state: dict[str, Any]) -> list[str]:
    """Extract unique actor order from realized output (spoken + action lines)."""
    spoken = [
        str(line.get("speaker_id") or "").strip()
        for line in (state.get("spoken_lines") or [])
        if isinstance(line, dict) and line.get("speaker_id")
    ]
    action = [
        str(line.get("actor_id") or "").strip()
        for line in (state.get("action_lines") or [])
        if isinstance(line, dict) and line.get("actor_id")
    ]
    return list(dict.fromkeys(filter(None, spoken + action)))


def _compute_reaction_order_divergence_for_render(state: dict[str, Any]) -> dict[str, Any]:
    """Compute canonical reaction order divergence structure from committed responders vs realized output.

    Returns dict with complete divergence metadata, structured for render_context and diagnostics.

    Returns:
        divergence: bool — True if preferred and realized orders differ
        reason: str | None — canonical reason code if divergence exists
        preferred_reaction_order_ids: list[str] — planned responder order
        realized_actor_order: list[str] — actual order in output
        not_realized_actor_ids: list[str] — nominated but not realized actors
        non_fatal: bool — divergence does not block output (always True)
        justified: bool — divergence has explicit reason (True if valid reason)
        justification: str | None — human-readable explanation
    """
    preferred = _preferred_reaction_order_ids_from_responders(
        state.get("selected_responder_set") or []
    )
    secondary = [
        r.get("actor_id")
        for r in (state.get("selected_responder_set") or [])
        if isinstance(r, dict) and r.get("actor_id") and r.get("role") in ("secondary_reactor",)
    ]
    realized = _extract_realized_actor_order_from_output(state)
    not_realized = [a for a in secondary if a not in realized]

    reason: str | None = None
    justification: str | None = None
    if not_realized and realized:
        reason = "secondary_responder_nominated_not_realized_in_output"
        justification = f"Secondary responders {not_realized} nominated but not realized in output"
    elif len(preferred) > 1 and len(realized) == 1:
        reason = "single_actor_only"
        justification = "Multiple responders nominated; only one actor realized in output"
    elif realized and realized != preferred:
        reason = "realized_order_differs"
        justification = f"Realization order {realized} differs from preferred {preferred}"

    divergence = reason is not None
    justified = bool(reason)

    return {
        "reaction_order_divergence": reason,
        "divergence": divergence,
        "preferred_reaction_order_ids": preferred,
        "realized_actor_order": realized,
        "not_realized_actor_ids": not_realized,
        "non_fatal": True,
        "justified": justified,
        "justification": justification,
    }


def _preferred_reaction_order_ids_from_responders(responders: list[Any]) -> list[str]:
    scored: list[tuple[int, str]] = []
    for row in responders:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or row.get("responder_id") or "").strip()
        if not actor_id:
            continue
        try:
            seq = int(row.get("preferred_reaction_order"))
        except (TypeError, ValueError):
            seq = 999
        scored.append((seq, actor_id))
    scored.sort(key=lambda item: item[0])
    ordered: list[str] = []
    for _, aid in scored:
        if aid not in ordered:
            ordered.append(aid)
    return ordered


def _build_npc_agency_plan_projection(
    *,
    state: RuntimeTurnState,
    responders: list[Any],
    responder_ids: list[str],
    npc_actor_ids: list[str],
    compact_minds: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    if not responder_ids and not npc_actor_ids:
        return None, None, None

    character_mind_records = (
        state.get("character_mind_records")
        if isinstance(state.get("character_mind_records"), list)
        else compact_minds
    )
    interpreted_input = (
        state.get("interpreted_input")
        if isinstance(state.get("interpreted_input"), dict)
        else {}
    )
    command_name = str(interpreted_input.get("command_name") or "").strip().lower()
    navigation_command = (
        str(interpreted_input.get("kind") or "").strip().lower() == "explicit_command"
        and command_name in {"move", "goto", "go", "scene", "travel", "look", "inspect"}
    )
    npc_response_expected = (
        False
        if interpreted_input.get("npc_response_expected") is False or navigation_command
        else None
    )
    simulation = build_npc_agency_simulation(
        selected_responder_set=responders,
        turn_number=state.get("turn_number"),
        character_mind_records=character_mind_records,
        social_state_record=state.get("social_state_record")
        if isinstance(state.get("social_state_record"), dict)
        else None,
        semantic_move_record=state.get("semantic_move_record")
        if isinstance(state.get("semantic_move_record"), dict)
        else None,
        selected_scene_function=str(state.get("selected_scene_function") or "").strip() or None,
        prior_planner_truth=state.get("prior_planner_truth")
        if isinstance(state.get("prior_planner_truth"), dict)
        else None,
        actor_lane_context=state.get("actor_lane_context")
        if isinstance(state.get("actor_lane_context"), dict)
            else None,
        preferred_reaction_order_ids=responder_ids,
        npc_actor_ids=npc_actor_ids,
        npc_response_expected=npc_response_expected,
    )
    plan = (
        simulation.get("npc_agency_plan")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_agency_plan"), dict)
        else None
    )
    if not plan and len(responder_ids) >= 2 and npc_response_expected is not False:
        plan = build_npc_agency_plan(
            selected_responder_set=responders,
            turn_number=state.get("turn_number"),
            character_mind_records=character_mind_records,
            social_state_record=state.get("social_state_record")
            if isinstance(state.get("social_state_record"), dict)
            else None,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            selected_scene_function=str(state.get("selected_scene_function") or "").strip() or None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
            actor_lane_context=state.get("actor_lane_context")
            if isinstance(state.get("actor_lane_context"), dict)
            else None,
            preferred_reaction_order_ids=responder_ids,
        )
    if not plan:
        return None, None, None
    required_actor_ids = list(plan.get("required_actor_ids") or [])
    secondary_ids = list(plan.get("secondary_responder_ids") or [])
    full_simulation = isinstance(simulation, dict)
    long_horizon_state = (
        simulation.get("npc_long_horizon_state")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_long_horizon_state"), dict)
        else {}
    )
    private_plans = (
        simulation.get("npc_private_plans")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_private_plans"), list)
        else []
    )
    conflict = (
        simulation.get("npc_plan_conflict_resolution")
        if isinstance(simulation, dict) and isinstance(simulation.get("npc_plan_conflict_resolution"), dict)
        else {}
    )
    selected_private_plan_ids = list(conflict.get("selected_private_plan_ids") or [])
    selected_plan_rows = [
        row
        for row in private_plans
        if isinstance(row, dict) and row.get("private_plan_id") in selected_private_plan_ids
    ]
    directives = {
        "contract": "npc_initiative_directives.v1",
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
        if full_simulation
        else "partial_runtime_projection",
        "not_full_multi_agent_simulation": not full_simulation,
        "independent_planning_used": full_simulation,
        "required_actor_ids": required_actor_ids,
        "minimum_secondary_initiatives_required": 1 if secondary_ids else 0,
        "long_horizon_state_present": bool(long_horizon_state),
        "private_plan_resolution_present": bool(selected_private_plan_ids),
        "selected_private_plan_ids": selected_private_plan_ids,
        "selected_private_plan_actor_ids": [
            row.get("actor_id") for row in selected_plan_rows if row.get("actor_id")
        ],
        "selected_private_plan_source_intention_thread_ids": [
            thread_id
            for row in selected_plan_rows
            for thread_id in (row.get("source_intention_thread_ids") or [])
        ],
        "withheld_private_plan_ids": list(conflict.get("withheld_private_plan_ids") or []),
        "instruction": (
            "Use npc_agency_simulation as the NPC initiative plan. "
            "Realize required_actor_ids in spoken_lines or action_lines unless validation constraints prevent it; "
            "initiative_events alone do not close required NPC initiative."
        ),
    }
    return plan, directives, simulation


def _build_dramatic_generation_packet(state: RuntimeTurnState) -> dict[str, Any]:
    """Build the authoritative dramatic packet consumed by generation."""
    responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
    responder_ids: list[str] = []
    for row in responders:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or row.get("responder_id") or "").strip()
        if actor_id and actor_id not in responder_ids:
            responder_ids.append(actor_id)
    preferred_reaction_order_ids = _preferred_reaction_order_ids_from_responders(responders)
    actor_lane_ctx = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
    forbidden_actor_ids: set[str] = set()
    for raw_actor_id in actor_lane_ctx.get("ai_forbidden_actor_ids") or []:
        forbidden_actor_ids.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
    human_actor_id = str(actor_lane_ctx.get("human_actor_id") or "").strip()
    forbidden_actor_ids.update(expand_goc_actor_id_aliases(human_actor_id))
    allowed_actor_ids = npc_actor_ids_from_context(actor_lane_ctx)
    if not allowed_actor_ids:
        allowed_actor_ids = [
            actor_id
            for actor_id in responder_ids
            if actor_id and actor_id not in forbidden_actor_ids
        ]

    minds = state.get("character_mind_records") if isinstance(state.get("character_mind_records"), list) else []
    compact_minds: list[dict[str, Any]] = []
    for row in minds[:4]:
        if not isinstance(row, dict):
            continue
        compact_minds.append(
            {
                "actor_id": row.get("runtime_actor_id") or row.get("character_key"),
                "formal_role_label": row.get("formal_role_label"),
                "tactical_posture": row.get("tactical_posture"),
                "pressure_response_bias": row.get("pressure_response_bias"),
            }
        )
    voices = state.get("character_voice_profiles") if isinstance(state.get("character_voice_profiles"), list) else []
    compact_voice_profiles: list[dict[str, Any]] = []
    for row in voices[:4]:
        if not isinstance(row, dict):
            continue
        compact_voice_profiles.append(
            {
                "actor_id": row.get("runtime_actor_id") or row.get("character_key"),
                "baseline_tone": row.get("baseline_tone"),
                "speech_patterns": row.get("speech_patterns") if isinstance(row.get("speech_patterns"), dict) else {},
                "current_phase_voice_hint": row.get("current_phase_voice_hint"),
                "pitfalls_to_avoid": row.get("pitfalls_to_avoid") if isinstance(row.get("pitfalls_to_avoid"), list) else [],
            }
        )

    npc_agency_plan, npc_initiative_directives, npc_agency_simulation = _build_npc_agency_plan_projection(
        state=state,
        responders=responders,
        responder_ids=responder_ids,
        npc_actor_ids=allowed_actor_ids,
        compact_minds=compact_minds,
    )
    dramatic_irony_context = compact_dramatic_irony_context(
        state.get("dramatic_irony_record")
        if isinstance(state.get("dramatic_irony_record"), dict)
        else None
    )
    improvisational_context = compact_improvisational_coherence_context(
        state.get("improvisational_coherence_target")
        if isinstance(state.get("improvisational_coherence_target"), dict)
        else None
    )
    prior_cascade = (
        state.get("prior_consequence_cascade_state")
        if isinstance(state.get("prior_consequence_cascade_state"), dict)
        else {}
    )
    cascade_items = prior_cascade.get("items") if isinstance(prior_cascade.get("items"), list) else []
    compact_cascade_items = [
        {
            "consequence_id": item.get("consequence_id"),
            "source_turn_number": item.get("source_turn_number"),
            "continuity_class": item.get("continuity_class"),
            "status": item.get("status"),
            "thread_ids": list(item.get("thread_ids") or [])[:4],
        }
        for item in cascade_items[:5]
        if isinstance(item, dict)
    ]

    prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else []
    continuity_constraints: list[dict[str, str]] = []
    for item in prior[:6]:
        if not isinstance(item, dict):
            continue
        continuity_constraints.append(
            {
                "class": str(item.get("class") or item.get("continuity_class") or "").strip(),
                "description": str(item.get("description") or item.get("summary") or item.get("note") or "").strip(),
            }
        )

    scene_assessment = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
    interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
    semantic = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}
    subtext = semantic.get("subtext") if isinstance(semantic.get("subtext"), dict) else {}
    ranked_semantic = semantic.get("ranked_move_candidates") if isinstance(semantic.get("ranked_move_candidates"), list) else []
    ranked_semantic_compact: list[dict[str, Any]] = []
    for row in ranked_semantic[:3]:
        if not isinstance(row, dict):
            continue
        ranked_semantic_compact.append(
            {
                "move_type": row.get("move_type"),
                "confidence": row.get("confidence"),
                "rank": row.get("rank"),
            }
        )
    preferred_instruction = None
    if len(preferred_reaction_order_ids) > 1:
        order_txt = ", ".join(preferred_reaction_order_ids)
        preferred_instruction = (
            "Deliver visible actor beats in this reaction order when multiple responders are nominated: "
            f"{order_txt}. Secondary and interruption slots should appear when nominated unless validation "
            "constraints make that impossible."
        )

    packet = {
        "contract": "dramatic_generation_packet.v1",
        "session_id": state.get("session_id"),
        "module_id": state.get("module_id"),
        "current_scene_id": state.get("current_scene_id"),
        "selected_scene_function": state.get("selected_scene_function"),
        "selected_responder_set": responders,
        "primary_responder_id": responder_ids[0] if responder_ids else None,
        "secondary_responder_ids": responder_ids[1:] if len(responder_ids) > 1 else [],
        "actor_lane_boundary": {
            "human_actor_id": human_actor_id or None,
            "ai_forbidden_actor_ids": sorted(forbidden_actor_ids),
            "ai_allowed_actor_ids": allowed_actor_ids,
            "hard_rule": (
                "Only ai_allowed_actor_ids may appear in primary_responder_id, secondary_responder_ids, "
                "responder_actor_ids, spoken_lines, action_lines, or initiative_events. The human actor may be "
                "addressed or observed only through NPC behavior; never speak, act, emote, counter, or seize initiative for them."
            ),
        }
        if forbidden_actor_ids or allowed_actor_ids
        else None,
        "preferred_reaction_order_ids": preferred_reaction_order_ids,
        "preferred_reaction_order_instruction": preferred_instruction,
        "secondary_responder_directive": (
            "When secondary responders are nominated in a high-pressure scene, at least one nominated secondary_responder_id SHOULD appear in spoken_lines or action_lines unless an interruption or validation constraint makes that impossible."
            if len(responder_ids) > 1
            else None
        ),
        "npc_agency_simulation": npc_agency_simulation,
        "npc_agency_plan": npc_agency_plan,
        "npc_initiative_directives": npc_initiative_directives,
        "dramatic_irony_context": dramatic_irony_context,
        "pacing_mode": state.get("pacing_mode"),
        "silence_brevity_decision": state.get("silence_brevity_decision")
        if isinstance(state.get("silence_brevity_decision"), dict)
        else {},
        "scene_energy": {
            "target": state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else {},
            "transition": state.get("scene_energy_transition")
            if isinstance(state.get("scene_energy_transition"), dict)
            else {},
        },
        "pacing_rhythm": {
            "state": state.get("pacing_rhythm_state")
            if isinstance(state.get("pacing_rhythm_state"), dict)
            else {},
            "target": state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else {},
            "instruction": (
                "Follow the selected rhythm target with structured spoken_lines/action_lines counts. "
                "Do not satisfy rhythm by adding unstructured prose; preserve actor-lane and silence constraints."
            ),
        },
        "social_pressure": {
            "state": state.get("social_pressure_state")
            if isinstance(state.get("social_pressure_state"), dict)
            else {},
            "target": state.get("social_pressure_target")
            if isinstance(state.get("social_pressure_target"), dict)
            else {},
            "instruction": (
                "Treat social_pressure as bounded structural pressure guidance. "
                "Use approved actors and structured visible beats; do not invent hidden facts or resolve pressure outside validation."
            ),
        },
        "information_disclosure": {
            "target": state.get("information_disclosure_target")
            if isinstance(state.get("information_disclosure_target"), dict)
            else {},
            "instruction": (
                "Emit disclosure_events only for selected_unit_ids when relevant. "
                "Do not reveal forbidden_unit_ids; withheld units may be implied only as pressure, not confirmed truth."
            ),
        },
        "improvisational_coherence": {
            "target": improvisational_context,
            "instruction": (
                "Treat the selected contribution as the playable input for this turn. "
                "When emitting structured output, add improvisational_coherence_events with contribution_id, "
                "acceptance_mode, anchor_refs, advance_class, visible_actor_ids, and boundary_reason_code when required. "
                "Do not revise, speak for, or negate the player contribution; contain off-scope input with a playable reason."
            ),
        },
        "consequence_cascade_context": {
            "feedback_contract": prior_cascade.get("feedback_contract"),
            "cascade_id": prior_cascade.get("cascade_id"),
            "atom_count": int(prior_cascade.get("atom_count") or 0),
            "edge_count": int(prior_cascade.get("edge_count") or 0),
            "selected_consequence_ids": prior_cascade.get("selected_consequence_ids") or [],
            "selected_continuity_classes": prior_cascade.get("selected_continuity_classes") or [],
            "selected_statuses": prior_cascade.get("selected_statuses") or [],
            "items": compact_cascade_items,
        },
        "semantic_interpretation": {
            "primary_move_type": semantic.get("move_type"),
            "secondary_move_type": semantic.get("secondary_move_type"),
            "secondary_dramatic_features": semantic.get("secondary_dramatic_features")
            if isinstance(semantic.get("secondary_dramatic_features"), list)
            else [],
            "ranked_move_candidates": ranked_semantic_compact,
        },
        "subtext_interpretation": {
            "surface_mode": subtext.get("surface_mode"),
            "explicit_intent": subtext.get("explicit_intent"),
            "hidden_intent_hypothesis": subtext.get("hidden_intent_hypothesis"),
            "subtext_function": subtext.get("subtext_function"),
            "sincerity_band": subtext.get("sincerity_band"),
            "evidence_codes": subtext.get("evidence_codes")
            if isinstance(subtext.get("evidence_codes"), list)
            else [],
            "policy_source": subtext.get("policy_source"),
            "policy_rule_id": subtext.get("policy_rule_id"),
        },
        "player_intent_surface": {
            "player_input_kind": interpreted_input.get("player_input_kind"),
            "player_action_committed": bool(interpreted_input.get("player_action_committed")),
            "player_speech_committed": bool(interpreted_input.get("player_speech_committed")),
            "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")),
            "npc_response_expected": bool(interpreted_input.get("npc_response_expected")),
        },
        "character_mind_records": compact_minds,
        "character_voice_profiles": compact_voice_profiles,
        "continuity_constraints": continuity_constraints,
        "escalation_pressure": {
            "pressure_state": scene_assessment.get("pressure_state"),
            "thread_pressure_state": scene_assessment.get("thread_pressure_state"),
        },
        "active_scene_packet": {
            "scene_core": scene_assessment.get("scene_core"),
            "guidance_phase_key": scene_assessment.get("guidance_phase_key"),
            "guidance_phase_title": scene_assessment.get("guidance_phase_title"),
            "canonical_setting": scene_assessment.get("canonical_setting"),
            "narrative_scope": scene_assessment.get("narrative_scope"),
        },
    }
    environment_state = state.get("environment_state") if isinstance(state.get("environment_state"), dict) else {}
    environment_model = state.get("environment_model") if isinstance(state.get("environment_model"), dict) else {}
    if environment_state or environment_model:
        packet["environment_context"] = build_environment_generation_context(
            environment_state=environment_state,
            environment_model=environment_model,
        )
    knowledge_contract = (
        state.get("goc_runtime_knowledge_contract")
        if isinstance(state.get("goc_runtime_knowledge_contract"), dict)
        else {}
    )
    if knowledge_contract:
        packet["knowledge_runtime_contract"] = {
            "contract": knowledge_contract.get("contract"),
            "opening_scene_sequence_id": knowledge_contract.get("opening_scene_sequence_id"),
            "hard_forbidden_detection_policy": knowledge_contract.get("hard_forbidden_detection_policy"),
            "hard_forbidden_rule_ids": knowledge_contract.get("hard_forbidden_rule_ids"),
        }
        packet["hard_forbidden_rules"] = {
            "negative_constraints": knowledge_contract.get("hard_forbidden_negative_constraints") or [],
            "detection_policy": knowledge_contract.get("hard_forbidden_detection_policy") or {},
        }
        if str(state.get("turn_input_class") or "").strip().lower() == "opening":
            packet["opening_scene_sequence"] = {
                "id": knowledge_contract.get("opening_scene_sequence_id"),
                "must_establish": knowledge_contract.get("opening_must_establish") or [],
                "event_tasks": knowledge_contract.get("opening_event_tasks") or [],
                "handover_to_scene_phase": knowledge_contract.get("opening_handover_to_scene_phase"),
                "role_variant": knowledge_contract.get("selected_role_variant") or {},
            }
            packet["opening_render_policy"] = knowledge_contract.get("opening_render_policy") or {}
    # Add prior_initiative_truth if any initiative fields are present
    prior_planner = state.get("prior_planner_truth") if isinstance(state.get("prior_planner_truth"), dict) else {}
    _pit = {
        "initiative_seizer_id": prior_planner.get("initiative_seizer_id"),
        "initiative_loser_id": prior_planner.get("initiative_loser_id"),
        "initiative_pressure_label": prior_planner.get("initiative_pressure_label"),
        "carry_forward_tension_notes": prior_planner.get("carry_forward_tension_notes"),
    }
    # Collapse to None when all values are empty/None (avoid prompt noise)
    if any(v for v in _pit.values() if v):
        packet["prior_initiative_truth"] = _pit
    return packet


def _drama_aware_routing_requirements(state: RuntimeTurnState) -> dict[str, Any]:
    """Derive bounded dramatic requirements used by routing policy selection."""
    scene_assessment = (
        state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
    )
    semantic = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}
    responders = (
        state.get("selected_responder_set")
        if isinstance(state.get("selected_responder_set"), list)
        else []
    )
    actor_count = len([x for x in responders if isinstance(x, dict)])
    scene_fn = str(state.get("selected_scene_function") or "").strip()
    pressure_state = str(scene_assessment.get("pressure_state") or "").strip()
    semantic_family = str(semantic.get("social_move_family") or "").strip()
    semantic_risk = str(semantic.get("scene_risk_band") or "").strip()
    move_type = str(semantic.get("move_type") or "").strip()
    escalation_density = "low"
    if scene_fn in {"escalate_conflict", "redirect_blame", "scene_pivot"}:
        escalation_density = "high"
    elif scene_fn in {"probe_motive", "withhold_or_evade"}:
        escalation_density = "moderate"
    if move_type in {"escalation_threat", "direct_accusation", "humiliating_exposure"}:
        escalation_density = "high"
    if semantic_family in {"escalate", "attack"} and escalation_density != "high":
        escalation_density = "moderate"
    if semantic_risk == "high":
        escalation_density = "high"

    dialogue_complexity = "low"
    player_text = str(state.get("player_input") or "")
    word_count = len([w for w in player_text.replace("\n", " ").split(" ") if w.strip()])
    if actor_count >= 2 or word_count >= 18 or semantic_risk == "high":
        dialogue_complexity = "high"
    elif word_count >= 8 or escalation_density == "moderate":
        dialogue_complexity = "moderate"

    return {
        "contract": "dramatic_routing_requirements.v1",
        "scene_pressure": pressure_state or "unknown",
        "actor_count": actor_count,
        "escalation_density": escalation_density,
        "dialogue_complexity": dialogue_complexity,
        "selected_scene_function": scene_fn or None,
        "semantic_move_type": move_type or None,
    }


@dataclass
class RuntimeTurnGraphExecutor:
    """``RuntimeTurnGraphExecutor`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    interpreter: Any
    routing: RoutingPolicy
    registry: ModelRegistry
    adapters: dict[str, BaseModelAdapter]
    retriever: ContextRetriever
    assembler: ContextPackAssembler
    capability_registry: CapabilityRegistry | None = None
    graph_name: str = "wos_runtime_turn_graph"
    graph_version: str = RUNTIME_TURN_GRAPH_VERSION
    max_self_correction_attempts: int = 3
    allow_degraded_commit_after_retries: bool = True
    generation_execution_mode: str | None = None
    retrieval_config: RuntimeRetrievalConfig | None = None
    action_resolution_short_path_enabled: bool = True

    def __post_init__(self) -> None:
        """``__post_init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        """
        from ai_stack.langgraph_runtime import ensure_langgraph_available

        ensure_langgraph_available()
        self._graph = self._build_graph()

    def _build_graph(self):
        """``_build_graph`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        """
        graph = StateGraph(RuntimeTurnState)
        graph.add_node("interpret_input", self._interpret_input)
        graph.add_node("meta_control_turn", self._meta_control_turn)
        graph.add_node("resolve_player_action", self._resolve_player_action)
        graph.add_node("authoritative_action_resolution", self._authoritative_action_resolution_turn)
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("goc_resolve_canonical_content", self._goc_resolve_canonical_content)
        graph.add_node("director_assess_scene", self._director_assess_scene)
        graph.add_node("director_select_dramatic_parameters", self._director_select_dramatic_parameters)
        graph.add_node("derive_scene_energy", self._derive_scene_energy)
        graph.add_node("derive_pacing_rhythm", self._derive_pacing_rhythm)
        graph.add_node("derive_social_pressure", self._derive_social_pressure)
        graph.add_node("derive_improvisational_coherence", self._derive_improvisational_coherence)
        graph.add_node("derive_information_disclosure", self._derive_information_disclosure)
        graph.add_node("derive_dramatic_irony", self._derive_dramatic_irony)
        graph.add_node("synthesize_context", self._synthesize_context)
        graph.add_node("assemble_model_context", self._assemble_model_context)
        graph.add_node("route_model", self._route_model)
        graph.add_node("invoke_model", self._invoke_model)
        graph.add_node("fallback_model", self._fallback_model)
        graph.add_node("proposal_normalize", self._proposal_normalize)
        graph.add_node("validate_seam", self._validate_seam)
        graph.add_node("commit_seam", self._commit_seam)
        graph.add_node("render_visible", self._render_visible)
        graph.add_node("package_output", self._package_output)
        graph.set_entry_point("interpret_input")
        graph.add_conditional_edges(
            "interpret_input",
            self._route_after_interpret_input,
            {
                "meta_control_turn": "meta_control_turn",
                "resolve_player_action": "resolve_player_action",
            },
        )
        graph.add_edge("meta_control_turn", "package_output")
        graph.add_conditional_edges(
            "resolve_player_action",
            self._route_after_resolve_player_action,
            {
                "full_pipeline": "retrieve_context",
                "authoritative_action_resolution": "authoritative_action_resolution",
            },
        )
        graph.add_edge("authoritative_action_resolution", "proposal_normalize")
        graph.add_edge("retrieve_context", "goc_resolve_canonical_content")
        graph.add_edge("goc_resolve_canonical_content", "director_assess_scene")
        graph.add_edge("director_assess_scene", "director_select_dramatic_parameters")
        graph.add_edge("director_select_dramatic_parameters", "derive_scene_energy")
        graph.add_edge("derive_scene_energy", "derive_pacing_rhythm")
        graph.add_edge("derive_pacing_rhythm", "derive_social_pressure")
        graph.add_edge("derive_social_pressure", "derive_improvisational_coherence")
        graph.add_edge("derive_improvisational_coherence", "derive_information_disclosure")
        graph.add_edge("derive_information_disclosure", "derive_dramatic_irony")
        graph.add_edge("derive_dramatic_irony", "synthesize_context")
        graph.add_edge("synthesize_context", "assemble_model_context")
        graph.add_edge("assemble_model_context", "route_model")
        graph.add_edge("route_model", "invoke_model")
        graph.add_conditional_edges(
            "invoke_model",
            self._next_step_after_invoke,
            {"fallback_model": "fallback_model", "proposal_normalize": "proposal_normalize"},
        )
        graph.add_edge("fallback_model", "proposal_normalize")
        graph.add_edge("proposal_normalize", "validate_seam")
        graph.add_edge("validate_seam", "commit_seam")
        graph.add_edge("commit_seam", "render_visible")
        graph.add_edge("render_visible", "package_output")
        graph.add_edge("package_output", END)
        return graph.compile()

    def _route_after_interpret_input(self, state: RuntimeTurnState) -> str:
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        if is_non_story_control_player_input_kind(interp.get("player_input_kind")):
            return "meta_control_turn"
        return "resolve_player_action"

    def run(
        self,
        *,
        session_id: str,
        module_id: str,
        current_scene_id: str,
        player_input: str,
        trace_id: str | None = None,
        host_versions: dict[str, Any] | None = None,
        active_narrative_threads: list[dict[str, Any]] | None = None,
        thread_pressure_summary: str | None = None,
        host_experience_template: dict[str, Any] | None = None,
        force_experiment_preview: bool | None = None,
        prior_continuity_impacts: list[dict[str, Any]] | None = None,
        prior_dramatic_signature: dict[str, str] | None = None,
        prior_social_state_record: dict[str, Any] | None = None,
        prior_narrative_thread_state: dict[str, Any] | None = None,
        prior_callback_web_state: dict[str, Any] | None = None,
        prior_consequence_cascade_state: dict[str, Any] | None = None,
        prior_pacing_rhythm_state: dict[str, Any] | None = None,
        prior_social_pressure_state: dict[str, Any] | None = None,
        prior_planner_truth: dict[str, Any] | None = None,
        hierarchical_memory_context: dict[str, Any] | None = None,
        turn_number: int | None = None,
        turn_id: str | None = None,
        turn_timestamp_iso: str | None = None,
        turn_initiator_type: str | None = None,
        turn_input_class: str | None = None,
        turn_execution_mode: str | None = None,
        live_player_truth_surface: bool | None = None,
        actor_lane_context: dict[str, Any] | None = None,
        session_output_language: str | None = None,
        story_runtime_experience: dict[str, Any] | None = None,
        validation_execution_mode: str | None = None,
        environment_state: dict[str, Any] | None = None,
    ) -> RuntimeTurnState:
        """Describe what ``run`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            session_id: ``session_id`` (str); meaning follows the type and call sites.
            module_id: ``module_id`` (str); meaning follows the type and call sites.
            current_scene_id: ``current_scene_id`` (str); meaning follows the type and call sites.
            player_input: ``player_input`` (str); meaning follows the type and call sites.
            trace_id: ``trace_id`` (str | None); meaning follows the type and call sites.
            host_versions: ``host_versions`` (dict[str,
                Any] | None); meaning follows the type and call sites.
            active_narrative_threads: ``active_narrative_threads`` (list[dict[str, Any]] |
                None); meaning follows the type and call sites.
            thread_pressure_summary: ``thread_pressure_summary`` (str | None); meaning follows the type and call sites.
            host_experience_template: ``host_experience_template`` (dict[str, Any] | None); meaning follows the type and call sites.
            force_experiment_preview: ``force_experiment_preview`` (bool | None); meaning follows the type and call sites.
            prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] |
                None); meaning follows the type and call sites.
            prior_dramatic_signature: ``prior_dramatic_signature`` (dict[str, str] | None); meaning follows the type and call sites.
            prior_social_state_record: previously committed social-state record
                rehydrated from planner truth.
            prior_narrative_thread_state: committed narrative-thread continuity
                snapshot rehydrated from the story session.
            prior_callback_web_state: bounded committed callback-web feedback
                snapshot rehydrated from the story session.
            prior_consequence_cascade_state: bounded committed consequence
                cascade feedback snapshot rehydrated from the story session.
            prior_pacing_rhythm_state: bounded committed rhythm feedback
                snapshot rehydrated from the story session.
            prior_social_pressure_state: bounded committed pressure metric
                snapshot rehydrated from the story session.
            prior_planner_truth: bounded committed planner-truth snapshot used
                to bias retrieval toward continuity-relevant precedents.
            hierarchical_memory_context: bounded committed memory context
                derived from canonical turn records.
            turn_number: ``turn_number`` (int | None); meaning follows the type and call sites.
            turn_id: ``turn_id`` (str | None); meaning follows the type and call sites.
            turn_timestamp_iso: ``turn_timestamp_iso`` (str | None); meaning follows the type and call sites.
            turn_initiator_type: ``turn_initiator_type`` (str | None); meaning follows the type and call sites.
            turn_input_class: ``turn_input_class`` (str |
                None); meaning follows the type and call sites.
            turn_execution_mode: ``turn_execution_mode`` (str | None); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        ts = turn_timestamp_iso
        if not ts:
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        tid = turn_id if turn_id is not None else (trace_id or "")
        effective_turn_number = int(turn_number or 0)
        effective_turn_kind = str(
            turn_input_class
            or ("opening" if effective_turn_number <= 0 else turn_initiator_type)
            or "player"
        ).strip() or "player"
        runtime_profile_id = _runtime_profile_id_from_host_template(host_experience_template)
        initial_state: RuntimeTurnState = {
            "session_id": session_id,
            "module_id": module_id,
            "current_scene_id": current_scene_id,
            "player_input": player_input,
            "trace_id": trace_id or "",
            "host_versions": host_versions or {},
            "host_experience_template": host_experience_template or {},
            "nodes_executed": [],
            "node_outcomes": {},
            "graph_errors": [],
            "failure_markers": [],
            "fallback_markers": [],
            "turn_timestamp_iso": ts,
            "turn_id": tid,
            "turn_initiator_type": turn_initiator_type or "player",
            "turn_execution_mode": turn_execution_mode or "langgraph_runtime_turn_graph",
            "turn_aspect_ledger": initialize_runtime_aspect_ledger(
                session_id=session_id,
                module_id=module_id,
                turn_number=effective_turn_number,
                turn_kind=effective_turn_kind,
                raw_player_input=player_input if effective_turn_number > 0 else None,
                input_kind=turn_input_class,
                turn_id=tid,
                trace_id=trace_id,
                runtime_profile_id=runtime_profile_id,
            ),
        }
        try:
            module_policy = load_module_runtime_policy(
                module_id=module_id,
                runtime_profile_id=runtime_profile_id,
            ).to_dict()
            initial_state["module_runtime_policy"] = module_policy
        except Exception as exc:
            module_policy = {}
            initial_state["module_runtime_policy"] = {
                "schema_version": "module_runtime_policy.v1",
                "module_id": module_id,
                "runtime_profile_id": runtime_profile_id,
                "policy_load_status": "failed",
                "failure_reason": str(exc),
            }
        env_model = build_environment_model(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        )
        initial_state["environment_model"] = env_model
        initial_state["environment_state"] = normalize_environment_state(
            environment_state,
            module_id=module_id,
            environment_model=env_model,
            runtime_projection=host_experience_template,
            actor_lane_context=actor_lane_context,
            turn_number=effective_turn_number,
        )
        if turn_number is not None:
            initial_state["turn_number"] = int(turn_number)
        if turn_input_class is not None:
            initial_state["turn_input_class"] = turn_input_class
        if force_experiment_preview is not None:
            initial_state["force_experiment_preview"] = force_experiment_preview
        lt = live_player_truth_surface
        if lt is None:
            lt = not bool(force_experiment_preview)
        initial_state["live_player_truth_surface"] = bool(lt)
        # MVP2: actor-lane enforcement context — passed through state to validate_seam.
        if actor_lane_context and isinstance(actor_lane_context, dict):
            initial_state["actor_lane_context"] = actor_lane_context
        if active_narrative_threads:
            initial_state["active_narrative_threads"] = active_narrative_threads
        if thread_pressure_summary:
            # Keep in sync with world-engine story_runtime narrative_threads.THREAD_PRESSURE_SUMMARY_MAX (128).
            initial_state["thread_pressure_summary"] = thread_pressure_summary[:128]
        if prior_continuity_impacts:
            initial_state["prior_continuity_impacts"] = list(prior_continuity_impacts)
        if prior_dramatic_signature:
            initial_state["prior_dramatic_signature"] = dict(prior_dramatic_signature)
        if prior_social_state_record:
            initial_state["prior_social_state_record"] = dict(prior_social_state_record)
        if prior_narrative_thread_state:
            initial_state["prior_narrative_thread_state"] = dict(prior_narrative_thread_state)
        if prior_callback_web_state:
            initial_state["prior_callback_web_state"] = dict(prior_callback_web_state)
        if prior_consequence_cascade_state:
            initial_state["prior_consequence_cascade_state"] = dict(
                prior_consequence_cascade_state
            )
        if prior_pacing_rhythm_state:
            initial_state["prior_pacing_rhythm_state"] = dict(prior_pacing_rhythm_state)
        if prior_social_pressure_state:
            initial_state["prior_social_pressure_state"] = dict(prior_social_pressure_state)
        if prior_planner_truth:
            initial_state["prior_planner_truth"] = dict(prior_planner_truth)
        if hierarchical_memory_context:
            initial_state["hierarchical_memory_context"] = dict(hierarchical_memory_context)
        sol = str(session_output_language or "de").strip().lower()[:2] or "de"
        initial_state["session_output_language"] = sol
        if story_runtime_experience and isinstance(story_runtime_experience, dict):
            initial_state["story_runtime_experience"] = dict(story_runtime_experience)
        if validation_execution_mode:
            initial_state["validation_execution_mode"] = str(validation_execution_mode)
        return self._graph.invoke(initial_state)

    def _interpret_input(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_interpret_input`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        interpretation = self.interpreter(state["player_input"])
        task_type = "classification" if interpretation.kind.value in {"explicit_command", "meta"} else "narrative_formulation"
        interp_dict = interpretation.model_dump(mode="json")
        alc = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
        human_actor_id = str(alc.get("human_actor_id") or "").strip()
        selected_player_role = str(alc.get("selected_player_role") or "").strip()
        actor_for_event = human_actor_id or selected_player_role or None
        raw_pi = str(state.get("player_input") or "").strip()
        kind_raw = str(interp_dict.get("kind") or "").strip().lower()
        interp_intent = str(interp_dict.get("intent") or "").strip().lower()
        interp_ambiguity = str(interp_dict.get("ambiguity") or "").strip().lower()
        pi14_no_lexical_silence = (
            not raw_pi
            or interp_ambiguity in {"empty_input", "no_lexical_tokens", "punctuation_only"}
        )
        pi14_withheld_silence = (
            "withheld_response_or_silence" in interp_intent
            or "silence" in interp_intent
            or pi14_no_lexical_silence
        )
        session_lang = str(state.get("session_output_language") or "de").strip().lower()[:2] or "de"
        module_for_rules = str(state.get("module_id") or "").strip() or GOC_MODULE_ID
        input_kind_map = {
            "speech": "speech",
            "action": "action",
            "mixed": "mixed",
            "reaction": "speech",
            "intent_only": "speech",
            "ambiguous": "action",   # ambiguous inputs route through action path, not speech
            "explicit_command": "speech",
            "meta": "meta",
            "unclear": "action",
        }
        intent_fields: dict[str, Any] = {
            "source": "player_input",
            "actor_id": actor_for_event,
            "selected_player_role": selected_player_role or human_actor_id or None,
            "original_text": raw_pi,
            "player_input_actor_id": actor_for_event,
            "player_input_visible_block_present": True,
        }
        if kind_raw in ("explicit_command", "meta"):
            pik = "meta" if kind_raw == "meta" else "unclear"
            intent_fields["player_input_kind"] = pik
            intent_fields["projection_key"] = None
            intent_fields["projection_captures"] = {}
            intent_fields["semantic_category"] = pik
            intent_fields["speech_projection_allowed"] = False
            if is_non_story_control_player_input_kind(pik):
                intent_fields.update(default_player_intent_commit_flags(pik))
                intent_fields["control_path"] = "meta"
            else:
                intent_fields["player_action_committed"] = False
                intent_fields["player_speech_committed"] = True
                intent_fields["narrator_response_expected"] = False
                intent_fields["npc_response_expected"] = True
        else:
            hit = classify_player_input_from_rules(
                raw_pi,
                module_id=module_for_rules,
                lang_hint=session_lang,
                content_modules_root=None,
            )
            rid = str(hit.get("deterministic_intent_rule") or "")
            if rid not in ("no_rules", "no_rule_match"):
                pik = str(hit.get("player_input_kind") or "unclear").strip().lower()
                intent_fields["player_input_kind"] = pik
                intent_fields["projection_key"] = hit.get("projection_key")
                intent_fields["projection_captures"] = hit.get("captures") or {}
                intent_fields["player_action_committed"] = bool(hit.get("player_action_committed"))
                intent_fields["player_speech_committed"] = bool(hit.get("player_speech_committed"))
                intent_fields["narrator_response_expected"] = bool(hit.get("narrator_response_expected"))
                intent_fields["npc_response_expected"] = bool(hit.get("npc_response_expected"))
                family = player_input_kind_family(pik)
                if is_speech_like_player_input_kind(pik):
                    json_kind = "speech"
                elif is_mixed_player_input_kind(pik):
                    json_kind = "mixed"
                elif family in {"action", "perception", "social_nonverbal_action", "wait_or_observe"}:
                    json_kind = "action"
                else:
                    json_kind = kind_raw
                # Also propagate semantic fields from rules hit
                intent_fields["semantic_category"] = hit.get("semantic_category") or pik
                intent_fields["speech_projection_allowed"] = bool(hit.get("speech_projection_allowed"))
                interp_dict["kind"] = json_kind
                kind_raw = json_kind
            else:
                if pi14_withheld_silence:
                    pik = "wait_or_observe" if pi14_no_lexical_silence else "social_nonverbal_action"
                else:
                    imap = {
                        "speech": "speech",
                        "action": "action",
                        "mixed": "mixed",
                        "reaction": "speech",
                        "intent_only": "speech",
                        # ambiguous social inputs (e.g. "I press someone") stay on full pipeline — keep as speech
                        "ambiguous": "speech",
                    }
                    pik = imap.get(kind_raw, "speech")
                intent_fields["player_input_kind"] = pik
                intent_fields["semantic_category"] = "silence_withdrawal" if pi14_withheld_silence else pik
                intent_fields["speech_projection_allowed"] = pik in SPEECH_PROJECTION_KINDS
                intent_fields["projection_key"] = None
                intent_fields["projection_captures"] = {}
                flags = default_player_intent_commit_flags(pik)
                intent_fields.update(flags)
                if pi14_withheld_silence:
                    intent_fields["pi14_silence_signal"] = True
                    intent_fields["pi14_silence_signal_source"] = (
                        "non_lexical_input" if pi14_no_lexical_silence else "withheld_response_or_silence"
                    )
        input_kind = input_kind_map.get(kind_raw, "speech")
        if is_perception_like_player_input_kind(intent_fields.get("player_input_kind")):
            input_kind = "action"
        intent_fields["input_kind"] = input_kind
        interp_dict = {**interp_dict, **intent_fields}
        update = _track(state, node_name="interpret_input")
        update["interpreted_input"] = interp_dict
        move_class = str(interp_dict.get("kind") or "unknown")
        update["interpreted_move"] = {
            "player_intent": str(interp_dict.get("intent") or "unspecified"),
            "move_class": move_class,
            "player_input_kind": str(interp_dict.get("player_input_kind") or "").strip().lower() or None,
            "narrator_response_expected": bool(interp_dict.get("narrator_response_expected")),
            "npc_response_expected": bool(interp_dict.get("npc_response_expected")),
        }
        update["task_type"] = task_type
        turn_number = int(state.get("turn_number") or 0)
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_INPUT,
            make_aspect_record(
                applicable=True,
                status="passed" if raw_pi or turn_number <= 0 else "missing",
                expected={
                    "turn_number": turn_number,
                    "turn_kind": state.get("turn_input_class") or move_class,
                    "real_player_turn_evidence_lane": turn_number > 0,
                },
                actual={
                    "raw_player_input": raw_pi,
                    "input_kind": input_kind,
                    "player_input_kind": interp_dict.get("player_input_kind"),
                    "semantic_kind": interp_dict.get("kind"),
                    "action_text": interp_dict.get("action_text"),
                    "speech_text": interp_dict.get("speech_text"),
                    "narrator_response_expected": bool(interp_dict.get("narrator_response_expected")),
                    "npc_response_expected": bool(interp_dict.get("npc_response_expected")),
                    "real_player_turn_evidence_lane": turn_number > 0,
                },
                reasons=[] if raw_pi or turn_number <= 0 else ["raw_player_input_missing"],
                source="runtime",
                failure_class=None if raw_pi or turn_number <= 0 else "observability_gap",
                failure_reason=None if raw_pi or turn_number <= 0 else "raw_player_input_missing",
                missing_field=None if raw_pi or turn_number <= 0 else "raw_player_input",
            ),
        )
        if "turn_input_class" not in state or not state.get("turn_input_class"):
            update["turn_input_class"] = move_class
        return update

    def _meta_control_turn(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Handle out-of-world meta input without story generation or commit."""
        update = _track(state, node_name="meta_control_turn")
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        rc = self.retrieval_config or RuntimeRetrievalConfig()
        retrieval = {
            "domain": RetrievalDomain.RUNTIME.value,
            "profile": rc.retrieval_profile,
            "status": "skipped",
            "retrieval_route": "meta_control_path",
            "hit_count": 0,
            "sources": [],
            "ranking_notes": ["meta_control_path_no_retrieval"],
            "index_version": "",
            "corpus_fingerprint": "",
            "storage_path": "",
            "embedding_model_id": "",
            "top_hit_score": "",
        }
        attach_retrieval_governance_summary(retrieval)
        structured_output = {
            "schema_version": "meta_control_turn_v1",
            "control_events": [
                {
                    "type": "meta_input_acknowledged",
                    "selected_handling_path": interp.get("selected_handling_path") or "meta",
                    "player_input_kind": interp.get("player_input_kind") or "meta",
                }
            ],
            "spoken_lines": [],
            "action_lines": [],
            "initiative_events": [],
            "state_effects": [],
        }
        generation = {
            "attempted": False,
            "success": True,
            "error": None,
            "content": "",
            "retrieval_context_attached": False,
            "prompt_length": 0,
            "fallback_used": False,
            "metadata": {
                "adapter": "meta_control",
                "adapter_invocation_mode": ADAPTER_INVOCATION_META_CONTROL,
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": structured_output,
                "meta_control_path": True,
            },
        }
        routing = dict(state.get("routing") or {})
        routing.update(
            {
                "selected_model": "meta_control_path",
                "selected_provider": "wos_runtime",
                "reason": "meta_control_path",
                "route_reason": "meta_control_path",
                "route_reason_code": "meta_control_path",
                "fallback_model": None,
                "fallback_chain": ["meta_control_path"],
                "route_mode": "deterministic_control_path",
                "generation_required": False,
                "meta_control_path": True,
            }
        )
        update["retrieval"] = retrieval
        update["context_text"] = ""
        update["model_prompt"] = ""
        update["generation"] = generation
        update["routing"] = routing
        update["selected_scene_function"] = "meta_control"
        update["selected_responder_set"] = []
        update["response_plan"] = {
            "meta_control_path": True,
            "generation_required": False,
            "narrator_response_expected": False,
            "npc_response_expected": False,
        }
        update["validation_outcome"] = {
            "status": "approved",
            "reason": "meta_input_isolated",
            "validator_lane": "meta_control_path_v1",
            "dramatic_quality_gate": "not_applicable_meta_control",
            "intent_surface_diagnostics": {
                "meta_control_path": True,
                "npc_narrated_player_action_violation": False,
            },
        }
        update["committed_result"] = {
            "committed_effects": [],
            "commit_applied": False,
            "commit_not_applicable": True,
            "commit_lane": "meta_control_path_v1",
        }
        update["visible_output_bundle"] = {
            "gm_narration": [],
            "spoken_lines": [],
            "action_lines": [],
            "control_events": structured_output["control_events"],
        }
        update["visibility_class_markers"] = ["meta_control_path", "non_story_control"]
        update["transition_pattern"] = "diagnostics_only"
        update["fallback_needed"] = False
        return update

    def _retrieve_context(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_retrieve_context`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        rc = self.retrieval_config or RuntimeRetrievalConfig()
        query_context, query_signal = _retrieval_continuity_query_context(state)
        query_str = f"{state['player_input']}\nscene:{state['current_scene_id']}\nmodule:{state['module_id']}"
        if query_context:
            query_str = f"{query_str}\n{query_context}"
        capability_audit: list[dict[str, Any]] = []

        if rc.retrieval_disabled:
            retrieval = {
                "domain": RetrievalDomain.RUNTIME.value,
                "profile": rc.retrieval_profile,
                "status": "skipped",
                "retrieval_route": "disabled_by_config",
                "hit_count": 0,
                "sources": [],
                "ranking_notes": ["retrieval_execution_mode=disabled"],
                "index_version": "",
                "corpus_fingerprint": "",
                "storage_path": "",
                "embedding_model_id": "",
                "top_hit_score": "",
            }
            attach_retrieval_governance_summary(retrieval)
            context_text = ""
        else:
            payload = {
                "domain": RetrievalDomain.RUNTIME.value,
                "profile": rc.retrieval_profile,
                "query": query_str,
                "module_id": state["module_id"],
                "scene_id": state["current_scene_id"],
                "max_chunks": rc.max_chunks,
                "use_sparse_only": rc.use_sparse_only,
                "retrieval_min_score": rc.retrieval_min_score,
            }
            if self.capability_registry is not None:
                result = self.capability_registry.invoke(
                    name="wos.context_pack.build",
                    mode="runtime",
                    actor="runtime_turn_graph",
                    payload=payload,
                )
                retrieval = result["retrieval"]
                if isinstance(retrieval, dict):
                    attach_retrieval_governance_summary(retrieval)
                context_text = result["context_text"]
                capability_audit = self.capability_registry.recent_audit(limit=3)
            else:
                request = RetrievalRequest(
                    domain=RetrievalDomain.RUNTIME,
                    profile=rc.retrieval_profile,
                    query=query_str,
                    module_id=state["module_id"],
                    scene_id=state["current_scene_id"],
                    max_chunks=rc.max_chunks,
                    use_sparse_only=rc.use_sparse_only,
                )
                retrieval_result = self.retriever.retrieve(request)
                retrieval_result, _removed_count = filter_retrieval_result_by_min_score(
                    retrieval_result,
                    rc.retrieval_min_score,
                )
                pack = self.assembler.assemble(retrieval_result)
                top_score = ""
                if pack.sources:
                    top_score = str(pack.sources[0].get("score", ""))
                retrieval = {
                    "domain": pack.domain,
                    "profile": pack.profile,
                    "status": pack.status,
                    "hit_count": pack.hit_count,
                    "sources": pack.sources,
                    "ranking_notes": pack.ranking_notes,
                    "index_version": pack.index_version,
                    "corpus_fingerprint": pack.corpus_fingerprint,
                    "storage_path": pack.storage_path,
                    "retrieval_route": pack.retrieval_route,
                    "embedding_model_id": pack.embedding_model_id,
                    "top_hit_score": top_score,
                }
                attach_retrieval_governance_summary(retrieval)
                context_text = pack.compact_context
        if isinstance(retrieval, dict):
            _attach_retrieval_continuity_signal(retrieval, query_signal)
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpretation_block = (
            "Runtime interpretation (structured):\n"
            f"- kind: {interp.get('kind')}\n"
            f"- confidence: {interp.get('confidence')}\n"
            f"- ambiguity: {interp.get('ambiguity')}\n"
            f"- intent: {interp.get('intent')}\n"
            f"- selected_handling_path: {interp.get('selected_handling_path')}\n"
            f"- runtime_delivery_hint: {interp.get('runtime_delivery_hint')}\n"
        )
        base = state["player_input"]
        if context_text:
            base = f"{base}\n\n{context_text}"
        prompt = f"{base}\n\n{interpretation_block}"

        additional_context_lines = []

        # Scene Assessment
        scene_assess = state.get("scene_assessment")
        if isinstance(scene_assess, dict):
            assess_summary = scene_assess.get("assessment_summary", "")
            if assess_summary:
                additional_context_lines.append("Scene Assessment:")
                additional_context_lines.append(f"{assess_summary[:256]}")

        # Social State
        social_rec = state.get("social_state_record")
        if isinstance(social_rec, dict):
            rel_states = social_rec.get("relationship_states", {})
            if rel_states:
                additional_context_lines.append("\nCurrent Relationship State:")
                for key, val in list(rel_states.items())[:4]:
                    additional_context_lines.append(f"- {key}: {val}")
            emotional = social_rec.get("emotional_state", {})
            if emotional:
                additional_context_lines.append("\nEmotional State:")
                for char, emo in list(emotional.items())[:4]:
                    additional_context_lines.append(f"- {char}: {emo}")

        # Pacing Directive
        pacing = state.get("pacing_mode")
        if isinstance(pacing, str) and pacing.strip():
            additional_context_lines.append(f"\nPacing Directive: {pacing.strip()}")

        # Responder & Function Selection
        responders = state.get("selected_responder_set")
        if isinstance(responders, list) and responders:
            additional_context_lines.append("\nEligible Responders:")
            for r in responders[:3]:
                if isinstance(r, dict):
                    rid = r.get("responder_id", "?")
                    rtype = r.get("responder_type", "?")
                    additional_context_lines.append(f"- {rid} (type: {rtype})")

        # Continuity impacts
        cont = state.get("prior_continuity_impacts")
        if isinstance(cont, dict):
            impacts = cont.get("continuity_constraints", [])
            if impacts:
                additional_context_lines.append("\nContinuity Constraints:")
                for ic in impacts[:3]:
                    if isinstance(ic, dict):
                        desc = ic.get("description", "")
                        if desc:
                            additional_context_lines.append(f"- {desc[:100]}")

        if additional_context_lines:
            prompt = f"{prompt}\n\n" + "\n".join(additional_context_lines)

        threads = state.get("active_narrative_threads")
        if isinstance(threads, list) and threads:
            lines = ["Prior narrative threads (bounded snapshot, not authoritative diagnostics):"]
            for item in threads:
                if not isinstance(item, dict):
                    continue
                rid = item.get("thread_id")
                kind = item.get("thread_kind")
                st = item.get("status")
                intens = item.get("intensity")
                ent = item.get("related_entities")
                if not isinstance(ent, list):
                    ent = []
                lines.append(
                    f"- id={rid} kind={kind} status={st} intensity={intens} related_entities={ent[:4]}"
                )
            tsum = state.get("thread_pressure_summary")
            if isinstance(tsum, str) and tsum.strip():
                lines.append(f"thread_pressure_summary: {tsum.strip()[:128]}")
            prompt = f"{prompt}\n\n" + "\n".join(lines)

        callback_state = state.get("prior_callback_web_state")
        if isinstance(callback_state, dict) and callback_state:
            edges = callback_state.get("edges") if isinstance(callback_state.get("edges"), list) else []
            lines = ["Prior callback web (bounded committed index, not authoritative diagnostics):"]
            selected_kind = callback_state.get("selected_callback_kind")
            selected_classes = callback_state.get("selected_continuity_classes")
            if selected_kind or selected_classes:
                lines.append(
                    f"selected_kind={selected_kind} selected_continuity_classes={selected_classes or []}"
                )
            for edge in edges[:4]:
                if not isinstance(edge, dict):
                    continue
                lines.append(
                    " ".join(
                        [
                            f"- id={edge.get('edge_id')}",
                            f"kind={edge.get('callback_kind')}",
                            f"source={edge.get('source_turn_number')}",
                            f"target={edge.get('target_turn_number')}",
                            f"continuity_classes={list(edge.get('continuity_classes') or [])[:4]}",
                            f"thread_ids={list(edge.get('thread_ids') or [])[:4]}",
                        ]
                    )
                )
            prompt = f"{prompt}\n\n" + "\n".join(lines)

        cascade_state = state.get("prior_consequence_cascade_state")
        if isinstance(cascade_state, dict) and cascade_state:
            items = cascade_state.get("items") if isinstance(cascade_state.get("items"), list) else []
            lines = ["Prior consequence cascade (bounded committed state):"]
            selected_classes = cascade_state.get("selected_continuity_classes")
            selected_statuses = cascade_state.get("selected_statuses")
            selected_ids = cascade_state.get("selected_consequence_ids")
            if selected_classes or selected_statuses or selected_ids:
                lines.append(
                    " ".join(
                        [
                            f"selected_consequence_ids={list(selected_ids or [])[:5]}",
                            f"selected_continuity_classes={list(selected_classes or [])[:5]}",
                            f"selected_statuses={list(selected_statuses or [])[:5]}",
                        ]
                    )
                )
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    " ".join(
                        [
                            f"- id={item.get('consequence_id')}",
                            f"source={item.get('source_turn_number')}",
                            f"class={item.get('continuity_class')}",
                            f"status={item.get('status')}",
                            f"thread_ids={list(item.get('thread_ids') or [])[:4]}",
                        ]
                    )
                )
            prompt = f"{prompt}\n\n" + "\n".join(lines)
        update = _track(state, node_name="retrieve_context")
        update["retrieval"] = retrieval
        update["context_text"] = context_text
        update["model_prompt"] = prompt
        if capability_audit:
            update["capability_audit"] = capability_audit
        return update

    def _resolve_player_action(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Build PlayerActionFrame + AffordanceResolution before validation."""
        update = _track(state, node_name="resolve_player_action")
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        runtime_projection: dict[str, Any] = {}
        actor_lane_ctx = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
        if actor_lane_ctx:
            runtime_projection = {
                "human_actor_id": actor_lane_ctx.get("human_actor_id"),
                "selected_player_role": actor_lane_ctx.get("selected_player_role"),
                "npc_actor_ids": list(actor_lane_ctx.get("npc_actor_ids") or []),
                "actor_lanes": dict(actor_lane_ctx.get("actor_lanes") or {}),
            }
        host_template = (
            state.get("host_experience_template")
            if isinstance(state.get("host_experience_template"), dict)
            else {}
        )
        if host_template and not runtime_projection:
            runtime_projection = host_template
        resolution = resolve_player_action(
            raw_text=str(state.get("player_input") or ""),
            interpreted_input=interp,
            module_id=str(state.get("module_id") or ""),
            runtime_projection=runtime_projection,
            content_modules_root=None,
            player_local_context=state.get("player_local_context") if isinstance(state.get("player_local_context"), dict) else None,
            environment_state=state.get("environment_state") if isinstance(state.get("environment_state"), dict) else None,
            environment_model=state.get("environment_model") if isinstance(state.get("environment_model"), dict) else None,
        )
        frame = resolution.get("player_action_frame") if isinstance(resolution.get("player_action_frame"), dict) else {}
        aff = resolution.get("affordance_resolution") if isinstance(resolution.get("affordance_resolution"), dict) else {}
        if frame:
            update["player_action_frame"] = frame
        if aff:
            update["affordance_resolution"] = aff
        model = (
            resolution.get("scene_affordance_model")
            if isinstance(resolution.get("scene_affordance_model"), dict)
            else {}
        )
        if model:
            update["scene_affordance_model"] = model
        if interp and frame:
            affn = frame.get("affordance_resolution") if isinstance(frame.get("affordance_resolution"), dict) else {}
            pol = str(affn.get("action_commit_policy") or "").strip().lower()
            merged_interp = {
                **interp,
                "player_input_kind": frame.get("player_input_kind") or interp.get("player_input_kind"),
                "narrator_response_expected": bool(frame.get("narrator_response_expected")),
                "npc_response_expected": bool(frame.get("npc_response_expected")),
                "player_action_committed": pol == "commit_action",
                "player_speech_committed": pol == "commit_speech" or bool(str(frame.get("speech_text") or "").strip()),
                "movement_return_intent": bool(interp.get("movement_return_intent")),
            }
            update["interpreted_input"] = merged_interp
            move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
            update["interpreted_move"] = {
                **move,
                "player_input_kind": frame.get("player_input_kind") or move.get("player_input_kind"),
                "resolved_action_verb": frame.get("verb"),
                "resolved_target_type": frame.get("resolved_target_type"),
                "resolved_target_id": frame.get("resolved_target_id"),
                "affordance_status": frame.get("affordance_status"),
                "movement_return_intent": bool(interp.get("movement_return_intent")),
            }
        final_interp = (
            update.get("interpreted_input")
            if isinstance(update.get("interpreted_input"), dict)
            else interp
        )
        turn_number = int(state.get("turn_number") or 0)
        player_input_kind = str(
            frame.get("player_input_kind")
            or final_interp.get("player_input_kind")
            or ""
        ).strip().lower()
        action_applicable = turn_number > 0 and (
            is_action_like_player_input_kind(player_input_kind)
            or is_perception_like_player_input_kind(player_input_kind)
            or is_mixed_player_input_kind(player_input_kind)
        )
        affordance_status = str(aff.get("affordance_status") or "").strip()
        action_commit_policy = str(aff.get("action_commit_policy") or "").strip()
        resolution_present = bool(frame and aff)
        if turn_number <= 0:
            aspect_record = make_aspect_record(
                applicable=False,
                status="not_applicable",
                expected={"real_player_turn_evidence_lane": False},
                actual={"raw_player_input": None},
                reasons=["opening_turn_not_player_action_evidence_lane"],
                source="runtime",
            )
        elif not action_applicable:
            aspect_record = make_aspect_record(
                applicable=False,
                status="not_applicable",
                expected={"real_player_turn_evidence_lane": True},
                actual={
                    "raw_player_input": state.get("player_input"),
                    "input_kind": final_interp.get("input_kind"),
                    "player_input_kind": player_input_kind or None,
                    "action_kind": frame.get("action_kind"),
                    "action_commit_policy": action_commit_policy or None,
                    "narrator_response_expected": bool(final_interp.get("narrator_response_expected")),
                    "npc_response_expected": bool(final_interp.get("npc_response_expected")),
                    "real_player_turn_evidence_lane": True,
                },
                reasons=["input_kind_not_action_resolution_applicable"],
                source="runtime",
            )
        else:
            missing_field = None
            if not resolution_present:
                missing_field = "player_action_frame"
            elif not affordance_status:
                missing_field = "affordance_status"
            elif not action_commit_policy:
                missing_field = "action_commit_policy"
            ok = bool(resolution_present and affordance_status and action_commit_policy)
            aspect_record = make_aspect_record(
                applicable=True,
                status="passed" if ok else "missing",
                expected={
                    "real_player_turn_evidence_lane": True,
                    "deterministic_action_resolution": True,
                },
                actual={
                    "raw_player_input": state.get("player_input"),
                    "input_kind": final_interp.get("input_kind"),
                    "player_input_kind": player_input_kind,
                    "action_kind": frame.get("action_kind"),
                    "verb": frame.get("verb"),
                    "speech_text": frame.get("speech_text"),
                    "action_text": frame.get("source_text") or state.get("player_input"),
                    "target_query": frame.get("target_query"),
                    "source_query": frame.get("source_query"),
                    "resolved_target_status": affordance_status or None,
                    "resolved_target_id": frame.get("resolved_target_id") or aff.get("resolved_target_id"),
                    "resolved_target_type": frame.get("resolved_target_type") or aff.get("resolved_target_type"),
                    "target_resolution_source": frame.get("target_resolution_source") or aff.get("target_resolution_source"),
                    "resolved_source_id": frame.get("resolved_source_id"),
                    "resolved_source_type": frame.get("resolved_source_type"),
                    "source_resolution_source": frame.get("source_resolution_source"),
                    "affordance_status": affordance_status or None,
                    "action_commit_policy": action_commit_policy or None,
                    "narrator_response_expected": bool(frame.get("narrator_response_expected")),
                    "npc_response_expected": bool(frame.get("npc_response_expected")),
                    "response_plan": {
                        "narrator_response_expected": bool(frame.get("narrator_response_expected")),
                        "npc_response_expected": bool(frame.get("npc_response_expected")),
                        "commit_policy": action_commit_policy or None,
                    },
                    "real_player_turn_evidence_lane": True,
                },
                reasons=[] if ok else ["action_resolution_evidence_missing"],
                source="runtime",
                failure_class=None if ok else "observability_gap",
                failure_reason=None if ok else "action_resolution_evidence_missing",
                missing_field=missing_field,
            )
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_ACTION_RESOLUTION,
            aspect_record,
        )
        return update

    def _route_after_resolve_player_action(self, state: RuntimeTurnState) -> str:
        """Branch: full LLM pipeline vs synthetic action-resolution surface."""
        if not self.action_resolution_short_path_enabled:
            return "full_pipeline"
        interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        if bool(interp.get("pi14_silence_signal")):
            return "full_pipeline"
        frame = state.get("player_action_frame") if isinstance(state.get("player_action_frame"), dict) else {}
        aff = state.get("affordance_resolution") if isinstance(state.get("affordance_resolution"), dict) else {}
        # Ontology fallback verb for unmatched ``action`` inputs — not a spatial
        # affordance verb; keep dramatic director + model path (see GoC breadth tests).
        verb_early = str(frame.get("verb") or "").strip().lower()
        if verb_early == "interact":
            return "full_pipeline"
        pik = str(frame.get("player_input_kind") or "").strip().lower()
        if is_speech_like_player_input_kind(pik) or pik == "meta":
            return "full_pipeline"
        if is_mixed_player_input_kind(pik):
            return "full_pipeline"
        short_path_policy = _runtime_governance_section(state, "action_resolution_short_path")
        if not bool(short_path_policy.get("enabled")):
            return "full_pipeline"
        blocked_kinds = {
            str(item).strip().lower()
            for item in (short_path_policy.get("blocked_player_input_kinds") or [])
            if str(item).strip()
        }
        if pik in blocked_kinds:
            return "full_pipeline"
        allowed_kinds = {
            str(item).strip().lower()
            for item in (short_path_policy.get("allowed_player_input_kinds") or [])
            if str(item).strip()
        }
        if allowed_kinds and pik not in allowed_kinds:
            return "full_pipeline"
        pol = str(aff.get("action_commit_policy") or "").strip().lower()
        st = str(aff.get("affordance_status") or "").strip().lower()
        verb = str(frame.get("verb") or "").strip().lower()
        if pol == "needs_clarification" or st in {"unknown_target", "ambiguous"}:
            return "authoritative_action_resolution"
        if st in {"blocked", "unsafe"}:
            return "authoritative_action_resolution"
        allowed_verbs = {
            str(item).strip().lower()
            for item in (short_path_policy.get("allowed_verbs") or [])
            if str(item).strip()
        }
        if st in {"allowed", "allowed_offscreen", "partial"} and verb in allowed_verbs:
            return "authoritative_action_resolution"
        return "full_pipeline"

    def _authoritative_action_resolution_turn(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Deterministic authoritative surface; no LLM invoke (not mock/LDSS/fallback)."""
        update = _track(state, node_name="authoritative_action_resolution")
        frame = dict(state.get("player_action_frame") or {})
        aff = dict(state.get("affordance_resolution") or {})
        frame["validation_surface"] = "authoritative_action_resolution"
        lang = str(state.get("session_output_language") or "de").strip().lower()[:2] or "de"
        gen = build_synthetic_generation_for_action_resolution(
            module_id=str(state.get("module_id") or ""),
            lang=lang,
            player_action_frame=frame,
            affordance_resolution=aff,
            content_modules_root=None,
            scene_affordance_model=state.get("scene_affordance_model") if isinstance(state.get("scene_affordance_model"), dict) else None,
            current_player_local_context=state.get("player_local_context") if isinstance(state.get("player_local_context"), dict) else None,
            environment_state=state.get("environment_state") if isinstance(state.get("environment_state"), dict) else None,
            environment_model=state.get("environment_model") if isinstance(state.get("environment_model"), dict) else None,
            actor_lane_context=state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else None,
            turn_number=int(state.get("turn_number") or 0),
        )
        routing = dict(state.get("routing") or {})
        routing["action_resolution_branch"] = "authoritative_deterministic"
        routing["action_resolution_short_path"] = True
        routing["action_resolution_short_path_reason"] = "authoritative_action_resolution"
        routing["generation_required"] = False
        routing.setdefault("selected_model", "authoritative_action_resolution")
        routing.setdefault("selected_provider", "wos_runtime")
        routing.setdefault("route_reason", "authoritative_action_resolution")
        player_input_kind = str(frame.get("player_input_kind") or "").strip().lower()
        action_kind = str(frame.get("action_kind") or "").strip().lower()
        verb = str(frame.get("verb") or "").strip().lower()
        affordance_status = str(aff.get("affordance_status") or frame.get("affordance_status") or "").strip().lower()
        scene_id = str(state.get("current_scene_id") or "unknown_scene").strip() or "unknown_scene"
        response_plan = {
            "deterministic_action_resolution": True,
            "generation_required": False,
            "player_action_frame_present": bool(frame),
            "affordance_resolution_present": bool(aff),
            "narrator_response_expected": bool(frame.get("narrator_response_expected")),
            "npc_response_expected": bool(frame.get("npc_response_expected")),
            "affordance_status": affordance_status or None,
            "action_commit_policy": aff.get("action_commit_policy") or frame.get("action_commit_policy"),
        }
        expected_realization: list[str] = []
        if response_plan["narrator_response_expected"]:
            expected_realization.append(
                NARRATOR_PERCEPTION_RESULT_DESCRIBE
                if is_perception_like_player_input_kind(player_input_kind) or verb in {"look_at", "listen_to"}
                else NARRATOR_LOCATION_TRANSITION_DESCRIBE
                if action_kind == "movement" or verb == "move_to"
                else NARRATOR_OBJECT_STATE_DESCRIBE
                if action_kind == "object_interaction"
                else NARRATOR_ACTION_CONSEQUENCE_DESCRIBE
            )
        if response_plan["npc_response_expected"]:
            expected_realization.append(NPC_SOCIAL_REACTION_OPTIONAL)
        deterministic_beat_id = f"{scene_id}:deterministic_action_resolution:{action_kind or player_input_kind or 'input'}"
        beat_candidates = phase_beat_candidates(
            module_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
            phase_id=scene_id,
            fallback_candidate_ids=[deterministic_beat_id],
            expected_visible_functions=expected_realization,
        )
        beat_selection = select_beat_candidate(
            beat_candidates,
            deterministic_fallback_id=deterministic_beat_id,
            selection_source="module_policy",
            selection_reason="authoritative_action_resolution_short_path",
        )
        selected_beat_id = beat_selection.selected_beat_id or deterministic_beat_id
        rc = self.retrieval_config or RuntimeRetrievalConfig()
        skip_retrieval: dict[str, Any] = {
            "domain": RetrievalDomain.RUNTIME.value,
            "profile": rc.retrieval_profile,
            "status": "skipped",
            "retrieval_route": "authoritative_action_resolution_short_path",
            "hit_count": 0,
            "sources": [],
            "ranking_notes": ["authoritative_action_resolution_short_path_no_retrieval"],
            "index_version": "",
            "corpus_fingerprint": "",
            "storage_path": "",
            "embedding_model_id": "",
            "top_hit_score": "",
        }
        attach_retrieval_governance_summary(skip_retrieval)
        update["retrieval"] = skip_retrieval
        update["context_text"] = str(state.get("context_text") or "")
        update["player_action_frame"] = frame
        update["generation"] = gen
        update["routing"] = routing
        update["response_plan"] = response_plan
        _gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        _lct = _gen_meta.get("local_context_transition")
        _ncp = _gen_meta.get("narrator_consequence_plan")
        _uplc = _gen_meta.get("updated_player_local_context")
        _env_candidate = _gen_meta.get("candidate_environment_state")
        if _lct:
            update["local_context_transition"] = _lct
        if _ncp:
            update["narrator_consequence_plan"] = _ncp
        if _uplc:
            update["player_local_context"] = _uplc
        if isinstance(_env_candidate, dict) and _env_candidate:
            update["environment_transition"] = {
                "contract": "environment_transition.v1",
                "candidate_state_available": True,
                "source": "authoritative_action_resolution",
            }
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_BEAT,
            make_aspect_record(
                applicable=True,
                status="partial",
                expected={
                    "prior_beat_id": (
                        (state.get("prior_dramatic_signature") or {}).get("prior_beat_id")
                        if isinstance(state.get("prior_dramatic_signature"), dict)
                        else None
                    ),
                    "candidate_beats": [candidate.id for candidate in beat_candidates] or [selected_beat_id],
                    "expected_realization": expected_realization,
                    "expected_visible_functions": expected_realization,
                    "deterministic_action_resolution_marker": True,
                },
                selected={
                    "selected_beat_id": selected_beat_id,
                    "selected_scene_function": "deterministic_action_resolution",
                    "selection_reason": beat_selection.selection_reason,
                    "selection_source": beat_selection.selection_source,
                    "transition_allowed": affordance_status not in {"unsafe"},
                },
                actual={
                    "realized": None,
                    "committed": None,
                    "lost_at_stage": None,
                    "failure_classification": "observability_gap",
                    "deterministic_action_resolution": True,
                    "response_plan": response_plan,
                },
                reasons=["deterministic_action_resolution_beat_selected_not_yet_realized"],
                source="runtime",
                selected_beat=selected_beat_id,
            ),
        )
        update["transition_pattern"] = "hard"
        update["fallback_needed"] = False
        return update

    def _goc_resolve_canonical_content(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Describe what ``_goc_resolve_canonical_content`` does in one
        line (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="goc_resolve_canonical_content")
        failure_markers = list(state.get("failure_markers") or [])
        module_id = state.get("module_id") or ""
        if module_id == GOC_MODULE_ID:
            try:
                yaml_mod = load_goc_canonical_module_yaml()
                yaml_slice = load_goc_yaml_slice_bundle()
                opening_scene_sequence = (
                    yaml_slice.get("opening_scene_sequence")
                    if isinstance(yaml_slice.get("opening_scene_sequence"), dict)
                    else {}
                )
                hard_forbidden_rules = (
                    yaml_slice.get("hard_forbidden_rules")
                    if isinstance(yaml_slice.get("hard_forbidden_rules"), dict)
                    else {}
                )
                update["goc_canonical_yaml"] = yaml_mod
                update["goc_yaml_slice"] = yaml_slice
                if not isinstance(state.get("module_runtime_policy"), dict) or not state.get("module_runtime_policy"):
                    update["module_runtime_policy"] = load_module_runtime_policy(
                        module_id=str(module_id),
                        runtime_profile_id=_runtime_profile_id_from_host_template(
                            state.get("host_experience_template")
                            if isinstance(state.get("host_experience_template"), dict)
                            else None
                        ),
                    ).to_dict()
                update["opening_scene_sequence"] = opening_scene_sequence
                update["hard_forbidden_rules"] = hard_forbidden_rules
                _structured_knowledge_keys = (
                    "apartment_layout",
                    "apartment_objects",
                    "premise_and_backstory",
                    "actor_pressure_profiles",
                    "phase_beat_policy",
                    "narrator_sensory_palette",
                    "scene_affordances",
                )
                for _knowledge_key in _structured_knowledge_keys:
                    _value = yaml_slice.get(_knowledge_key)
                    if isinstance(_value, dict):
                        update[_knowledge_key] = _value
                env_model = (
                    state.get("environment_model")
                    if isinstance(state.get("environment_model"), dict)
                    else build_environment_model(module_id=str(module_id))
                )
                update["environment_model"] = env_model
                update["environment_state"] = normalize_environment_state(
                    state.get("environment_state")
                    if isinstance(state.get("environment_state"), dict)
                    else None,
                    module_id=str(module_id),
                    environment_model=env_model,
                    actor_lane_context=state.get("actor_lane_context")
                    if isinstance(state.get("actor_lane_context"), dict)
                    else None,
                    turn_number=int(state.get("turn_number") or 0),
                )
                update["knowledge_runtime_loaded"] = {
                    "opening_scene_sequence_loaded": bool(opening_scene_sequence),
                    "hard_forbidden_rules_loaded": bool(hard_forbidden_rules),
                    "apartment_layout_loaded": bool(isinstance(yaml_slice.get("apartment_layout"), dict) and yaml_slice.get("apartment_layout")),
                    "apartment_objects_loaded": bool(isinstance(yaml_slice.get("apartment_objects"), dict) and yaml_slice.get("apartment_objects")),
                    "premise_and_backstory_loaded": bool(isinstance(yaml_slice.get("premise_and_backstory"), dict) and yaml_slice.get("premise_and_backstory")),
                    "actor_pressure_profiles_loaded": bool(isinstance(yaml_slice.get("actor_pressure_profiles"), dict) and yaml_slice.get("actor_pressure_profiles")),
                    "phase_beat_policy_loaded": bool(isinstance(yaml_slice.get("phase_beat_policy"), dict) and yaml_slice.get("phase_beat_policy")),
                    "narrator_sensory_palette_loaded": bool(isinstance(yaml_slice.get("narrator_sensory_palette"), dict) and yaml_slice.get("narrator_sensory_palette")),
                    "scene_affordances_loaded": bool(isinstance(yaml_slice.get("scene_affordances"), dict) and yaml_slice.get("scene_affordances")),
                }
                update["goc_runtime_knowledge_contract"] = build_runtime_knowledge_contract(
                    opening_scene_sequence=opening_scene_sequence,
                    hard_forbidden_rules=hard_forbidden_rules,
                    actor_lane_context=state.get("actor_lane_context")
                    if isinstance(state.get("actor_lane_context"), dict)
                    else None,
                    session_output_language=state.get("session_output_language")
                    if isinstance(state.get("session_output_language"), str)
                    else None,
                    story_runtime_experience=state.get("story_runtime_experience")
                    if isinstance(state.get("story_runtime_experience"), dict)
                    else None,
                )
                update["goc_slice_active"] = True
                host = state.get("host_experience_template")
                if isinstance(host, dict):
                    conflict = detect_builtin_yaml_title_conflict(
                        host_template_id=host.get("template_id") if isinstance(host.get("template_id"), str) else None,
                        host_template_title=host.get("title") if isinstance(host.get("title"), str) else None,
                    )
                    if conflict:
                        failure_markers.append(conflict)
            except Exception as exc:  # pragma: no cover - exercised when yaml missing in broken checkout
                failure_markers.append({"failure_class": "graph_error", "note": f"goc_yaml_load_failed:{exc}"})
                update["goc_slice_active"] = True
        else:
            update["goc_slice_active"] = False
        update["failure_markers"] = failure_markers
        return update

    def _director_assess_scene(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Describe what ``_director_assess_scene`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="director_assess_scene")
        module_id = state.get("module_id") or ""
        yaml_blob = state.get("goc_canonical_yaml") if isinstance(state.get("goc_canonical_yaml"), dict) else None
        interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        prior_early = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        pc_early = prior_continuity_classes(prior_early)
        if module_id != GOC_MODULE_ID:
            placeholder = {
                "scene_core": "non_goc_placeholder",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            update["scene_assessment"] = placeholder
            sem_e = interpret_goc_semantic_move(
                module_id=module_id,
                player_input=state.get("player_input") or "",
                interpreted_input=interpreted_input,
                interpreted_move=interpreted_move,
                prior_continuity_classes=pc_early,
            )
            soc_e = build_social_state_record(
                prior_continuity_impacts=prior_early,
                active_narrative_threads=state.get("active_narrative_threads")
                if isinstance(state.get("active_narrative_threads"), list)
                else None,
                thread_pressure_summary=state.get("thread_pressure_summary")
                if isinstance(state.get("thread_pressure_summary"), str)
                else None,
                scene_assessment=placeholder,
                prior_social_state_record=state.get("prior_social_state_record")
                if isinstance(state.get("prior_social_state_record"), dict)
                else None,
            )
            update["semantic_move_record"] = sem_e.to_runtime_dict()
            update["social_state_record"] = soc_e.to_runtime_dict()
            return update
        if not yaml_blob:
            markers = list(state.get("failure_markers") or [])
            markers.append({"failure_class": "missing_scene_director", "note": "goc_canonical_yaml_missing"})
            update["failure_markers"] = markers
            unresolved = {
                "scene_core": "goc_unresolved",
                "pressure_state": "unknown",
                "module_slice": module_id,
            }
            update["scene_assessment"] = unresolved
            sem_u = interpret_goc_semantic_move(
                module_id=module_id,
                player_input=state.get("player_input") or "",
                interpreted_input=interpreted_input,
                interpreted_move=interpreted_move,
                prior_continuity_classes=pc_early,
            )
            soc_u = build_social_state_record(
                prior_continuity_impacts=prior_early,
                active_narrative_threads=state.get("active_narrative_threads")
                if isinstance(state.get("active_narrative_threads"), list)
                else None,
                thread_pressure_summary=state.get("thread_pressure_summary")
                if isinstance(state.get("thread_pressure_summary"), str)
                else None,
                scene_assessment=unresolved,
                prior_social_state_record=state.get("prior_social_state_record")
                if isinstance(state.get("prior_social_state_record"), dict)
                else None,
            )
            update["semantic_move_record"] = sem_u.to_runtime_dict()
            update["social_state_record"] = soc_u.to_runtime_dict()
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        interpreted_input = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        base_sa = build_scene_assessment(
            module_id=module_id,
            current_scene_id=state.get("current_scene_id") or "",
            canonical_yaml=yaml_blob,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
            prior_narrative_thread_state=state.get("prior_narrative_thread_state")
            if isinstance(state.get("prior_narrative_thread_state"), dict)
            else None,
        )
        callback_state = (
            state.get("prior_callback_web_state")
            if isinstance(state.get("prior_callback_web_state"), dict)
            else {}
        )
        if callback_state:
            base_sa["callback_web_feedback"] = {
                "feedback_contract": callback_state.get("feedback_contract"),
                "edge_count": int(callback_state.get("edge_count") or 0),
                "observation_count": int(callback_state.get("observation_count") or 0),
                "selected_callback_edge_id": callback_state.get("selected_callback_edge_id"),
                "selected_callback_kind": callback_state.get("selected_callback_kind"),
                "selected_continuity_classes": callback_state.get("selected_continuity_classes")
                or [],
                "selected_thread_ids": callback_state.get("selected_thread_ids") or [],
            }
        cascade_state = (
            state.get("prior_consequence_cascade_state")
            if isinstance(state.get("prior_consequence_cascade_state"), dict)
            else {}
        )
        if cascade_state:
            base_sa["consequence_cascade_feedback"] = {
                "feedback_contract": cascade_state.get("feedback_contract"),
                "atom_count": int(cascade_state.get("atom_count") or 0),
                "edge_count": int(cascade_state.get("edge_count") or 0),
                "selected_consequence_ids": cascade_state.get("selected_consequence_ids") or [],
                "selected_continuity_classes": cascade_state.get("selected_continuity_classes")
                or [],
                "selected_statuses": cascade_state.get("selected_statuses") or [],
            }
        pc = prior_continuity_classes(prior)
        sem_model = interpret_goc_semantic_move(
            module_id=module_id,
            player_input=state.get("player_input") or "",
            interpreted_input=interpreted_input,
            interpreted_move=interpreted_move,
            prior_continuity_classes=pc,
        )
        sem_dict = sem_model.to_runtime_dict()
        soc_model = build_social_state_record(
            prior_continuity_impacts=prior,
            active_narrative_threads=state.get("active_narrative_threads")
            if isinstance(state.get("active_narrative_threads"), list)
            else None,
            thread_pressure_summary=state.get("thread_pressure_summary")
            if isinstance(state.get("thread_pressure_summary"), str)
            else None,
            scene_assessment=base_sa,
            prior_social_state_record=state.get("prior_social_state_record")
            if isinstance(state.get("prior_social_state_record"), dict)
            else None,
        )
        soc_dict = soc_model.to_runtime_dict()
        base_sa["semantic_move_fingerprint"] = semantic_move_fingerprint(sem_model)
        base_sa["social_state_fingerprint"] = social_state_fingerprint(soc_model)
        update["scene_assessment"] = base_sa
        update["semantic_move_record"] = sem_dict
        update["social_state_record"] = soc_dict
        return update

    def _director_select_dramatic_parameters(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Describe what ``_director_select_dramatic_parameters`` does in
        one line (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="director_select_dramatic_parameters")
        module_id = state.get("module_id") or ""
        interpreted_move = state.get("interpreted_move") if isinstance(state.get("interpreted_move"), dict) else {}
        player_input = state.get("player_input") or ""
        pacing, silence = build_pacing_and_silence(
            player_input=player_input,
            interpreted_move=interpreted_move,
            module_id=module_id,
            prior_narrative_thread_state=state.get("prior_narrative_thread_state")
            if isinstance(state.get("prior_narrative_thread_state"), dict)
            else None,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
        )
        if module_id != GOC_MODULE_ID:
            update["selected_responder_set"] = []
            update["selected_scene_function"] = "establish_pressure"
            update["pacing_mode"] = pacing
            update["silence_brevity_decision"] = silence
            update["character_mind_records"] = []
            update["character_voice_profiles"] = []
            update["scene_plan_record"] = ScenePlanRecord(
                selected_scene_function="establish_pressure",
                selected_responder_set=[],
                pacing_mode=pacing,
                silence_brevity_decision=dict(silence),
                planner_rationale_codes=["non_goc_slice"],
                selection_source="non_goc_slice",
            ).to_runtime_dict()
            return update
        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else None
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else None
        base_sa = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
        sem_rec = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else None
        soc_rec = state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else None
        responders, scene_fn, _implied, resolution = build_responder_and_function(
            player_input=player_input,
            interpreted_move=interpreted_move,
            interpreted_input=state.get("interpreted_input")
            if isinstance(state.get("interpreted_input"), dict)
            else None,
            pacing_mode=pacing,
            prior_continuity_impacts=prior,
            yaml_slice=yslice,
            current_scene_id=state.get("current_scene_id") or "",
            semantic_move_record=sem_rec,
            social_state_record=soc_rec,
            prior_narrative_thread_state=state.get("prior_narrative_thread_state")
            if isinstance(state.get("prior_narrative_thread_state"), dict)
            else None,
        )
        merged_sa = {**base_sa, "multi_pressure_resolution": resolution}
        update["scene_assessment"] = merged_sa
        update["selected_responder_set"] = responders
        update["selected_scene_function"] = scene_fn
        update["pacing_mode"] = pacing
        update["silence_brevity_decision"] = silence
        primary = responders[0] if responders and isinstance(responders[0], dict) else {}
        # Derive the active cast from the module's YAML characters block and
        # order it so the primary responder's key comes first. The
        # God of Carnage fallback kicks in only when no YAML cast is
        # published, so any module shipping an authored characters block
        # works without further code changes here.
        active_keys = _derive_active_character_keys(
            yaml_slice=yslice,
            primary_responder=primary,
            module_id=str(state.get("module_id") or ""),
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        mind_models = build_character_mind_records_for_goc(
            yaml_slice=yslice,
            active_character_keys=active_keys,
            current_scene_id=state.get("current_scene_id") or "",
            module_id=str(state.get("module_id") or ""),
        )
        mind_dicts = [m.to_runtime_dict() for m in mind_models]
        voice_models = build_character_voice_profiles_for_goc(
            yaml_slice=yslice,
            active_character_keys=active_keys,
            current_scene_id=state.get("current_scene_id") or "",
            module_id=str(state.get("module_id") or ""),
        )
        voice_dicts = [v.to_runtime_dict() for v in voice_models]
        actor_lane_ctx = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
        forbidden_actor_ids: set[str] = set()
        for raw_actor_id in actor_lane_ctx.get("ai_forbidden_actor_ids") or []:
            forbidden_actor_ids.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
        forbidden_actor_ids.update(expand_goc_actor_id_aliases(str(actor_lane_ctx.get("human_actor_id") or "")))
        if forbidden_actor_ids:
            filtered_responders: list[dict[str, Any]] = []
            for responder in responders:
                if not isinstance(responder, dict):
                    continue
                actor_id = str(responder.get("actor_id") or responder.get("responder_id") or "").strip()
                if actor_id and actor_id not in forbidden_actor_ids:
                    filtered_responders.append(responder)
            if len(filtered_responders) != len(responders):
                if not filtered_responders:
                    for mind in mind_dicts:
                        if not isinstance(mind, dict):
                            continue
                        actor_id = str(mind.get("runtime_actor_id") or mind.get("character_key") or "").strip()
                        if actor_id and actor_id not in forbidden_actor_ids:
                            filtered_responders.append(
                                {
                                    "actor_id": actor_id,
                                    "role": "primary_responder",
                                    "reason": "actor_lane_human_responder_pruned",
                                }
                            )
                            break
                responders = filtered_responders
                resolution = dict(resolution) if isinstance(resolution, dict) else {}
                resolution["human_actor_responder_pruned"] = True
                update["scene_assessment"] = {**base_sa, "multi_pressure_resolution": resolution}
                update["selected_responder_set"] = responders
        update["character_mind_records"] = mind_dicts
        update["character_voice_profiles"] = voice_dicts
        sem_fp = ""
        soc_fp = ""
        if sem_rec:
            try:
                sem_fp = semantic_move_fingerprint(SemanticMoveRecord.model_validate(sem_rec))
            except Exception:
                sem_fp = str(sem_rec.get("move_type", ""))[:32]
        if soc_rec:
            try:
                soc_fp = social_state_fingerprint(SocialStateRecord.model_validate(soc_rec))
            except Exception:
                soc_fp = ""
        rationale_codes: list[str] = [
            str(resolution.get("selection_source") or "unknown"),
            f"scene_fn:{scene_fn}",
        ]
        if bool(resolution.get("legacy_keyword_scene_candidates_used")):
            rationale_codes.append("legacy_keyword_scene_candidates_used")
        if isinstance(sem_rec, dict) and isinstance(sem_rec.get("subtext"), dict):
            subtext = sem_rec["subtext"]
            subtext_function = str(subtext.get("subtext_function") or "").strip()
            if subtext_function:
                rationale_codes.append(f"subtext_function:{subtext_function}")
            policy_rule_id = str(subtext.get("policy_rule_id") or "").strip()
            if policy_rule_id:
                rationale_codes.append(f"subtext_policy_rule:{policy_rule_id}")
        pik = str(
            (
                state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
            ).get("player_input_kind")
            or ""
        ).strip()
        if pik:
            rationale_codes.append(f"player_input_kind:{pik}")
        scene_plan = ScenePlanRecord(
            selected_scene_function=scene_fn,
            selected_responder_set=list(responders),
            pacing_mode=pacing,
            silence_brevity_decision=dict(silence),
            planner_rationale_codes=rationale_codes,
            semantic_move_fingerprint=sem_fp,
            social_state_fingerprint=soc_fp,
            selection_source=str(resolution.get("selection_source") or "semantic_pipeline_v1"),
        )
        scene_plan_dict = scene_plan.to_runtime_dict()
        # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.1: record which structured knowledge surfaces the
        # planner had available so dashboards/diagnostics can answer "did the director see X?".
        knowledge_loaded = state.get("knowledge_runtime_loaded") if isinstance(state.get("knowledge_runtime_loaded"), dict) else {}
        _content_sources: list[str] = []
        for _src_key, _src_flag in (
            ("actor_pressure_profiles", "actor_pressure_profiles_loaded"),
            ("phase_beat_policy", "phase_beat_policy_loaded"),
            ("hard_forbidden_rules", "hard_forbidden_rules_loaded"),
            ("opening_scene_sequence", "opening_scene_sequence_loaded"),
            ("apartment_layout", "apartment_layout_loaded"),
            ("apartment_objects", "apartment_objects_loaded"),
            ("scene_affordances", "scene_affordances_loaded"),
            ("narrator_sensory_palette", "narrator_sensory_palette_loaded"),
            ("premise_and_backstory", "premise_and_backstory_loaded"),
        ):
            if knowledge_loaded.get(_src_flag):
                _content_sources.append(_src_key)
        scene_plan_dict["scene_director_content_sources"] = _content_sources
        _pbp = state.get("phase_beat_policy") if isinstance(state.get("phase_beat_policy"), dict) else {}
        _phase_id_for_policy = str(state.get("current_scene_id") or "").strip().lower()
        _phase_block = _pbp.get("phases", {}).get(_phase_id_for_policy) if isinstance(_pbp.get("phases"), dict) else None
        if isinstance(_phase_block, dict):
            scene_plan_dict["phase_policy_applied"] = {
                "phase_id": _phase_id_for_policy,
                "allowed_beats": list(_phase_block.get("allowed_beats") or _phase_block.get("allowed_narrator_beats") or [])
                if isinstance(_phase_block.get("allowed_beats") or _phase_block.get("allowed_narrator_beats"), list)
                else [],
                "forbidden_beats": list(_phase_block.get("forbidden_beats") or _phase_block.get("forbidden_early_escalations") or [])
                if isinstance(_phase_block.get("forbidden_beats") or _phase_block.get("forbidden_early_escalations"), list)
                else [],
            }
        _actor_profiles_block = state.get("actor_pressure_profiles") if isinstance(state.get("actor_pressure_profiles"), dict) else {}
        _responder_actor_id = str(scene_plan_dict.get("responder_actor_id") or "").strip()
        if _responder_actor_id and isinstance(_actor_profiles_block.get(_responder_actor_id), dict):
            scene_plan_dict["actor_pressure_profile_used"] = {
                "actor_id": _responder_actor_id,
                "profile_keys": sorted(list(_actor_profiles_block[_responder_actor_id].keys())),
            }
        # NPC participation policy: respect actor_lane forbidden ids; record human exclusion.
        _alc = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
        scene_plan_dict["npc_participation_policy"] = {
            "human_actor_id": _alc.get("human_actor_id"),
            "ai_forbidden_actor_ids": list(_alc.get("ai_forbidden_actor_ids") or []) if isinstance(_alc.get("ai_forbidden_actor_ids"), list) else [],
            "selected_responder_set": [
                str(_row.get("actor_id") or "").strip()
                for _row in (state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else [])
                if isinstance(_row, dict) and str(_row.get("actor_id") or "").strip()
            ],
        }
        if str(state.get("turn_input_class") or "").strip().lower() == "opening":
            opening_meta = build_opening_scene_plan_metadata(
                opening_scene_sequence=state.get("opening_scene_sequence")
                if isinstance(state.get("opening_scene_sequence"), dict)
                else (yslice.get("opening_scene_sequence") if isinstance(yslice, dict) else {}),
                hard_forbidden_rules=state.get("hard_forbidden_rules")
                if isinstance(state.get("hard_forbidden_rules"), dict)
                else (yslice.get("hard_forbidden_rules") if isinstance(yslice, dict) else {}),
                actor_lane_context=state.get("actor_lane_context")
                if isinstance(state.get("actor_lane_context"), dict)
                else None,
            )
            scene_plan_dict.update(opening_meta)
            rationale_codes.append("opening_scene_sequence_runtime_contract")
            if opening_meta.get("opening_scene_sequence_id"):
                rationale_codes.append(f"opening_scene_sequence:{opening_meta['opening_scene_sequence_id']}")
            scene_plan_dict["planner_rationale_codes"] = rationale_codes
            update["scene_assessment"] = {
                **(update.get("scene_assessment") if isinstance(update.get("scene_assessment"), dict) else merged_sa),
                "opening_scene_sequence_id": opening_meta.get("opening_scene_sequence_id"),
                "opening_handover_to_scene_phase": opening_meta.get("opening_handover_to_scene_phase"),
                "hard_forbidden_constraints_active": bool(opening_meta.get("hard_forbidden_rule_ids")),
            }
        update["scene_plan_record"] = scene_plan_dict
        prior_sig = state.get("prior_dramatic_signature") if isinstance(state.get("prior_dramatic_signature"), dict) else {}
        prior_beat_id = str(prior_sig.get("prior_beat_id") or "").strip() or None
        scene_id = str(state.get("current_scene_id") or "").strip() or "unknown_scene"
        candidate_functions = [
            str(item).strip()
            for item in (resolution.get("candidates") or [])
            if str(item).strip()
        ]
        if scene_fn not in candidate_functions:
            candidate_functions.append(scene_fn)
        deterministic_beat_id = f"{scene_id}:{scene_fn}"
        expected_realization: list[str] = []
        interp_for_beat = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
        if bool(interp_for_beat.get("narrator_response_expected")):
            expected_realization.append(NARRATOR_ACTION_CONSEQUENCE_DESCRIBE)
        if bool(interp_for_beat.get("npc_response_expected")) or responders:
            expected_realization.append(NPC_SOCIAL_REACTION_OPTIONAL)
        beat_candidates = phase_beat_candidates(
            module_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
            phase_id=scene_id,
            fallback_candidate_ids=[f"{scene_id}:{fn}" for fn in candidate_functions] or [deterministic_beat_id],
            expected_visible_functions=expected_realization,
        )
        beat_selection = select_beat_candidate(
            beat_candidates,
            deterministic_fallback_id=deterministic_beat_id,
            selection_source=str(resolution.get("selection_source") or "scene_director"),
            selection_reason=str(resolution.get("selection_source") or "semantic_pipeline_v1"),
        )
        selected_beat_id = beat_selection.selected_beat_id or deterministic_beat_id
        scene_plan_dict.setdefault(
            "selection_source",
            str(resolution.get("selection_source") or "scene_director"),
        )
        scene_plan_dict["beat_selection_source"] = beat_selection.selection_source
        scene_plan_dict["selected_beat"] = {
            "id": selected_beat_id,
            "candidate_count": beat_selection.candidate_count,
        }
        scene_plan_dict["selected_capabilities"] = list(expected_realization)
        scene_plan_dict["authority_expectations"] = {
            "narrator_required": bool(interp_for_beat.get("narrator_response_expected")),
            "npc_policy": "optional_social_reaction" if responders or bool(interp_for_beat.get("npc_response_expected")) else "none",
        }
        update["scene_plan_record"] = scene_plan_dict
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_BEAT,
            make_aspect_record(
                applicable=True,
                status="partial",
                expected={
                    "prior_beat_id": prior_beat_id,
                    "candidate_beats": [candidate.id for candidate in beat_candidates],
                    "expected_realization": expected_realization,
                    "expected_visible_functions": expected_realization,
                },
                selected={
                    "selected_beat_id": selected_beat_id,
                    "selected_scene_function": scene_fn,
                    "selection_reason": beat_selection.selection_reason,
                    "selection_source": beat_selection.selection_source,
                    "transition_allowed": True,
                },
                actual={
                    "realized": None,
                    "committed": None,
                    "lost_at_stage": None,
                    "failure_classification": "observability_gap",
                },
                reasons=["beat_selected_not_yet_realized"],
                source="runtime",
                selected_beat=selected_beat_id,
            ),
        )
        return update

    def _derive_scene_energy(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_scene_energy")
        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        result = derive_scene_energy(
            scene_plan_record=scene_plan,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            social_state_record=state.get("social_state_record")
            if isinstance(state.get("social_state_record"), dict)
            else None,
            pacing_mode=state.get("pacing_mode") if isinstance(state.get("pacing_mode"), str) else None,
            silence_brevity_decision=state.get("silence_brevity_decision")
            if isinstance(state.get("silence_brevity_decision"), dict)
            else None,
            selected_responder_set=state.get("selected_responder_set")
            if isinstance(state.get("selected_responder_set"), list)
            else None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
            prior_continuity_impacts=state.get("prior_continuity_impacts")
            if isinstance(state.get("prior_continuity_impacts"), list)
            else None,
            npc_agency_simulation=state.get("npc_agency_simulation")
            if isinstance(state.get("npc_agency_simulation"), dict)
            else None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        transition = result.get("transition") if isinstance(result.get("transition"), dict) else {}
        if target:
            scene_plan["scene_energy_target"] = target
        if transition:
            scene_plan["scene_energy_transition"] = transition
        update["scene_plan_record"] = scene_plan
        update["scene_energy_target"] = target
        update["scene_energy_transition"] = transition
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_SCENE_ENERGY,
            _scene_energy_aspect_record(
                target=target,
                transition=transition,
                policy=result.get("policy") if isinstance(result.get("policy"), dict) else None,
            ),
        )
        return update

    def _derive_pacing_rhythm(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_pacing_rhythm")
        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        result = derive_pacing_rhythm(
            scene_plan_record=scene_plan,
            pacing_mode=state.get("pacing_mode") if isinstance(state.get("pacing_mode"), str) else None,
            silence_brevity_decision=state.get("silence_brevity_decision")
            if isinstance(state.get("silence_brevity_decision"), dict)
            else None,
            scene_energy_target=state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else None,
            selected_responder_set=state.get("selected_responder_set")
            if isinstance(state.get("selected_responder_set"), list)
            else None,
            prior_pacing_rhythm_state=state.get("prior_pacing_rhythm_state")
            if isinstance(state.get("prior_pacing_rhythm_state"), dict)
            else None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
            prior_dramatic_signature=state.get("prior_dramatic_signature")
            if isinstance(state.get("prior_dramatic_signature"), dict)
            else None,
            prior_narrative_thread_state=state.get("prior_narrative_thread_state")
            if isinstance(state.get("prior_narrative_thread_state"), dict)
            else None,
            prior_callback_web_state=state.get("prior_callback_web_state")
            if isinstance(state.get("prior_callback_web_state"), dict)
            else None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        rhythm_state = result.get("state") if isinstance(result.get("state"), dict) else {}
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        if rhythm_state:
            scene_plan["pacing_rhythm_state"] = rhythm_state
        if target:
            scene_plan["pacing_rhythm_target"] = target
        update["scene_plan_record"] = scene_plan
        update["pacing_rhythm_state"] = rhythm_state
        update["pacing_rhythm_target"] = target
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_PACING_RHYTHM,
            _pacing_rhythm_aspect_record(
                state_record=rhythm_state,
                target=target,
                policy=result.get("policy") if isinstance(result.get("policy"), dict) else None,
            ),
        )
        return update

    def _derive_social_pressure(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_social_pressure")
        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        result = derive_social_pressure(
            scene_assessment=state.get("scene_assessment")
            if isinstance(state.get("scene_assessment"), dict)
            else None,
            social_state_record=state.get("social_state_record")
            if isinstance(state.get("social_state_record"), dict)
            else None,
            scene_energy_target=state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else None,
            pacing_rhythm_target=state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else None,
            prior_social_pressure_state=state.get("prior_social_pressure_state")
            if isinstance(state.get("prior_social_pressure_state"), dict)
            else None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
            prior_narrative_thread_state=state.get("prior_narrative_thread_state")
            if isinstance(state.get("prior_narrative_thread_state"), dict)
            else None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        pressure_state = result.get("state") if isinstance(result.get("state"), dict) else {}
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        if pressure_state:
            scene_plan["social_pressure_state"] = pressure_state
        if target:
            scene_plan["social_pressure_target"] = target
        update["scene_plan_record"] = scene_plan
        update["social_pressure_state"] = pressure_state
        update["social_pressure_target"] = target
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_SOCIAL_PRESSURE,
            _social_pressure_aspect_record(
                state_record=pressure_state,
                target=target,
                policy=result.get("policy") if isinstance(result.get("policy"), dict) else None,
            ),
        )
        return update

    def _derive_improvisational_coherence(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_improvisational_coherence")
        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        result = derive_improvisational_coherence(
            player_input=state.get("player_input") if isinstance(state.get("player_input"), str) else None,
            interpreted_input=state.get("interpreted_input")
            if isinstance(state.get("interpreted_input"), dict)
            else None,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            scene_plan_record=scene_plan,
            selected_scene_function=state.get("selected_scene_function")
            if isinstance(state.get("selected_scene_function"), str)
            else None,
            current_scene_id=state.get("current_scene_id")
            if isinstance(state.get("current_scene_id"), str)
            else None,
            selected_responder_set=state.get("selected_responder_set")
            if isinstance(state.get("selected_responder_set"), list)
            else None,
            scene_energy_target=state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else None,
            pacing_rhythm_target=state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        if target:
            scene_plan["improvisational_coherence_target"] = target
        update["scene_plan_record"] = scene_plan
        update["improvisational_coherence_target"] = target
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_IMPROVISATIONAL_COHERENCE,
            build_improvisational_coherence_aspect_record(
                target=target,
                policy=result.get("policy") if isinstance(result.get("policy"), dict) else None,
            ),
        )
        return update

    def _derive_information_disclosure(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_information_disclosure")
        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        result = derive_information_disclosure(
            scene_plan_record=scene_plan,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            pacing_mode=state.get("pacing_mode") if isinstance(state.get("pacing_mode"), str) else None,
            prior_continuity_impacts=state.get("prior_continuity_impacts")
            if isinstance(state.get("prior_continuity_impacts"), list)
            else None,
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
        )
        target = result.get("target") if isinstance(result.get("target"), dict) else {}
        if target:
            scene_plan["information_disclosure_target"] = target
        update["scene_plan_record"] = scene_plan
        update["information_disclosure_target"] = target
        update["turn_aspect_ledger"] = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_INFORMATION_DISCLOSURE,
            _information_disclosure_aspect_record(
                target=target,
                policy=result.get("policy") if isinstance(result.get("policy"), dict) else None,
            ),
        )
        return update

    def _derive_dramatic_irony(self, state: RuntimeTurnState) -> RuntimeTurnState:
        update = _track(state, node_name="derive_dramatic_irony")
        responders = (
            state.get("selected_responder_set")
            if isinstance(state.get("selected_responder_set"), list)
            else []
        )
        responder_ids: list[str] = []
        for row in responders:
            if not isinstance(row, dict):
                continue
            actor_id = str(row.get("actor_id") or row.get("responder_id") or "").strip()
            if actor_id and actor_id not in responder_ids:
                responder_ids.append(actor_id)

        actor_lane_ctx = (
            state.get("actor_lane_context")
            if isinstance(state.get("actor_lane_context"), dict)
            else {}
        )
        forbidden_actor_ids: set[str] = set()
        for raw_actor_id in actor_lane_ctx.get("ai_forbidden_actor_ids") or []:
            forbidden_actor_ids.update(expand_goc_actor_id_aliases(str(raw_actor_id)))
        human_actor_id = str(actor_lane_ctx.get("human_actor_id") or "").strip()
        forbidden_actor_ids.update(expand_goc_actor_id_aliases(human_actor_id))
        allowed_actor_ids = npc_actor_ids_from_context(actor_lane_ctx)
        if not allowed_actor_ids:
            allowed_actor_ids = [
                actor_id
                for actor_id in responder_ids
                if actor_id and actor_id not in forbidden_actor_ids
            ]

        minds = (
            state.get("character_mind_records")
            if isinstance(state.get("character_mind_records"), list)
            else []
        )
        compact_minds: list[dict[str, Any]] = []
        for row in minds[:4]:
            if not isinstance(row, dict):
                continue
            compact_minds.append(
                {
                    "actor_id": row.get("runtime_actor_id") or row.get("character_key"),
                    "formal_role_label": row.get("formal_role_label"),
                    "tactical_posture": row.get("tactical_posture"),
                    "pressure_response_bias": row.get("pressure_response_bias"),
                }
            )

        _, _, npc_agency_simulation = _build_npc_agency_plan_projection(
            state=state,
            responders=responders,
            responder_ids=responder_ids,
            npc_actor_ids=allowed_actor_ids,
            compact_minds=compact_minds,
        )
        if isinstance(npc_agency_simulation, dict):
            update["npc_agency_simulation"] = npc_agency_simulation

        scene_plan = (
            dict(state.get("scene_plan_record"))
            if isinstance(state.get("scene_plan_record"), dict)
            else {}
        )
        dramatic_irony_record = build_dramatic_irony_record(
            module_runtime_policy=state.get("module_runtime_policy")
            if isinstance(state.get("module_runtime_policy"), dict)
            else None,
            actor_lane_context=actor_lane_ctx,
            selected_responder_set=responders,
            character_mind_records=minds,
            social_state_record=state.get("social_state_record")
            if isinstance(state.get("social_state_record"), dict)
            else None,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            scene_plan_record=scene_plan,
            npc_agency_simulation=npc_agency_simulation
            if isinstance(npc_agency_simulation, dict)
            else state.get("npc_agency_simulation")
            if isinstance(state.get("npc_agency_simulation"), dict)
            else None,
            prior_planner_truth=state.get("prior_planner_truth")
            if isinstance(state.get("prior_planner_truth"), dict)
            else None,
            current_scene_id=state.get("current_scene_id")
            if isinstance(state.get("current_scene_id"), str)
            else None,
            selected_scene_function=str(state.get("selected_scene_function") or "").strip()
            or None,
        )
        scene_plan["dramatic_irony_record"] = dramatic_irony_record
        update["scene_plan_record"] = scene_plan
        update["dramatic_irony_record"] = dramatic_irony_record
        update["turn_aspect_ledger"] = set_aspect_record(
            update.get("turn_aspect_ledger")
            if isinstance(update.get("turn_aspect_ledger"), dict)
            else state.get("turn_aspect_ledger")
            if isinstance(state.get("turn_aspect_ledger"), dict)
            else {},
            ASPECT_DRAMATIC_IRONY,
            build_dramatic_irony_aspect_record(
                record=dramatic_irony_record,
                validation=None,
                source="runtime",
            ),
        )
        return update

    def _build_context_synthesis_bundle_for_state(
        self,
        state: RuntimeTurnState,
        *,
        validation_feedback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return build_context_synthesis_bundle(
            retrieval=state.get("retrieval") if isinstance(state.get("retrieval"), dict) else None,
            context_text=state.get("context_text") if isinstance(state.get("context_text"), str) else None,
            scene_assessment=state.get("scene_assessment")
            if isinstance(state.get("scene_assessment"), dict)
            else None,
            semantic_move_record=state.get("semantic_move_record")
            if isinstance(state.get("semantic_move_record"), dict)
            else None,
            social_state_record=state.get("social_state_record")
            if isinstance(state.get("social_state_record"), dict)
            else None,
            turn_aspect_ledger=state.get("turn_aspect_ledger")
            if isinstance(state.get("turn_aspect_ledger"), dict)
            else None,
            hierarchical_memory_context=state.get("hierarchical_memory_context")
            if isinstance(state.get("hierarchical_memory_context"), dict)
            else None,
            validation_feedback=validation_feedback
            if isinstance(validation_feedback, dict)
            else (
                state.get("validation_feedback")
                if isinstance(state.get("validation_feedback"), dict)
                else None
            ),
        )

    def _synthesize_context(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Build a deterministic, non-authoritative context synthesis bundle."""
        update = _track(state, node_name="synthesize_context")
        try:
            bundle = self._build_context_synthesis_bundle_for_state(state)
        except Exception as exc:
            bundle = build_context_synthesis_error_bundle(exc)
            errors = list(state.get("graph_errors") or [])
            errors.append(f"context_synthesis_error:{type(exc).__name__}")
            update["graph_errors"] = errors
        update["context_synthesis_bundle"] = bundle
        update["context_synthesis_diagnostics"] = summarize_context_synthesis_for_diagnostics(bundle)
        return update

    def _synthesize_context_for_retry(
        self,
        state: RuntimeTurnState,
        *,
        validation_feedback: dict[str, Any],
        attempt_index: int,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Rebuild context synthesis with validation feedback for self-correction."""
        try:
            bundle = self._build_context_synthesis_bundle_for_state(
                state,
                validation_feedback=validation_feedback,
            )
        except Exception as exc:
            bundle = build_context_synthesis_error_bundle(exc)
        diagnostics = summarize_context_synthesis_for_diagnostics(bundle, used_in_model_prompt=True)
        diagnostics.update(
            {
                "retry_attempt_index": attempt_index,
                "validation_feedback": {
                    "codes": list(validation_feedback.get("codes") or []),
                    "trigger_source": validation_feedback.get("trigger_source"),
                    "failure_reason_before_retry": validation_feedback.get("failure_reason_before_retry"),
                    "validation_status_before_retry": validation_feedback.get("validation_status_before_retry"),
                },
                "used_for_self_correction": True,
            }
        )
        prompt_lines = context_synthesis_prompt_lines(bundle)
        prompt_block = ""
        if prompt_lines:
            prompt_block = (
                "Validation Feedback Resynthesis (proposal support, non-authoritative):\n"
                + "\n".join(prompt_lines)
            )
        return bundle, diagnostics, prompt_block

    def _assemble_model_context(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Attach post-director runtime state to the model-visible prompt."""
        prompt = str(state.get("model_prompt") or state.get("player_input") or "")
        dramatic_packet = _build_dramatic_generation_packet(state)
        lines: list[str] = []
        synthesis_bundle = (
            state.get("context_synthesis_bundle")
            if isinstance(state.get("context_synthesis_bundle"), dict)
            else {}
        )
        synthesis_lines = context_synthesis_prompt_lines(synthesis_bundle)
        if synthesis_lines:
            lines.extend(synthesis_lines)
        lines.append("Director runtime state (authoritative, model-visible):")

        scene_assess = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
        if scene_assess:
            lines.append("Scene Assessment:")
            for key in (
                "scene_core",
                "pressure_state",
                "guidance_phase_key",
                "guidance_phase_title",
                "guidance_civility_required",
                "canonical_setting",
                "narrative_scope",
                "continuity_carry_forward_note",
                "thread_pressure_state",
            ):
                val = scene_assess.get(key)
                if val is not None and str(val).strip():
                    lines.append(f"- {key}: {str(val).strip()[:220]}")
            thread_feedback = scene_assess.get("narrative_thread_feedback")
            if isinstance(thread_feedback, dict):
                lines.append(
                    f"- narrative_thread_feedback: {json.dumps(thread_feedback, sort_keys=True)[:260]}"
                )

        semantic = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}
        if semantic:
            lines.append("Semantic Move:")
            for key in ("move_type", "social_move_family", "target_actor_hint", "directness", "pressure_tactic", "scene_risk_band"):
                val = semantic.get(key)
                if val is not None and str(val).strip():
                    lines.append(f"- {key}: {str(val).strip()[:160]}")

        social = state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else {}
        if social:
            lines.append("Social State:")
            for key in (
                "scene_pressure_state",
                "guidance_phase_key",
                "responder_asymmetry_code",
                "social_risk_band",
                "social_continuity_status",
                "prior_social_risk_band",
                "prior_social_state_fingerprint",
                "active_thread_count",
                "thread_pressure_summary_present",
            ):
                val = social.get(key)
                if val is not None and str(val).strip():
                    lines.append(f"- {key}: {str(val).strip()[:160]}")
            prior_classes = social.get("prior_continuity_classes")
            if isinstance(prior_classes, list) and prior_classes:
                lines.append(f"- prior_continuity_classes: {prior_classes[:8]}")

        scene_fn = str(state.get("selected_scene_function") or "").strip()
        if scene_fn:
            lines.append(f"Selected Scene Function: {scene_fn}")
            lines.append(f"selected_scene_function: {scene_fn}")
        pacing = str(state.get("pacing_mode") or "").strip()
        if pacing:
            lines.append(f"Pacing Directive: {pacing}")
        silence = state.get("silence_brevity_decision") if isinstance(state.get("silence_brevity_decision"), dict) else {}
        if silence:
            lines.append(f"Silence/Brevity Decision: {json.dumps(silence, sort_keys=True)[:260]}")
        rhythm_target = (
            state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else {}
        )
        if rhythm_target:
            compact_rhythm = {
                key: rhythm_target.get(key)
                for key in (
                    "cadence",
                    "tempo_arc",
                    "response_shape",
                    "turn_change_policy",
                    "min_visible_blocks",
                    "max_visible_blocks",
                    "min_actor_turns",
                    "requires_pause",
                    "blocks_forced_speech",
                )
                if rhythm_target.get(key) is not None
            }
            lines.append(f"Pacing Rhythm Target: {json.dumps(compact_rhythm, sort_keys=True)[:320]}")

        memory_context = state.get("hierarchical_memory_context") if isinstance(state.get("hierarchical_memory_context"), dict) else {}
        memory_lines = memory_context.get("context_lines") if isinstance(memory_context.get("context_lines"), list) else []
        if memory_lines:
            lines.append("Hierarchical Memory:")
            for memory_line in memory_lines[:8]:
                text = str(memory_line or "").strip()
                if text:
                    lines.append(f"- {text[:220]}")

        responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        if responders:
            lines.append("Eligible Responders:")
            for responder in responders[:4]:
                if not isinstance(responder, dict):
                    continue
                actor = str(responder.get("actor_id") or responder.get("responder_id") or "?")
                reason = str(responder.get("reason") or responder.get("responder_type") or "")
                lines.append(f"- {actor}: {reason[:180]}")

        turn_ic = str(state.get("turn_input_class") or "").strip().lower()
        if str(state.get("module_id") or "") == GOC_MODULE_ID and turn_ic != "opening":
            alc = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
            hid = str(alc.get("human_actor_id") or "").strip()
            spr = str(alc.get("selected_player_role") or "").strip()
            raw_pi = str(state.get("player_input") or "").strip()
            if raw_pi and (hid or spr):
                pri = ""
                if responders and isinstance(responders[0], dict):
                    pri = str(responders[0].get("actor_id") or responders[0].get("responder_id") or "").strip()
                interp = state.get("interpreted_input") if isinstance(state.get("interpreted_input"), dict) else {}
                ik = str(interp.get("input_kind") or interp.get("kind") or "speech")
                pik = str(interp.get("player_input_kind") or ik or "speech").strip().lower()
                narrator_expected = bool(interp.get("narrator_response_expected"))
                npc_expected = bool(interp.get("npc_response_expected"))
                lines.append("PLAYER INPUT OWNERSHIP (canonical committed surface):")
                lines.append(
                    f"- human_actor_id (player words belong to this actor, not to primary_responder_id): {hid or spr}"
                )
                lines.append(f"- selected_player_role: {spr or hid}")
                lines.append(f"- input_kind: {ik}")
                lines.append(f"- player_input_kind: {pik}")
                lines.append(f"- narrator_response_expected: {str(narrator_expected).lower()}")
                lines.append(f"- npc_response_expected: {str(npc_expected).lower()}")
                lines.append(
                    f"- primary_responder_id / NPC reaction scope (must not steal the player's line as this NPC): "
                    f"{pri or '(model must still respect actor_lane_boundary)'}"
                )
                lines.append(
                    f"- verbatim_player_input (already attributed to the human in the UI; do not duplicate as NPC "
                    f"spoken_lines): {raw_pi[:420]}"
                )
                lines.append(
                    "- Require: do NOT assign verbatim_player_input to a different speaker_id. Generate only "
                    "NPC/narrator reaction; the human character has already spoken this line."
                )
                if pik in ("action", "perception"):
                    lines.append("PHYSICAL_PLAYER_MOVE (PLAYER-ACTION-INTENT-01):")
                    lines.append(
                        "- The human actor has already performed or attempted this physical move in-scene. "
                        "Do NOT recast it as NPC dialogue, coaching, or spatial explanation unless the NPC is "
                        "explicitly guiding the human in-world."
                    )
                    lines.append(
                        "- NPC spoken_lines: brief social reaction only; do NOT narrate the player's movement as "
                        "if the NPC performed it or explained what the player sees."
                    )
                    lines.append(
                        "- Narration (narrator / narration_summary): describe immediate environment and what the "
                        "human character perceives; NPCs do not replace narrator responsibilities."
                    )
                    if narrator_expected:
                        lines.append(
                            "- Hard requirement: emit a narrator-visible spatial/perceptual consequence for this turn."
                        )
                    if not npc_expected:
                        lines.append(
                            "- Hard requirement: do NOT produce NPC answer/explanation as primary response; "
                            "NPC contribution is optional social reaction only."
                        )

        actor_lane_boundary = dramatic_packet.get("actor_lane_boundary") if isinstance(dramatic_packet, dict) else None
        if isinstance(actor_lane_boundary, dict):
            allowed = actor_lane_boundary.get("ai_allowed_actor_ids")
            forbidden = actor_lane_boundary.get("ai_forbidden_actor_ids")
            lines.append("Actor Lane Boundary (hard validation):")
            lines.append(f"- human_actor_id: {actor_lane_boundary.get('human_actor_id') or 'none'}")
            lines.append(f"- ai_allowed_actor_ids: {allowed if isinstance(allowed, list) else []}")
            lines.append(f"- ai_forbidden_actor_ids: {forbidden if isinstance(forbidden, list) else []}")
            lines.append(
                "- hard_rule: use ONLY ai_allowed_actor_ids in primary_responder_id, secondary_responder_ids, "
                "responder_actor_ids, spoken_lines, action_lines, and initiative_events. Do not write dialogue, "
                "action, emotional state, counter, interruption, initiative, or narration-as-action for the human actor."
            )

        minds = state.get("character_mind_records") if isinstance(state.get("character_mind_records"), list) else []
        if minds:
            lines.append("Character Mind Records:")
            for mind in minds[:4]:
                if not isinstance(mind, dict):
                    continue
                lines.append(
                    "- "
                    f"{mind.get('runtime_actor_id') or mind.get('character_key')}: "
                    f"role={str(mind.get('formal_role_label') or '')[:80]}, "
                    f"posture={str(mind.get('tactical_posture') or '')[:80]}, "
                    f"bias={str(mind.get('pressure_response_bias') or '')[:80]}"
                )

        voices = state.get("character_voice_profiles") if isinstance(state.get("character_voice_profiles"), list) else []
        if voices:
            lines.append("Character Voice Profiles:")
            for voice in voices[:4]:
                if not isinstance(voice, dict):
                    continue
                speech = voice.get("speech_patterns") if isinstance(voice.get("speech_patterns"), dict) else {}
                speech_bits = []
                for key in ("vocabulary", "syntax", "rhythm", "idiom"):
                    val = str(speech.get(key) or "").strip()
                    if val:
                        speech_bits.append(f"{key}={val[:80]}")
                pitfalls = voice.get("pitfalls_to_avoid") if isinstance(voice.get("pitfalls_to_avoid"), list) else []
                lines.append(
                    "- "
                    f"{voice.get('runtime_actor_id') or voice.get('character_key')}: "
                    f"tone={str(voice.get('baseline_tone') or '')[:100]}, "
                    f"{'; '.join(speech_bits[:3])}"
                )
                if voice.get("current_phase_voice_hint"):
                    lines.append(f"  phase_voice={str(voice.get('current_phase_voice_hint'))[:160]}")
                if pitfalls:
                    lines.append(f"  avoid={'; '.join(str(item)[:120] for item in pitfalls[:2])}")

        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else []
        if prior:
            lines.append("Continuity Constraints:")
            for impact in prior[:4]:
                if isinstance(impact, dict):
                    cls = str(impact.get("class") or impact.get("continuity_class") or "")
                    desc = str(impact.get("description") or impact.get("summary") or impact.get("note") or "")
                    lines.append(f"- {cls}: {desc[:180]}")

        cascade_context = (
            dramatic_packet.get("consequence_cascade_context")
            if isinstance(dramatic_packet.get("consequence_cascade_context"), dict)
            else {}
        )
        cascade_items = (
            cascade_context.get("items") if isinstance(cascade_context.get("items"), list) else []
        )
        if cascade_items:
            lines.append("Consequence Cascade Context (bounded committed state):")
            selected_classes = cascade_context.get("selected_continuity_classes") or []
            selected_statuses = cascade_context.get("selected_statuses") or []
            lines.append(
                f"- selected_continuity_classes: {list(selected_classes)[:6]} "
                f"selected_statuses: {list(selected_statuses)[:6]}"
            )
            for item in cascade_items[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    "- "
                    f"id={str(item.get('consequence_id') or '')[:80]}, "
                    f"class={str(item.get('continuity_class') or '')[:80]}, "
                    f"status={str(item.get('status') or '')[:40]}, "
                    f"source_turn={item.get('source_turn_number')}"
                )

        dramatic_irony_context = (
            dramatic_packet.get("dramatic_irony_context")
            if isinstance(dramatic_packet.get("dramatic_irony_context"), dict)
            else {}
        )
        irony_opportunities = (
            dramatic_irony_context.get("opportunities")
            if isinstance(dramatic_irony_context.get("opportunities"), list)
            else []
        )
        if irony_opportunities:
            lines.append("Dramatic Irony Context (bounded, non-omniscient):")
            for row in irony_opportunities[:3]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    "- "
                    f"opportunity_id={str(row.get('opportunity_id') or '')[:160]}, "
                    f"ignorant_actor_id={str(row.get('ignorant_actor_id') or '')[:80]}, "
                    f"surface_mode={str(row.get('allowed_surface_mode') or '')[:80]}, "
                    f"risk_band={str(row.get('risk_band') or '')[:40]}"
                )
            lines.append(
                "- rule: realize only through subtext, behavior, misread reaction, or withheld context; "
                "do not state hidden intent or private motive as omniscient narration."
            )

        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else {}
        if state.get("module_id") == GOC_MODULE_ID and yslice:
            phase_key = str(scene_assess.get("guidance_phase_key") or "")
            phase_arc_key = GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY.get(phase_key, "")
            phases = yslice.get("scene_phases") if isinstance(yslice.get("scene_phases"), dict) else {}
            phase = phases.get(phase_arc_key) if isinstance(phases.get(phase_arc_key), dict) else {}
            if phase:
                lines.append("Canonical GoC Phase Law:")
                for key in ("name", "description", "active_triggers", "enforced_constraints", "engine_tasks", "exit_condition"):
                    val = phase.get(key)
                    if val:
                        lines.append(f"- {key}: {str(val)[:300]}")
            rel_axes = yslice.get("relationship_axes") if isinstance(yslice.get("relationship_axes"), dict) else {}
            if rel_axes:
                axis_names = []
                for axis_id, axis in list(rel_axes.items())[:4]:
                    if isinstance(axis, dict):
                        axis_names.append(f"{axis_id}:{axis.get('name') or ''}")
                if axis_names:
                    lines.append(f"Canonical Relationship Axes: {', '.join(axis_names)}")
            escalation_axes = yslice.get("escalation_axes") if isinstance(yslice.get("escalation_axes"), dict) else {}
            if escalation_axes:
                names = []
                for axis_id, axis in list(escalation_axes.items())[:4]:
                    if isinstance(axis, dict):
                        names.append(f"{axis_id}:{axis.get('name') or ''}")
                if names:
                    lines.append(f"Canonical Escalation Axes: {', '.join(names)}")

            knowledge_contract = (
                state.get("goc_runtime_knowledge_contract")
                if isinstance(state.get("goc_runtime_knowledge_contract"), dict)
                else {}
            )
            if knowledge_contract:
                lines.extend(
                    knowledge_contract_prompt_lines(
                        knowledge_contract,
                        opening_turn=turn_ic == "opening",
                    )
                )

        lines.append("Dramatic Generation Packet (authoritative JSON):")
        lines.append(json.dumps(dramatic_packet, sort_keys=True))
        lines.append(
            "Generation directive: produce actor-level exchange (spoken_lines/action_lines/initiative_events) "
            "aligned with selected_scene_function, responder scope, actor lane boundary, pacing, continuity constraints, "
            "the improvisational_coherence target, information_disclosure target, bounded dramatic_irony_context, "
            "and consequence_cascade_context."
        )

        update = _track(state, node_name="assemble_model_context")
        directive = _session_language_directive_for_model(state)
        update["model_prompt"] = f"{directive}{prompt}\n\n" + "\n".join(lines)
        update["dramatic_generation_packet"] = dramatic_packet
        if isinstance(synthesis_bundle, dict):
            update["context_synthesis_diagnostics"] = summarize_context_synthesis_for_diagnostics(
                synthesis_bundle,
                used_in_model_prompt=bool(synthesis_lines),
            )
        return update

    def _route_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_route_model`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        dramatic_requirements = _drama_aware_routing_requirements(state)
        try:
            decision = self.routing.choose(
                task_type=state["task_type"],
                dramatic_requirements=dramatic_requirements,
            )
        except TypeError:
            decision = self.routing.choose(task_type=state["task_type"])
        selected = self.registry.get(decision.selected_model)
        update = _track(state, node_name="route_model")
        fallback_chain: list[str] = [decision.selected_model]
        if decision.fallback_model:
            fallback_chain.append(decision.fallback_model)
        code = decision.route_reason
        if code not in ROUTING_LABELS:
            code = "role_matrix_primary"
        governed = bool(getattr(self.routing, "routes", None))
        # Surface route-family truth onto the per-turn state. The governed
        # routing policy exposes its most recent choice via
        # ``_last_choice_meta`` so this node can publish it without changing
        # the shared ``RoutingDecision`` dataclass in ``story_runtime_core``.
        last_choice_meta = getattr(self.routing, "_last_choice_meta", None)
        if not isinstance(last_choice_meta, dict):
            last_choice_meta = {}
        update["routing"] = {
            "selected_model": decision.selected_model,
            "selected_provider": decision.selected_provider,
            "reason": decision.route_reason,
            "route_reason_code": code,
            "fallback_model": decision.fallback_model,
            "fallback_chain": fallback_chain,
            "route_mode": "primary_graph_route",
            "policy_id_used": STORY_RUNTIME_ROUTING_POLICY_ID,
            "policy_version_used": STORY_RUNTIME_ROUTING_POLICY_VERSION,
            "timeout_seconds": selected.timeout_seconds if selected else None,
            "structured_output_success": bool(selected.structured_output_capable) if selected else False,
            "registered_adapter_providers": sorted(self.adapters.keys()),
            "governed_runtime_story_path": governed,
            "legacy_default_registry_path": not governed,
            "route_id": last_choice_meta.get("route_id"),
            "route_family": last_choice_meta.get("route_family"),
            "route_family_expected": last_choice_meta.get("route_family_expected"),
            "route_substitution_occurred": bool(
                last_choice_meta.get("route_substitution_occurred")
            ),
            "generation_execution_mode": last_choice_meta.get("generation_execution_mode")
            or (self.generation_execution_mode or None),
            "mock_fallback_blocked": bool(last_choice_meta.get("mock_fallback_blocked")),
            "drama_aware_requirements": dramatic_requirements,
            "drama_aware_profile": last_choice_meta.get("drama_aware_profile"),
        }
        update["selected_provider"] = decision.selected_provider or ""
        update["selected_timeout"] = float(selected.timeout_seconds) if selected else 10.0
        return update

    def _invoke_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_invoke_model`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        provider = state.get("selected_provider") or ""
        adapter = self.adapters.get(provider)
        routing = state.get("routing") if isinstance(state.get("routing"), dict) else {}
        selected_mid = str(routing.get("selected_model") or "").strip()
        spec = self.registry.get(selected_mid) if selected_mid else None
        provider_model = (
            str(getattr(spec, "provider_model_name", "") or "").strip()
            if spec is not None
            else ""
        )
        api_model = provider_model or (spec.model_name if spec is not None else None)
        generation: dict[str, Any] = {
            "attempted": False,
            "success": None,
            "error": None,
            "retrieval_context_attached": bool(state.get("context_text")),
            "prompt_length": len(state.get("model_prompt", "")),
            "fallback_used": False,
        }
        outcome = "ok"
        if adapter:
            generation["attempted"] = True
            invoke_kw: dict[str, Any] = {
                "adapter": adapter,
                "player_input": state["player_input"],
                "interpreted_input": state.get("interpreted_input", {}) if isinstance(state.get("interpreted_input"), dict) else {},
                "retrieval_context": state.get("context_text"),
                "timeout_seconds": float(state.get("selected_timeout", 10.0)),
                "model_prompt": state.get("model_prompt", ""),
                "dramatic_generation_packet": state.get("dramatic_generation_packet")
                if isinstance(state.get("dramatic_generation_packet"), dict)
                else None,
            }
            if api_model:
                invoke_kw["model_name"] = api_model
            runtime_result = _invoke_runtime_adapter_with_langchain(**invoke_kw)
            call = runtime_result.call
            generation["success"] = call.success
            generation["error"] = call.metadata.get("error") if not call.success else None
            generation["model_raw_text"] = call.content
            structured = None
            if runtime_result.parsed_output:
                structured = runtime_result.parsed_output.model_dump(mode="json")
            generation["metadata"] = {
                **call.metadata,
                "langchain_prompt_used": True,
                "langchain_parser_error": runtime_result.parser_error,
                "structured_output": structured,
                "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
                "dramatic_generation_packet_included": isinstance(
                    state.get("dramatic_generation_packet"), dict
                ),
                "dramatic_generation_packet_scene_function": (
                    state.get("dramatic_generation_packet", {}).get("selected_scene_function")
                    if isinstance(state.get("dramatic_generation_packet"), dict)
                    else None
                ),
                "dramatic_generation_packet_primary_responder": (
                    state.get("dramatic_generation_packet", {}).get("primary_responder_id")
                    if isinstance(state.get("dramatic_generation_packet"), dict)
                    else None
                ),
            }
            if not call.success:
                outcome = "error"
            # PRIMARY-PARSER-EVIDENCE-01: capture primary attempt evidence into a
            # separate state key so it survives self-correction and LDSS overwrites.
            raw_out = str(call.content or "").strip()
            raw_sha = (
                hashlib.sha256(raw_out.encode("utf-8", errors="replace")).hexdigest()
                if raw_out
                else ""
            )
            update_pa: dict[str, Any] = {
                "primary_attempt_provider": provider or "",
                "primary_attempt_model": selected_mid or "",
                "primary_attempt_api_model": api_model or "",
                "primary_attempt_api_success": bool(call.success),
                "primary_attempt_parser_error_present": bool(runtime_result.parser_error),
                "primary_attempt_parser_error": str(runtime_result.parser_error or "")[:400],
                "primary_attempt_structured_output_present": runtime_result.parsed_output is not None,
                "primary_attempt_raw_output_sha256": raw_sha,
                "primary_attempt_raw_output_excerpt": raw_out[:300],
            }
        else:
            generation["error"] = f"adapter_not_registered:{provider}"
            generation["metadata"] = {
                "adapter_invocation_mode": ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "note": "No adapter registered for routed provider; invoke_model did not call LangChain.",
            }
            outcome = "error"
            update_pa = {}
        update = _track(state, node_name="invoke_model", outcome=outcome)
        update["generation"] = generation
        update["fallback_needed"] = bool(generation["error"] or generation["success"] is False)
        if update["fallback_needed"]:
            _log.warning("Primary model invocation failed: provider=%s error=%s", provider or "unknown", generation.get("error") or "unknown")
        if update_pa:
            update["primary_attempt_evidence"] = update_pa
        return update

    def _next_step_after_invoke(self, state: RuntimeTurnState) -> str:
        """Describe what ``_next_step_after_invoke`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            str:
                Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
        """
        return "fallback_model" if state.get("fallback_needed") else "proposal_normalize"

    def _fallback_model(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_fallback_model`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        fallback_generation = dict(state.get("generation", {}))
        primary_error = (state.get("generation") or {}).get("error") or "unknown"
        configured_fallback_error: str | None = None
        routing = state.get("routing") if isinstance(state.get("routing"), dict) else {}
        selected_mid = str(routing.get("selected_model") or "").strip()
        fallback_mid = str(routing.get("fallback_model") or "").strip()
        if fallback_mid and fallback_mid != selected_mid:
            spec = self.registry.get(fallback_mid)
            provider = str(getattr(spec, "provider", "") or "").strip() if spec is not None else ""
            if spec is None:
                configured_fallback_error = f"fallback_model_not_registered:{fallback_mid}"
            elif provider == "mock":
                configured_fallback_error = "fallback_model_provider_is_mock"
            else:
                adapter = self.adapters.get(provider)
                if adapter is None:
                    configured_fallback_error = f"fallback_adapter_missing:{provider}"
                else:
                    provider_model = str(getattr(spec, "provider_model_name", "") or "").strip()
                    api_model = provider_model or str(getattr(spec, "model_name", "") or "").strip() or None
                    _log.warning(
                        "Falling back to configured runtime model: fallback_model=%s primary_error=%s",
                        fallback_mid,
                        primary_error,
                    )
                    invoke_kw: dict[str, Any] = {
                        "adapter": adapter,
                        "player_input": state["player_input"],
                        "interpreted_input": state.get("interpreted_input", {})
                        if isinstance(state.get("interpreted_input"), dict)
                        else {},
                        "retrieval_context": state.get("context_text"),
                        "timeout_seconds": float(getattr(spec, "timeout_seconds", 10.0) or 10.0),
                        "model_prompt": state.get("model_prompt", ""),
                        "dramatic_generation_packet": state.get("dramatic_generation_packet")
                        if isinstance(state.get("dramatic_generation_packet"), dict)
                        else None,
                    }
                    if api_model:
                        invoke_kw["model_name"] = api_model
                    runtime_result = _invoke_runtime_adapter_with_langchain(**invoke_kw)
                    call = runtime_result.call
                    fallback_generation["attempted"] = True
                    fallback_generation["success"] = call.success
                    fallback_generation["error"] = call.metadata.get("error") if not call.success else None
                    fallback_generation["model_raw_text"] = call.content
                    fallback_generation["content"] = call.content
                    fallback_generation["retrieval_context_attached"] = bool(state.get("context_text"))
                    fallback_generation["prompt_length"] = len(state.get("model_prompt", ""))
                    fallback_generation["fallback_used"] = True
                    fallback_generation["metadata"] = {
                        **call.metadata,
                        "langchain_prompt_used": True,
                        "langchain_parser_error": runtime_result.parser_error,
                        "structured_output": runtime_result.parsed_output.model_dump(mode="json")
                        if runtime_result.parsed_output
                        else None,
                        "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
                        "fallback_model_id": fallback_mid,
                        "fallback_provider": provider,
                        "fallback_reason": "primary_model_invocation_failed",
                        "primary_error": primary_error,
                        "dramatic_generation_packet_included": isinstance(
                            state.get("dramatic_generation_packet"), dict
                        ),
                        "dramatic_generation_packet_scene_function": (
                            state.get("dramatic_generation_packet", {}).get("selected_scene_function")
                            if isinstance(state.get("dramatic_generation_packet"), dict)
                            else None
                        ),
                        "dramatic_generation_packet_primary_responder": (
                            state.get("dramatic_generation_packet", {}).get("primary_responder_id")
                            if isinstance(state.get("dramatic_generation_packet"), dict)
                            else None
                        ),
                    }
                    if call.success:
                        update = _track(state, node_name="fallback_model")
                        update["generation"] = fallback_generation
                        update["fallback_needed"] = False
                        return update
                    configured_fallback_error = (
                        call.metadata.get("error")
                        if isinstance(call.metadata, dict) and call.metadata.get("error")
                        else f"fallback_model_failed:{fallback_mid}"
                    )

        _log.warning(
            "Falling back to mock adapter: primary_error=%s configured_fallback_error=%s",
            primary_error,
            configured_fallback_error or "not_attempted",
        )

        if (self.generation_execution_mode or "").strip().lower() == "ai_only":
            errors = list(state.get("graph_errors", []))
            errors.append("ai_only_mode_blocks_graph_managed_mock_fallback")
            if configured_fallback_error:
                errors.append(str(configured_fallback_error))
            fb_gen = dict(fallback_generation)
            meta = fb_gen.get("metadata") if isinstance(fb_gen.get("metadata"), dict) else {}
            fb_gen["metadata"] = {
                **meta,
                "note": "generation_execution_mode=ai_only — graph-managed mock fallback is disabled.",
                "configured_fallback_error": configured_fallback_error,
            }
            update = _track(state, node_name="fallback_model", outcome="error")
            update["graph_errors"] = errors
            update["generation"] = fb_gen
            update["fallback_needed"] = True
            return update

        fallback_adapter = self.adapters.get("mock")
        if fallback_adapter:
            call = fallback_adapter.generate(
                state.get("model_prompt", state["player_input"]),
                timeout_seconds=5.0,
                retrieval_context=state.get("context_text"),
            )
            fallback_generation["attempted"] = True
            fallback_generation["success"] = call.success
            fallback_generation["error"] = call.metadata.get("error") if not call.success else None
            fallback_generation["model_raw_text"] = call.content
            fallback_generation["metadata"] = {
                **call.metadata,
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "adapter_invocation_mode": ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
                "bypass_note": RAW_FALLBACK_BYPASS_NOTE,
                "configured_fallback_error": configured_fallback_error,
            }
            fallback_generation["fallback_used"] = True
            update = _track(state, node_name="fallback_model")
            update["generation"] = fallback_generation
            update["fallback_needed"] = False
            return update
        errors = list(state.get("graph_errors", []))
        errors.append("fallback_adapter_missing:mock")
        if configured_fallback_error:
            errors.append(str(configured_fallback_error))
        prior_meta = fallback_generation.get("metadata") if isinstance(fallback_generation.get("metadata"), dict) else {}
        fallback_generation["metadata"] = {
            **prior_meta,
            "adapter_invocation_mode": ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
            "langchain_prompt_used": False,
            "note": "fallback_adapter_missing:mock — graph could not run graph-managed raw fallback.",
            "configured_fallback_error": configured_fallback_error,
        }
        update = _track(state, node_name="fallback_model", outcome="error")
        update["graph_errors"] = errors
        update["generation"] = fallback_generation
        return update

    def _self_correct_generation(
        self,
        state: RuntimeTurnState,
        generation: dict[str, Any],
        current_proposed_effects: list[dict[str, Any]],
        feedback_codes: list[str],
        attempt_index: int,
        preserve_actor_lanes: bool = False,
        retry_context_synthesis_bundle: dict[str, Any] | None = None,
        retry_context_synthesis_prompt: str = "",
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        routing = state.get("routing") if isinstance(state.get("routing"), dict) else {}
        selected_mid = str(routing.get("selected_model") or "").strip()
        fallback_mid = str(routing.get("fallback_model") or "").strip()
        candidate_mid = selected_mid
        current_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        current_failed = generation.get("success") is False or bool(generation.get("error"))
        if current_meta.get("adapter") == "mock" and fallback_mid:
            candidate_mid = fallback_mid
        elif current_failed and fallback_mid:
            candidate_mid = fallback_mid
        spec = self.registry.get(candidate_mid) if candidate_mid else None
        provider = getattr(spec, "provider", "") or ""
        adapter = self.adapters.get(provider) if provider else None
        if adapter is None:
            return (
                generation,
                list(current_proposed_effects or []),
                {"attempt_index": attempt_index, "status": "adapter_missing", "candidate_model": candidate_mid},
            )
        provider_model = getattr(spec, "provider_model_name", None) if spec is not None else None
        allowed_actor_ids: list[str] = []
        selected = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        for row in selected:
            if isinstance(row, dict):
                actor_id = str(row.get("actor_id") or row.get("responder_id") or "").strip()
                if actor_id and actor_id not in allowed_actor_ids:
                    allowed_actor_ids.append(actor_id)
        retry_prompt = state.get("model_prompt") if isinstance(state.get("model_prompt"), str) else None
        if retry_context_synthesis_prompt.strip():
            retry_prompt = (
                f"{retry_prompt or state.get('player_input') or ''}\n\n"
                f"{retry_context_synthesis_prompt.strip()}"
            ).strip()
        retry_synthesis_status = ""
        if isinstance(retry_context_synthesis_bundle, dict):
            retry_synthesis_status = str(retry_context_synthesis_bundle.get("status") or "")
        runtime_result = _invoke_runtime_adapter_with_langchain(
            adapter=adapter,
            player_input=state["player_input"],
            interpreted_input=state.get("interpreted_input", {}) if isinstance(state.get("interpreted_input"), dict) else {},
            retrieval_context=state.get("context_text"),
            timeout_seconds=float(getattr(spec, "timeout_seconds", state.get("selected_timeout", 10.0)) or 10.0),
            model_prompt=retry_prompt,
            prior_output=str(generation.get("content") or generation.get("model_raw_text") or ""),
            feedback_codes=list(feedback_codes),
            rewrite_instruction=build_rewrite_instruction(
                list(feedback_codes),
                allowed_actor_ids=allowed_actor_ids,
                preserve_actor_lanes=preserve_actor_lanes,
            ),
            model_name=str(provider_model).strip() if provider_model else None,
            dramatic_generation_packet=state.get("dramatic_generation_packet")
            if isinstance(state.get("dramatic_generation_packet"), dict)
            else None,
        )
        call = runtime_result.call
        prior_raw = str(generation.get("content") or generation.get("model_raw_text") or "").strip()
        prior_success = generation.get("success") is True
        if not call.success and (prior_success or bool(prior_raw)):
            preserved = dict(generation)
            preserved_meta = preserved.get("metadata") if isinstance(preserved.get("metadata"), dict) else {}
            preserved["metadata"] = {
                **preserved_meta,
                "langchain_prompt_used": True,
                "langchain_parser_error": runtime_result.parser_error,
                "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
                "self_correction_attempt_index": attempt_index,
                "self_correction_feedback_codes": list(feedback_codes),
                "self_correction_candidate_model": candidate_mid,
                "self_correction_model_changed": bool(selected_mid)
                and bool(candidate_mid)
                and candidate_mid != selected_mid,
                "context_synthesis_retry_attached": bool(retry_context_synthesis_prompt.strip()),
                "context_synthesis_retry_status": retry_synthesis_status,
                "dramatic_generation_packet_included": isinstance(
                    state.get("dramatic_generation_packet"), dict
                ),
                "dramatic_generation_packet_scene_function": (
                    state.get("dramatic_generation_packet", {}).get("selected_scene_function")
                    if isinstance(state.get("dramatic_generation_packet"), dict)
                    else None
                ),
                "dramatic_generation_packet_primary_responder": (
                    state.get("dramatic_generation_packet", {}).get("primary_responder_id")
                    if isinstance(state.get("dramatic_generation_packet"), dict)
                    else None
                ),
            }
            return (
                preserved,
                list(current_proposed_effects or []),
                {
                    "attempt_index": attempt_index,
                    "candidate_model": candidate_mid,
                    "provider": provider,
                    "feedback_codes": list(feedback_codes),
                    "success": False,
                    "parser_error": runtime_result.parser_error,
                    "preserve_actor_lanes": bool(preserve_actor_lanes),
                    "context_synthesis_retry_attached": bool(retry_context_synthesis_prompt.strip()),
                    "context_synthesis_retry_status": retry_synthesis_status,
                    "status": "rewrite_failed_kept_prior_generation",
                },
            )
        rewritten = dict(generation)
        rewritten["attempted"] = True
        rewritten["success"] = call.success
        rewritten["error"] = call.metadata.get("error") if not call.success else None
        rewritten["model_raw_text"] = call.content
        rewritten["content"] = call.content
        parsed_structured = runtime_result.parsed_output.model_dump(mode="json") if runtime_result.parsed_output else None
        if parsed_structured is None:
            raw_content = str(call.content or "").strip()
            if raw_content.startswith("{"):
                try:
                    raw_parsed = json.loads(raw_content)
                except Exception:
                    raw_parsed = None
                if isinstance(raw_parsed, dict) and (
                    str(raw_parsed.get("schema_version") or "").strip() == "runtime_actor_turn_v1"
                    or any(
                        isinstance(raw_parsed.get(key), list)
                        for key in ("spoken_lines", "action_lines", "initiative_events", "state_effects")
                    )
                ):
                    parsed_structured = raw_parsed
        self_correction_model_changed = bool(selected_mid) and bool(candidate_mid) and candidate_mid != selected_mid
        rewritten["fallback_used"] = bool(generation.get("fallback_used"))
        rewritten["metadata"] = {
            **call.metadata,
            "langchain_prompt_used": True,
            "langchain_parser_error": runtime_result.parser_error,
            "structured_output": parsed_structured,
            "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
            "self_correction_attempt_index": attempt_index,
            "self_correction_feedback_codes": list(feedback_codes),
            "self_correction_candidate_model": candidate_mid,
            "self_correction_model_changed": self_correction_model_changed,
            "context_synthesis_retry_attached": bool(retry_context_synthesis_prompt.strip()),
            "context_synthesis_retry_status": retry_synthesis_status,
            "dramatic_generation_packet_included": isinstance(
                state.get("dramatic_generation_packet"), dict
            ),
            "dramatic_generation_packet_scene_function": (
                state.get("dramatic_generation_packet", {}).get("selected_scene_function")
                if isinstance(state.get("dramatic_generation_packet"), dict)
                else None
            ),
            "dramatic_generation_packet_primary_responder": (
                state.get("dramatic_generation_packet", {}).get("primary_responder_id")
                if isinstance(state.get("dramatic_generation_packet"), dict)
                else None
            ),
        }
        proposed = structured_output_to_proposed_effects(parsed_structured)
        attempt = {
            "attempt_index": attempt_index,
            "candidate_model": candidate_mid,
            "provider": provider,
            "feedback_codes": list(feedback_codes),
            "success": bool(call.success),
            "parser_error": runtime_result.parser_error,
            "preserve_actor_lanes": bool(preserve_actor_lanes),
            "self_correction_model_changed": self_correction_model_changed,
            "context_synthesis_retry_attached": bool(retry_context_synthesis_prompt.strip()),
            "context_synthesis_retry_status": retry_synthesis_status,
        }
        return rewritten, proposed, attempt

    def _proposal_normalize(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_proposal_normalize`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="proposal_normalize")
        generation = dict(state.get("generation") or {})
        meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        structured = meta.get("structured_output")
        if structured is None:
            raw = generation.get("content") if isinstance(generation.get("content"), str) else ""
            if not raw.strip():
                raw = generation.get("model_raw_text") if isinstance(generation.get("model_raw_text"), str) else ""
            if raw.strip().startswith("{"):
                try:
                    parsed = json.loads(raw)
                    parsed_narrative = ""
                    parsed_runtime_structure = False
                    if isinstance(parsed, dict):
                        narr_summary = parsed.get("narration_summary")
                        legacy_narrative = parsed.get("narrative_response")
                        if isinstance(narr_summary, str) and narr_summary.strip():
                            parsed_narrative = narr_summary.strip()
                        elif isinstance(legacy_narrative, str) and legacy_narrative.strip():
                            parsed_narrative = legacy_narrative.strip()
                        parsed_runtime_structure = any(
                            isinstance(parsed.get(key), list)
                            for key in ("spoken_lines", "action_lines", "initiative_events")
                        ) or str(parsed.get("schema_version") or "").strip() == "runtime_actor_turn_v1"
                    if (
                        isinstance(parsed, dict)
                        and (parsed_narrative or parsed_runtime_structure)
                    ):
                        meta = dict(meta)
                        meta["structured_output"] = parsed
                        generation["metadata"] = meta
                        structured = parsed
                except json.JSONDecodeError:
                    pass
        structured_dict = structured if isinstance(structured, dict) else None
        cleaned, strip_markers = strip_director_overwrites_from_structured_output(structured_dict)
        if cleaned is not None:
            meta = dict(meta)
            meta["structured_output"] = cleaned
            generation["metadata"] = meta
        proposed = structured_output_to_proposed_effects(cleaned)
        if isinstance(cleaned, dict):
            schema_version = str(cleaned.get("schema_version") or "").strip()
            narration_summary = narration_summary_to_plain_str(cleaned.get("narration_summary"))
            narrative_response = str(cleaned.get("narrative_response") or "").strip()
            spoken_count = len([x for x in (cleaned.get("spoken_lines") or []) if isinstance(x, dict)])
            action_count = len([x for x in (cleaned.get("action_lines") or []) if isinstance(x, dict)])
            has_actor_lane_substance = (spoken_count + action_count) > 0
            has_existing_narrative = bool(narration_summary or narrative_response)
            parser_error = (
                generation.get("parser_error")
                or meta.get("langchain_parser_error")
                or meta.get("parser_error")
            )
            transition_pattern = str(state.get("transition_pattern") or "").strip().lower()
            adapter_name = str(meta.get("adapter") or "").strip().lower()
            # LDSS adapters produce their own narration — synthesis must not override them.
            # Configured model fallbacks (gpt-5-nano) produce the same structured format as
            # the primary, so synthesis is valid there. Mock fallback is safe because its
            # structured_output=None → has_actor_lane_substance=False blocks synthesis anyway.
            ldss_active = adapter_name in {"ldss_fallback", "ldss_deterministic"}
            fallback_active = ldss_active
            actor_lane_validation = _actor_lane_validation(state, generation)
            actor_lane_status = str(actor_lane_validation.get("status") or "").strip().lower()
            can_synthesize = (
                schema_version == "runtime_actor_turn_v1"
                and has_actor_lane_substance
                and not has_existing_narrative
                and not _has_usable_narrative_effect(proposed)
                and actor_lane_status in {"approved", "not_applicable"}
                and not parser_error
                and transition_pattern != "diagnostics_only"
                and not fallback_active
                and int(state.get("turn_number") or 0) == 0
            )
            if can_synthesize:
                synthesized = _build_actor_lane_opening_narration(
                    state=state,
                    structured_output=cleaned,
                )
                if synthesized.strip():
                    cleaned = dict(cleaned)
                    cleaned["narration_summary"] = synthesized
                    cleaned["narrative_response"] = synthesized
                    meta = dict(meta)
                    meta["structured_output"] = cleaned
                    meta["narration_summary_synthesized"] = True
                    meta["narration_summary_source"] = "actor_lane_fallback"
                    meta["synthetic_narration_reason"] = (
                        "missing_narration_summary_with_approved_actor_lanes"
                    )
                    generation["metadata"] = meta
                    proposed = structured_output_to_proposed_effects(cleaned)
        if isinstance(cleaned, dict):
            if cleaned.get("primary_responder_id"):
                update["primary_responder_id"] = str(cleaned["primary_responder_id"])
            if cleaned.get("responder_id"):
                update["responder_id"] = str(cleaned["responder_id"])
            if cleaned.get("primary_responder_id") and not update.get("responder_id"):
                update["responder_id"] = str(cleaned["primary_responder_id"])
            secondary = cleaned.get("secondary_responder_ids")
            if (not isinstance(secondary, list) or not secondary) and isinstance(
                cleaned.get("responder_actor_ids"), list
            ):
                secondary = cleaned.get("responder_actor_ids")
            if isinstance(secondary, list):
                update["secondary_responder_ids"] = [str(x).strip() for x in secondary if str(x).strip()]
            spoken = cleaned.get("spoken_lines")
            if isinstance(spoken, list):
                update["spoken_lines"] = list(spoken)
            action = cleaned.get("action_lines")
            if isinstance(action, list):
                update["action_lines"] = list(action)
            initiative = cleaned.get("initiative_events")
            if isinstance(initiative, list):
                update["initiative_events"] = [x for x in initiative if isinstance(x, dict)]
            state_effects = cleaned.get("state_effects")
            if isinstance(state_effects, list):
                update["state_effects"] = [x for x in state_effects if isinstance(x, dict)]
            if cleaned.get("function_type"):
                update["function_type"] = str(cleaned["function_type"])
            if isinstance(cleaned.get("emotional_shift"), dict):
                update["emotional_shift"] = cleaned["emotional_shift"]
            if cleaned.get("social_outcome"):
                update["social_outcome"] = str(cleaned["social_outcome"])
            if cleaned.get("dramatic_direction"):
                update["dramatic_direction"] = str(cleaned["dramatic_direction"])
        fallback_markers = list(state.get("fallback_markers") or [])
        fallback_markers.extend(strip_markers)
        update["generation"] = generation
        update["proposed_state_effects"] = proposed
        update["fallback_markers"] = fallback_markers
        return update

    def _validate_seam(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_validate_seam`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="validate_seam")
        generation = dict(state.get("generation") or {})
        proposed = list(state.get("proposed_state_effects") or [])
        silence = state.get("silence_brevity_decision") if isinstance(state.get("silence_brevity_decision"), dict) else {}

        def _run_validation(
            current_generation: dict[str, Any],
            current_proposed: list[dict[str, Any]],
        ) -> dict[str, Any]:
            narr = extract_proposed_narrative_text(current_proposed)
            meta = current_generation.get("metadata") if isinstance(current_generation.get("metadata"), dict) else {}
            structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else {}
            _lane_val = _actor_lane_validation(state, current_generation)
            actor_lane_sum = {
                "spoken_line_count": len(structured.get("spoken_lines") or []),
                "action_line_count": len(structured.get("action_lines") or []),
                "initiative_event_count": len(structured.get("initiative_events") or []),
                "actor_lane_status": str(_lane_val.get("status") or "not_evaluated").strip().lower(),
            }
            eval_ctx = build_evaluation_context_from_runtime_state(
                module_id=str(state.get("module_id") or ""),
                proposed_narrative=narr,
                selected_scene_function=str(state.get("selected_scene_function") or "establish_pressure"),
                pacing_mode=str(state.get("pacing_mode") or "standard"),
                silence_brevity_decision=dict(silence),
                semantic_move_record=state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else None,
                social_state_record=state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else None,
                character_mind_records=list(state.get("character_mind_records") or [])
                if isinstance(state.get("character_mind_records"), list)
                else [],
                scene_plan_record=state.get("scene_plan_record") if isinstance(state.get("scene_plan_record"), dict) else None,
                prior_continuity_impacts=list(state.get("prior_continuity_impacts") or [])
                if isinstance(state.get("prior_continuity_impacts"), list)
                else [],
                selected_responder_set=list(state.get("selected_responder_set") or [])
                if isinstance(state.get("selected_responder_set"), list)
                else [],
                dramatic_irony_record=state.get("dramatic_irony_record")
                if isinstance(state.get("dramatic_irony_record"), dict)
                else None,
                actor_lane_summary=actor_lane_sum,
            )
            # MVP2: Pass actor_lane_context from state so human-actor enforcement fires
            # before commit. When absent (no solo runtime profile), enforcement is skipped.
            _actor_lane_ctx = state.get("actor_lane_context")
            if not isinstance(_actor_lane_ctx, dict):
                _actor_lane_ctx = None
            _sre = state.get("story_runtime_experience")
            _sre_arg = dict(_sre) if isinstance(_sre, dict) else None
            return run_validation_seam(
                module_id=state.get("module_id") or "",
                proposed_state_effects=current_proposed,
                generation=current_generation if isinstance(current_generation, dict) else {},
                evaluation_context=eval_ctx,
                actor_lane_summary=actor_lane_sum,
                actor_lane_context=_actor_lane_ctx,
                story_runtime_experience=_sre_arg,
                interpreted_input=state.get("interpreted_input")
                if isinstance(state.get("interpreted_input"), dict)
                else None,
                raw_player_input=str(state.get("player_input") or "").strip() or None,
                player_action_frame=state.get("player_action_frame")
                if isinstance(state.get("player_action_frame"), dict)
                else None,
                affordance_resolution=state.get("affordance_resolution")
                if isinstance(state.get("affordance_resolution"), dict)
                else None,
                opening_scene_sequence=state.get("opening_scene_sequence")
                if isinstance(state.get("opening_scene_sequence"), dict)
                else None,
                hard_forbidden_rules=state.get("hard_forbidden_rules")
                if isinstance(state.get("hard_forbidden_rules"), dict)
                else None,
                turn_input_class=state.get("turn_input_class")
                if isinstance(state.get("turn_input_class"), str)
                else None,
                scene_plan_record=state.get("scene_plan_record")
                if isinstance(state.get("scene_plan_record"), dict)
                else None,
                current_scene_id=state.get("current_scene_id")
                if isinstance(state.get("current_scene_id"), str)
                else None,
            )

        validation_eval = _build_runtime_aspect_validation(
            state=state,
            generation=generation,
            proposed_state_effects=proposed,
            outcome=_run_validation(generation, proposed),
        )
        outcome = validation_eval["outcome"]
        turn_number = int(state.get("turn_number") or 0)
        max_attempts = max(0, int(self.max_self_correction_attempts))
        self_correction_attempts: list[dict[str, Any]] = []
        context_synthesis_retry_history: list[dict[str, Any]] = []
        last_retry_context_synthesis_bundle: dict[str, Any] | None = None
        last_validation_feedback: dict[str, Any] | None = None
        # Disable degraded commits for opening turns to prevent silent failures on game start
        allow_degraded = self.allow_degraded_commit_after_retries and turn_number > 1
        retry_loop_exhausted = False
        for attempt_index in range(1, max_attempts + 1):
            actor_lane_validation = validation_eval["actor_lane_validation"]
            decision = decide_playability_recovery(
                turn_number=turn_number,
                attempt_index=attempt_index,
                max_attempts=max_attempts,
                outcome=outcome,
                generation=generation,
                proposed_state_effects=proposed,
                allow_degraded_commit_after_retries=bool(allow_degraded),
                actor_lane_validation=actor_lane_validation,
            )
            if not decision.should_retry:
                if decision.allow_degraded_commit:
                    outcome = degrade_validation_outcome(outcome)
                    validation_eval = _build_runtime_aspect_validation(
                        state=state,
                        generation=generation,
                        proposed_state_effects=proposed,
                        outcome=outcome,
                    )
                    outcome = validation_eval["outcome"]
                break
            failure_reason_before_retry = str(outcome.get("reason") or "").strip()
            trigger_source = "validation"
            if isinstance(outcome.get("runtime_aspect_failure"), dict):
                trigger_source = "runtime_aspect"
            elif isinstance(outcome.get("capability_failure"), dict):
                trigger_source = "capability"
            elif isinstance(outcome.get("scene_energy_failure"), dict):
                trigger_source = "scene_energy"
            elif isinstance(outcome.get("pacing_rhythm_failure"), dict):
                trigger_source = "pacing_rhythm"
            elif isinstance(outcome.get("improvisational_coherence_failure"), dict):
                trigger_source = "improvisational_coherence"
            elif isinstance(outcome.get("information_disclosure_failure"), dict):
                trigger_source = "information_disclosure"
            elif isinstance(outcome.get("dramatic_irony_failure"), dict):
                trigger_source = "dramatic_irony"
            runtime_aspect_failure_before_retry = (
                dict(outcome.get("runtime_aspect_failure"))
                if isinstance(outcome.get("runtime_aspect_failure"), dict)
                else None
            )
            capability_failure_before_retry = (
                dict(outcome.get("capability_failure"))
                if isinstance(outcome.get("capability_failure"), dict)
                else None
            )
            scene_energy_failure_before_retry = (
                dict(outcome.get("scene_energy_failure"))
                if isinstance(outcome.get("scene_energy_failure"), dict)
                else None
            )
            pacing_rhythm_failure_before_retry = (
                dict(outcome.get("pacing_rhythm_failure"))
                if isinstance(outcome.get("pacing_rhythm_failure"), dict)
                else None
            )
            improvisational_failure_before_retry = (
                dict(outcome.get("improvisational_coherence_failure"))
                if isinstance(outcome.get("improvisational_coherence_failure"), dict)
                else None
            )
            information_disclosure_failure_before_retry = (
                dict(outcome.get("information_disclosure_failure"))
                if isinstance(outcome.get("information_disclosure_failure"), dict)
                else None
            )
            dramatic_irony_failure_before_retry = (
                dict(outcome.get("dramatic_irony_failure"))
                if isinstance(outcome.get("dramatic_irony_failure"), dict)
                else None
            )
            validation_feedback = {
                "codes": list(decision.feedback_codes),
                "attempt_index": attempt_index,
                "trigger_source": trigger_source,
                "validation_status_before_retry": outcome.get("status"),
                "failure_reason_before_retry": failure_reason_before_retry,
                "runtime_aspect_failure_before_retry": runtime_aspect_failure_before_retry,
                "capability_failure_before_retry": capability_failure_before_retry,
                "scene_energy_failure_before_retry": scene_energy_failure_before_retry,
                "pacing_rhythm_failure_before_retry": pacing_rhythm_failure_before_retry,
                "improvisational_coherence_failure_before_retry": improvisational_failure_before_retry,
                "information_disclosure_failure_before_retry": information_disclosure_failure_before_retry,
                "dramatic_irony_failure_before_retry": dramatic_irony_failure_before_retry,
                "actor_lane_status_before_retry": actor_lane_validation.get("status")
                if isinstance(actor_lane_validation, dict)
                else None,
            }
            retry_context_synthesis_bundle, retry_context_synthesis_diagnostics, retry_context_synthesis_prompt = (
                self._synthesize_context_for_retry(
                    state,
                    validation_feedback=validation_feedback,
                    attempt_index=attempt_index,
                )
            )
            last_retry_context_synthesis_bundle = retry_context_synthesis_bundle
            last_validation_feedback = validation_feedback
            context_synthesis_retry_history.append(retry_context_synthesis_diagnostics)
            generation, proposed, attempt_record = self._self_correct_generation(
                state,
                generation,
                proposed,
                decision.feedback_codes,
                attempt_index,
                preserve_actor_lanes=decision.preserve_actor_lanes,
                retry_context_synthesis_bundle=retry_context_synthesis_bundle,
                retry_context_synthesis_prompt=retry_context_synthesis_prompt,
            )
            validation_eval = _build_runtime_aspect_validation(
                state=state,
                generation=generation,
                proposed_state_effects=proposed,
                outcome=_run_validation(generation, proposed),
            )
            outcome = validation_eval["outcome"]
            attempt_record = dict(attempt_record)
            attempt_record.update(
                {
                    "trigger_source": trigger_source,
                    "failure_reason_before_retry": failure_reason_before_retry,
                    "runtime_aspect_failure_before_retry": runtime_aspect_failure_before_retry,
                    "capability_failure_before_retry": capability_failure_before_retry,
                    "scene_energy_failure_before_retry": scene_energy_failure_before_retry,
                    "pacing_rhythm_failure_before_retry": pacing_rhythm_failure_before_retry,
                    "improvisational_coherence_failure_before_retry": improvisational_failure_before_retry,
                    "information_disclosure_failure_before_retry": information_disclosure_failure_before_retry,
                    "dramatic_irony_failure_before_retry": dramatic_irony_failure_before_retry,
                    "validation_status_after_retry": outcome.get("status"),
                    "failure_reason_after_retry": outcome.get("reason"),
                    "context_synthesis_retry": retry_context_synthesis_diagnostics,
                    "resolved_failure": (
                        str(outcome.get("status") or "").strip().lower() == "approved"
                        or (
                            bool(failure_reason_before_retry)
                            and str(outcome.get("reason") or "").strip() != failure_reason_before_retry
                        )
                    ),
                }
            )
            self_correction_attempts.append(attempt_record)
        else:
            retry_loop_exhausted = max_attempts > 0
        if retry_loop_exhausted:
            actor_lane_validation = validation_eval["actor_lane_validation"]
            decision = decide_playability_recovery(
                turn_number=turn_number,
                attempt_index=max_attempts + 1,
                max_attempts=max_attempts,
                outcome=outcome,
                generation=generation,
                proposed_state_effects=proposed,
                allow_degraded_commit_after_retries=bool(allow_degraded),
                actor_lane_validation=actor_lane_validation,
            )
            if decision.allow_degraded_commit:
                outcome = degrade_validation_outcome(outcome)
                validation_eval = _build_runtime_aspect_validation(
                    state=state,
                    generation=generation,
                    proposed_state_effects=proposed,
                    outcome=outcome,
                )
                outcome = validation_eval["outcome"]

        reason = str(outcome.get("reason") or "")
        generation_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        if turn_number <= 1 and outcome.get("status") == "rejected" and reason == "dramatic_alignment_narrative_too_short":
            raw = str(generation.get("content") or generation.get("model_raw_text") or "")
            if len(raw.strip()) >= 48 or generation.get("success") is True:
                outcome = degrade_validation_outcome(outcome, reason="opening_leniency_approved")
                validation_eval = _build_runtime_aspect_validation(
                    state=state,
                    generation=generation,
                    proposed_state_effects=proposed,
                    outcome=outcome,
                )
                outcome = validation_eval["outcome"]

        actor_lane_validation = validation_eval["actor_lane_validation"]
        authority_ledger = validation_eval["turn_aspect_ledger"]
        update["generation"] = generation
        update["proposed_state_effects"] = proposed
        update["validation_outcome"] = outcome
        update["actor_lane_validation"] = actor_lane_validation
        update["turn_aspect_ledger"] = authority_ledger
        if context_synthesis_retry_history:
            update["context_synthesis_retry_history"] = context_synthesis_retry_history
            if last_validation_feedback is not None:
                update["validation_feedback"] = last_validation_feedback
            if isinstance(last_retry_context_synthesis_bundle, dict):
                retry_diag = summarize_context_synthesis_for_diagnostics(
                    last_retry_context_synthesis_bundle,
                    used_in_model_prompt=True,
                )
                retry_diag.update(
                    {
                        "resynthesis_count": len(context_synthesis_retry_history),
                        "used_for_self_correction": True,
                        "retry_attempts": context_synthesis_retry_history,
                    }
                )
                update["context_synthesis_bundle"] = last_retry_context_synthesis_bundle
                update["context_synthesis_diagnostics"] = retry_diag
        if isinstance(validation_eval.get("voice_consistency_validation"), dict):
            update["voice_consistency_validation"] = validation_eval["voice_consistency_validation"]
        if isinstance(validation_eval.get("scene_energy_validation"), dict):
            update["scene_energy_validation"] = validation_eval["scene_energy_validation"]
        if isinstance(validation_eval.get("pacing_rhythm_validation"), dict):
            update["pacing_rhythm_validation"] = validation_eval["pacing_rhythm_validation"]
        if isinstance(validation_eval.get("improvisational_coherence_validation"), dict):
            update["improvisational_coherence_validation"] = validation_eval[
                "improvisational_coherence_validation"
            ]
        if isinstance(validation_eval.get("social_pressure_validation"), dict):
            update["social_pressure_validation"] = validation_eval["social_pressure_validation"]
        if isinstance(validation_eval.get("information_disclosure_validation"), dict):
            update["information_disclosure_validation"] = validation_eval[
                "information_disclosure_validation"
            ]
        if isinstance(validation_eval.get("dramatic_irony_validation"), dict):
            update["dramatic_irony_validation"] = validation_eval["dramatic_irony_validation"]
            if isinstance(validation_eval["dramatic_irony_validation"].get("record"), dict):
                update["dramatic_irony_record"] = validation_eval["dramatic_irony_validation"]["record"]
        if isinstance(validation_eval.get("npc_initiative_validation"), dict):
            update["npc_initiative_validation"] = validation_eval["npc_initiative_validation"]
        update["self_correction"] = {
            "attempt_count": len(self_correction_attempts),
            "attempts": self_correction_attempts,
        }
        geo = outcome.get("dramatic_effect_gate_outcome")
        if isinstance(geo, dict):
            update["dramatic_effect_outcome"] = geo

        # Reconcile the model's proposed responder fields against the
        # director's selected responder set. Out-of-scope actors are dropped
        # so downstream commit / rendering never carries an actor the scene
        # never authorized, and the reconciliation outcome is published onto
        # state for the governance surface.
        reconciliation = _reconcile_model_responders(state, generation)

        # Prune out-of-scope actors from structured output lanes (spoken_lines, action_lines)
        # to prevent out-of-scope actors from flowing through to commit and rendering
        out_of_scope = reconciliation.get("dropped_out_of_scope_actors") or []
        pruning_stats = _prune_out_of_scope_actor_lanes(generation, out_of_scope)
        reconciliation.update(pruning_stats)

        update["responder_reconciliation"] = reconciliation
        primary_responder = reconciliation.get("effective_responder_id")
        if primary_responder:
            update["responder_id"] = primary_responder
        elif reconciliation.get("dropped_out_of_scope_count"):
            # The model's proposal was entirely out of scope. Clear the prior
            # top-level ``responder_id`` so planner-truth extraction reflects
            # that the model's responder claim was rejected.
            update["responder_id"] = ""
        return update

    def _commit_seam(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_commit_seam`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="commit_seam")
        validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
        proposed = list(state.get("proposed_state_effects") or [])
        candidate_deltas = state.get("candidate_deltas")
        state_delta_boundary = state.get("state_delta_boundary")
        committed = run_commit_seam(
            module_id=state.get("module_id") or "",
            validation_outcome=validation,
            proposed_state_effects=proposed,
            candidate_deltas=candidate_deltas if isinstance(candidate_deltas, list) else None,
            state_delta_boundary=state_delta_boundary if isinstance(state_delta_boundary, dict) else None,
            player_action_frame=state.get("player_action_frame")
            if isinstance(state.get("player_action_frame"), dict)
            else None,
        )
        continuity: list[dict[str, Any]] = []
        if (
            _runtime_governance_hook_enabled(state, "module_continuity_impacts_on_commit_v1")
            and validation.get("status") == "approved"
            and committed.get("commit_applied")
        ):
            continuity = build_goc_continuity_impacts_on_commit(
                module_id=str(state.get("module_id") or ""),
                selected_scene_function=str(state.get("selected_scene_function") or ""),
                proposed_state_effects=proposed,
                social_outcome=state.get("social_outcome"),
                emotional_shift=state.get("emotional_shift") if isinstance(state.get("emotional_shift"), dict) else None,
                dramatic_direction=state.get("dramatic_direction"),
            )
        action_authority = (
            committed.get("player_action_authority")
            if isinstance(committed.get("player_action_authority"), dict)
            else {}
        )
        committed_environment_state: dict[str, Any] | None = None
        if bool(committed.get("commit_applied")) and bool(action_authority.get("player_action_committed")):
            committed_environment_state = apply_action_to_environment_state(
                environment_state=state.get("environment_state")
                if isinstance(state.get("environment_state"), dict)
                else None,
                environment_model=state.get("environment_model")
                if isinstance(state.get("environment_model"), dict)
                else None,
                player_action_frame=state.get("player_action_frame")
                if isinstance(state.get("player_action_frame"), dict)
                else None,
                affordance_resolution=state.get("affordance_resolution")
                if isinstance(state.get("affordance_resolution"), dict)
                else None,
                local_context_transition=state.get("local_context_transition")
                if isinstance(state.get("local_context_transition"), dict)
                else None,
                narrator_consequence_plan=state.get("narrator_consequence_plan")
                if isinstance(state.get("narrator_consequence_plan"), dict)
                else None,
                actor_lane_context=state.get("actor_lane_context")
                if isinstance(state.get("actor_lane_context"), dict)
                else None,
                turn_number=int(state.get("turn_number") or 0),
            )
            committed["environment_state_after"] = committed_environment_state
        validation_status = str(validation.get("status") or "").strip().lower()
        commit_applied = bool(committed.get("commit_applied"))
        commit_status = "partial"
        if (validation_status == "approved" and commit_applied) or (
            validation_status != "approved" and not commit_applied
        ):
            commit_status = "passed"
        commit_failure_reason = None
        state_delta_rejection = (
            committed.get("state_delta_rejection")
            if isinstance(committed.get("state_delta_rejection"), dict)
            else {}
        )
        if state_delta_rejection:
            commit_status = "failed"
            commit_failure_reason = str(
                state_delta_rejection.get("error_code") or "state_delta_boundary_violation"
            )
        if validation_status == "approved" and not commit_applied and not state_delta_rejection:
            commit_failure_reason = "approved_turn_without_committed_effects"
        ledger_aspects = (
            (state.get("turn_aspect_ledger") or {}).get("turn_aspect_ledger")
            if isinstance(state.get("turn_aspect_ledger"), dict)
            else {}
        )
        cap_aspect = (
            ledger_aspects.get(ASPECT_CAPABILITY_SELECTION)
            if isinstance(ledger_aspects, dict)
            else {}
        )
        cap_selected = cap_aspect.get("selected") if isinstance(cap_aspect, dict) and isinstance(cap_aspect.get("selected"), dict) else {}
        cap_actual = cap_aspect.get("actual") if isinstance(cap_aspect, dict) and isinstance(cap_aspect.get("actual"), dict) else {}
        commit_ledger = set_aspect_record(
            state.get("turn_aspect_ledger") if isinstance(state.get("turn_aspect_ledger"), dict) else {},
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status=commit_status,
                expected={
                    "validation_status": validation.get("status"),
                    "commit_applies_only_after_validation": True,
                },
                actual={
                    "commit_applied": commit_applied,
                    "commit_lane": committed.get("commit_lane"),
                    "committed_effect_count": len(committed.get("committed_effects") or []),
                    "player_action_committed": action_authority.get("player_action_committed"),
                    "player_speech_committed": action_authority.get("player_speech_committed"),
                    "affordance_status": action_authority.get("affordance_status"),
                    "action_commit_status": action_authority.get("action_commit_status"),
                    "validation_rejection_not_committed": (
                        validation_status != "approved" and not commit_applied
                    ),
                    "deliberately_not_committed_failure": (
                        validation.get("reason") if validation_status != "approved" else None
                    ),
                    "selected_capabilities": cap_selected.get("selected_capabilities"),
                    "realized_capabilities": cap_actual.get("realized_capabilities"),
                    "forbidden_capability_realized": cap_actual.get("forbidden_capability_realized"),
                    "state_delta_rejection": state_delta_rejection,
                },
                reasons=[commit_failure_reason] if commit_failure_reason else [],
                source="runtime",
                failure_class=(
                    "hard_contract_failure"
                    if state_delta_rejection
                    else "observability_gap"
                    if commit_failure_reason
                    else None
                ),
                failure_reason=commit_failure_reason,
            ),
        )
        update["committed_result"] = committed
        update["continuity_impacts"] = continuity
        if committed_environment_state:
            update["environment_state"] = committed_environment_state
            update["environment_transition"] = {
                "contract": "environment_transition.v1",
                "committed": True,
                "source": "commit_seam",
                "last_environment_event": (
                    committed_environment_state.get("last_environment_events") or [None]
                )[-1],
            }
        update["turn_aspect_ledger"] = commit_ledger
        return update

    def _render_visible(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_render_visible`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        update = _track(state, node_name="render_visible")
        generation = dict(state.get("generation") or {})
        if "content" not in generation and generation.get("model_raw_text"):
            generation["content"] = generation["model_raw_text"]
        committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}
        validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
        tp = "diagnostics_only"
        if state.get("graph_errors"):
            tp = "diagnostics_only"
        elif committed.get("commit_applied"):
            tp = "hard"
        elif validation.get("status") == "approved":
            tp = "soft"
        elif "fallback_model" in (state.get("nodes_executed") or []):
            tp = "diagnostics_only"
        yslice = state.get("goc_yaml_slice") if isinstance(state.get("goc_yaml_slice"), dict) else {}
        sg = yslice.get("scene_guidance") if isinstance(yslice.get("scene_guidance"), dict) else {}
        responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        primary = responders[0] if responders and isinstance(responders[0], dict) else {}
        actor_id = str(primary.get("actor_id") or "")
        actor_reason = str(primary.get("reason") or "")
        actor_lane_ctx = state.get("actor_lane_context") if isinstance(state.get("actor_lane_context"), dict) else {}
        hid = str(actor_lane_ctx.get("human_actor_id") or "").strip()
        spr = str(actor_lane_ctx.get("selected_player_role") or "").strip()
        pri = str(actor_id or state.get("primary_responder_id") or "").strip()
        char_snippet = goc_character_profile_snippet(
            actor_id=actor_id,
            yaml_slice=yslice,
            scene_id=state.get("current_scene_id") or "",
        )
        guidance_snip = scene_guidance_snippets(
            scene_guidance=sg,
            scene_id=state.get("current_scene_id") or "",
        )
        proposed_fx = list(state.get("proposed_state_effects") or [])
        prop_narr = extract_proposed_narrative_text(proposed_fx)
        bundle, vis_markers = run_visible_render(
            module_id=state.get("module_id") or "",
            committed_result=committed,
            validation_outcome=validation,
            generation=generation,
            transition_pattern=tp,
            live_player_truth_surface=bool(state.get("live_player_truth_surface")),
            render_context={
                "turn_number": int(state.get("turn_number") or 0),
                "turn_input_class": str(state.get("turn_input_class") or ""),
                "pacing_mode": state.get("pacing_mode") or "",
                "silence_brevity_decision": state.get("silence_brevity_decision")
                if isinstance(state.get("silence_brevity_decision"), dict)
                else {},
                "current_scene_id": state.get("current_scene_id") or "",
                "scene_guidance": sg,
                "proposed_narrative_excerpt": prop_narr,
                "responder_actor_id": actor_id,
                "responder_reason": actor_reason,
                "character_profile_snippet": char_snippet,
                "scene_guidance_snippets": guidance_snip,
                "carry_forward_tension_notes": (state.get("prior_planner_truth") or {}).get("carry_forward_tension_notes"),
                "player_input": str(state.get("player_input") or "").strip(),
                "human_actor_id": hid,
                "selected_player_role": spr,
                "primary_responder_id": pri,
                "runtime_projection": {
                    "human_actor_id": hid,
                    "selected_player_role": spr,
                    "npc_actor_ids": list(actor_lane_ctx.get("npc_actor_ids") or []),
                },
                "environment_render_context": build_environment_render_context(
                    environment_state=state.get("environment_state")
                    if isinstance(state.get("environment_state"), dict)
                    else None,
                    environment_model=state.get("environment_model")
                    if isinstance(state.get("environment_model"), dict)
                    else None,
                ),
                # C3: Reaction order divergence for render support surfacing (computed from realized output)
                **_compute_reaction_order_divergence_for_render(state),
            },
        )
        update["generation"] = generation
        update["visible_output_bundle"] = bundle
        update["visibility_class_markers"] = vis_markers
        update["transition_pattern"] = tp
        return update

    def _package_output(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """``_package_output`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        
        Returns:
            RuntimeTurnState:
                Returns a value of type ``RuntimeTurnState``; see the function body for structure, error paths, and sentinels.
        """
        from ai_stack.langgraph_runtime_package_output import package_runtime_graph_output

        return package_runtime_graph_output(
            state, graph_name=self.graph_name, graph_version=self.graph_version
        )
