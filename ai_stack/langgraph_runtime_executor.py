"""
``ai_stack/langgraph_runtime_executor.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger(__name__)

from ai_stack.langgraph_imports import END, StateGraph

from story_runtime_core.adapters import BaseModelAdapter
from story_runtime_core.model_registry import ModelRegistry, RoutingPolicy
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
from ai_stack.operational_profile import build_operational_cost_hints_for_runtime_graph
from ai_stack.runtime_turn_contracts import (
    ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK,
    ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
    ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    RAW_FALLBACK_BYPASS_NOTE,
)
from ai_stack.version import AI_STACK_SEMANTIC_VERSION, RUNTIME_TURN_GRAPH_VERSION
from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_frozen_vocab import expand_goc_actor_id_aliases
from ai_stack.goc_roadmap_semantic_surface import ROUTING_LABELS
from ai_stack.goc_yaml_authority import (
    detect_builtin_yaml_title_conflict,
    goc_character_profile_snippet,
    load_goc_canonical_module_yaml,
    load_goc_yaml_slice_bundle,
    scene_guidance_snippets,
)
from ai_stack.goc_scene_identity import GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY
from ai_stack.character_mind_goc import build_character_mind_records_for_goc
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


_GOC_FALLBACK_CAST_KEYS: tuple[str, ...] = ("veronique", "michel", "annette", "alain")


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


def _derive_active_character_keys(
    *,
    yaml_slice: dict[str, Any] | None,
    primary_responder: dict[str, Any],
    module_id: str,
) -> list[str]:
    """Compute the active cast for character-mind construction from module data.

    Resolution is data-driven: keys declared in ``yaml_slice.characters`` are
    preferred. They are reordered so the primary responder's key — matched
    either by direct key equality or by actor_id substring — comes first, with
    the remaining keys following YAML declaration order. When a module
    publishes no YAML characters block this helper falls back to the known
    God of Carnage cast so the currently-supported module keeps working.
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
        if (module_id or "").strip().lower() in {"god_of_carnage", "goc"}:
            yaml_keys = list(_GOC_FALLBACK_CAST_KEYS)
        else:
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
    allowed_actor_ids = sorted({actor_id for actor_id in responder_ids if actor_id and actor_id not in forbidden_actor_ids})

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
    semantic = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}
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
        "pacing_mode": state.get("pacing_mode"),
        "silence_brevity_decision": state.get("silence_brevity_decision")
        if isinstance(state.get("silence_brevity_decision"), dict)
        else {},
        "semantic_interpretation": {
            "primary_move_type": semantic.get("move_type"),
            "secondary_move_type": semantic.get("secondary_move_type"),
            "secondary_dramatic_features": semantic.get("secondary_dramatic_features")
            if isinstance(semantic.get("secondary_dramatic_features"), list)
            else [],
            "ranked_move_candidates": ranked_semantic_compact,
        },
        "character_mind_records": compact_minds,
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
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("goc_resolve_canonical_content", self._goc_resolve_canonical_content)
        graph.add_node("director_assess_scene", self._director_assess_scene)
        graph.add_node("director_select_dramatic_parameters", self._director_select_dramatic_parameters)
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
        graph.add_edge("interpret_input", "retrieve_context")
        graph.add_edge("retrieve_context", "goc_resolve_canonical_content")
        graph.add_edge("goc_resolve_canonical_content", "director_assess_scene")
        graph.add_edge("director_assess_scene", "director_select_dramatic_parameters")
        graph.add_edge("director_select_dramatic_parameters", "assemble_model_context")
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
        prior_planner_truth: dict[str, Any] | None = None,
        turn_number: int | None = None,
        turn_id: str | None = None,
        turn_timestamp_iso: str | None = None,
        turn_initiator_type: str | None = None,
        turn_input_class: str | None = None,
        turn_execution_mode: str | None = None,
        live_player_truth_surface: bool | None = None,
        actor_lane_context: dict[str, Any] | None = None,
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
            prior_planner_truth: bounded committed planner-truth snapshot used
                to bias retrieval toward continuity-relevant precedents.
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
        }
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
        if prior_planner_truth:
            initial_state["prior_planner_truth"] = dict(prior_planner_truth)
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
        update = _track(state, node_name="interpret_input")
        update["interpreted_input"] = interp_dict
        move_class = str(interp_dict.get("kind") or "unknown")
        update["interpreted_move"] = {
            "player_intent": str(interp_dict.get("intent") or "unspecified"),
            "move_class": move_class,
        }
        update["task_type"] = task_type
        if "turn_input_class" not in state or not state.get("turn_input_class"):
            update["turn_input_class"] = move_class
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
        update = _track(state, node_name="retrieve_context")
        update["retrieval"] = retrieval
        update["context_text"] = context_text
        update["model_prompt"] = prompt
        if capability_audit:
            update["capability_audit"] = capability_audit
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
                update["goc_canonical_yaml"] = yaml_mod
                update["goc_yaml_slice"] = load_goc_yaml_slice_bundle()
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
        )
        mind_models = build_character_mind_records_for_goc(
            yaml_slice=yslice,
            active_character_keys=active_keys,
            current_scene_id=state.get("current_scene_id") or "",
            module_id=str(state.get("module_id") or ""),
        )
        mind_dicts = [m.to_runtime_dict() for m in mind_models]
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
        update["scene_plan_record"] = scene_plan.to_runtime_dict()
        return update

    def _assemble_model_context(self, state: RuntimeTurnState) -> RuntimeTurnState:
        """Attach post-director runtime state to the model-visible prompt."""
        prompt = str(state.get("model_prompt") or state.get("player_input") or "")
        dramatic_packet = _build_dramatic_generation_packet(state)
        lines: list[str] = ["Director runtime state (authoritative, model-visible):"]

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

        responders = state.get("selected_responder_set") if isinstance(state.get("selected_responder_set"), list) else []
        if responders:
            lines.append("Eligible Responders:")
            for responder in responders[:4]:
                if not isinstance(responder, dict):
                    continue
                actor = str(responder.get("actor_id") or responder.get("responder_id") or "?")
                reason = str(responder.get("reason") or responder.get("responder_type") or "")
                lines.append(f"- {actor}: {reason[:180]}")

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

        prior = state.get("prior_continuity_impacts") if isinstance(state.get("prior_continuity_impacts"), list) else []
        if prior:
            lines.append("Continuity Constraints:")
            for impact in prior[:4]:
                if isinstance(impact, dict):
                    cls = str(impact.get("class") or impact.get("continuity_class") or "")
                    desc = str(impact.get("description") or impact.get("summary") or impact.get("note") or "")
                    lines.append(f"- {cls}: {desc[:180]}")

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

        lines.append("Dramatic Generation Packet (authoritative JSON):")
        lines.append(json.dumps(dramatic_packet, sort_keys=True))
        lines.append(
            "Generation directive: produce actor-level exchange (spoken_lines/action_lines/initiative_events) "
            "aligned with selected_scene_function, responder scope, actor lane boundary, pacing, and continuity constraints."
        )

        update = _track(state, node_name="assemble_model_context")
        update["model_prompt"] = f"{prompt}\n\n" + "\n".join(lines)
        update["dramatic_generation_packet"] = dramatic_packet
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
        update = _track(state, node_name="invoke_model", outcome=outcome)
        update["generation"] = generation
        update["fallback_needed"] = bool(generation["error"] or generation["success"] is False)
        if update["fallback_needed"]:
            _log.warning("Primary model invocation failed: provider=%s error=%s", provider or "unknown", generation.get("error") or "unknown")
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
        runtime_result = _invoke_runtime_adapter_with_langchain(
            adapter=adapter,
            player_input=state["player_input"],
            interpreted_input=state.get("interpreted_input", {}) if isinstance(state.get("interpreted_input"), dict) else {},
            retrieval_context=state.get("context_text"),
            timeout_seconds=float(getattr(spec, "timeout_seconds", state.get("selected_timeout", 10.0)) or 10.0),
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
                "dramatic_generation_packet_included": isinstance(
                    state.get("dramatic_generation_packet"), dict
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
        rewritten["fallback_used"] = bool(generation.get("fallback_used")) or (
            bool(selected_mid) and bool(candidate_mid) and candidate_mid != selected_mid
        )
        rewritten["metadata"] = {
            **call.metadata,
            "langchain_prompt_used": True,
            "langchain_parser_error": runtime_result.parser_error,
            "structured_output": parsed_structured,
            "adapter_invocation_mode": ADAPTER_INVOCATION_LANGCHAIN_PRIMARY,
            "self_correction_attempt_index": attempt_index,
            "self_correction_feedback_codes": list(feedback_codes),
            "self_correction_candidate_model": candidate_mid,
            "dramatic_generation_packet_included": isinstance(
                state.get("dramatic_generation_packet"), dict
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
            actor_lane_sum = {
                "spoken_line_count": len(structured.get("spoken_lines") or []),
                "action_line_count": len(structured.get("action_lines") or []),
                "initiative_event_count": len(structured.get("initiative_events") or []),
                "actor_lane_status": "not_evaluated",
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
                actor_lane_summary=actor_lane_sum,
            )
            # MVP2: Pass actor_lane_context from state so human-actor enforcement fires
            # before commit. When absent (no solo runtime profile), enforcement is skipped.
            _actor_lane_ctx = state.get("actor_lane_context")
            if not isinstance(_actor_lane_ctx, dict):
                _actor_lane_ctx = None
            return run_validation_seam(
                module_id=state.get("module_id") or "",
                proposed_state_effects=current_proposed,
                generation=current_generation if isinstance(current_generation, dict) else {},
                evaluation_context=eval_ctx,
                actor_lane_summary=actor_lane_sum,
                actor_lane_context=_actor_lane_ctx,
            )

        outcome = _run_validation(generation, proposed)
        turn_number = int(state.get("turn_number") or 0)
        max_attempts = max(0, int(self.max_self_correction_attempts))
        self_correction_attempts: list[dict[str, Any]] = []
        # Disable degraded commits for opening turns to prevent silent failures on game start
        allow_degraded = self.allow_degraded_commit_after_retries and turn_number > 1
        for attempt_index in range(1, max_attempts + 1):
            actor_lane_validation = _actor_lane_validation(state, generation)
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
                break
            generation, proposed, attempt_record = self._self_correct_generation(
                state,
                generation,
                proposed,
                decision.feedback_codes,
                attempt_index,
                preserve_actor_lanes=decision.preserve_actor_lanes,
            )
            self_correction_attempts.append(attempt_record)
            outcome = _run_validation(generation, proposed)

        reason = str(outcome.get("reason") or "")
        generation_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
        if turn_number <= 1 and outcome.get("status") == "rejected" and reason == "dramatic_alignment_narrative_too_short":
            raw = str(generation.get("content") or generation.get("model_raw_text") or "")
            if len(raw.strip()) >= 48 or generation.get("success") is True:
                outcome = degrade_validation_outcome(outcome, reason="opening_leniency_approved")

        actor_lane_validation = _actor_lane_validation(state, generation)
        if (
            actor_lane_validation.get("status") == "rejected"
            and outcome.get("status") == "approved"
        ):
            outcome = {
                **outcome,
                "status": "rejected",
                "reason": actor_lane_validation.get("reason") or "actor_lane_validation_rejected",
                "actor_lane_validation": actor_lane_validation,
            }
        else:
            outcome = {
                **outcome,
                "actor_lane_validation": actor_lane_validation,
            }

        update["generation"] = generation
        update["proposed_state_effects"] = proposed
        update["validation_outcome"] = outcome
        update["actor_lane_validation"] = actor_lane_validation
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
        committed = run_commit_seam(
            module_id=state.get("module_id") or "",
            validation_outcome=validation,
            proposed_state_effects=proposed,
        )
        continuity: list[dict[str, Any]] = []
        if (
            state.get("module_id") == GOC_MODULE_ID
            and validation.get("status") == "approved"
            and committed.get("commit_applied")
        ):
            continuity = build_goc_continuity_impacts_on_commit(
                module_id=GOC_MODULE_ID,
                selected_scene_function=str(state.get("selected_scene_function") or ""),
                proposed_state_effects=proposed,
                social_outcome=state.get("social_outcome"),
                emotional_shift=state.get("emotional_shift") if isinstance(state.get("emotional_shift"), dict) else None,
                dramatic_direction=state.get("dramatic_direction"),
            )
        update["committed_result"] = committed
        update["continuity_impacts"] = continuity
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
