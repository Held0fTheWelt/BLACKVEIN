"""MCP handlers for projection-test orchestration and Langfuse trace verification."""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from ai_stack.langfuse_evaluator_catalog import (
    BACKEND_TURN_ROOT_TRACE_NAME,
    JUDGE_DISPLAY_SHORT as _JUDGE_DISPLAY_SHORT,
    JUDGE_TO_REPAIR_CARD as _JUDGE_TO_REPAIR_CARD,
    LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE,
    LANGFUSE_TURN_GENERATION_FILTER_BUNDLE,
    LEGACY_JUDGE_ISSUE_TOKENS as _LEGACY_JUDGE_ISSUE_TOKENS,
    LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
    MATRIX_JUDGE_COLUMN_KEYS as _MATRIX_JUDGE_COLUMN_KEYS,
    OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
    TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
    WORLD_ENGINE_TURN_TRACE_NAME,
    WOS_CATEGORICAL_JUDGES_ORDER,
    WOS_JUDGE_ISSUE_CATEGORIES as _WOS_JUDGE_ISSUE_CATEGORIES,
    build_llm_judge_interpretation as _build_llm_judge_interpretation,
    category_severity as _category_severity,
    get_categorical_evaluator_spec as _get_categorical_evaluator_spec,
    judge_names_for_scope as _judge_names_for_scope,
    normalize_judge_category_label as _normalize_judge_category_label,
)
from ai_stack.npc_agency_claim_readiness import assess_npc_agency_claim_readiness
from tools.mcp_server.config import Config
from tools.mcp_server.langfuse_tracing import McpLangfuseTracer


def _to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return _to_plain(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_plain(vars(value))
        except Exception:
            pass
    return str(value)


def _extract_scores(raw_trace: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    score_rows = raw_trace.get("scores")
    if isinstance(score_rows, list):
        for row in score_rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            out[name] = row.get("value")
    return out


def _is_judge_score(name: str) -> bool:
    return name.endswith("_judge")


def _extract_judge_category_from_row(row: dict[str, Any]) -> str | None:
    """Resolve categorical label from Langfuse score row metadata (API shape varies)."""
    row_meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    for key in (
        "category",
        "label",
        "selectedCategory",
        "selected_category",
        "valueCategory",
        "value_category",
    ):
        if key not in row_meta:
            continue
        v = row_meta.get(key)
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    cats = row_meta.get("categories")
    if isinstance(cats, list):
        non_empty = [str(c).strip() for c in cats if str(c).strip()]
        if len(non_empty) == 1:
            return non_empty[0]
    if isinstance(cats, str) and cats.strip():
        return cats.strip()
    matched = row_meta.get("matched_categories")
    if isinstance(matched, list) and len(matched) == 1:
        s = str(matched[0]).strip()
        if s:
            return s
    return None


def _normalize_judge_category_for_issue_check(judge_name: str, category: str | None) -> str | None:
    """Map legacy evaluator labels to current rubric tokens (case-insensitive)."""
    mapped = _normalize_judge_category_label(judge_name, category)
    if not mapped:
        return None
    return str(mapped).strip()


def _judge_category_triggers_issue(judge_name: str, category: str | None) -> bool:
    if not category:
        return False
    normalized = _normalize_judge_category_for_issue_check(judge_name, category)
    if not normalized:
        return False
    low = normalized.strip().lower()
    spec = _WOS_JUDGE_ISSUE_CATEGORIES.get(judge_name)
    if spec is not None:
        return low in spec
    return low in _LEGACY_JUDGE_ISSUE_TOKENS


def _judge_score_coverage_gaps(*, is_opening: bool, judge_scores: dict[str, Any]) -> list[dict[str, Any]]:
    expected = (
        _judge_names_for_scope("opening_generation")
        if is_opening
        else _judge_names_for_scope("turn_generation")
    )
    present = {str(k) for k in judge_scores if str(k).endswith("_judge")}
    gaps: list[dict[str, Any]] = []
    for name in expected:
        if name not in present:
            gaps.append(
                {
                    "evaluator": name,
                    "gap_kind": "missing_score_row",
                    "note": (
                        "Observability / evaluator coverage gap — not a deterministic runtime failure. "
                        "Attach or backfill Langfuse scores if this rubric should be tracked."
                    ),
                }
            )
    return gaps


def _evaluator_column_metadata() -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for jname, col_key in _MATRIX_JUDGE_COLUMN_KEYS.items():
        spec = _get_categorical_evaluator_spec(jname)
        if spec is None:
            continue
        meta[col_key] = {
            "evaluator": jname,
            "evaluator_group": spec.evaluator_group,
            "qualitative_only": spec.qualitative_only,
            "runtime_gate": spec.runtime_gate,
            "suggested_repair_area": spec.repair_card,
        }
    return meta


def _extract_scores_split(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split trace scores into (deterministic_gates, judge_scores).

    Deduplicates by name (first occurrence wins). Judge scores carry
    category and reasoning extracted from score row metadata/comment.
    """
    det: dict[str, Any] = {}
    judge: dict[str, Any] = {}
    score_rows = raw_trace.get("scores")
    if not isinstance(score_rows, list):
        return det, judge
    for row in score_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        value = row.get("value")
        if _is_judge_score(name):
            if name in judge:
                continue
            comment = str(row.get("comment") or "").strip()
            category = _extract_judge_category_from_row(row)
            judge[name] = {"value": value, "category": category, "reasoning": comment or None}
        else:
            if name in det:
                continue
            det[name] = value
    return det, judge


def _extract_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = raw_trace.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


# ---------------------------------------------------------------------------
# WoS evidence extraction helpers
# ---------------------------------------------------------------------------

def _coerce_dict_or_json(value: Any) -> dict[str, Any]:
    """Return dict from value; parse JSON if it's a string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return {}


def _get_observations(raw_trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Return observations list, normalising each entry to a plain dict."""
    raw_obs = raw_trace.get("observations") or []
    result: list[dict[str, Any]] = []
    for o in raw_obs:
        if isinstance(o, dict):
            result.append(o)
        elif hasattr(o, "model_dump"):
            try:
                d = o.model_dump()
                if isinstance(d, dict):
                    result.append(d)
            except Exception:
                pass
    return result


def _find_observation_by_name(
    observations: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    for obs in observations:
        if obs.get("name") == name:
            return obs
    return None


def _parse_status_tokens(status_message: str) -> dict[str, str]:
    """Parse 'key=value ...' tokens from a Langfuse statusMessage string."""
    result: dict[str, str] = {}
    for m in re.finditer(r"(\w+)=([^\s]+)", str(status_message or "")):
        result[m.group(1).lower()] = m.group(2).strip()
    return result


def _first_score_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    """Return metadata from the first score row that has a non-empty metadata dict.

    All scores in a trace share the same ``score_metadata_base`` (session_id,
    selected_player_role, human_actor_id, final_adapter, quality_class, etc.)
    so any score entry is an equally valid source.
    """
    for row in (raw_trace.get("scores") or []):
        if not isinstance(row, dict):
            continue
        meta = _coerce_dict_or_json(row.get("metadata"))
        if meta:
            return meta
    return {}


def _is_opening_trace(raw_trace: dict[str, Any]) -> bool:
    """Return True when this trace is a turn-0 (opening) trace.

    Detection order (first match wins):
    1. trace.name == "world-engine.session.create"
    2. Any score row has metadata.turn_number == 0
    3. trace.metadata.turn_number == 0
    """
    trace_name = str(raw_trace.get("name") or "").strip()
    if trace_name == "world-engine.session.create":
        return True
    for row in (raw_trace.get("scores") or []):
        if not isinstance(row, dict):
            continue
        row_meta = _coerce_dict_or_json(row.get("metadata"))
        try:
            if int(row_meta.get("turn_number", -1)) == 0:
                return True
        except (TypeError, ValueError):
            pass
    top_meta = _extract_metadata(raw_trace)
    try:
        if int(top_meta.get("turn_number", -1)) == 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _live_opening_value(
    det_scores: dict[str, Any],
    raw_trace: dict[str, Any],
) -> float | str:
    """Return live_opening_contract_pass as float, or "not_applicable" for turn-1+ traces.

    Rules:
    - Score present (0.0 or 1.0) → return as float regardless of turn.
    - Score absent on opening trace (turn 0) → 0.0 (missing = gate fail).
    - Score absent on non-opening trace (turn 1+) → "not_applicable".
    """
    val = det_scores.get("live_opening_contract_pass")
    if val is not None:
        return float(val)
    if _is_opening_trace(raw_trace):
        return 0.0
    return "not_applicable"


def _sif(ev: dict[str, Any], field: str, value: Any) -> None:
    """Set ev[field] = value only if the field is currently None."""
    if value is not None and ev.get(field) is None:
        ev[field] = value


def _extract_normalized_wos_evidence(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract WoS evidence from a Langfuse trace using a four-source priority chain.

    Priority (first non-None wins per field):
      1. trace.output.path_summary (or trace.output if it IS the path_summary)
      2. story.graph.path_summary observation (output → input → metadata)
      3. Score metadata (score_metadata_base carries player-role, adapter, quality)
      4. Turn span metadata (backend.turn.execute / world-engine.turn.execute)
      5. trace.metadata (top-level, usually only trace_origin/execution_tier)
      6. world-engine.session.create statusMessage (key=value fallback)

    Returns (evidence_dict, evidence_sources_dict).
    """
    obs_list = _get_observations(raw_trace)

    ev: dict[str, Any] = {
        "trace_id": str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip(),
        "session_id": None,
        "selected_player_role": None,
        "human_actor_id": None,
        "npc_actor_ids": [],
        "trace_origin": None,
        "execution_tier": None,
        "canonical_player_flow": None,
        "final_adapter": None,
        "quality_class": None,
        "fallback_reason": None,
    }

    path_summary_source = "missing"
    score_source = "missing"
    status_message_fallback_used = False

    _PS_FIELDS = {
        "session_id", "selected_player_role", "human_actor_id", "npc_actor_ids",
        "canonical_turn_id", "runtime_profile_id", "turn_aspect_ledger_present",
        "trace_origin", "execution_tier", "canonical_player_flow",
        "final_adapter", "quality_class", "fallback_reason",
        "first_actor_block_index",
        "narrator_block_count",
        "structured_narration_summary_kind",
        "opening_narration_normalized",
        "opening_narration_source",
        "opening_narration_beat_count",
        "narration_summary_input_kind",
    }
    _CLASSIFICATION_FIELDS = {"trace_origin", "execution_tier", "canonical_player_flow"}

    def _apply(src: dict[str, Any], fields: set[str]) -> None:
        for f in fields:
            _sif(ev, f, src.get(f))

    # --- Source 1: trace.output ---
    trace_output = _coerce_dict_or_json(raw_trace.get("output"))
    if trace_output:
        nested_ps = _coerce_dict_or_json(trace_output.get("path_summary"))
        direct_ps = (
            trace_output
            if trace_output.get("contract") == "story_runtime_path_observability.v1"
            else {}
        )
        ps = nested_ps or direct_ps
        if ps:
            path_summary_source = "trace.output"
            _apply(ps, _PS_FIELDS)
        # Classification fields may be present even without a full path_summary
        _apply(trace_output, _CLASSIFICATION_FIELDS)

    # --- Source 2: story.graph.path_summary observation ---
    ps_obs = _find_observation_by_name(obs_list, "story.graph.path_summary")
    if ps_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(ps_obs.get(block_key))
            if block:
                if path_summary_source == "missing":
                    path_summary_source = f"observation.{block_key}"
                _apply(block, _PS_FIELDS)

    # --- Source 3: score metadata (score_metadata_base carries WoS-specific fields) ---
    score_meta = _first_score_metadata(raw_trace)
    if score_meta:
        score_source = "trace.scores"
        _apply(score_meta, {
            "session_id", "selected_player_role", "human_actor_id",
            "final_adapter", "quality_class", "fallback_reason",
            "first_actor_block_index",
            "narrator_block_count",
            "structured_narration_summary_kind",
            "opening_narration_normalized",
            "opening_narration_source",
            "opening_narration_beat_count",
            "narration_summary_input_kind",
            "opening_shape_subgates",
            "opening_shape_failure_reasons",
            "scene_block_summary",
        })

    # --- Source 4: turn span metadata ---
    for span_name in ("backend.turn.execute", "world-engine.turn.execute"):
        span_obs = _find_observation_by_name(obs_list, span_name)
        if span_obs:
            for block_key in ("metadata", "output", "input"):
                block = _coerce_dict_or_json(span_obs.get(block_key))
                _apply(block, _CLASSIFICATION_FIELDS | {"session_id"})

    # --- Source 5: trace.metadata (top-level) ---
    trace_meta = _extract_metadata(raw_trace)
    _apply(trace_meta, _PS_FIELDS)

    # --- Source 6: world-engine.session.create statusMessage (key=value fallback) ---
    we_create = _find_observation_by_name(obs_list, "world-engine.session.create")
    if we_create:
        sm = str(
            we_create.get("statusMessage")
            or we_create.get("status_message")
            or ""
        )
        if sm:
            tokens = _parse_status_tokens(sm)
            if tokens:
                status_message_fallback_used = True
                if not ev.get("final_adapter") and tokens.get("adapter"):
                    ev["final_adapter"] = tokens["adapter"]
                if not ev.get("quality_class") and tokens.get("quality"):
                    ev["quality_class"] = tokens["quality"]

    # --- Gate scores ---
    det_scores, _ = _extract_scores_split(raw_trace)
    if det_scores:
        score_source = "trace.scores"
    for gate in (
        "opening_shape_contract_pass",
        "opening_contract_pass",
        "live_runtime_contract_pass",
        "live_runtime_visible_surface_pass",
        "live_opening_contract_pass",
        "fallback_absent",
        "non_mock_generation_pass",
        "visible_output_present",
        "usage_present",
        "rag_context_attached",
        "actor_lane_safety_pass",
        "turn_aspect_ledger_present",
        "beat_selected",
        "beat_realized",
        "scene_energy_target_present",
        "scene_energy_contract_pass",
        "scene_energy_transition_allowed",
        "scene_energy_pressure_realized",
        "pacing_rhythm_target_present",
        "pacing_rhythm_contract_pass",
        "pacing_rhythm_density_respected",
        "pacing_rhythm_pause_respected",
        "temporal_control_policy_present",
        "temporal_control_target_selected",
        "temporal_control_operation_allowed",
        "temporal_control_committed_sources_bounded",
        "temporal_control_history_rewrite_absent",
        "temporal_control_contract_pass",
        "sensory_context_target_present",
        "sensory_context_contract_pass",
        "sensory_context_required_layers_realized",
        "sensory_context_source_refs_valid",
        "improvisational_coherence_policy_present",
        "improvisational_coherence_target_selected",
        "improvisational_coherence_acknowledged",
        "improvisational_coherence_scene_anchor_preserved",
        "improvisational_coherence_contract_pass",
        "social_pressure_target_present",
        "social_pressure_contract_pass",
        "social_pressure_metric_bounded",
        "relationship_state_target_present",
        "relationship_state_contract_pass",
        "information_disclosure_policy_present",
        "information_disclosure_target_selected",
        "information_disclosure_budget_pass",
        "information_disclosure_premature_reveal_absent",
        "information_disclosure_contract_pass",
        "expectation_variation_policy_present",
        "expectation_variation_target_selected",
        "expectation_variation_budget_pass",
        "expectation_variation_setup_supported",
        "expectation_variation_contract_pass",
        "dramatic_irony_opportunity_present",
        "dramatic_irony_contract_pass",
        "consequence_cascade_policy_present",
        "consequence_cascade_contract_pass",
        "narrator_required_when_expected",
        "npc_takeover_absent",
        "npc_agency_plan_present",
        "npc_independent_planning_used",
        "npc_long_horizon_state_present",
        "npc_private_plan_resolution_present",
        "npc_private_plan_visibility_respected",
        "npc_intention_threads_carried_forward",
        "npc_required_initiatives_realized",
        "multi_npc_initiative_realized",
        "npc_carry_forward_closed",
        "npc_forbidden_actor_absent",
        "capability_selection_present",
        "selected_capabilities_realized",
        "visible_block_origin_present",
        "narrative_aspect_policy_present",
        "narrative_aspect_selected",
        "narrative_aspect_visible_when_required",
        "narrative_aspect_contract_pass",
        "theme_tracking_policy_present",
        "theme_tracking_selected",
        "theme_semantic_classification_present",
        "theme_weak_alignment_absent",
        "theme_tracking_contract_pass",
        "voice_consistency_policy_present",
        "voice_semantic_classification_present",
        "voice_cross_actor_confusion_absent",
        "voice_forbidden_markers_absent",
        "voice_consistency_contract_pass",
        "tonal_consistency_policy_present",
        "tonal_consistency_target_selected",
        "tonal_consistency_classification_present",
        "tonal_consistency_marker_hits_absent",
        "tonal_consistency_contract_pass",
        "hierarchical_memory_present",
        "memory_policy_applied",
        "memory_write_from_committed_turn",
        "memory_context_bounded",
        "hierarchical_memory_contract_pass",
    ):
        ev[gate] = det_scores.get(gate)

    if not isinstance(ev.get("npc_actor_ids"), list):
        ev["npc_actor_ids"] = []

    sources = {
        "path_summary_source": path_summary_source,
        "score_source": score_source,
        "status_message_fallback_used": status_message_fallback_used,
    }
    return ev, sources


def _trace_summary(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = _extract_metadata(raw_trace)
    scores = _extract_scores(raw_trace)
    trace_id = str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip()
    return {
        "trace_id": trace_id,
        "name": raw_trace.get("name"),
        "timestamp": raw_trace.get("timestamp"),
        "metadata": metadata,
        "scores": scores,
    }


_RUNTIME_ASPECT_MATRIX_COLUMNS: tuple[str, ...] = (
    "session_id",
    "trace_id",
    "canonical_turn_id",
    "environment",
    "turn_number",
    "raw_input",
    "input_kind",
    "action_kind",
    "turn_aspect_ledger_present",
    "beat_selected",
    "selected_beat",
    "beat_realized",
    "scene_energy_target_present",
    "scene_energy_level",
    "scene_energy_transition",
    "scene_energy_contract_pass",
    "scene_energy_transition_allowed",
    "scene_energy_pressure_realized",
    "scene_energy_failure_codes",
    "pacing_rhythm_target_present",
    "pacing_rhythm_cadence",
    "pacing_rhythm_response_shape",
    "pacing_rhythm_contract_pass",
    "pacing_rhythm_density_respected",
    "pacing_rhythm_pause_respected",
    "pacing_rhythm_failure_codes",
    "temporal_control_policy_present",
    "temporal_control_target_selected",
    "temporal_control_operation",
    "temporal_control_recalled_turn_ids",
    "temporal_control_recalled_consequence_ids",
    "temporal_control_event_count",
    "temporal_control_committed_sources_bounded",
    "temporal_control_history_rewrite_absent",
    "temporal_control_contract_pass",
    "temporal_control_failure_codes",
    "sensory_context_target_present",
    "sensory_context_intensity",
    "sensory_context_location_id",
    "sensory_context_object_id",
    "sensory_context_contract_pass",
    "sensory_context_required_layers_realized",
    "sensory_context_source_refs_valid",
    "sensory_context_failure_codes",
    "improvisational_coherence_policy_present",
    "improvisational_coherence_target_selected",
    "improvisational_coherence_contribution_id",
    "improvisational_coherence_contribution_kind",
    "improvisational_coherence_acceptance_mode",
    "improvisational_coherence_advance_class",
    "improvisational_coherence_acknowledged",
    "improvisational_coherence_scene_anchor_preserved",
    "improvisational_coherence_boundary_reason_code",
    "improvisational_coherence_contract_pass",
    "improvisational_coherence_failure_codes",
    "social_pressure_target_present",
    "social_pressure_score",
    "social_pressure_band",
    "social_pressure_trend",
    "social_pressure_contract_pass",
    "social_pressure_metric_bounded",
    "social_pressure_failure_codes",
    "relationship_state_target_present",
    "relationship_state_pressure_band",
    "relationship_state_pair_count",
    "relationship_state_transition_event_count",
    "relationship_state_contract_pass",
    "relationship_state_failure_codes",
    "information_disclosure_policy_present",
    "information_disclosure_target_selected",
    "information_disclosure_selected_units",
    "information_disclosure_visible_units",
    "information_disclosure_withheld_units",
    "information_disclosure_budget_used",
    "information_disclosure_budget_pass",
    "information_disclosure_premature_reveal_absent",
    "information_disclosure_contract_pass",
    "information_disclosure_failure_codes",
    "expectation_variation_policy_present",
    "expectation_variation_target_selected",
    "expectation_variation_selected_ids",
    "expectation_variation_selected_types",
    "expectation_variation_realized_ids",
    "expectation_variation_realized_types",
    "expectation_variation_budget_used",
    "expectation_variation_budget_pass",
    "expectation_variation_setup_supported",
    "expectation_variation_contract_pass",
    "expectation_variation_failure_codes",
    "dramatic_irony_policy_present",
    "dramatic_irony_opportunity_present",
    "dramatic_irony_selected_opportunities",
    "dramatic_irony_realized_opportunities",
    "dramatic_irony_realization_status",
    "dramatic_irony_leak_blocked",
    "dramatic_irony_contract_pass",
    "dramatic_irony_violation_codes",
    "callback_web_policy_present",
    "callback_web_selected",
    "callback_web_selected_edge_id",
    "callback_web_selected_kind",
    "callback_web_selected_continuity_classes",
    "callback_web_edge_count",
    "callback_web_observation_count",
        "callback_web_graph_edge_count",
        "callback_web_contract_pass",
        "callback_web_failure_codes",
    "consequence_cascade_policy_present",
    "consequence_cascade_selected",
    "consequence_cascade_selected_consequence_ids",
    "consequence_cascade_selected_continuity_classes",
    "consequence_cascade_selected_statuses",
    "consequence_cascade_atom_count",
    "consequence_cascade_edge_count",
    "consequence_cascade_active_atom_count",
    "consequence_cascade_contract_pass",
    "consequence_cascade_failure_codes",
    "narrator_required_when_expected",
    "narrator_required",
    "narrator_present",
        "npc_policy",
        "npc_takeover_absent",
        "npc_takeover_detected",
        "npc_agency_plan_present",
        "npc_independent_planning_used",
        "npc_long_horizon_state_present",
        "npc_private_plan_resolution_present",
        "npc_private_plan_visibility_respected",
        "npc_intention_threads_carried_forward",
        "npc_required_initiatives_realized",
        "multi_npc_initiative_realized",
        "npc_carry_forward_closed",
        "npc_forbidden_actor_absent",
        "npc_agency_candidate_actor_ids",
        "npc_agency_missing_required_actor_ids",
        "npc_agency_claim_readiness_status",
        "npc_agency_full_claim_allowed",
        "capability_selection_present",
    "selected_capabilities",
    "realized_capabilities",
    "selected_capabilities_realized",
    "forbidden_capability_realized",
    "visible_block_origin_present",
    "visible_origin_present",
    "narrative_aspect_policy_present",
    "narrative_aspect_selected",
    "selected_narrative_aspects",
    "realized_narrative_aspects",
    "narrative_aspect_visible_when_required",
    "narrative_aspect_contract_pass",
    "theme_tracking_policy_present",
    "theme_tracking_selected",
    "selected_theme_aspects",
    "realized_theme_aspects",
    "theme_semantic_classification_present",
    "theme_semantic_classification_count",
    "theme_weak_alignment_count",
    "theme_tracking_contract_pass",
    "voice_consistency_policy_present",
    "voice_semantic_classification_enabled",
    "voice_semantic_classification_present",
    "voice_semantic_classification_count",
    "voice_spoken_line_count",
    "voice_cross_actor_confusion_absent",
    "voice_cross_actor_confusion_count",
    "voice_forbidden_markers_absent",
    "voice_consistency_contract_pass",
    "tonal_consistency_policy_present",
    "tonal_consistency_target_selected",
    "tonal_consistency_profile_id",
    "tonal_consistency_required_dimensions",
    "tonal_consistency_realized_dimensions",
    "tonal_consistency_classification_present",
    "tonal_consistency_marker_hits_absent",
    "tonal_consistency_contract_pass",
    "tonal_consistency_failure_codes",
    "hierarchical_memory_present",
    "memory_policy_applied",
    "selected_memory_tiers",
    "memory_written_item_count",
    "memory_context_item_count",
    "memory_write_from_committed_turn",
    "memory_context_bounded",
    "hierarchical_memory_contract_pass",
    "turn_status",
    "http_status",
    "main_failure",
    "recommended_repair",
)


def _extract_path_summary_from_trace(raw_trace: dict[str, Any]) -> dict[str, Any]:
    trace_output = _coerce_dict_or_json(raw_trace.get("output"))
    nested = _coerce_dict_or_json(trace_output.get("path_summary")) if trace_output else {}
    if nested:
        return nested
    if trace_output.get("contract") == "story_runtime_path_observability.v1":
        return trace_output
    ps_obs = _find_observation_by_name(_get_observations(raw_trace), "story.graph.path_summary")
    if ps_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(ps_obs.get(block_key))
            if block.get("contract") == "story_runtime_path_observability.v1" or block.get("turn_aspect_ledger"):
                return block
    return {}


def _extract_runtime_aspect_ledger_from_trace(raw_trace: dict[str, Any]) -> dict[str, Any]:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    ledger = path_summary.get("turn_aspect_ledger") if isinstance(path_summary, dict) else None
    if isinstance(ledger, dict) and isinstance(ledger.get("turn_aspect_ledger"), dict):
        return ledger
    aspect_obs = _find_observation_by_name(_get_observations(raw_trace), "story.turn.aspect_summary")
    if aspect_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(aspect_obs.get(block_key))
            ledger = block.get("turn_aspect_ledger") if isinstance(block, dict) else None
            if isinstance(ledger, dict) and isinstance(ledger.get("turn_aspect_ledger"), dict):
                return ledger
    return {}


def _aspect_record(ledger: dict[str, Any], aspect_name: str) -> dict[str, Any]:
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    row = aspects.get(aspect_name) if isinstance(aspects, dict) else {}
    return row if isinstance(row, dict) else {}


def _aspect_block(record: dict[str, Any], block_name: str) -> dict[str, Any]:
    block = record.get(block_name) if isinstance(record, dict) else {}
    return block if isinstance(block, dict) else {}


def _runtime_aspect_recommended_repair(main_failure: str | None) -> str | None:
    failure = str(main_failure or "").strip()
    if not failure:
        return None
    if "npc_execut" in failure:
        return "repair_npc_authority_prevent_execute_player_action"
    if "npc_narrat" in failure:
        return "repair_npc_authority_prevent_player_perception_narration"
    if "narrator_required" in failure:
        return "repair_narrator_authority_required_consequence"
    if "forbidden_capability" in failure:
        return "repair_capability_selection_block_forbidden_realization"
    if "voice" in failure or "cross_actor_voice" in failure:
        return "repair_voice_consistency_follow_character_profiles"
    if failure.startswith("tonal_consistency_"):
        return "repair_tonal_consistency_follow_policy_target"
    if failure.startswith("callback_"):
        return "repair_callback_web_bounded_committed_evidence"
    if failure.startswith("consequence_cascade_"):
        return "repair_consequence_cascade_bounded_committed_evidence"
    if failure.startswith("scene_energy_"):
        return "repair_scene_energy_structured_realization"
    if failure.startswith("symbolic_object_resonance_"):
        return "repair_symbolic_object_resonance_structured_selection"
    if failure.startswith("temporal_control_"):
        return "repair_temporal_control_bounded_committed_refs"
    if failure.startswith("improv_") or failure.startswith("improvisational_coherence_"):
        return "repair_improvisational_coherence_structured_acceptance"
    if failure.startswith("expectation_variation_"):
        return "repair_expectation_variation_structured_selection"
    if "beat" in failure:
        return "repair_beat_realization_or_contract_classification"
    if "origin" in failure or "projection" in failure:
        return "repair_visible_projection_origin_metadata"
    return "inspect_runtime_aspect_ledger"


def _runtime_aspect_matrix_row(raw_trace: dict[str, Any]) -> dict[str, Any]:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    ledger = _extract_runtime_aspect_ledger_from_trace(raw_trace)
    det_scores, _judge = _extract_scores_split(raw_trace)
    input_rec = _aspect_record(ledger, "input")
    action_rec = _aspect_record(ledger, "action_resolution")
    beat_rec = _aspect_record(ledger, "beat")
    scene_energy_rec = _aspect_record(ledger, "scene_energy")
    pacing_rhythm_rec = _aspect_record(ledger, "pacing_rhythm")
    temporal_control_rec = _aspect_record(ledger, "temporal_control")
    sensory_context_rec = _aspect_record(ledger, "sensory_context")
    symbolic_object_rec = _aspect_record(ledger, "symbolic_object_resonance")
    improvisational_rec = _aspect_record(ledger, "improvisational_coherence")
    social_pressure_rec = _aspect_record(ledger, "social_pressure")
    relationship_state_rec = _aspect_record(ledger, "relationship_state")
    disclosure_rec = _aspect_record(ledger, "information_disclosure")
    expectation_variation_rec = _aspect_record(ledger, "expectation_variation")
    dramatic_irony_rec = _aspect_record(ledger, "dramatic_irony")
    callback_rec = _aspect_record(ledger, "callback_web")
    cascade_rec = _aspect_record(ledger, "consequence_cascade")
    narr_rec = _aspect_record(ledger, "narrator_authority")
    npc_rec = _aspect_record(ledger, "npc_authority")
    npc_agency_rec = _aspect_record(ledger, "npc_agency")
    cap_rec = _aspect_record(ledger, "capability_selection")
    vis_rec = _aspect_record(ledger, "visible_projection")
    narrative_rec = _aspect_record(ledger, "narrative_aspect")
    voice_rec = _aspect_record(ledger, "voice_consistency")
    tonal_rec = _aspect_record(ledger, "tonal_consistency")
    memory_rec = _aspect_record(ledger, "hierarchical_memory")

    input_actual = _aspect_block(input_rec, "actual")
    action_actual = _aspect_block(action_rec, "actual")
    beat_selected = _aspect_block(beat_rec, "selected")
    beat_actual = _aspect_block(beat_rec, "actual")
    scene_energy_selected = _aspect_block(scene_energy_rec, "selected")
    scene_energy_actual = _aspect_block(scene_energy_rec, "actual")
    pacing_rhythm_selected = _aspect_block(pacing_rhythm_rec, "selected")
    pacing_rhythm_actual = _aspect_block(pacing_rhythm_rec, "actual")
    temporal_control_expected = _aspect_block(temporal_control_rec, "expected")
    temporal_control_selected = _aspect_block(temporal_control_rec, "selected")
    temporal_control_actual = _aspect_block(temporal_control_rec, "actual")
    sensory_context_selected = _aspect_block(sensory_context_rec, "selected")
    sensory_context_actual = _aspect_block(sensory_context_rec, "actual")
    symbolic_object_expected = _aspect_block(symbolic_object_rec, "expected")
    symbolic_object_selected = _aspect_block(symbolic_object_rec, "selected")
    symbolic_object_actual = _aspect_block(symbolic_object_rec, "actual")
    improvisational_expected = _aspect_block(improvisational_rec, "expected")
    improvisational_selected = _aspect_block(improvisational_rec, "selected")
    improvisational_actual = _aspect_block(improvisational_rec, "actual")
    social_pressure_selected = _aspect_block(social_pressure_rec, "selected")
    social_pressure_actual = _aspect_block(social_pressure_rec, "actual")
    relationship_state_selected = _aspect_block(relationship_state_rec, "selected")
    relationship_state_actual = _aspect_block(relationship_state_rec, "actual")
    disclosure_expected = _aspect_block(disclosure_rec, "expected")
    disclosure_selected = _aspect_block(disclosure_rec, "selected")
    disclosure_actual = _aspect_block(disclosure_rec, "actual")
    expectation_variation_expected = _aspect_block(expectation_variation_rec, "expected")
    expectation_variation_selected = _aspect_block(expectation_variation_rec, "selected")
    expectation_variation_actual = _aspect_block(expectation_variation_rec, "actual")
    dramatic_irony_expected = _aspect_block(dramatic_irony_rec, "expected")
    dramatic_irony_selected = _aspect_block(dramatic_irony_rec, "selected")
    dramatic_irony_actual = _aspect_block(dramatic_irony_rec, "actual")
    callback_expected = _aspect_block(callback_rec, "expected")
    callback_selected = _aspect_block(callback_rec, "selected")
    callback_actual = _aspect_block(callback_rec, "actual")
    cascade_expected = _aspect_block(cascade_rec, "expected")
    cascade_selected = _aspect_block(cascade_rec, "selected")
    cascade_actual = _aspect_block(cascade_rec, "actual")
    narr_expected = _aspect_block(narr_rec, "expected")
    narr_actual = _aspect_block(narr_rec, "actual")
    npc_expected = _aspect_block(npc_rec, "expected")
    npc_actual = _aspect_block(npc_rec, "actual")
    npc_agency_actual = _aspect_block(npc_agency_rec, "actual")
    cap_selected = _aspect_block(cap_rec, "selected")
    cap_actual = _aspect_block(cap_rec, "actual")
    vis_actual = _aspect_block(vis_rec, "actual")
    narrative_expected = _aspect_block(narrative_rec, "expected")
    narrative_selected = _aspect_block(narrative_rec, "selected")
    narrative_actual = _aspect_block(narrative_rec, "actual")
    voice_expected = _aspect_block(voice_rec, "expected")
    voice_actual = _aspect_block(voice_rec, "actual")
    tonal_expected = _aspect_block(tonal_rec, "expected")
    tonal_selected = _aspect_block(tonal_rec, "selected")
    tonal_actual = _aspect_block(tonal_rec, "actual")
    memory_selected = _aspect_block(memory_rec, "selected")
    memory_actual = _aspect_block(memory_rec, "actual")
    claim_readiness = assess_npc_agency_claim_readiness(
        runtime_aspect={
            **npc_agency_actual,
            "npc_independent_planning_used": npc_agency_actual.get("independent_planning_used")
            if "independent_planning_used" in npc_agency_actual
            else det_scores.get("npc_independent_planning_used"),
            "npc_forbidden_actor_absent": (
                not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
                and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            )
            if (
                "forbidden_planned_actor_ids" in npc_agency_actual
                or "forbidden_realized_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_forbidden_actor_absent"),
            "long_horizon_state_present": npc_agency_actual.get("long_horizon_state_present")
            if "long_horizon_state_present" in npc_agency_actual
            else det_scores.get("npc_long_horizon_state_present"),
            "private_plan_resolution_present": npc_agency_actual.get("private_plan_resolution_present")
            if "private_plan_resolution_present" in npc_agency_actual
            else det_scores.get("npc_private_plan_resolution_present"),
            "private_plan_visibility_respected": npc_agency_actual.get("private_plan_visibility_respected")
            if "private_plan_visibility_respected" in npc_agency_actual
            else det_scores.get("npc_private_plan_visibility_respected"),
        },
        live_trace_evidence={
            "live_trace_present": str(_extract_metadata(raw_trace).get("trace_origin") or "").strip().lower()
            == "live_ui",
            "non_mock_generation_pass": det_scores.get("non_mock_generation_pass"),
            "fallback_used": not bool(det_scores.get("fallback_absent")),
        },
        mcp_evidence={"runtime_aspect_matrix_present": True},
    )
    voice_drift_counts = (
        voice_actual.get("drift_class_counts")
        if isinstance(voice_actual.get("drift_class_counts"), dict)
        else {}
    )
    voice_cross_actor_count = int(
        voice_actual.get("semantic_cross_actor_confusion_count")
        or voice_drift_counts.get("cross_actor_voice_confusion")
        or 0
    )
    voice_forbidden_marker_count = int(
        voice_drift_counts.get("forbidden_language_marker") or 0
    )
    tonal_target = (
        tonal_selected.get("target")
        if isinstance(tonal_selected.get("target"), dict)
        else tonal_selected
    )
    tonal_failure_codes = tonal_actual.get("failure_codes") or []
    if not isinstance(tonal_failure_codes, list):
        tonal_failure_codes = []
    scene_energy_target = (
        scene_energy_selected.get("target")
        if isinstance(scene_energy_selected.get("target"), dict)
        else scene_energy_selected
    )
    scene_energy_transition = (
        scene_energy_selected.get("transition")
        if isinstance(scene_energy_selected.get("transition"), dict)
        else {}
    )
    scene_energy_failure_codes = scene_energy_actual.get("failure_codes") or []
    if not isinstance(scene_energy_failure_codes, list):
        scene_energy_failure_codes = []
    pacing_rhythm_target = (
        pacing_rhythm_selected.get("target")
        if isinstance(pacing_rhythm_selected.get("target"), dict)
        else pacing_rhythm_selected
    )
    pacing_rhythm_failure_codes = pacing_rhythm_actual.get("failure_codes") or []
    if not isinstance(pacing_rhythm_failure_codes, list):
        pacing_rhythm_failure_codes = []
    temporal_control_target = (
        temporal_control_selected.get("target")
        if isinstance(temporal_control_selected.get("target"), dict)
        else temporal_control_selected
    )
    temporal_control_failure_codes = temporal_control_actual.get("failure_codes") or []
    if not isinstance(temporal_control_failure_codes, list):
        temporal_control_failure_codes = []
    sensory_context_target = (
        sensory_context_selected.get("target")
        if isinstance(sensory_context_selected.get("target"), dict)
        else sensory_context_selected
    )
    sensory_context_failure_codes = sensory_context_actual.get("failure_codes") or []
    if not isinstance(sensory_context_failure_codes, list):
        sensory_context_failure_codes = []
    symbolic_object_target = (
        symbolic_object_selected.get("target")
        if isinstance(symbolic_object_selected.get("target"), dict)
        else symbolic_object_selected
    )
    symbolic_object_failure_codes = symbolic_object_actual.get("failure_codes") or []
    if not isinstance(symbolic_object_failure_codes, list):
        symbolic_object_failure_codes = []
    improvisational_failure_codes = improvisational_actual.get("failure_codes") or []
    if not isinstance(improvisational_failure_codes, list):
        improvisational_failure_codes = []
    social_pressure_target = (
        social_pressure_selected.get("target")
        if isinstance(social_pressure_selected.get("target"), dict)
        else social_pressure_selected
    )
    social_pressure_failure_codes = social_pressure_actual.get("failure_codes") or []
    if not isinstance(social_pressure_failure_codes, list):
        social_pressure_failure_codes = []
    relationship_state_target = (
        relationship_state_selected.get("target")
        if isinstance(relationship_state_selected.get("target"), dict)
        else relationship_state_selected
    )
    relationship_state_failure_codes = relationship_state_actual.get("failure_codes") or []
    if not isinstance(relationship_state_failure_codes, list):
        relationship_state_failure_codes = []
    disclosure_failure_codes = disclosure_actual.get("failure_codes") or []
    if not isinstance(disclosure_failure_codes, list):
        disclosure_failure_codes = []
    expectation_variation_failure_codes = (
        expectation_variation_actual.get("failure_codes") or []
    )
    if not isinstance(expectation_variation_failure_codes, list):
        expectation_variation_failure_codes = []
    dramatic_irony_violation_codes = dramatic_irony_actual.get("violation_codes") or []
    if not isinstance(dramatic_irony_violation_codes, list):
        dramatic_irony_violation_codes = []
    callback_failure_codes = callback_actual.get("failure_codes") or []
    if not isinstance(callback_failure_codes, list):
        callback_failure_codes = []
    cascade_failure_codes = cascade_actual.get("failure_codes") or []
    if not isinstance(cascade_failure_codes, list):
        cascade_failure_codes = []
    failed_records = [
        r
        for r in (
            narr_rec,
            npc_rec,
            npc_agency_rec,
            cap_rec,
            beat_rec,
            scene_energy_rec,
            pacing_rhythm_rec,
            temporal_control_rec,
            sensory_context_rec,
            symbolic_object_rec,
            improvisational_rec,
            social_pressure_rec,
            relationship_state_rec,
            disclosure_rec,
            expectation_variation_rec,
            dramatic_irony_rec,
            callback_rec,
            cascade_rec,
            vis_rec,
            narrative_rec,
            voice_rec,
            tonal_rec,
            memory_rec,
        )
        if r.get("status") == "failed"
    ]
    partial_records = [
        r
        for r in (
            beat_rec,
            scene_energy_rec,
            pacing_rhythm_rec,
            temporal_control_rec,
            sensory_context_rec,
            symbolic_object_rec,
            improvisational_rec,
            social_pressure_rec,
            relationship_state_rec,
            disclosure_rec,
            expectation_variation_rec,
            dramatic_irony_rec,
            callback_rec,
            cascade_rec,
            npc_agency_rec,
            cap_rec,
            vis_rec,
            narrative_rec,
            voice_rec,
            tonal_rec,
            memory_rec,
        )
        if r.get("status") == "partial"
    ]
    main_record = failed_records[0] if failed_records else partial_records[0] if partial_records else {}
    reasons = main_record.get("reasons") if isinstance(main_record.get("reasons"), list) else []
    main_failure = str(main_record.get("failure_reason") or (reasons[0] if reasons else "")).strip() or None
    row = {
        "session_id": ledger.get("session_id") or path_summary.get("session_id") or _extract_metadata(raw_trace).get("session_id"),
        "trace_id": str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip(),
        "canonical_turn_id": ledger.get("canonical_turn_id") or path_summary.get("canonical_turn_id") or _extract_metadata(raw_trace).get("canonical_turn_id"),
        "environment": raw_trace.get("environment") or _extract_metadata(raw_trace).get("environment") or path_summary.get("environment"),
        "turn_number": ledger.get("turn_number") if ledger else path_summary.get("turn_number"),
        "raw_input": input_actual.get("raw_player_input") or action_actual.get("raw_player_input") or path_summary.get("raw_player_input"),
        "input_kind": input_actual.get("player_input_kind") or input_actual.get("input_kind") or action_actual.get("input_kind") or path_summary.get("player_input_kind"),
        "action_kind": action_actual.get("action_kind"),
        "turn_aspect_ledger_present": bool(ledger.get("turn_aspect_ledger")) if ledger else bool(path_summary.get("turn_aspect_ledger_present") or det_scores.get("turn_aspect_ledger_present")),
        "beat_selected": bool(beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function")) if beat_selected else det_scores.get("beat_selected"),
        "selected_beat": beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function"),
        "beat_realized": beat_actual.get("realized") if "realized" in beat_actual else det_scores.get("beat_realized"),
        "scene_energy_target_present": bool(scene_energy_target) if scene_energy_rec else det_scores.get("scene_energy_target_present"),
        "scene_energy_level": scene_energy_target.get("energy_level"),
        "scene_energy_transition": scene_energy_target.get("target_transition") or scene_energy_transition.get("transition_intent"),
        "scene_energy_contract_pass": (
            scene_energy_actual.get("contract_pass")
            if "contract_pass" in scene_energy_actual
            else det_scores.get("scene_energy_contract_pass")
        ),
        "scene_energy_transition_allowed": (
            scene_energy_actual.get("transition_allowed")
            if "transition_allowed" in scene_energy_actual
            else det_scores.get("scene_energy_transition_allowed")
        ),
        "scene_energy_pressure_realized": (
            "scene_energy_missing_required_pressure" not in scene_energy_failure_codes
            if scene_energy_actual
            else det_scores.get("scene_energy_pressure_realized")
        ),
        "scene_energy_failure_codes": scene_energy_failure_codes,
        "pacing_rhythm_target_present": (
            bool(pacing_rhythm_target)
            if pacing_rhythm_rec
            else det_scores.get("pacing_rhythm_target_present")
        ),
        "pacing_rhythm_cadence": pacing_rhythm_target.get("cadence"),
        "pacing_rhythm_response_shape": pacing_rhythm_target.get("response_shape"),
        "pacing_rhythm_contract_pass": (
            pacing_rhythm_actual.get("contract_pass")
            if "contract_pass" in pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_contract_pass")
        ),
        "pacing_rhythm_density_respected": (
            "pacing_rhythm_visible_density_exceeded" not in pacing_rhythm_failure_codes
            if pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_density_respected")
        ),
        "pacing_rhythm_pause_respected": (
            "pacing_rhythm_pause_obligation_lost" not in pacing_rhythm_failure_codes
            and "pacing_rhythm_forced_speech_violation" not in pacing_rhythm_failure_codes
            if pacing_rhythm_actual
            else det_scores.get("pacing_rhythm_pause_respected")
        ),
        "pacing_rhythm_failure_codes": pacing_rhythm_failure_codes,
        "temporal_control_policy_present": (
            temporal_control_expected.get("policy_present")
            if "policy_present" in temporal_control_expected
            else det_scores.get("temporal_control_policy_present")
        ),
        "temporal_control_target_selected": (
            bool(temporal_control_target.get("operation"))
            if temporal_control_selected
            else det_scores.get("temporal_control_target_selected")
        ),
        "temporal_control_operation": temporal_control_target.get("operation")
        if isinstance(temporal_control_target, dict)
        else None,
        "temporal_control_recalled_turn_ids": temporal_control_target.get(
            "recalled_turn_ids"
        )
        if isinstance(temporal_control_target, dict)
        else [],
        "temporal_control_recalled_consequence_ids": temporal_control_target.get(
            "recalled_consequence_ids"
        )
        if isinstance(temporal_control_target, dict)
        else [],
        "temporal_control_event_count": int(
            temporal_control_actual.get("event_count") or 0
        ),
        "temporal_control_committed_sources_bounded": (
            "temporal_control_uncommitted_source" not in temporal_control_failure_codes
            and "temporal_control_unbounded_jump" not in temporal_control_failure_codes
            if temporal_control_actual
            else det_scores.get("temporal_control_committed_sources_bounded")
        ),
        "temporal_control_history_rewrite_absent": (
            "temporal_control_history_rewrite_attempt"
            not in temporal_control_failure_codes
            and "temporal_control_branch_state_adoption"
            not in temporal_control_failure_codes
            if temporal_control_actual
            else det_scores.get("temporal_control_history_rewrite_absent")
        ),
        "temporal_control_contract_pass": (
            temporal_control_actual.get("contract_pass")
            if "contract_pass" in temporal_control_actual
            else det_scores.get("temporal_control_contract_pass")
        ),
        "temporal_control_failure_codes": temporal_control_failure_codes,
        "sensory_context_target_present": (
            bool(sensory_context_target)
            if sensory_context_rec
            else det_scores.get("sensory_context_target_present")
        ),
        "sensory_context_intensity": sensory_context_target.get("intensity"),
        "sensory_context_location_id": sensory_context_target.get("location_id"),
        "sensory_context_object_id": sensory_context_target.get("object_id"),
        "sensory_context_contract_pass": (
            sensory_context_actual.get("contract_pass")
            if "contract_pass" in sensory_context_actual
            else det_scores.get("sensory_context_contract_pass")
        ),
        "sensory_context_required_layers_realized": (
            "sensory_context_missing_required_layer" not in sensory_context_failure_codes
            and "sensory_context_structured_event_missing" not in sensory_context_failure_codes
            if sensory_context_actual
            else det_scores.get("sensory_context_required_layers_realized")
        ),
        "sensory_context_source_refs_valid": (
            "sensory_context_source_ref_mismatch" not in sensory_context_failure_codes
            and "sensory_context_unselected_layer" not in sensory_context_failure_codes
            if sensory_context_actual
            else det_scores.get("sensory_context_source_refs_valid")
        ),
        "sensory_context_failure_codes": sensory_context_failure_codes,
        "symbolic_object_resonance_policy_present": (
            symbolic_object_expected.get("policy_present")
            if "policy_present" in symbolic_object_expected
            else det_scores.get("symbolic_object_resonance_policy_present")
        ),
        "symbolic_object_resonance_target_selected": (
            bool(symbolic_object_target.get("selected_object_ids"))
            if symbolic_object_selected
            else det_scores.get("symbolic_object_resonance_target_selected")
        ),
        "symbolic_object_resonance_selected_object_ids": (
            symbolic_object_target.get("selected_object_ids")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_selected_symbol_ids": (
            symbolic_object_target.get("selected_symbol_ids")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_selected_roles": (
            symbolic_object_target.get("selected_resonance_roles")
            if isinstance(symbolic_object_target, dict)
            else []
        )
        or [],
        "symbolic_object_resonance_realized_object_ids": (
            symbolic_object_actual.get("realized_object_ids") or []
        ),
        "symbolic_object_resonance_realized_symbol_ids": (
            symbolic_object_actual.get("realized_symbol_ids") or []
        ),
        "symbolic_object_resonance_event_count": int(
            symbolic_object_actual.get("event_count") or 0
        ),
        "symbolic_object_resonance_source_refs_valid": (
            "symbolic_object_resonance_source_ref_mismatch"
            not in symbolic_object_failure_codes
            and "symbolic_object_resonance_unselected_object"
            not in symbolic_object_failure_codes
            if symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_source_refs_valid")
        ),
        "symbolic_object_resonance_budget_pass": (
            "symbolic_object_resonance_budget_exceeded"
            not in symbolic_object_failure_codes
            if symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_budget_pass")
        ),
        "symbolic_object_resonance_contract_pass": (
            symbolic_object_actual.get("contract_pass")
            if "contract_pass" in symbolic_object_actual
            else det_scores.get("symbolic_object_resonance_contract_pass")
        ),
        "symbolic_object_resonance_failure_codes": symbolic_object_failure_codes,
        "improvisational_coherence_policy_present": (
            improvisational_expected.get("policy_present")
            if "policy_present" in improvisational_expected
            else det_scores.get("improvisational_coherence_policy_present")
        ),
        "improvisational_coherence_target_selected": (
            bool(
                improvisational_selected.get("contribution_id")
                or improvisational_selected.get("acceptance_mode")
                or improvisational_selected.get("required_anchor_refs")
            )
            if improvisational_selected
            else det_scores.get("improvisational_coherence_target_selected")
        ),
        "improvisational_coherence_contribution_id": improvisational_selected.get(
            "contribution_id"
        ),
        "improvisational_coherence_contribution_kind": improvisational_selected.get(
            "contribution_kind"
        ),
        "improvisational_coherence_acceptance_mode": (
            improvisational_selected.get("acceptance_mode")
            or improvisational_actual.get("acceptance_mode")
        ),
        "improvisational_coherence_advance_class": improvisational_actual.get(
            "advance_class"
        ),
        "improvisational_coherence_acknowledged": (
            improvisational_actual.get("contribution_acknowledged")
            if "contribution_acknowledged" in improvisational_actual
            else (
                det_scores.get("improvisational_coherence_acknowledged")
                if "improvisational_coherence_acknowledged" in det_scores
                else det_scores.get("player_contribution_acknowledged")
            )
        ),
        "improvisational_coherence_scene_anchor_preserved": (
            "improv_scene_anchor_missing" not in improvisational_failure_codes
            if improvisational_actual
            else (
                det_scores.get("improvisational_coherence_scene_anchor_preserved")
                if "improvisational_coherence_scene_anchor_preserved" in det_scores
                else det_scores.get("improv_scene_anchor_preserved")
            )
        ),
        "improvisational_coherence_boundary_reason_code": (
            improvisational_actual.get("boundary_reason_code")
            or improvisational_selected.get("boundary_reason_code")
        ),
        "improvisational_coherence_contract_pass": (
            improvisational_actual.get("contract_pass")
            if "contract_pass" in improvisational_actual
            else (
                det_scores.get("improvisational_coherence_contract_pass")
                if "improvisational_coherence_contract_pass" in det_scores
                else det_scores.get("improv_contract_pass")
            )
        ),
        "improvisational_coherence_failure_codes": improvisational_failure_codes,
        "social_pressure_target_present": (
            bool(social_pressure_target)
            if social_pressure_rec
            else det_scores.get("social_pressure_target_present")
        ),
        "social_pressure_score": social_pressure_target.get("target_score")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_band": social_pressure_target.get("target_band")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_trend": social_pressure_target.get("trend")
        if isinstance(social_pressure_target, dict)
        else None,
        "social_pressure_contract_pass": (
            social_pressure_actual.get("contract_pass")
            if "contract_pass" in social_pressure_actual
            else det_scores.get("social_pressure_contract_pass")
        ),
        "social_pressure_metric_bounded": (
            "social_pressure_score_out_of_bounds" not in social_pressure_failure_codes
            if social_pressure_actual
            else det_scores.get("social_pressure_metric_bounded")
        ),
        "social_pressure_failure_codes": social_pressure_failure_codes,
        "relationship_state_target_present": (
            bool(relationship_state_target)
            if relationship_state_rec
            else det_scores.get("relationship_state_target_present")
        ),
        "relationship_state_pressure_band": relationship_state_target.get("pressure_band")
        if isinstance(relationship_state_target, dict)
        else None,
        "relationship_state_pair_count": int(
            relationship_state_actual.get("pair_count") or 0
        ),
        "relationship_state_transition_event_count": int(
            relationship_state_actual.get("transition_event_count") or 0
        ),
        "relationship_state_contract_pass": (
            relationship_state_actual.get("contract_pass")
            if "contract_pass" in relationship_state_actual
            else det_scores.get("relationship_state_contract_pass")
        ),
        "relationship_state_failure_codes": relationship_state_failure_codes,
        "information_disclosure_policy_present": (
            disclosure_expected.get("policy_present")
            if "policy_present" in disclosure_expected
            else det_scores.get("information_disclosure_policy_present")
        ),
        "information_disclosure_target_selected": (
            bool(disclosure_selected.get("selected_unit_ids"))
            if disclosure_selected
            else det_scores.get("information_disclosure_target_selected")
        ),
        "information_disclosure_selected_units": disclosure_selected.get("selected_unit_ids") or [],
        "information_disclosure_visible_units": disclosure_actual.get("visible_unit_ids") or [],
        "information_disclosure_withheld_units": disclosure_selected.get("withheld_unit_ids")
        or disclosure_actual.get("withheld_unit_ids")
        or [],
        "information_disclosure_budget_used": disclosure_actual.get("budget_used"),
        "information_disclosure_budget_pass": (
            "information_disclosure_over_budget" not in disclosure_failure_codes
            if disclosure_actual
            else det_scores.get("information_disclosure_budget_pass")
        ),
        "information_disclosure_premature_reveal_absent": (
            "information_disclosure_forbidden_unit" not in disclosure_failure_codes
            if disclosure_actual
            else det_scores.get("information_disclosure_premature_reveal_absent")
        ),
        "information_disclosure_contract_pass": (
            disclosure_actual.get("contract_pass")
            if "contract_pass" in disclosure_actual
            else det_scores.get("information_disclosure_contract_pass")
        ),
        "information_disclosure_failure_codes": disclosure_failure_codes,
        "expectation_variation_policy_present": (
            expectation_variation_expected.get("policy_present")
            if "policy_present" in expectation_variation_expected
            else det_scores.get("expectation_variation_policy_present")
        ),
        "expectation_variation_target_selected": (
            bool(expectation_variation_selected.get("selected_variation_ids"))
            if expectation_variation_selected
            else det_scores.get("expectation_variation_target_selected")
        ),
        "expectation_variation_selected_ids": expectation_variation_selected.get(
            "selected_variation_ids"
        )
        or [],
        "expectation_variation_selected_types": expectation_variation_selected.get(
            "selected_variation_types"
        )
        or [],
        "expectation_variation_realized_ids": expectation_variation_actual.get(
            "realized_variation_ids"
        )
        or [],
        "expectation_variation_realized_types": expectation_variation_actual.get(
            "realized_variation_types"
        )
        or [],
        "expectation_variation_budget_used": expectation_variation_actual.get(
            "budget_used"
        ),
        "expectation_variation_budget_pass": (
            "expectation_variation_over_budget" not in expectation_variation_failure_codes
            if expectation_variation_actual
            else det_scores.get("expectation_variation_budget_pass")
        ),
        "expectation_variation_setup_supported": (
            "expectation_variation_unearned_event" not in expectation_variation_failure_codes
            and "expectation_variation_target_mismatch" not in expectation_variation_failure_codes
            if expectation_variation_actual
            else det_scores.get("expectation_variation_setup_supported")
        ),
        "expectation_variation_contract_pass": (
            expectation_variation_actual.get("contract_pass")
            if "contract_pass" in expectation_variation_actual
            else det_scores.get("expectation_variation_contract_pass")
        ),
        "expectation_variation_failure_codes": expectation_variation_failure_codes,
        "dramatic_irony_policy_present": (
            dramatic_irony_expected.get("policy_present")
            if "policy_present" in dramatic_irony_expected
            else det_scores.get("dramatic_irony_policy_present")
        ),
        "dramatic_irony_opportunity_present": (
            bool(dramatic_irony_actual.get("opportunity_count"))
            if "opportunity_count" in dramatic_irony_actual
            else det_scores.get("dramatic_irony_opportunity_present")
        ),
        "dramatic_irony_selected_opportunities": dramatic_irony_selected.get("selected_opportunity_ids") or [],
        "dramatic_irony_realized_opportunities": dramatic_irony_actual.get("realized_opportunity_ids") or [],
        "dramatic_irony_realization_status": dramatic_irony_actual.get("realization_status"),
        "dramatic_irony_leak_blocked": bool(dramatic_irony_actual.get("leak_blocked")),
        "dramatic_irony_contract_pass": (
            dramatic_irony_actual.get("contract_pass")
            if "contract_pass" in dramatic_irony_actual
            else det_scores.get("dramatic_irony_contract_pass")
        ),
        "dramatic_irony_violation_codes": dramatic_irony_violation_codes,
        "callback_web_policy_present": (
            callback_expected.get("policy_present")
            if "policy_present" in callback_expected
            else det_scores.get("callback_web_policy_present")
        ),
        "callback_web_selected": bool(
            callback_selected.get("selected_callback_edge_id")
            or callback_selected.get("selected_callback_kind")
        ),
        "callback_web_selected_edge_id": callback_selected.get("selected_callback_edge_id"),
        "callback_web_selected_kind": callback_selected.get("selected_callback_kind"),
        "callback_web_selected_continuity_classes": callback_selected.get("selected_continuity_classes")
        or [],
        "callback_web_edge_count": callback_actual.get("edge_count"),
        "callback_web_observation_count": callback_actual.get("observation_count"),
        "callback_web_graph_edge_count": callback_actual.get("graph_edge_count"),
        "callback_web_contract_pass": (
            callback_actual.get("contract_pass")
            if "contract_pass" in callback_actual
            else det_scores.get("callback_web_contract_pass")
        ),
        "callback_web_failure_codes": callback_failure_codes,
        "consequence_cascade_policy_present": (
            cascade_expected.get("policy_present")
            if "policy_present" in cascade_expected
            else det_scores.get("consequence_cascade_policy_present")
        ),
        "consequence_cascade_selected": bool(
            cascade_selected.get("selected_consequence_ids")
            or cascade_selected.get("selected_continuity_classes")
        ),
        "consequence_cascade_selected_consequence_ids": cascade_selected.get(
            "selected_consequence_ids"
        )
        or [],
        "consequence_cascade_selected_continuity_classes": cascade_selected.get(
            "selected_continuity_classes"
        )
        or [],
        "consequence_cascade_selected_statuses": cascade_selected.get("selected_statuses") or [],
        "consequence_cascade_atom_count": cascade_actual.get("atom_count"),
        "consequence_cascade_edge_count": cascade_actual.get("edge_count"),
        "consequence_cascade_active_atom_count": cascade_actual.get("active_atom_count"),
        "consequence_cascade_contract_pass": (
            cascade_actual.get("contract_pass")
            if "contract_pass" in cascade_actual
            else det_scores.get("consequence_cascade_contract_pass")
        ),
        "consequence_cascade_failure_codes": cascade_failure_codes,
        "narrator_required_when_expected": det_scores.get("narrator_required_when_expected"),
        "narrator_required": narr_expected.get("required"),
        "narrator_present": narr_actual.get("narrator_block_present") or narr_actual.get("consequence_realized"),
        "npc_policy": npc_expected.get("policy"),
        "npc_takeover_absent": (not bool(npc_actual.get("npc_takeover_detected"))) if "npc_takeover_detected" in npc_actual else det_scores.get("npc_takeover_absent"),
        "npc_takeover_detected": npc_actual.get("npc_takeover_detected"),
        "npc_agency_plan_present": bool(npc_agency_rec) if npc_agency_rec else det_scores.get("npc_agency_plan_present"),
        "npc_independent_planning_used": npc_agency_actual.get("independent_planning_used") if "independent_planning_used" in npc_agency_actual else det_scores.get("npc_independent_planning_used"),
        "npc_long_horizon_state_present": npc_agency_actual.get("long_horizon_state_present") if "long_horizon_state_present" in npc_agency_actual else det_scores.get("npc_long_horizon_state_present"),
        "npc_private_plan_resolution_present": npc_agency_actual.get("private_plan_resolution_present") if "private_plan_resolution_present" in npc_agency_actual else det_scores.get("npc_private_plan_resolution_present"),
        "npc_private_plan_visibility_respected": npc_agency_actual.get("private_plan_visibility_respected") if "private_plan_visibility_respected" in npc_agency_actual else det_scores.get("npc_private_plan_visibility_respected"),
        "npc_intention_threads_carried_forward": (
            (
                int(npc_agency_actual.get("intention_threads_carried_forward") or 0) > 0
                or int(npc_agency_actual.get("intention_threads_active") or 0)
                > len(npc_agency_actual.get("candidate_actor_ids") or [])
            )
            if (
                "intention_threads_carried_forward" in npc_agency_actual
                or "intention_threads_active" in npc_agency_actual
            )
            else det_scores.get("npc_intention_threads_carried_forward")
        ),
        "npc_required_initiatives_realized": (
            not bool(npc_agency_actual.get("missing_required_actor_ids"))
            if "missing_required_actor_ids" in npc_agency_actual
            else det_scores.get("npc_required_initiatives_realized")
        ),
        "multi_npc_initiative_realized": npc_agency_actual.get("multi_npc_initiative_realized") if "multi_npc_initiative_realized" in npc_agency_actual else det_scores.get("multi_npc_initiative_realized"),
        "npc_carry_forward_closed": (
            (
                not bool(npc_agency_actual.get("carry_forward_actor_ids"))
                and not bool(npc_agency_actual.get("missing_required_actor_ids"))
            )
            if (
                "carry_forward_actor_ids" in npc_agency_actual
                or "missing_required_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_carry_forward_closed")
        ),
        "npc_forbidden_actor_absent": (
            not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
            and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            if (
                "forbidden_planned_actor_ids" in npc_agency_actual
                or "forbidden_realized_actor_ids" in npc_agency_actual
            )
            else det_scores.get("npc_forbidden_actor_absent")
        ),
        "npc_agency_candidate_actor_ids": npc_agency_actual.get("candidate_actor_ids") or [],
        "npc_agency_missing_required_actor_ids": npc_agency_actual.get("missing_required_actor_ids") or [],
        "npc_agency_claim_readiness_status": claim_readiness.get("claim_status"),
        "npc_agency_full_claim_allowed": claim_readiness.get("full_claim_allowed"),
        "capability_selection_present": bool(cap_rec) if cap_rec else det_scores.get("capability_selection_present"),
        "selected_capabilities": cap_selected.get("selected_capabilities") or [],
        "realized_capabilities": cap_actual.get("realized_capabilities") or [],
        "selected_capabilities_realized": (
            not bool(cap_actual.get("missing_required_capabilities"))
            if "missing_required_capabilities" in cap_actual
            else det_scores.get("selected_capabilities_realized")
        ),
        "forbidden_capability_realized": cap_actual.get("forbidden_capability_realized"),
        "visible_block_origin_present": vis_actual.get("visible_block_origin_present") if "visible_block_origin_present" in vis_actual else det_scores.get("visible_block_origin_present"),
        "visible_origin_present": vis_actual.get("visible_block_origin_present") if "visible_block_origin_present" in vis_actual else det_scores.get("visible_block_origin_present"),
        "narrative_aspect_policy_present": narrative_expected.get("policy_present") if "policy_present" in narrative_expected else det_scores.get("narrative_aspect_policy_present"),
        "narrative_aspect_selected": bool(narrative_selected.get("selected_aspects")) if narrative_selected else det_scores.get("narrative_aspect_selected"),
        "selected_narrative_aspects": narrative_selected.get("selected_aspects") or [],
        "realized_narrative_aspects": narrative_actual.get("realized_aspects") or [],
        "narrative_aspect_visible_when_required": narrative_actual.get("visible_when_required") if "visible_when_required" in narrative_actual else det_scores.get("narrative_aspect_visible_when_required"),
        "narrative_aspect_contract_pass": det_scores.get("narrative_aspect_contract_pass"),
        "theme_tracking_policy_present": narrative_expected.get("theme_tracking_policy_present") if "theme_tracking_policy_present" in narrative_expected else det_scores.get("theme_tracking_policy_present"),
        "theme_tracking_selected": bool(narrative_actual.get("selected_theme_aspects")) if narrative_actual else det_scores.get("theme_tracking_selected"),
        "selected_theme_aspects": narrative_actual.get("selected_theme_aspects") or narrative_selected.get("selected_theme_aspects") or [],
        "realized_theme_aspects": narrative_actual.get("realized_theme_aspects") or [],
        "theme_semantic_classification_present": det_scores.get("theme_semantic_classification_present"),
        "theme_semantic_classification_count": narrative_actual.get("semantic_classification_count"),
        "theme_weak_alignment_count": narrative_actual.get("semantic_weak_alignment_count"),
        "theme_tracking_contract_pass": det_scores.get("theme_tracking_contract_pass"),
        "voice_consistency_policy_present": voice_expected.get("policy_present") if "policy_present" in voice_expected else det_scores.get("voice_consistency_policy_present"),
        "voice_semantic_classification_enabled": voice_expected.get("semantic_classification_enabled"),
        "voice_semantic_classification_present": det_scores.get("voice_semantic_classification_present"),
        "voice_semantic_classification_count": voice_actual.get("semantic_classification_count"),
        "voice_spoken_line_count": voice_actual.get("spoken_line_count"),
        "voice_cross_actor_confusion_absent": (
            voice_cross_actor_count == 0
            if voice_actual
            else det_scores.get("voice_cross_actor_confusion_absent")
        ),
        "voice_cross_actor_confusion_count": voice_cross_actor_count,
        "voice_forbidden_markers_absent": (
            voice_forbidden_marker_count == 0
            if voice_actual
            else det_scores.get("voice_forbidden_markers_absent")
        ),
        "voice_consistency_contract_pass": det_scores.get("voice_consistency_contract_pass"),
        "tonal_consistency_policy_present": (
            tonal_expected.get("policy_present")
            if "policy_present" in tonal_expected
            else det_scores.get("tonal_consistency_policy_present")
        ),
        "tonal_consistency_target_selected": (
            bool(
                tonal_target.get("profile_id")
                or tonal_target.get("target_dimension_ids")
                or tonal_selected.get("required_dimension_ids")
            )
            if tonal_selected
            else det_scores.get("tonal_consistency_target_selected")
        ),
        "tonal_consistency_profile_id": tonal_target.get("profile_id"),
        "tonal_consistency_required_dimensions": tonal_target.get("required_dimension_ids")
        or tonal_selected.get("required_dimension_ids")
        or [],
        "tonal_consistency_realized_dimensions": tonal_actual.get("realized_dimension_ids")
        or [],
        "tonal_consistency_classification_present": (
            tonal_actual.get("structured_classification_present")
            if "structured_classification_present" in tonal_actual
            else det_scores.get("tonal_consistency_classification_present")
        ),
        "tonal_consistency_marker_hits_absent": (
            int(tonal_actual.get("marker_hit_count") or 0) == 0
            if tonal_actual
            else det_scores.get("tonal_consistency_marker_hits_absent")
        ),
        "tonal_consistency_contract_pass": (
            tonal_actual.get("contract_pass")
            if "contract_pass" in tonal_actual
            else det_scores.get("tonal_consistency_contract_pass")
        ),
        "tonal_consistency_failure_codes": tonal_failure_codes,
        "hierarchical_memory_present": memory_actual.get("memory_present") if "memory_present" in memory_actual else det_scores.get("hierarchical_memory_present"),
        "memory_policy_applied": det_scores.get("memory_policy_applied"),
        "selected_memory_tiers": memory_selected.get("selected_tiers") or [],
        "memory_written_item_count": memory_actual.get("written_item_count"),
        "memory_context_item_count": memory_actual.get("context_item_count"),
        "memory_write_from_committed_turn": det_scores.get("memory_write_from_committed_turn"),
        "memory_context_bounded": memory_actual.get("context_bounded") if "context_bounded" in memory_actual else det_scores.get("memory_context_bounded"),
        "hierarchical_memory_contract_pass": det_scores.get("hierarchical_memory_contract_pass"),
        "turn_status": path_summary.get("turn_status"),
        "http_status": path_summary.get("http_status"),
        "main_failure": main_failure,
        "recommended_repair": _runtime_aspect_recommended_repair(main_failure),
    }
    return {col: row.get(col) for col in _RUNTIME_ASPECT_MATRIX_COLUMNS}


def _runtime_aspect_trace_matches_filters(raw_trace: dict[str, Any], arguments: dict[str, Any]) -> bool:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    meta = _extract_metadata(raw_trace)
    trace_origin = arguments.get("trace_origin")
    if trace_origin is not None:
        actual_origin = str(
            meta.get("trace_origin") or path_summary.get("trace_origin") or ""
        ).strip().lower()
        if actual_origin != str(trace_origin).strip().lower():
            return False
    execution_tier = arguments.get("execution_tier")
    if execution_tier is not None:
        actual_tier = str(
            meta.get("execution_tier") or path_summary.get("execution_tier") or ""
        ).strip().lower()
        if actual_tier != str(execution_tier).strip().lower():
            return False
    environment = arguments.get("environment")
    if environment is not None:
        env_target = str(environment).strip().lower()
        env_candidates = (
            raw_trace.get("environment"),
            meta.get("environment"),
            meta.get("langfuse_environment"),
            meta.get("wos_langfuse_environment"),
            path_summary.get("environment"),
            path_summary.get("langfuse_environment"),
        )
        if not any(str(value or "").strip().lower() == env_target for value in env_candidates):
            return False
    if arguments.get("canonical_player_flow") is not None:
        expected = bool(arguments.get("canonical_player_flow"))
        actual = meta.get("canonical_player_flow")
        if actual is None:
            actual = path_summary.get("canonical_player_flow")
        if bool(actual) is not expected:
            return False
    return True


def _runtime_aspect_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
    trace_id = str(arguments.get("trace_id") or arguments.get("langfuse_trace_id") or "").strip()
    if trace_id:
        raw_rows = [_langfuse_get_trace(trace_id)]
    else:
        raw_rows = _langfuse_query_traces(
            limit=int(arguments.get("limit") or 20),
            trace_origin=arguments.get("trace_origin"),
            canonical_player_flow=arguments.get("canonical_player_flow"),
            execution_tier=arguments.get("execution_tier"),
            environment=arguments.get("environment"),
            trace_name=arguments.get("trace_name"),
            trace_names=("backend.turn.execute", "world-engine.turn.execute"),
        )
        raw_rows = [
            _langfuse_get_trace(str(row.get("id") or row.get("trace_id") or "").strip())
            if isinstance(row, dict) and not row.get("observations")
            else row
            for row in raw_rows
            if isinstance(row, dict)
        ]
        if not raw_rows and any(
            arguments.get(key) is not None
            for key in ("trace_origin", "execution_tier", "environment", "canonical_player_flow")
        ):
            broad_rows = _langfuse_query_traces(
                limit=int(arguments.get("limit") or 20),
                trace_origin=None,
                canonical_player_flow=None,
                execution_tier=None,
                environment=None,
                trace_name=arguments.get("trace_name"),
                trace_names=("backend.turn.execute", "world-engine.turn.execute"),
            )
            raw_rows = [
                _langfuse_get_trace(str(row.get("id") or row.get("trace_id") or "").strip())
                if isinstance(row, dict) and not row.get("observations")
                else row
                for row in broad_rows
                if isinstance(row, dict)
            ]
        raw_rows = [
            row
            for row in raw_rows
            if isinstance(row, dict)
            and (row.get("error") or _runtime_aspect_trace_matches_filters(row, arguments))
        ]
    rows = [_runtime_aspect_matrix_row(row) for row in raw_rows if isinstance(row, dict) and not row.get("error")]
    errors = [row for row in raw_rows if isinstance(row, dict) and row.get("error")]
    return {
        "ok": not errors,
        "columns": list(_RUNTIME_ASPECT_MATRIX_COLUMNS),
        "count": len(rows),
        "rows": rows,
        "errors": errors,
    }


def _langfuse_public_get_json(
    *,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tracer = McpLangfuseTracer.get_instance()
    tracer._get_client()  # best effort: ensures backend/env credential fetch happened
    public_key = str(getattr(tracer, "_public_key", "") or "").strip()
    secret_key = str(getattr(tracer, "_secret_key", "") or "").strip()
    # Verify tools are read-only; bypass LANGFUSE_MCP_ENABLED gate if keys still missing.
    # _get_client() returns early when LANGFUSE_MCP_ENABLED≠1, leaving keys empty even
    # when INTERNAL_RUNTIME_CONFIG_TOKEN is present and the backend has credentials.
    if not (public_key and secret_key) and not getattr(tracer, "_credentials_fetched", False):
        tracer._fetch_credentials_from_backend()
        public_key = str(getattr(tracer, "_public_key", "") or "").strip()
        secret_key = str(getattr(tracer, "_secret_key", "") or "").strip()
    base_url = str(getattr(tracer, "_base_url", "") or "").strip()
    if not (public_key and secret_key and base_url):
        return {"error": "langfuse_credentials_unavailable"}
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        resp = requests.get(
            url,
            params=params or {},
            auth=(public_key, secret_key),
            timeout=12.0,
        )
    except Exception as exc:
        return {"error": f"langfuse_http_request_failed:{exc}"}
    if resp.status_code != 200:
        return {"error": f"langfuse_http_{resp.status_code}", "body": resp.text[:400]}
    try:
        return resp.json()
    except Exception as exc:
        return {"error": f"langfuse_json_decode_failed:{exc}"}


def _langfuse_get_trace(trace_id: str) -> dict[str, Any]:
    tracer = McpLangfuseTracer.get_instance()
    client = tracer._get_client()
    if client is not None and hasattr(client, "get_trace"):
        try:
            raw = _to_plain(client.get_trace(trace_id))
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
    payload = _langfuse_public_get_json(endpoint=f"/api/public/traces/{trace_id}")
    if payload.get("error"):
        return payload
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload, dict):
        return payload
    return {"error": "langfuse_trace_unreadable"}


def _langfuse_query_traces(
    *,
    limit: int,
    trace_origin: str | None,
    canonical_player_flow: bool | None,
    execution_tier: str | None = None,
    trace_name: str | None = None,
    trace_names: tuple[str, ...] | None = None,
    environment: str | None = None,
) -> list[dict[str, Any]]:
    payload = _langfuse_public_get_json(
        endpoint="/api/public/traces",
        params={"limit": max(1, min(int(limit), 100))},
    )
    if payload.get("error"):
        return [{"error": payload["error"], "body": payload.get("body")}]
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []
    filtered: list[dict[str, Any]] = []
    env_target = str(environment or "").strip().lower() or None
    for row in rows:
        if not isinstance(row, dict):
            continue
        meta = _extract_metadata(row)
        origin_ok = True
        canonical_ok = True
        if trace_origin is not None:
            origin_ok = str(meta.get("trace_origin") or "").strip().lower() == trace_origin.lower()
        if canonical_player_flow is not None:
            canonical_ok = bool(meta.get("canonical_player_flow")) is canonical_player_flow
        tier_ok = True
        if execution_tier is not None:
            tier_ok = (
                str(meta.get("execution_tier") or "").strip().lower()
                == str(execution_tier).strip().lower()
            )
        name_ok = True
        if trace_name is not None:
            name_ok = str(row.get("name") or "").strip() == str(trace_name).strip()
        elif trace_names:
            allowed_names = {str(name).strip() for name in trace_names if str(name).strip()}
            name_ok = str(row.get("name") or "").strip() in allowed_names
        env_ok = True
        if env_target is not None:
            # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.4: staging environment filter so MCP
            # discovery does not silently drop staging traces. Match either the top-level
            # ``environment`` field Langfuse exposes or the metadata mirror written by
            # ``_align_langfuse_otel_resource_environment`` / world-engine adapter.
            candidates = (
                str(row.get("environment") or "").strip().lower(),
                str(meta.get("environment") or "").strip().lower(),
                str(meta.get("langfuse_environment") or "").strip().lower(),
            )
            env_ok = any(value == env_target for value in candidates if value)
        if origin_ok and canonical_ok and tier_ok and name_ok and env_ok:
            filtered.append(row)
    return filtered


def _assertions_for_mode(mode: str) -> list[tuple[str, bool, str]]:
    if mode == "test":
        return [
            ("trace_origin == pytest", True, "metadata.trace_origin must be pytest"),
            (
                "canonical_player_flow == false",
                True,
                "metadata.canonical_player_flow must be false",
            ),
            (
                "live_opening_contract_pass == 0",
                True,
                "score live_opening_contract_pass must be 0",
            ),
        ]
    return [
        ("trace_origin == live_ui", True, "metadata.trace_origin must be live_ui"),
        ("execution_tier == live", True, "metadata.execution_tier must be live"),
        (
            "canonical_player_flow == true",
            True,
            "metadata.canonical_player_flow must be true",
        ),
        (
            "selected_player_role present",
            True,
            "metadata.selected_player_role must be present",
        ),
        (
            "human_actor_id == selected_player_role",
            True,
            "metadata.human_actor_id must equal selected_player_role",
        ),
        (
            "opening_shape_contract_pass == 1",
            True,
            "score opening_shape_contract_pass must be 1",
        ),
        (
            "live_runtime_contract_pass == 1",
            True,
            "score live_runtime_contract_pass must be 1",
        ),
        (
            "live_opening_contract_pass == 1",
            True,
            "score live_opening_contract_pass must be 1",
        ),
        (
            "final_adapter != ldss_fallback",
            True,
            "metadata.final_adapter must not be ldss_fallback",
        ),
        (
            "quality_class not in [degraded, failed]",
            True,
            "metadata.quality_class must not be degraded/failed",
        ),
    ]


def build_langfuse_verify_mcp_handlers() -> dict[str, Callable[..., dict[str, Any]]]:
    config = Config()
    repo_root = Path(config.repo_root)

    def run_projection_tests(arguments: dict[str, Any]) -> dict[str, Any]:
        python_executable = sys.executable
        extra_pytest_args: list[str] = []
        if arguments.get("extra_pytest_args") and isinstance(arguments["extra_pytest_args"], list):
            extra_pytest_args = [str(x) for x in arguments["extra_pytest_args"] if str(x).strip()]
        evidence_metadata = {
            "evidence_scope": "local_pytest",
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
            "governance_adr": "ADR-0039",
        }

        def _tail(raw: str) -> str:
            return "\n".join((raw or "").splitlines()[-40:])

        def _run_pytest_subprocess(
            *,
            cmd: list[str],
            cwd: Path,
            pythonpath_parts: list[str],
        ) -> dict[str, Any]:
            env = dict(os.environ)
            existing_py_path = str(env.get("PYTHONPATH") or "").strip()
            py_path_parts = [x for x in pythonpath_parts if str(x).strip()]
            if existing_py_path:
                py_path_parts.append(existing_py_path)
            env["PYTHONPATH"] = os.pathsep.join(py_path_parts)
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            return {
                **evidence_metadata,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "command": cmd,
                "cwd": str(cwd),
                "pythonpath": env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(proc.stdout),
                "stderr_tail": _tail(proc.stderr),
            }

        world_engine_path = repo_root / "world-engine"
        world_engine_cwd = world_engine_path
        world_engine_py_path = [str(world_engine_path), str(repo_root)]
        world_engine_preflight_env = dict(os.environ)
        existing_preflight_path = str(world_engine_preflight_env.get("PYTHONPATH") or "").strip()
        if existing_preflight_path:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(
                [*world_engine_py_path, existing_preflight_path]
            )
        else:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(world_engine_py_path)
        preflight_cmd = [
            python_executable,
            "-c",
            "import app.story_runtime; print('import_ok=app.story_runtime')",
        ]
        preflight = subprocess.run(
            preflight_cmd,
            cwd=str(world_engine_cwd),
            env=world_engine_preflight_env,
            text=True,
            capture_output=True,
            check=False,
        )
        if preflight.returncode != 0:
            world_engine_result = {
                **evidence_metadata,
                "ok": False,
                "returncode": preflight.returncode,
                "command": preflight_cmd,
                "cwd": str(world_engine_cwd),
                "pythonpath": world_engine_preflight_env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(preflight.stdout),
                "stderr_tail": _tail(preflight.stderr),
            }
            ai_stack_result = {
                **evidence_metadata,
                "ok": False,
                "returncode": None,
                "command": [
                    python_executable,
                    "-m",
                    "pytest",
                    "ai_stack/tests/test_actor_lane_absence_governance.py",
                    "-q",
                    *extra_pytest_args,
                ],
                "cwd": str(repo_root),
                "pythonpath": "",
                "stdout_tail": "",
                "stderr_tail": "skipped_due_to_world_engine_preflight_failure",
            }
            return {
                **evidence_metadata,
                "ok": False,
                "world_engine": world_engine_result,
                "ai_stack": ai_stack_result,
            }

        world_engine_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "tests/test_trace_middleware.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=world_engine_cwd,
            pythonpath_parts=world_engine_py_path,
        )
        ai_stack_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "ai_stack/tests/test_actor_lane_absence_governance.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=repo_root,
            pythonpath_parts=[str(repo_root)],
        )
        return {
            **evidence_metadata,
            "ok": bool(world_engine_result["ok"] and ai_stack_result["ok"]),
            "world_engine": world_engine_result,
            "ai_stack": ai_stack_result,
        }

    def fetch_langfuse_trace(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if not trace_id:
            return {"error": "langfuse_trace_id required"}
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        evidence, sources = _extract_normalized_wos_evidence(raw)
        return {
            "ok": True,
            "trace": _trace_summary(raw),
            "raw_trace": raw,
            "normalized_wos_evidence": evidence,
            "evidence_sources": sources,
        }

    def query_langfuse_traces(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 10)
        trace_origin = arguments.get("trace_origin")
        cpf_raw = arguments.get("canonical_player_flow")
        canonical_player_flow = (
            bool(cpf_raw)
            if isinstance(cpf_raw, bool)
            else None
        )
        exec_tier = arguments.get("execution_tier")
        trace_nm = arguments.get("trace_name")
        env_arg = arguments.get("environment")
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin=str(trace_origin) if isinstance(trace_origin, str) else None,
            canonical_player_flow=canonical_player_flow,
            execution_tier=str(exec_tier).strip()
            if isinstance(exec_tier, str) and str(exec_tier).strip()
            else None,
            trace_name=str(trace_nm).strip()
            if isinstance(trace_nm, str) and str(trace_nm).strip()
            else None,
            environment=str(env_arg).strip()
            if isinstance(env_arg, str) and str(env_arg).strip()
            else None,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"], "details": rows[0].get("body")}
        return {"ok": True, "count": len(rows), "traces": [_trace_summary(x) for x in rows]}

    def assert_langfuse_opening_contract(arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode") or "live").strip().lower()
        if mode not in {"live", "test"}:
            return {"ok": False, "error": "mode must be live or test"}
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if trace_id:
            raw = _langfuse_get_trace(trace_id)
            if raw.get("error"):
                return {"ok": False, "error": raw["error"], "missing_field": "trace"}
        else:
            origin = "live_ui" if mode == "live" else "pytest"
            rows = _langfuse_query_traces(
                limit=int(arguments.get("limit") or 10),
                trace_origin=origin,
                canonical_player_flow=True if mode == "live" else False,
            )
            if not rows or (isinstance(rows[0], dict) and rows[0].get("error")):
                return {"ok": False, "error": "no_matching_trace_found", "missing_field": "trace"}
            raw = rows[0]
            trace_id = str(raw.get("id") or "")

        ev, _src = _extract_normalized_wos_evidence(raw)
        failures: list[dict[str, Any]] = []

        def fail(rule: str, message: str, field: str, actual: Any) -> None:
            failures.append(
                {"rule": rule, "message": message, "missing_field": field, "actual": actual}
            )

        if mode == "live":
            if str(ev.get("trace_origin") or "").lower() != "live_ui":
                fail("trace_origin == live_ui", "live trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if str(ev.get("execution_tier") or "").lower() != "live":
                fail("execution_tier == live", "execution tier mismatch", "normalized.execution_tier", ev.get("execution_tier"))
            if bool(ev.get("canonical_player_flow")) is not True:
                fail("canonical_player_flow == true", "canonical flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            role = str(ev.get("selected_player_role") or "").strip().lower()
            if not role:
                fail("selected_player_role present", "role missing", "normalized.selected_player_role", ev.get("selected_player_role"))
            if str(ev.get("human_actor_id") or "").lower() != role:
                fail("human_actor_id == selected_player_role", "human actor mismatch", "normalized.human_actor_id", ev.get("human_actor_id"))
            for score_name in (
                "opening_shape_contract_pass",
                "live_runtime_contract_pass",
                "live_opening_contract_pass",
            ):
                if float(ev.get(score_name) or 0.0) != 1.0:
                    fail(f"{score_name} == 1", "score mismatch", f"scores.{score_name}", ev.get(score_name))
            if str(ev.get("final_adapter") or "").lower() == "ldss_fallback":
                fail("final_adapter != ldss_fallback", "fallback adapter used", "normalized.final_adapter", ev.get("final_adapter"))
            if str(ev.get("quality_class") or "").lower() in {"degraded", "failed"}:
                fail("quality_class not degraded/failed", "quality class degraded", "normalized.quality_class", ev.get("quality_class"))
        else:
            if str(ev.get("trace_origin") or "").lower() != "pytest":
                fail("trace_origin == pytest", "test trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if bool(ev.get("canonical_player_flow")) is not False:
                fail("canonical_player_flow == false", "test flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            if float(ev.get("live_opening_contract_pass") or 0.0) != 0.0:
                fail(
                    "live_opening_contract_pass == 0",
                    "test trace has live opening pass",
                    "scores.live_opening_contract_pass",
                    ev.get("live_opening_contract_pass"),
                )

        return {
            "ok": len(failures) == 0,
            "trace_id": trace_id,
            "mode": mode,
            "failures": failures,
            "trace": _trace_summary(raw),
            "assertion_count": len(_assertions_for_mode(mode)),
        }

    def summarize_live_opening_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 20)
        exec_tier = arguments.get("execution_tier")
        trace_nm = arguments.get("trace_name")
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin="live_ui",
            canonical_player_flow=True,
            execution_tier=str(exec_tier).strip()
            if isinstance(exec_tier, str) and str(exec_tier).strip()
            else None,
            trace_name=str(trace_nm).strip()
            if isinstance(trace_nm, str) and str(trace_nm).strip()
            else None,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ev, _src = _extract_normalized_wos_evidence(row)
            det_scores, _ = _extract_scores_split(row)
            is_opening = _is_opening_trace(row)
            lo_val = _live_opening_value(det_scores, row)
            matrix.append(
                {
                    "trace_id": row.get("id"),
                    "trace_name": row.get("name"),
                    "is_opening_trace": is_opening,
                    "selected_player_role": ev.get("selected_player_role"),
                    "trace_origin": ev.get("trace_origin"),
                    "execution_tier": ev.get("execution_tier"),
                    "canonical_player_flow": ev.get("canonical_player_flow"),
                    "opening_shape_contract_pass": ev.get("opening_shape_contract_pass"),
                    "live_runtime_contract_pass": ev.get("live_runtime_contract_pass"),
                    "live_opening_contract_pass": lo_val,
                    "final_adapter": ev.get("final_adapter"),
                    "quality_class": ev.get("quality_class"),
                    "narration_summary_synthesized": _extract_metadata(row).get("narration_summary_synthesized"),
                }
            )
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(matrix),
            "rows": matrix,
        }

    def fetch_langfuse_trace_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        allow_non_live = bool(arguments.get("allow_non_live", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        meta = _extract_metadata(raw)
        if not allow_non_live:
            origin = str(meta.get("trace_origin") or "").lower()
            tier = str(meta.get("execution_tier") or "").lower()
            cpf = bool(meta.get("canonical_player_flow"))
            if origin != "live_ui" or tier != "live" or not cpf:
                return {
                    "ok": False,
                    "error": "trace_filtered_as_non_live",
                    "reason": (
                        "trace_origin, execution_tier, or canonical_player_flow does not match "
                        "live evidence criteria (live_ui / live / true)"
                    ),
                    "actual": {
                        "trace_origin": meta.get("trace_origin"),
                        "execution_tier": meta.get("execution_tier"),
                        "canonical_player_flow": meta.get("canonical_player_flow"),
                    },
                    "hint": "Pass allow_non_live: true to inspect non-live traces",
                }
        det_scores, judge_scores = _extract_scores_split(raw)
        is_opening = _is_opening_trace(raw)
        lo_val = _live_opening_value(det_scores, raw)
        enriched_det = dict(det_scores)
        enriched_det["live_opening_contract_pass"] = lo_val
        sm = _first_score_metadata(raw) or {}
        opening_shape_diagnostics = {
            k: sm.get(k)
            for k in (
                "opening_shape_subgates",
                "opening_shape_failure_reasons",
                "scene_block_summary",
                "first_actor_block_index",
                "narrator_block_count",
                "structured_narration_summary_kind",
                "opening_narration_normalized",
                "opening_narration_source",
                "opening_narration_beat_count",
                "narration_summary_input_kind",
            )
            if sm.get(k) is not None
        }
        return {
            "ok": True,
            "trace_id": trace_id,
            "is_opening_trace": is_opening,
            "trace_name": raw.get("name"),
            "trace_origin": meta.get("trace_origin"),
            "execution_tier": meta.get("execution_tier"),
            "canonical_player_flow": meta.get("canonical_player_flow"),
            "selected_player_role": meta.get("selected_player_role"),
            "human_actor_id": meta.get("human_actor_id"),
            "deterministic_scores": enriched_det,
            "judge_scores": judge_scores,
            "opening_shape_diagnostics": opening_shape_diagnostics,
            "canonical_live_langfuse_filters": {
                "opening_evaluators": {
                    "trace.name": "world-engine.session.create",
                    "world_engine_generation_observation.name": "story.model.generation",
                    "trace_origin": "live_ui",
                    "execution_tier": "live",
                    "canonical_player_flow": True,
                    "observation_filters": dict(OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "legacy_trace_names_for_search_only": LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE[
                        "legacy_trace_names_for_search_only"
                    ],
                    "trace_metadata_when_available": dict(
                        LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE["metadata"]
                    ),
                },
                "opening_generation_categorical_evaluators": {
                    "judges": list(_judge_names_for_scope("opening_generation")),
                    "observation_filters": dict(OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "legacy_trace_names_for_search_only": LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE[
                        "legacy_trace_names_for_search_only"
                    ],
                    "trace_metadata_when_available": dict(
                        LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE["metadata"]
                    ),
                },
                "turn_evaluators": {
                    "primary_trace_name": WORLD_ENGINE_TURN_TRACE_NAME,
                    "alternate_backend_root_trace_name": BACKEND_TURN_ROOT_TRACE_NAME,
                    "distributed_trace_note": (
                        f"Backend opens {BACKEND_TURN_ROOT_TRACE_NAME}; world-engine participates with "
                        f"{WORLD_ENGINE_TURN_TRACE_NAME} on the same Langfuse trace. Prefer GENERATION "
                        "story.model.generation scoped to the world-engine turn span when attaching judges."
                    ),
                    "world_engine_turn_observation_name": WORLD_ENGINE_TURN_TRACE_NAME,
                    "trace_origin": "live_ui",
                    "execution_tier": "live",
                    "canonical_player_flow": True,
                },
                # Langfuse evaluator UI: attach scores to GENERATION on story.model.generation
                # under live turn traces (WoS canonical live metadata when available).
                "turn_generation_categorical_evaluators": {
                    "judges": list(_judge_names_for_scope("turn_generation")),
                    "observation_filters": dict(TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS),
                    "alternate_backend_root_trace_names": list(
                        LANGFUSE_TURN_GENERATION_FILTER_BUNDLE.get("legacy_trace_names") or []
                    ),
                    "trace_metadata_when_available": {
                        "trace_origin": "live_ui",
                        "execution_tier": "live",
                        "canonical_player_flow": True,
                        "opening_turn": False,
                    },
                },
            },
            "categorical_judge_names": list(WOS_CATEGORICAL_JUDGES_ORDER),
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
            "llm_judge_interpretation": _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(raw.get("name") or ""),
            ),
            "judge_score_coverage_gaps": _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            ),
            "evaluator_column_metadata": _evaluator_column_metadata(),
        }

    def summarize_opening_judge_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_origin = str(arguments.get("trace_origin") or "live_ui").strip()
        execution_tier = str(arguments.get("execution_tier") or "live").strip()
        cpf_arg = arguments.get("canonical_player_flow")
        canonical_player_flow = bool(cpf_arg) if isinstance(cpf_arg, bool) else True
        trace_nm = arguments.get("trace_name")
        trace_name_filter = (
            str(trace_nm).strip() if isinstance(trace_nm, str) and str(trace_nm).strip() else None
        )
        roles_raw = arguments.get("roles")
        roles = (
            [str(r).strip().lower() for r in roles_raw if str(r).strip()]
            if isinstance(roles_raw, list)
            else None
        )
        limit_per_role = int(arguments.get("limit_per_role") or 5)
        fetch_limit = min(max(limit_per_role * (len(roles) if roles else 2) * 4, 20), 100)
        rows = _langfuse_query_traces(
            limit=fetch_limit,
            trace_origin=trace_origin,
            canonical_player_flow=canonical_player_flow,
            execution_tier=execution_tier,
            trace_name=trace_name_filter,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        role_counts: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            meta = _extract_metadata(row)
            score_meta_row = _first_score_metadata(row)
            role = str(
                meta.get("selected_player_role") or score_meta_row.get("selected_player_role") or ""
            ).strip().lower() or None
            if roles is not None and role not in roles:
                continue
            r_key = role or "unknown"
            if role_counts.get(r_key, 0) >= limit_per_role:
                continue
            role_counts[r_key] = role_counts.get(r_key, 0) + 1
            det_scores, judge_scores = _extract_scores_split(row)
            lo_val = _live_opening_value(det_scores, row)
            is_opening = _is_opening_trace(row)

            def _jcat(jname: str, _j: dict = judge_scores) -> str | None:
                j = _j.get(jname)
                if not j:
                    return None
                return j.get("category")

            if lo_val == "not_applicable":
                live_opening_str = "not_applicable"
            elif lo_val == 1.0:
                live_opening_str = "pass"
            elif lo_val == 0.0:
                live_opening_str = "fail"
            else:
                live_opening_str = str(lo_val or "—")
            main_issue: str | None = None
            if lo_val == 0.0 and is_opening:
                main_issue = "live_opening_fail"
            elif det_scores.get("live_runtime_contract_pass") == 0.0:
                main_issue = "runtime_contract_fail"
            else:
                for jname in WOS_CATEGORICAL_JUDGES_ORDER:
                    cat = _jcat(jname)
                    if _judge_category_triggers_issue(jname, cat):
                        main_issue = jname
                        break
            row_out: dict[str, Any] = {
                "role": role,
                "trace_id": row.get("id"),
                "trace_name": row.get("name"),
                "is_opening_trace": is_opening,
                "live_opening": live_opening_str,
                "main_issue": main_issue,
            }
            sev_by_col: dict[str, Any] = {}
            for jname, col_key in _MATRIX_JUDGE_COLUMN_KEYS.items():
                cat = _jcat(jname)
                row_out[col_key] = cat
                sev_by_col[col_key] = _category_severity(jname, cat)
            row_out["judge_category_severity"] = sev_by_col
            row_out["llm_judge_interpretation"] = _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(row.get("name") or ""),
            )
            row_out["judge_score_coverage_gaps"] = _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            )
            matrix.append(row_out)
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filter": {
                "trace_origin": trace_origin,
                "execution_tier": execution_tier,
                "canonical_player_flow": canonical_player_flow,
                "trace_name": trace_name_filter,
                "roles": roles,
                "limit_per_role": limit_per_role,
            },
            "count": len(matrix),
            "matrix": matrix,
            "evaluator_column_metadata": _evaluator_column_metadata(),
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
        }

    def build_opening_quality_context(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        include_raw_reasoning = bool(arguments.get("include_raw_reasoning", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"]}
        meta = _extract_metadata(raw)
        origin = str(meta.get("trace_origin") or "").lower()
        cpf = bool(meta.get("canonical_player_flow"))
        if origin != "live_ui" or not cpf:
            return {
                "ok": False,
                "error": "trace_not_live_evidence",
                "reason": (
                    "build_opening_quality_context only interprets live_ui traces "
                    "with canonical_player_flow=true"
                ),
                "actual": {
                    "trace_origin": meta.get("trace_origin"),
                    "canonical_player_flow": meta.get("canonical_player_flow"),
                },
            }
        det_scores, judge_scores = _extract_scores_split(raw)
        is_opening = _is_opening_trace(raw)
        score_meta = _first_score_metadata(raw)
        role = str(
            meta.get("selected_player_role") or score_meta.get("selected_player_role") or ""
        ).strip().title() or "Unknown"
        lo_val = _live_opening_value(det_scores, raw)
        live_runtime = float(det_scores.get("live_runtime_contract_pass") or 0.0)

        def _jcat(name: str) -> str | None:
            j = judge_scores.get(name)
            return (j or {}).get("category") if j else None

        recommended_next_card: str | None = None
        must_not_change = [
            "Do not weaken live_opening_contract_pass",
            "Do not let LLM judge override deterministic actor-lane gates",
        ]
        summary_parts: list[str] = [f"This {role} live opening"] if is_opening else [f"This {role} live continuation trace"]
        if lo_val == "not_applicable":
            summary_parts.append(
                "is a continuation turn (turn 1+); live_opening_contract_pass is not evaluated here."
            )
        elif lo_val < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append(
                "failed deterministic runtime gates — contract repair required before quality work."
            )
            must_not_change.append("Do not attempt style/content repairs until runtime gates pass")
        elif live_runtime < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append("failed live_runtime_contract_pass — runtime repair required.")
        else:
            summary_parts.append("passed deterministic runtime gates")
            judge_issue_labels: list[str] = []
            detail_parts: list[str] = []
            for full in WOS_CATEGORICAL_JUDGES_ORDER:
                cat = _jcat(full)
                short = _JUDGE_DISPLAY_SHORT.get(full, full.replace("_", " "))
                if cat:
                    sev = _category_severity(full, cat)
                    detail_parts.append(f"{short}: {cat} ({sev})")
                if _judge_category_triggers_issue(full, cat):
                    judge_issue_labels.append(short.replace("-", "_").replace(" ", "_"))
                    if not recommended_next_card:
                        recommended_next_card = _JUDGE_TO_REPAIR_CARD.get(full)
                    if full == "actor_lane_narrative_violation_judge":
                        must_not_change.append(
                            "Deterministic actor-lane gate is authoritative — judge is advisory only"
                        )
            if detail_parts:
                summary_parts.append(f"({', '.join(detail_parts)})")
            if judge_issue_labels:
                summary_parts.append(
                    f". Main improvement targets: {', '.join(judge_issue_labels)}."
                )
            else:
                summary_parts.append(". No judge issues detected.")
        evidence_judges: dict[str, Any] = {}
        qualitative_concerns: list[str] = []
        neutral_judge_labels: list[str] = []
        for jname, detail in judge_scores.items():
            entry: dict[str, Any] = {"category": detail.get("category"), "value": detail.get("value")}
            if include_raw_reasoning and detail.get("reasoning"):
                entry["reasoning"] = detail["reasoning"]
            cat = (detail or {}).get("category")
            norm = _normalize_judge_category_label(jname, str(cat) if cat is not None else None)
            sev = _category_severity(jname, norm)
            entry["normalized_category"] = norm
            entry["category_severity"] = sev
            evidence_judges[jname] = entry
            if sev in {"failure", "warning"}:
                qualitative_concerns.append(f"{jname}:{norm or cat}({sev})")
            elif sev == "neutral":
                neutral_judge_labels.append(f"{jname}:{norm or cat}")
        enriched_det = dict(det_scores)
        enriched_det["live_opening_contract_pass"] = lo_val
        det_gate_fail = bool(lo_val != "not_applicable" and lo_val < 1.0) or live_runtime < 1.0
        return {
            "ok": True,
            "trace_id": trace_id,
            "is_opening_trace": is_opening,
            "trace_name": raw.get("name"),
            "ai_context_summary": " ".join(summary_parts),
            "recommended_next_card": recommended_next_card,
            "must_not_change": must_not_change,
            "evidence": {"deterministic": enriched_det, "judges": evidence_judges},
            "canonical_evaluator_definition_doc": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
            "llm_judge_interpretation": _build_llm_judge_interpretation(
                judge_scores,
                trace_context=str(raw.get("name") or ""),
            ),
            "judge_score_coverage_gaps": _judge_score_coverage_gaps(
                is_opening=is_opening,
                judge_scores=judge_scores,
            ),
            "deterministic_vs_qualitative": {
                "deterministic_gate_failure": det_gate_fail,
                "qualitative_concerns": qualitative_concerns,
                "neutral_or_missing_evidence_labels": neutral_judge_labels,
            },
        }

    def summarize_runtime_aspect_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
        return _runtime_aspect_matrix(arguments)

    def summarize_beat_realization_failures(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            row for row in matrix.get("rows", [])
            if row.get("selected_beat") and row.get("beat_realized") not in {True, 1, 1.0}
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "beat_realization_failures"}

    def summarize_narrator_npc_authority(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "trace_id",
                    "turn_number",
                    "raw_input",
                    "narrator_required",
                    "narrator_present",
                    "npc_policy",
                    "npc_takeover_detected",
                    "main_failure",
                    "recommended_repair",
                )
            }
            for row in matrix.get("rows", [])
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "narrator_npc_authority"}

    def summarize_capability_realization(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "trace_id",
                    "turn_number",
                    "raw_input",
                    "selected_capabilities",
                    "realized_capabilities",
                    "forbidden_capability_realized",
                    "main_failure",
                    "recommended_repair",
                )
            }
            for row in matrix.get("rows", [])
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "capability_realization"}

    def summarize_visible_projection_origin_loss(arguments: dict[str, Any]) -> dict[str, Any]:
        matrix = _runtime_aspect_matrix(arguments)
        rows = [
            row for row in matrix.get("rows", [])
            if row.get("visible_origin_present") not in {True, 1, 1.0}
        ]
        return {**matrix, "count": len(rows), "rows": rows, "summary_kind": "visible_projection_origin_loss"}

    return {
        "run_projection_tests": run_projection_tests,
        "fetch_langfuse_trace": fetch_langfuse_trace,
        "query_langfuse_traces": query_langfuse_traces,
        "assert_langfuse_opening_contract": assert_langfuse_opening_contract,
        "summarize_live_opening_matrix": summarize_live_opening_matrix,
        "fetch_langfuse_trace_scores": fetch_langfuse_trace_scores,
        "summarize_opening_judge_scores": summarize_opening_judge_scores,
        "build_opening_quality_context": build_opening_quality_context,
        "summarize_runtime_aspect_matrix": summarize_runtime_aspect_matrix,
        "summarize_beat_realization_failures": summarize_beat_realization_failures,
        "summarize_narrator_npc_authority": summarize_narrator_npc_authority,
        "summarize_capability_realization": summarize_capability_realization,
        "summarize_visible_projection_origin_loss": summarize_visible_projection_origin_loss,
    }
