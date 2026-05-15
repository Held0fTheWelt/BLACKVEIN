from __future__ import annotations

import logging
import os
import re
import threading
import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    greeting_imperative_addressee_fragment,
    greeting_imperative_visible_pair,
    resolve_string,
)
from story_runtime_core.player_input_intent_contract import (
    FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES,
    INTENT_CONTRACT_VERSION,
    PLAYER_INPUT_KINDS,
    is_perception_like_player_input_kind,
    is_question_punctuation_probe_guarded,
    is_speech_like_player_input_kind,
    player_input_kind_family,
)
from story_runtime_core.branching import (
    BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES,
    BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
    BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_EVENT_TREE_EXPIRED,
    BRANCHING_TIMELINE_SCOPE_ACTIVE,
    BRANCHING_TREE_STATUS_COMMITTED,
    BRANCHING_TREE_STATUS_EXPIRED,
    BRANCHING_TREE_STATUS_NOT_APPLICABLE,
    BRANCHING_TREE_STATUS_SIMULATED,
    BRANCHING_TREE_STATUS_STALE,
    append_simulation_node,
    branch_tree_is_fresh,
    branch_tree_path_nodes,
    clamp_simulation_limits,
    find_branch_tree_node,
    finalize_simulation_tree,
    forecast_has_options,
    make_branch_tree_record,
    make_simulated_turn_node,
    make_simulation_tree,
    mark_branch_tree_committed,
    mark_branch_tree_expired,
    mark_branch_tree_stale,
    simulated_input_for_branch_option,
    build_branching_forecast,
    append_branch_timeline_event,
    archive_branch_timeline,
    compact_branch_timeline,
    make_branch_timeline_event,
    make_branch_timeline_record,
    stable_branch_timeline_id,
)
from story_runtime_core.callbacks import (
    build_graph_callback_web_export,
    build_callback_web_record,
    stable_callback_web_id,
)
from story_runtime_core.consequences import (
    build_consequence_cascade_record,
    build_graph_consequence_cascade_export,
    stable_consequence_cascade_id,
)
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from ai_stack import (
    RuntimeTurnGraphExecutor,
    build_runtime_retriever,
    create_default_capability_registry,
)
from ai_stack.rag_retrieval_dtos import retrieval_config_from_governed
from ai_stack.runtime_quality_semantics import canonical_quality_class
from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_CALLBACK_WEB,
    ASPECT_COMMIT,
    ASPECT_CONSEQUENCE_CASCADE,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_HIERARCHICAL_MEMORY,
    ASPECT_INFORMATION_DISCLOSURE,
    ASPECT_INPUT,
    ASPECT_NARRATIVE_ASPECT,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_PACING_RHYTHM,
    ASPECT_SCENE_ENERGY,
    ASPECT_VALIDATION,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_VISIBLE_PROJECTION,
    aspect_score_metadata,
    ensure_runtime_aspect_ledger,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    normalize_runtime_aspect_ledger,
    set_aspect_record,
)
from ai_stack.callback_web_contracts import (
    callback_web_aspect_blocks,
    callback_web_bounds_from_policy,
    callback_web_policy_from_module_runtime,
    normalize_callback_web_policy,
    validate_callback_web_record,
)
from ai_stack.consequence_cascade_contracts import (
    consequence_cascade_aspect_blocks,
    consequence_cascade_bounds_from_policy,
    consequence_cascade_policy_from_module_runtime,
    normalize_consequence_cascade_policy,
    validate_consequence_cascade_record,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.environment_state_contracts import (
    build_environment_model,
    normalize_environment_state,
)
from ai_stack.hierarchical_memory_contracts import (
    build_hierarchical_memory_write,
    empty_hierarchical_memory_snapshot,
    merge_hierarchical_memory_snapshot,
    normalize_hierarchical_memory_snapshot,
    project_hierarchical_memory_context,
)
from ai_stack.narrative_aspect_contracts import validate_narrative_aspects
from ai_stack.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_LOCATION_TRANSITION_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    PLAYER_ACTION_REQUEST,
    PLAYER_MOVEMENT_REQUEST,
    PLAYER_OBJECT_INTERACTION_REQUEST,
    PLAYER_PERCEPTION_REQUEST,
    PLAYER_SPEECH_REQUEST,
)
from ai_stack.visible_origin_contracts import (
    EVIDENCE_REQUIRED,
    EVIDENCE_SUPPORTING,
    REQUIRED_VISIBLE_ORIGIN_KEYS,
    block_has_required_origin,
    preserve_folded_origin_metadata,
    visible_origin_from_block,
)
from ai_stack.runtime_turn_contracts import (
    DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED,
    DEGRADATION_SIGNAL_DEGRADED_COMMIT,
    DEGRADATION_SIGNAL_FALLBACK_USED,
    DEGRADATION_SIGNAL_NON_FACTUAL_STAGING,
    DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY,
    DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
    DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE,
    DEGRADATION_SIGNAL_VALUES,
    DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED,
    QUALITY_CLASS_DEGRADED,
    QUALITY_CLASS_FAILED,
    QUALITY_CLASS_VALUES,
)
from ai_stack.story_runtime_playability import is_hard_boundary_failure
from ai_stack.live_dramatic_scene_simulator import (
    LDSSInput,
    build_ldss_input_from_session,
    build_scene_turn_envelope_v2,
    run_ldss,
)
from ai_stack.diagnostics_envelope import (
    DegradationEvent,
    build_diagnostics_envelope,
    build_narrative_gov_summary,
)
from ai_stack.runtime_cost_attribution import aggregate_phase_costs, build_deterministic_phase_cost
from ai_stack.narrative import NarrativeRuntimeAgent, NarrativeRuntimeAgentInput, NarrativeEventKind
from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id, expand_goc_actor_id_aliases
from ai_stack.goc_npc_transcript_projection import (
    goc_transcript_policy_flags,
    split_merged_goc_actor_line_segments,
)
from ai_stack.goc_opening_handover import (
    compute_opening_handover_from_scene_blocks,
    polish_first_opening_actor_block,
    role_display_name as _role_display_name,
)
from ai_stack.goc_knowledge_runtime_gates import (
    build_knowledge_path_summary,
    build_narrator_packet,
)
from ai_stack.semantic_move_contract import SEMANTIC_MOVE_TYPES
from ai_stack.opening_shape_normalizer import normalize_opening_narration_beats
from ai_stack.visible_narrative_contract import (
    _goc_visible_lane_text_fold,
    dedupe_goc_speaker_colon_stutter_visible,
    finalize_visible_scene_blocks,
    prune_goc_actor_actions_subsumed_by_prior_actor_lines,
    sanitize_visible_block_text,
)

from app.config import APP_VERSION
from app.repo_root import resolve_wos_repo_root
from app.observability.audit_log import log_story_runtime_failure, log_story_turn_event
from app.observability.langfuse_adapter import LangfuseAdapter
from app.observability.runtime_metrics import StoryRuntimeMetrics
from app.observability.trace import get_langfuse_trace_id
from app.story_runtime.governed_runtime import build_governed_story_runtime_components
from app.story_runtime.live_governance import (
    BlockedLiveStoryRoutingPolicy,
    LiveStoryGovernanceError,
    is_governed_resolved_config_operational,
    opening_text_contains_preview_placeholder,
)
from app.story_runtime.commit_models import (
    BeatProgression,
    resolve_narrative_commit,
)
from app.story_runtime.canonical_turn_lifecycle import TurnLifecycleChain
from app.story_runtime.branch_timeline_store import JsonBranchTimelineStore
from app.story_runtime.branching_tree_store import JsonBranchingTreeStore
from app.story_runtime.callback_web_store import JsonCallbackWebStore
from app.story_runtime.consequence_cascade_store import JsonConsequenceCascadeStore
from app.story_runtime.story_session_store import JsonStorySessionStore
from app.story_runtime.module_turn_hooks import (
    GOD_OF_CARNAGE_MODULE_ID,
    goc_append_continuity_impacts,
    goc_host_experience_template,
    goc_npc_shell_legal_name,
    goc_prior_continuity_for_graph,
    goc_player_role_display_name,
    goc_shell_actor_firstname,
)
from app.story_runtime.narrative_threads import (
    NARRATIVE_COMMIT_HISTORY_TAIL,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    build_graph_thread_export,
    thread_continuity_metrics,
    update_narrative_threads,
)


def _goc_content_modules_root() -> Path:
    return resolve_wos_repo_root() / "content" / "modules"


SUPPORTED_LIVE_STORY_MODULE_IDS = (GOD_OF_CARNAGE_MODULE_ID,)


class StorySessionContractError(ValueError):
    """Raised when a direct story-session create violates the governed runtime contract."""


def _require_non_empty_string(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise StorySessionContractError(f"{field_name} is required for governed live story sessions.")
    return text


def _validate_runtime_projection_contract(module_id: str, runtime_projection: dict[str, Any]) -> None:
    if module_id != GOD_OF_CARNAGE_MODULE_ID:
        return

    if not isinstance(runtime_projection, dict):
        raise StorySessionContractError("runtime_projection must be a JSON object.")

    projection_module_id = str(runtime_projection.get("module_id") or "").strip()
    if projection_module_id and projection_module_id != module_id:
        raise StorySessionContractError(
            "runtime_projection.module_id must match the requested module_id for governed live sessions."
        )

    human_actor_id = _require_non_empty_string(runtime_projection.get("human_actor_id"), "human_actor_id")
    selected_player_role = _require_non_empty_string(
        runtime_projection.get("selected_player_role"),
        "selected_player_role",
    )
    if selected_player_role != human_actor_id:
        raise StorySessionContractError(
            "selected_player_role must match human_actor_id for the canonical single-human live runtime path."
        )

    raw_npc_actor_ids = runtime_projection.get("npc_actor_ids")
    if not isinstance(raw_npc_actor_ids, list) or not raw_npc_actor_ids:
        raise StorySessionContractError("npc_actor_ids must contain the AI-controlled cast for governed live sessions.")
    npc_actor_ids = [str(item).strip() for item in raw_npc_actor_ids if str(item).strip()]
    if not npc_actor_ids:
        raise StorySessionContractError("npc_actor_ids must contain non-empty actor ids.")
    if human_actor_id in npc_actor_ids:
        raise StorySessionContractError("human_actor_id cannot also appear in npc_actor_ids.")

    actor_lanes = runtime_projection.get("actor_lanes")
    if not isinstance(actor_lanes, dict) or not actor_lanes:
        raise StorySessionContractError("actor_lanes is required for governed live sessions.")

    human_lane = str(actor_lanes.get(human_actor_id) or "").strip().lower()
    if human_lane != "human":
        raise StorySessionContractError("actor_lanes must mark human_actor_id with lane='human'.")

    missing_npcs = [actor_id for actor_id in npc_actor_ids if str(actor_lanes.get(actor_id) or "").strip().lower() != "npc"]
    if missing_npcs:
        raise StorySessionContractError(
            f"actor_lanes must mark every npc_actor_id with lane='npc' (missing: {', '.join(missing_npcs)})."
        )


def _recoverable_runtime_aspect_ledger(
    *,
    session_id: str,
    module_id: str,
    turn_number: int,
    turn_kind: str,
    player_input: str,
    trace_id: str | None,
    reason: str,
    validation_status: str = "rejected",
    existing_ledger: dict[str, Any] | None = None,
    visible_output_present: bool = True,
) -> dict[str, Any]:
    """Return a ledger for a playable rejected turn path."""
    ledger = ensure_runtime_aspect_ledger(
        existing_ledger,
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=player_input,
        trace_id=trace_id,
    )
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    existing_validation = aspects.get(ASPECT_VALIDATION) if isinstance(aspects.get(ASPECT_VALIDATION), dict) else {}
    existing_commit = aspects.get(ASPECT_COMMIT) if isinstance(aspects.get(ASPECT_COMMIT), dict) else {}
    existing_visible = (
        aspects.get(ASPECT_VISIBLE_PROJECTION)
        if isinstance(aspects.get(ASPECT_VISIBLE_PROJECTION), dict)
        else {}
    )
    existing_validation_expected = (
        existing_validation.get("expected")
        if isinstance(existing_validation.get("expected"), dict)
        else {}
    )
    existing_validation_actual = (
        existing_validation.get("actual")
        if isinstance(existing_validation.get("actual"), dict)
        else {}
    )
    existing_commit_expected = (
        existing_commit.get("expected")
        if isinstance(existing_commit.get("expected"), dict)
        else {}
    )
    existing_commit_actual = (
        existing_commit.get("actual")
        if isinstance(existing_commit.get("actual"), dict)
        else {}
    )
    existing_failure_class = (
        str(existing_commit.get("failure_class") or existing_validation.get("failure_class") or "").strip()
        or None
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed",
            expected=existing_validation_expected,
            actual={
                **existing_validation_actual,
                "validation_status": validation_status,
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
            },
            reasons=[reason],
            source="validator",
            failure_class=existing_failure_class or "recoverable_dramatic_failure",
            failure_reason=reason,
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_COMMIT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                **existing_commit_expected,
                "player_action_commit_allowed": False,
            },
            actual={
                **existing_commit_actual,
                "commit_applied": False,
                "recoverable_rejection": True,
                "failure_committed_to_player_surface": visible_output_present,
            },
            reasons=[reason],
            source="runtime",
            failure_class=existing_failure_class or "recoverable_dramatic_failure",
            failure_reason=reason,
        ),
    )
    if existing_visible.get("status") != "failed":
        ledger = set_aspect_record(
            ledger,
            ASPECT_VISIBLE_PROJECTION,
            make_aspect_record(
                applicable=True,
                status="passed" if visible_output_present else "failed",
                expected={"visible_output_present": True},
                actual={"visible_output_present": bool(visible_output_present)},
                reasons=[] if visible_output_present else [reason],
                source="projection",
                failure_class=None if visible_output_present else "projection_failure",
                failure_reason=None if visible_output_present else reason,
            ),
        )
    return normalize_runtime_aspect_ledger(ledger)


def _canonical_turn_id(session_id: str, turn_number: int) -> str:
    sid = str(session_id or "").strip() or "session"
    return f"{sid}:turn:{int(turn_number or 0)}"


def _runtime_profile_id_from_projection(projection: dict[str, Any] | None) -> str | None:
    if not isinstance(projection, dict):
        return None
    for key in ("runtime_profile_id", "experience_template_id", "seed_template_id", "template_id"):
        value = str(projection.get(key) or "").strip()
        if value:
            return value
    return None


def _observability_environment_for_session(session: "StorySession") -> str | None:
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    provenance = session.content_provenance if isinstance(session.content_provenance, dict) else {}
    trace_classification = (
        provenance.get("trace_classification")
        if isinstance(provenance.get("trace_classification"), dict)
        else {}
    )
    for value in (
        trace_classification.get("environment"),
        projection.get("environment"),
        os.environ.get("LANGFUSE_ENVIRONMENT"),
        os.environ.get("WOS_LANGFUSE_ENVIRONMENT"),
        os.environ.get("ENVIRONMENT"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _stamp_turn_aspect_ledger_identity(
    ledger: dict[str, Any] | None,
    *,
    session: "StorySession",
    commit_turn_number: int,
    turn_kind: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(ledger, dict):
        return None
    stamped = normalize_runtime_aspect_ledger(ledger)
    stamped["session_id"] = session.session_id
    stamped["story_session_id"] = session.session_id
    stamped["canonical_turn_id"] = _canonical_turn_id(session.session_id, commit_turn_number)
    stamped["turn_number"] = int(commit_turn_number or 0)
    if turn_kind:
        stamped["turn_kind"] = str(turn_kind)
    stamped.setdefault("module_id", session.module_id)
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    if runtime_profile_id and not stamped.get("runtime_profile_id"):
        stamped["runtime_profile_id"] = runtime_profile_id
    return normalize_runtime_aspect_ledger(stamped)


def _runtime_aspect_commit_blocking_failure(ledger: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ledger, dict):
        return None
    normalized = normalize_runtime_aspect_ledger(ledger)
    aspects = (
        normalized.get("turn_aspect_ledger")
        if isinstance(normalized.get("turn_aspect_ledger"), dict)
        else {}
    )
    blocking_failure_classes = {
        "hard_contract_failure",
        "projection_failure",
        "recoverable_dramatic_failure",
    }
    for aspect in (
        ASPECT_VISIBLE_PROJECTION,
        ASPECT_BEAT,
        ASPECT_CAPABILITY_SELECTION,
        ASPECT_NARRATIVE_ASPECT,
        ASPECT_VALIDATION,
    ):
        record = aspects.get(aspect)
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "").strip().lower()
        failure_class = str(record.get("failure_class") or "").strip()
        failure_reason = str(record.get("failure_reason") or "").strip()
        actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
        reasons = record.get("reasons") if isinstance(record.get("reasons"), list) else []
        reason = failure_reason or next((str(item).strip() for item in reasons if str(item).strip()), "")
        if status == "failed" and (
            failure_class in blocking_failure_classes
            or aspect in {ASPECT_VISIBLE_PROJECTION, ASPECT_CAPABILITY_SELECTION}
            or bool(actual.get("projection_failure_detected"))
            or bool(actual.get("required_beat_lost"))
            or bool(actual.get("narrative_aspect_failure"))
        ):
            return {
                "aspect": aspect,
                "status": status,
                "failure_class": failure_class or "hard_contract_failure",
                "failure_reason": reason or f"{aspect}_failed",
            }
    return None


def _scene_blocks_from_visible_bundle(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []
    blocks = bundle.get("scene_blocks")
    if not isinstance(blocks, list):
        return []
    return [dict(block) for block in blocks if isinstance(block, dict)]


def _recoverable_turn_message(*, session: "StorySession", reason: str) -> str:
    lang = str(getattr(session, "session_output_language", "de") or "de").strip().lower()[:2] or "de"
    if lang == "en":
        if reason == "graph_execution_exception":
            return "This turn could not be fully loaded. Please try again."
        return "This action cannot be resolved cleanly from the current scene right now."
    if reason == "graph_execution_exception":
        return "Dieser Zug konnte nicht vollstaendig geladen werden. Bitte versuche es erneut."
    return "Dieser Zug laesst sich im Moment nicht sauber aus der Szene heraus aufloesen."


def _recoverable_narrator_visible_output_bundle(*, message: str) -> dict[str, Any]:
    """Single writer for narrator-led recoverable player surface (ADR-0038 Phase C)."""
    block: dict[str, Any] = {
        "block_type": "narrator",
        "text": message,
        "player_display_text": message,
        "origin_aspect": "validation",
        "origin_beat_id": None,
        "origin_capability": "narrator.recoverable_failure",
        "authority_owner": "narrator",
    }
    return {
        "gm_narration": [message],
        "spoken_lines": [],
        "action_lines": [],
        "scene_blocks": [block],
    }


def _recoverable_playable_turn_envelope(
    *,
    session: "StorySession",
    commit_turn_number: int,
    player_input: str,
    trace_id: str | None,
    turn_kind: str,
    interpreted_input: dict[str, Any],
    narrative_commit: dict[str, Any],
    validation_outcome: dict[str, Any],
    message: str,
    turn_aspect_ledger: dict[str, Any],
    reason: str,
    diagnostics_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shared transport envelope for recoverable / graph-rescue short paths (ADR-0038 Phase C)."""
    turn_aspect_ledger = _stamp_turn_aspect_ledger_identity(
        turn_aspect_ledger,
        session=session,
        commit_turn_number=commit_turn_number,
        turn_kind=turn_kind,
    ) or turn_aspect_ledger
    diag: dict[str, Any] = {
        "recoverable_rejection": True,
        "hard_boundary_failure": False,
        "turn_aspect_ledger": turn_aspect_ledger,
    }
    if diagnostics_extras:
        diag.update(diagnostics_extras)
    return {
        "turn_number": commit_turn_number,
        "canonical_turn_id": _canonical_turn_id(session.session_id, commit_turn_number),
        "turn_kind": turn_kind,
        "raw_input": player_input,
        "trace_id": trace_id,
        "turn_aspect_ledger": turn_aspect_ledger,
        "interpreted_input": interpreted_input,
        "narrative_commit": narrative_commit,
        "validation_outcome": validation_outcome,
        "committed_result": {
            "commit_applied": False,
            "committed_effects": [],
            "reason": reason,
            "recoverable_rejection": True,
        },
        "visible_output_bundle": _recoverable_narrator_visible_output_bundle(message=message),
        "ok": False,
        "turn_status": "rejected_recoverable",
        "reason": reason,
        "player_visible_message": message,
        "diagnostics": diag,
    }


def _build_human_input_attribution_record(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    interpreted_input: dict[str, Any],
    selected_responder_set: list[dict[str, Any]] | None,
    commit_turn_number: int,
    player_input: str,
) -> dict[str, Any]:
    vis_diag = (
        graph_state.get("_visible_narrative_contract")
        if isinstance(graph_state.get("_visible_narrative_contract"), dict)
        else {}
    )
    raw_bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
    render_support = raw_bundle.get("render_support") if isinstance(raw_bundle.get("render_support"), dict) else {}
    human_filters = (
        render_support.get("human_lane_structured_filters")
        if isinstance(render_support.get("human_lane_structured_filters"), dict)
        else {}
    )
    generated_human_rows_dropped = int(human_filters.get("spoken_lines_dropped") or 0) + int(
        human_filters.get("action_lines_dropped") or 0
    )
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    human_actor_id = str(projection.get("human_actor_id") or "").strip()
    selected_player_role = str(projection.get("selected_player_role") or "").strip()
    responders = selected_responder_set if isinstance(selected_responder_set, list) else []
    first_responder = responders[0] if responders and isinstance(responders[0], dict) else {}
    primary_responder_id = str(
        graph_state.get("primary_responder_id")
        or first_responder.get("actor_id")
        or first_responder.get("responder_id")
        or ""
    ).strip()
    player_input_kind = interpreted_input.get("player_input_kind")
    graph_input_kind = interpreted_input.get("input_kind") or interpreted_input.get("kind")
    if not player_input_kind:
        player_input_kind = graph_input_kind
    echo_count = int(vis_diag.get("player_input_echo_removed_from_npc_block") or 0)
    return {
        "player_input_actor_id": interpreted_input.get("actor_id"),
        "human_actor_id": human_actor_id or None,
        "selected_player_role": selected_player_role or None,
        "primary_responder_id": primary_responder_id or None,
        "player_input_kind": player_input_kind,
        "graph_input_kind": graph_input_kind,
        "player_action_committed": bool(interpreted_input.get("player_action_committed")),
        "player_speech_committed": bool(interpreted_input.get("player_speech_committed")),
        "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")),
        "npc_response_expected": bool(interpreted_input.get("npc_response_expected")),
        "player_input_visible_block_present": bool(
            str(player_input or "").strip() and (human_actor_id or selected_player_role) and commit_turn_number > 0
        ),
        "npc_echoed_player_input": echo_count > 0,
        "player_input_attribution_pass": bool(
            str(player_input or "").strip()
            and (human_actor_id or selected_player_role)
            and commit_turn_number > 0
            and echo_count == 0
        ),
        "generated_human_actor_output_filtered": generated_human_rows_dropped > 0,
        "generated_human_lane_rows_dropped": generated_human_rows_dropped,
    }


def _record_visible_projection_aspect(
    *,
    ledger: dict[str, Any] | None,
    session_id: str,
    module_id: str,
    turn_number: int,
    turn_kind: str,
    raw_player_input: str,
    trace_id: str | None,
    scene_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    out = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=raw_player_input,
        trace_id=trace_id,
    )
    required_keys = REQUIRED_VISIBLE_ORIGIN_KEYS
    origin_present = bool(scene_blocks) and all(
        isinstance(block, dict) and block_has_required_origin(block)
        for block in scene_blocks
    )
    aspects = out.get("turn_aspect_ledger") if isinstance(out.get("turn_aspect_ledger"), dict) else {}
    narr = aspects.get(ASPECT_NARRATOR_AUTHORITY) if isinstance(aspects, dict) else {}
    narr_expected = narr.get("expected") if isinstance(narr, dict) and isinstance(narr.get("expected"), dict) else {}
    narrator_required = bool(narr_expected.get("required"))
    narrator_present = any(
        str(block.get("block_type") or "").strip().lower() == "narrator"
        and str(block.get("origin_aspect") or "").strip() == ASPECT_NARRATOR_AUTHORITY
        for block in scene_blocks
        if isinstance(block, dict)
    )
    failure_reason = None
    missing_field = None
    lost_at_stage = None
    if not origin_present:
        failure_reason = "visible_block_origin_missing"
        missing_field = "origin_metadata"
        lost_at_stage = "visible_projection"
    elif narrator_required and not narrator_present:
        failure_reason = "required_narrator_block_lost_in_projection"
        lost_at_stage = "visible_projection"
    status = "passed" if failure_reason is None else "failed"
    out = set_aspect_record(
        out,
        ASPECT_VISIBLE_PROJECTION,
        make_aspect_record(
            applicable=True,
            status=status,
            expected={
                "visible_block_origin_metadata": True,
                "required_narrator_block_preserved": narrator_required,
            },
        actual={
            "scene_block_count": len(scene_blocks),
            "visible_block_origin_present": origin_present,
            "blocks_have_origin_aspect": origin_present,
            "required_narrator_block_present": narrator_present,
            "required_blocks_present": (not narrator_required) or narrator_present,
            "lost_required_narrator_block": narrator_required and not narrator_present,
            "required_visible_origin_preserved": origin_present,
            "narrator_required": narrator_required,
            "visible_block_origins": [
                visible_origin_from_block(block)
                for block in scene_blocks
                if isinstance(block, dict) and visible_origin_from_block(block)
            ],
        },
            reasons=[] if failure_reason is None else [failure_reason],
            source="projection",
            failure_class=None if failure_reason is None else "projection_failure",
            failure_reason=failure_reason,
            missing_field=missing_field,
            expected_owner="narrator" if narrator_required else None,
            actual_owner="narrator" if narrator_present else None,
            lost_at_stage=lost_at_stage,
        ),
    )
    if failure_reason is not None:
        validation_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_VALIDATION)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        commit_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_COMMIT)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        out = set_aspect_record(
            out,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="failed",
                expected={
                    **(
                        validation_record.get("expected")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("expected"), dict)
                        else {}
                    ),
                    "visible_projection_preserves_required_blocks": True,
                },
                actual={
                    **(
                        validation_record.get("actual")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                        else {}
                    ),
                    "projection_failure_detected": True,
                    "visible_projection_failure_reason": failure_reason,
                },
                reasons=[failure_reason],
                source="validator",
                failure_class="projection_failure",
                failure_reason=failure_reason,
                missing_field=missing_field,
                expected_owner="narrator" if narrator_required else None,
                actual_owner="narrator" if narrator_present else None,
                lost_at_stage=lost_at_stage,
            ),
        )
        out = set_aspect_record(
            out,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="partial",
                expected={
                    **(
                        commit_record.get("expected")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("expected"), dict)
                        else {}
                    ),
                    "projection_failure_recorded": True,
                },
                actual={
                    **(
                        commit_record.get("actual")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                        else {}
                    ),
                    "projection_failure_detected": True,
                    "visible_projection_failure_reason": failure_reason,
                },
                reasons=[failure_reason],
                source="commit",
                failure_class="projection_failure",
                failure_reason=failure_reason,
                missing_field=missing_field,
                lost_at_stage=lost_at_stage,
            ),
        )
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=out.get("runtime_profile_id"),
        ).to_dict()
    except Exception:
        runtime_policy = {}
    narrative_policy = (
        runtime_policy.get("narrative_aspect_policy")
        if isinstance(runtime_policy.get("narrative_aspect_policy"), dict)
        else {}
    )
    narrative_validation = validate_narrative_aspects(
        narrative_aspect_policy=narrative_policy,
        runtime_context={
            "ledger": out,
            "scene_blocks": scene_blocks,
            "visible_blocks": scene_blocks,
            "input": {
                "kind": turn_kind,
                "raw_player_input": raw_player_input,
            },
            "turn": {
                "number": turn_number,
                "kind": turn_kind,
            },
        },
    ).to_dict()
    candidate_aspects = [
        str(row.get("id") or "").strip()
        for row in (narrative_policy.get("aspects") or [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    ]
    semantic_profile_aspects = [
        str(row.get("id") or "").strip()
        for row in (narrative_policy.get("aspects") or [])
        if isinstance(row, dict)
        and str(row.get("id") or "").strip()
        and isinstance(row.get("semantic_profile"), dict)
        and row.get("semantic_profile")
    ]
    missing_narrative_evidence = narrative_validation.get("missing_required_evidence") or []
    if not isinstance(missing_narrative_evidence, list):
        missing_narrative_evidence = []
    missing_visible_narrative_evidence = [
        item
        for item in missing_narrative_evidence
        if isinstance(item, dict) and str(item.get("kind") or "").startswith("visible_")
    ]
    narrative_commit_impact = str(narrative_validation.get("commit_impact") or "diagnostic")
    narrative_failure_reason = narrative_validation.get("failure_reason")
    out = set_aspect_record(
        out,
        ASPECT_NARRATIVE_ASPECT,
        make_aspect_record(
            applicable=bool(narrative_policy.get("aspects")),
            status=str(narrative_validation.get("status") or "not_applicable"),
            expected={
                "policy_present": bool(narrative_policy.get("aspects")),
                "candidate_aspects": candidate_aspects,
                "evidence_required": bool(candidate_aspects),
                "commit_impact": narrative_commit_impact,
                "semantic_tracking_enabled": bool(semantic_profile_aspects),
                "semantic_profile_aspects": semantic_profile_aspects,
                "theme_tracking_policy_present": bool(semantic_profile_aspects),
            },
            selected={
                "selected_aspects": narrative_validation.get("selected_aspects") or [],
                "selection_source": "module_policy" if candidate_aspects else "not_applicable",
                "selected_theme_aspects": narrative_validation.get("semantic_aspect_ids") or [],
            },
            actual={
                "realized_aspects": narrative_validation.get("realized_aspects") or [],
                "missing_required_evidence": missing_narrative_evidence,
                "evidence": narrative_validation.get("evidence") or [],
                "visible_when_required": not bool(missing_visible_narrative_evidence),
                "semantic_classifications": narrative_validation.get("semantic_classifications") or [],
                "semantic_classification_count": int(narrative_validation.get("semantic_classification_count") or 0),
                "semantic_weak_alignment_count": int(narrative_validation.get("semantic_weak_alignment_count") or 0),
                "semantic_required_weak_alignment_count": int(narrative_validation.get("semantic_required_weak_alignment_count") or 0),
                "selected_theme_aspects": narrative_validation.get("semantic_aspect_ids") or [],
                "realized_theme_aspects": narrative_validation.get("realized_semantic_aspects") or [],
            },
            reasons=[str(narrative_failure_reason)] if narrative_failure_reason else [],
            source="projection",
            failure_class=(
                "hard_contract_failure"
                if narrative_failure_reason and narrative_commit_impact == "reject"
                else "recoverable_dramatic_failure"
                if narrative_failure_reason and narrative_commit_impact == "recover"
                else "degradation_only"
                if narrative_failure_reason
                else None
            ),
            failure_reason=str(narrative_failure_reason) if narrative_failure_reason else None,
            missing_field="narrative_aspect_evidence" if narrative_failure_reason else None,
            lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
        ),
    )
    if narrative_failure_reason and narrative_commit_impact in {"recover", "reject"}:
        validation_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_VALIDATION)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        commit_record = (
            out.get("turn_aspect_ledger", {}).get(ASPECT_COMMIT)
            if isinstance(out.get("turn_aspect_ledger"), dict)
            else {}
        )
        failure_class = (
            "hard_contract_failure"
            if narrative_commit_impact == "reject"
            else "recoverable_dramatic_failure"
        )
        out = set_aspect_record(
            out,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="failed",
                expected={
                    **(
                        validation_record.get("expected")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("expected"), dict)
                        else {}
                    ),
                    "narrative_aspect_contract_pass": True,
                },
                actual={
                    **(
                        validation_record.get("actual")
                        if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                        else {}
                    ),
                    "narrative_aspect_failure": True,
                    "narrative_aspect_failure_reason": narrative_failure_reason,
                },
                reasons=[str(narrative_failure_reason)],
                source="validator",
                failure_class=failure_class,
                failure_reason=str(narrative_failure_reason),
                missing_field="narrative_aspect_evidence",
                lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
            ),
        )
        out = set_aspect_record(
            out,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="partial",
                expected={
                    **(
                        commit_record.get("expected")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("expected"), dict)
                        else {}
                    ),
                    "narrative_aspect_failure_recorded": True,
                },
                actual={
                    **(
                        commit_record.get("actual")
                        if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                        else {}
                    ),
                    "narrative_aspect_failure": True,
                    "narrative_aspect_failure_reason": narrative_failure_reason,
                },
                reasons=[str(narrative_failure_reason)],
                source="commit",
                failure_class=failure_class,
                failure_reason=str(narrative_failure_reason),
                missing_field="narrative_aspect_evidence",
                lost_at_stage="visible_projection" if missing_visible_narrative_evidence else None,
            ),
        )
    beat = aspects.get(ASPECT_BEAT) if isinstance(aspects, dict) else {}
    if isinstance(beat, dict) and beat.get("applicable"):
        expected = beat.get("expected") if isinstance(beat.get("expected"), dict) else {}
        selected = beat.get("selected") if isinstance(beat.get("selected"), dict) else {}
        expected_realization = [
            str(item)
            for item in (expected.get("expected_realization") or [])
            if str(item).strip()
        ]
        narrator_realized = any(
            str(block.get("origin_aspect") or "") == ASPECT_NARRATOR_AUTHORITY
            for block in scene_blocks
            if isinstance(block, dict)
        )
        npc_realized = any(
            str(block.get("origin_aspect") or "") == ASPECT_NPC_AUTHORITY
            for block in scene_blocks
            if isinstance(block, dict)
        )
        realized_capabilities = {
            str(block.get("origin_capability") or "").strip()
            for block in scene_blocks
            if isinstance(block, dict) and str(block.get("origin_capability") or "").strip()
        }
        for block in scene_blocks:
            if not isinstance(block, dict):
                continue
            folded = block.get("folded_origin_evidence")
            if isinstance(folded, list):
                for origin in folded:
                    if isinstance(origin, dict) and str(origin.get("origin_capability") or "").strip():
                        realized_capabilities.add(str(origin.get("origin_capability")).strip())
        missing_expected: list[str] = []
        for expected_item in expected_realization:
            if expected_item in realized_capabilities:
                continue
            if expected_item in {"narrator", "narrator_authority"} and narrator_realized:
                continue
            if expected_item in {"npc", "npc_authority"} and npc_realized:
                continue
            missing_expected.append(expected_item)
        beat_realized = origin_present and not missing_expected
        beat_contractually_required = bool(
            expected.get("contractually_required")
            or selected.get("contractually_required")
            or expected.get("hard_contract_required")
        )
        if beat_realized:
            beat_status = "passed"
            beat_failure_class = None
            beat_failure_reason = None
        elif beat_contractually_required:
            beat_status = "failed"
            beat_failure_class = "hard_contract_failure"
            beat_failure_reason = "selected_required_beat_lost"
        elif missing_expected:
            beat_status = "partial"
            beat_failure_class = "degradation_only"
            beat_failure_reason = "beat_realization_not_visible"
        else:
            beat_status = "partial"
            beat_failure_class = "observability_gap"
            beat_failure_reason = "beat_realization_not_visible"
        out = set_aspect_record(
            out,
            ASPECT_BEAT,
            make_aspect_record(
                applicable=True,
                status=beat_status,
                expected=expected,
                selected=selected,
                actual={
                    **(beat.get("actual") if isinstance(beat.get("actual"), dict) else {}),
                    "realized": beat_realized,
                    "visible": bool(scene_blocks),
                    "committed": (
                        (beat.get("actual") or {}).get("committed")
                        if isinstance(beat.get("actual"), dict)
                        else None
                    ),
                    "missing_expected_realization": missing_expected,
                    "realization_evidence": [
                        visible_origin_from_block(block)
                        for block in scene_blocks
                        if isinstance(block, dict)
                        and (
                            str(block.get("origin_beat_id") or "").strip()
                            == str(selected.get("selected_beat_id") or "").strip()
                            or str(block.get("origin_capability") or "").strip() in set(expected_realization)
                        )
                    ],
                    "failure_classification": beat_failure_class,
                },
                reasons=[] if beat_realized else [beat_failure_reason],
                source="projection",
                failure_class=beat_failure_class,
                failure_reason=beat_failure_reason,
                selected_beat=selected.get("selected_beat_id"),
                lost_at_stage="visible_projection" if not beat_realized else None,
            ),
        )
        if beat_failure_class == "hard_contract_failure":
            validation_record = (
                out.get("turn_aspect_ledger", {}).get(ASPECT_VALIDATION)
                if isinstance(out.get("turn_aspect_ledger"), dict)
                else {}
            )
            commit_record = (
                out.get("turn_aspect_ledger", {}).get(ASPECT_COMMIT)
                if isinstance(out.get("turn_aspect_ledger"), dict)
                else {}
            )
            out = set_aspect_record(
                out,
                ASPECT_VALIDATION,
                make_aspect_record(
                    applicable=True,
                    status="failed",
                    expected={
                        **(
                            validation_record.get("expected")
                            if isinstance(validation_record, dict) and isinstance(validation_record.get("expected"), dict)
                            else {}
                        ),
                        "contractually_required_beat_realized": True,
                    },
                    actual={
                        **(
                            validation_record.get("actual")
                            if isinstance(validation_record, dict) and isinstance(validation_record.get("actual"), dict)
                            else {}
                        ),
                        "required_beat_lost": True,
                        "selected_beat": selected.get("selected_beat_id"),
                    },
                    reasons=[beat_failure_reason],
                    source="validator",
                    failure_class=beat_failure_class,
                    failure_reason=beat_failure_reason,
                    selected_beat=selected.get("selected_beat_id"),
                    lost_at_stage="visible_projection",
                ),
            )
            out = set_aspect_record(
                out,
                ASPECT_COMMIT,
                make_aspect_record(
                    applicable=True,
                    status="partial",
                    expected={
                        **(
                            commit_record.get("expected")
                            if isinstance(commit_record, dict) and isinstance(commit_record.get("expected"), dict)
                            else {}
                        ),
                        "contractually_required_beat_recorded": True,
                    },
                    actual={
                        **(
                            commit_record.get("actual")
                            if isinstance(commit_record, dict) and isinstance(commit_record.get("actual"), dict)
                            else {}
                        ),
                        "required_beat_lost": True,
                        "selected_beat": selected.get("selected_beat_id"),
                    },
                    reasons=[beat_failure_reason],
                    source="commit",
                    failure_class=beat_failure_class,
                    failure_reason=beat_failure_reason,
                    selected_beat=selected.get("selected_beat_id"),
                    lost_at_stage="visible_projection",
                ),
            )
    return out


@dataclass
class StorySession:
    session_id: str
    module_id: str
    runtime_projection: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_counter: int = 0
    current_scene_id: str = ""
    session_output_language: str = "de"
    history: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    narrative_threads: StoryNarrativeThreadSet = field(default_factory=StoryNarrativeThreadSet)
    last_thread_update_trace: ThreadUpdateTrace | None = None
    # Bounded carry-forward of committed GoC continuity classes (not a second memory surface).
    prior_continuity_impacts: list[dict[str, Any]] = field(default_factory=list)
    # Bounded hierarchical memory derived only from canonical committed turns.
    hierarchical_memory: dict[str, Any] = field(default_factory=dict)
    # Durable Pi15 environment state derived from canonical content and committed turns.
    environment_state: dict[str, Any] = field(default_factory=dict)
    # Immutable-ish snapshot of published content identity at session birth (audit F-M3).
    content_provenance: dict[str, Any] = field(default_factory=dict)


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def story_session_to_payload(session: StorySession) -> dict[str, Any]:
    trace = session.last_thread_update_trace
    return {
        "format_version": 1,
        "session_id": session.session_id,
        "module_id": session.module_id,
        "runtime_projection": session.runtime_projection,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "turn_counter": session.turn_counter,
        "current_scene_id": session.current_scene_id,
        "session_output_language": session.session_output_language,
        "history": session.history,
        "diagnostics": session.diagnostics,
        "narrative_threads": session.narrative_threads.model_dump(mode="json"),
        "last_thread_update_trace": trace.model_dump(mode="json") if trace is not None else None,
        "prior_continuity_impacts": session.prior_continuity_impacts,
        "hierarchical_memory": session.hierarchical_memory,
        "environment_state": session.environment_state,
        "content_provenance": session.content_provenance,
    }


def story_session_from_payload(data: dict[str, Any]) -> StorySession:
    fv = data.get("format_version", 1)
    if fv != 1:
        raise ValueError(f"Unsupported story session snapshot format_version: {fv!r}")

    raw_trace = data.get("last_thread_update_trace")
    trace: ThreadUpdateTrace | None = None
    if isinstance(raw_trace, dict):
        trace = ThreadUpdateTrace.model_validate(raw_trace)

    threads_raw = data.get("narrative_threads") or {}
    threads = StoryNarrativeThreadSet.model_validate(threads_raw)

    created_at = _parse_iso_datetime(str(data["created_at"]))
    updated_at = _parse_iso_datetime(str(data["updated_at"]))

    provenance = data.get("content_provenance")
    if not isinstance(provenance, dict):
        provenance = {}

    return StorySession(
        session_id=str(data["session_id"]),
        module_id=str(data["module_id"]),
        runtime_projection=dict(data["runtime_projection"]),
        created_at=created_at,
        updated_at=updated_at,
        turn_counter=int(data.get("turn_counter", 0)),
        current_scene_id=str(data.get("current_scene_id") or ""),
        session_output_language=str(data.get("session_output_language") or "de"),
        history=list(data.get("history") or []),
        diagnostics=list(data.get("diagnostics") or []),
        narrative_threads=threads,
        last_thread_update_trace=trace,
        prior_continuity_impacts=list(data.get("prior_continuity_impacts") or []),
        hierarchical_memory=dict(data.get("hierarchical_memory") or {}),
        environment_state=dict(data.get("environment_state") or {}),
        content_provenance=provenance,
    )


def _load_module_memory_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return {}, {}
    memory_policy = (
        runtime_policy.get("memory_policy")
        if isinstance(runtime_policy.get("memory_policy"), dict)
        else {}
    )
    return runtime_policy, memory_policy


def _load_module_callback_web_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> dict[str, Any]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return normalize_callback_web_policy(None)
    return callback_web_policy_from_module_runtime(runtime_policy)


def _load_module_consequence_cascade_policy(
    *,
    module_id: str,
    runtime_profile_id: str | None,
) -> dict[str, Any]:
    try:
        runtime_policy = load_module_runtime_policy(
            module_id=module_id,
            runtime_profile_id=runtime_profile_id,
        ).to_dict()
    except Exception:
        return normalize_consequence_cascade_policy(None)
    return consequence_cascade_policy_from_module_runtime(runtime_policy)


def _record_hierarchical_memory_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    committed_turn: dict[str, Any],
    allow_write: bool,
) -> dict[str, Any]:
    """Record policy-driven memory evidence and optionally update session memory."""
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    runtime_policy, memory_policy = _load_module_memory_policy(
        module_id=session.module_id,
        runtime_profile_id=runtime_profile_id,
    )
    prior_snapshot = (
        session.hierarchical_memory
        if isinstance(session.hierarchical_memory, dict)
        else empty_hierarchical_memory_snapshot(
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
    )
    memory_turn = dict(committed_turn)
    memory_turn.setdefault("module_id", session.module_id)
    memory_turn.setdefault("runtime_profile_id", runtime_profile_id)
    if not allow_write:
        memory_turn["recoverable_outcome"] = True
    write_result = build_hierarchical_memory_write(
        memory_policy=memory_policy,
        committed_turn=memory_turn,
        runtime_policy=runtime_policy,
    )
    if allow_write and write_result.get("write_allowed") and not write_result.get("uncommitted_write_detected"):
        snapshot_after = merge_hierarchical_memory_snapshot(
            prior_snapshot=prior_snapshot,
            write_result=write_result,
            memory_policy=memory_policy,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        session.hierarchical_memory = snapshot_after
    else:
        snapshot_after = normalize_hierarchical_memory_snapshot(
            prior_snapshot,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        session.hierarchical_memory = snapshot_after
    context = project_hierarchical_memory_context(
        snapshot=snapshot_after,
        memory_policy=memory_policy,
    )
    memory_surface = {
        "contract": "hierarchical_memory_runtime_surface.v1",
        "write_result": write_result,
        "context": context,
    }
    event["hierarchical_memory"] = memory_surface
    graph_state["hierarchical_memory_context"] = context
    selected_tiers = [
        str(item).strip()
        for item in (write_result.get("selected_tiers") or [])
        if str(item).strip()
    ]
    written_items = [
        item
        for item in (write_result.get("written_items") or [])
        if isinstance(item, dict)
    ]
    tiers_written: list[str] = []
    for item in written_items:
        tier_id = str(item.get("tier") or "").strip()
        if tier_id and tier_id not in tiers_written:
            tiers_written.append(tier_id)
    ledger = (
        event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else None
    )
    ledger = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=event.get("turn_number"),
        turn_kind=str(event.get("turn_kind") or "player"),
        raw_player_input=event.get("raw_input"),
        trace_id=event.get("trace_id"),
        runtime_profile_id=runtime_profile_id,
    )
    policy_present = bool(write_result.get("policy_present"))
    status = str(write_result.get("status") or "not_applicable")
    failure_reason = write_result.get("failure_reason")
    ledger = set_aspect_record(
        ledger,
        ASPECT_HIERARCHICAL_MEMORY,
        make_aspect_record(
            applicable=policy_present,
            status=status,
            expected={
                "policy_present": policy_present,
                "policy_enabled": bool(write_result.get("policy_enabled")),
                "committed_turn_required": True,
                "allow_uncommitted_writes": bool(memory_policy.get("allow_uncommitted_writes")),
                "context_projection_bounded": True,
            },
            selected={
                "selected_tiers": selected_tiers,
                "source_canonical_turn_id": write_result.get("source_canonical_turn_id"),
            },
            actual={
                "write_allowed": bool(write_result.get("write_allowed")),
                "written_item_count": len(written_items),
                "tiers_written": tiers_written,
                "memory_present": bool(context.get("memory_present")),
                "context_item_count": int(context.get("item_count") or 0),
                "context_bounded": bool(context.get("bounded")),
                "uncommitted_write_detected": bool(write_result.get("uncommitted_write_detected")),
                "snapshot_item_count": int(snapshot_after.get("item_count") or 0),
            },
            reasons=[str(failure_reason)] if failure_reason else [],
            source="commit" if allow_write else "commit_guard",
            failure_class="hard_contract_failure" if write_result.get("uncommitted_write_detected") else None,
            failure_reason=str(failure_reason) if failure_reason else None,
            missing_field="canonical_turn_id" if failure_reason == "canonical_turn_id_missing" else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger
    return memory_surface


def _record_callback_web_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    blocks = callback_web_aspect_blocks(
        record=record,
        graph_export=graph_export,
        validation=validation,
        policy=policy,
    )
    status = str(validation.get("status") or "missing")
    failure_codes = [
        str(code)
        for code in (validation.get("failure_codes") or [])
        if str(code).strip()
    ]
    ledger = (
        event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else None
    )
    ledger = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=event.get("turn_number"),
        turn_kind=str(event.get("turn_kind") or "player"),
        raw_player_input=event.get("raw_input"),
        trace_id=event.get("trace_id"),
        runtime_profile_id=runtime_profile_id,
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CALLBACK_WEB,
        make_aspect_record(
            applicable=bool(policy.get("enabled")),
            status=status,
            expected=blocks.get("expected") if isinstance(blocks.get("expected"), dict) else {},
            selected=blocks.get("selected") if isinstance(blocks.get("selected"), dict) else {},
            actual=blocks.get("actual") if isinstance(blocks.get("actual"), dict) else {},
            reasons=failure_codes,
            source="commit",
            failure_class="observability_gap" if failure_codes else None,
            failure_reason=failure_codes[0] if failure_codes else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger


def _record_consequence_cascade_aspect(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    event: dict[str, Any],
    record: dict[str, Any] | None,
    graph_export: dict[str, Any] | None,
    validation: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    blocks = consequence_cascade_aspect_blocks(
        record=record,
        graph_export=graph_export,
        validation=validation,
        policy=policy,
    )
    status = str(validation.get("status") or "missing")
    failure_codes = [
        str(code)
        for code in (validation.get("failure_codes") or [])
        if str(code).strip()
    ]
    ledger = (
        event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else None
    )
    ledger = ensure_runtime_aspect_ledger(
        ledger,
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=event.get("turn_number"),
        turn_kind=str(event.get("turn_kind") or "player"),
        raw_player_input=event.get("raw_input"),
        trace_id=event.get("trace_id"),
        runtime_profile_id=runtime_profile_id,
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CONSEQUENCE_CASCADE,
        make_aspect_record(
            applicable=bool(policy.get("enabled")),
            status=status,
            expected=blocks.get("expected") if isinstance(blocks.get("expected"), dict) else {},
            selected=blocks.get("selected") if isinstance(blocks.get("selected"), dict) else {},
            actual=blocks.get("actual") if isinstance(blocks.get("actual"), dict) else {},
            reasons=failure_codes,
            source="commit",
            failure_class="observability_gap" if failure_codes else None,
            failure_reason=failure_codes[0] if failure_codes else None,
        ),
    )
    event["turn_aspect_ledger"] = ledger
    graph_state["turn_aspect_ledger"] = ledger


def _module_scope_truth(module_id: str | None = None) -> dict[str, Any]:
    requested = str(module_id or "").strip() or None
    supported = (
        requested in SUPPORTED_LIVE_STORY_MODULE_IDS
        if requested is not None
        else None
    )
    return {
        "contract": "story_runtime_module_scope.v1",
        "runtime_scope": "module_specific",
        "supported_live_module_ids": list(SUPPORTED_LIVE_STORY_MODULE_IDS),
        "requested_module_id": requested,
        "requested_module_supported": supported,
        "module_specific_hooks": [
            "goc_host_experience_template",
            "goc_prior_continuity_for_graph",
            "goc_append_continuity_impacts",
            "callback_web",
            "consequence_cascade",
        ],
        "unsupported_module_policy": (
            "non_goc_modules_are_not_advertised_as_full_live_story_support"
        ),
        "support_note": (
            "God of Carnage is the only fully wired live story module in this "
            "runtime lane; other module ids must be reported honestly until "
            "module-general support is implemented."
        ),
    }


def _coerce_visible_text_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        line = value.strip()
        return [line] if line else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _ensure_gm_narration_from_narrator_scene_blocks(bundle: dict[str, Any]) -> dict[str, Any]:
    """When gm_narration is absent but scene_blocks include narrator lanes, mirror text for MVP4 contracts."""
    out = dict(bundle)
    if _coerce_visible_text_lines(out.get("gm_narration")):
        return out
    blocks = out.get("scene_blocks")
    if not isinstance(blocks, list):
        return out
    lines: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if str(block.get("block_type") or "").strip() != "narrator":
            continue
        t = str(block.get("text") or "").strip()
        if t:
            lines.append(t)
    if lines:
        out["gm_narration"] = lines
    return out


def _finalize_visible_bundle_opening_gm_narration(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    packaged_bundle: Any,
    commit_turn_number: int,
) -> Any:
    """After experience packaging, restore three GM opening beats for GoC turn 0 when needed."""
    graph_state.pop("_opening_narration_normalization", None)
    if commit_turn_number != 0 or session.module_id != GOD_OF_CARNAGE_MODULE_ID:
        return packaged_bundle
    if not isinstance(packaged_bundle, dict):
        return packaged_bundle
    gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    if structured is None and isinstance(gen.get("structured_output"), dict):
        structured = gen["structured_output"]
    if not isinstance(structured, dict):
        return packaged_bundle
    narration = structured.get("narration_summary")
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    selected = proj.get("selected_player_role")
    human = proj.get("human_actor_id")
    spoken = structured.get("spoken_lines")
    beats, norm_meta = normalize_opening_narration_beats(
        narration,
        selected_player_role=str(selected).strip() if selected else None,
        human_actor_id=str(human).strip() if human else None,
        module_id=session.module_id,
        turn_number=commit_turn_number,
        output_language=getattr(session, "session_output_language", None),
        existing_actor_lines=spoken if isinstance(spoken, list) else None,
    )
    if isinstance(norm_meta, dict):
        graph_state["_opening_narration_normalization"] = norm_meta
    if beats is None or len(beats) < 3:
        return packaged_bundle
    out = dict(packaged_bundle)
    out["gm_narration"] = beats[:3]
    return out


def _maybe_split_goc_opening_into_two_movements(
    blocks: list[dict[str, Any]],
    *,
    commit_turn_number: int,
) -> list[dict[str, Any]]:
    """ADR-0035: Prefer two visible narrator blocks for opening (premise → salon) when prose uses paragraph breaks."""
    if commit_turn_number != 0 or len(blocks) != 1:
        return blocks
    b0 = blocks[0]
    if str(b0.get("block_type") or "").strip() != "narrator":
        return blocks
    text = str(b0.get("text") or "").strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) < 2:
        return blocks
    out: list[dict[str, Any]] = []
    for i, p in enumerate(parts):
        nb = dict(b0)
        nb["text"] = p
        nb["id"] = f"turn-{commit_turn_number}-live-block-{i + 1}"
        out.append(nb)
    return out


def _annotate_goc_opening_narration_beats(
    blocks: list[dict[str, Any]],
    *,
    module_id: str | None,
    turn_number: int,
) -> None:
    """Tag the first three opening narrator blocks for play UI (premise / scene / role anchor)."""
    if turn_number != 0 or str(module_id or "").strip() != GOD_OF_CARNAGE_MODULE_ID:
        return
    if len(blocks) < 3:
        return
    for i in range(3):
        b = blocks[i]
        if not isinstance(b, dict):
            return
        bt = str(b.get("block_type") or b.get("type") or "").strip().lower()
        if bt != "narrator":
            return
    beats = ("premise", "scene_setup", "role_anchor")
    for i in range(3):
        blocks[i]["narration_beat"] = beats[i]


def _dedupe_goc_speaker_colon_stutter(text: str) -> str:
    """Delegate to shared visible-text helper (also applied inside ``sanitize_visible_block_text``)."""
    return dedupe_goc_speaker_colon_stutter_visible(text)


def _apply_goc_actor_block_colon_stutter_cleanup(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize actor_line / actor_action visible text before split/prune."""
    out: list[dict[str, Any]] = []
    for b in blocks:
        if not isinstance(b, dict):
            out.append(b)
            continue
        bt = str(b.get("block_type") or "").strip().lower()
        if bt in {"actor_line", "actor_action"}:
            nb = dict(b)
            nb["text"] = dedupe_goc_speaker_colon_stutter_visible(
                str(b.get("text") or ""),
                speaker_label=str(b.get("speaker_label") or "") or None,
                actor_id=str(b.get("actor_id") or "").strip() or None,
            )
            out.append(nb)
        else:
            out.append(b)
    return out


def _goc_visible_text_fold(s: str) -> str:
    """Lowercase + light accent fold so prune substring checks survive accent drift."""
    return _goc_visible_lane_text_fold(s)


def _split_merged_goc_actor_line_segments(
    text: str,
    *,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[tuple[str, str, str]]:
    """Split one ``actor_line`` by roster speaker prefixes (``ai_stack.goc_npc_transcript_projection``)."""
    return split_merged_goc_actor_line_segments(
        text,
        runtime_projection=runtime_projection,
        story_runtime_experience=story_runtime_experience,
    )


def _expand_multi_speaker_actor_lines(
    blocks: list[dict[str, Any]],
    *,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Turn one model ``actor_line`` that jams multiple speakers into separate blocks."""
    out: list[dict[str, Any]] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = str(b.get("block_type") or "").strip().lower()
        if bt != "actor_line":
            out.append(b)
            continue
        segs = _split_merged_goc_actor_line_segments(
            str(b.get("text") or ""),
            runtime_projection=runtime_projection,
            story_runtime_experience=story_runtime_experience,
        )
        if len(segs) < 2:
            out.append(b)
            continue
        base_id = str(b.get("id") or "live-block").strip() or "live-block"
        for idx, (aid, sh, body) in enumerate(segs):
            nb = dict(b)
            nb["id"] = base_id if idx == 0 else f"{base_id}-spk{idx}"
            nb["actor_id"] = aid
            nb["speaker_label"] = sh
            nb["text"] = f"{sh}: {body}"
            out.append(nb)
    return out


def _prune_actor_actions_subsumed_by_prior_actor_lines(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Delegate to shared ai_stack prune (also used by backend player bundle polish)."""
    return prune_goc_actor_actions_subsumed_by_prior_actor_lines(blocks)


def _finalize_visible_blocks_with_goc_actor_split(
    blocks: list[dict[str, Any]],
    *,
    expected_language: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    turn_number: int,
    player_input_echo_strings: list[str] | None,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks = _apply_goc_actor_block_colon_stutter_cleanup(blocks)
    blocks = _expand_multi_speaker_actor_lines(
        blocks,
        runtime_projection=runtime_projection,
        story_runtime_experience=story_runtime_experience,
    )
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language=expected_language,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        turn_number=turn_number,
        player_input_echo_strings=player_input_echo_strings,
    )
    return _prune_actor_actions_subsumed_by_prior_actor_lines(out), diag


def _actor_line_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    count = 0
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                count += 1
            continue
        if str(item).strip():
            count += 1
    return count


def _structured_lane_dict_counts(structured: dict[str, Any] | None) -> tuple[int, int]:
    """Count dict-only rows with visible text (structured lanes used for actor projection)."""
    if not isinstance(structured, dict):
        return 0, 0

    def _dict_text_count(key: str) -> int:
        lane = structured.get(key)
        if not isinstance(lane, list):
            return 0
        return sum(
            1
            for item in lane
            if isinstance(item, dict) and str(item.get("text") or item.get("line") or "").strip()
        )

    return _dict_text_count("spoken_lines"), _dict_text_count("action_lines")


def _is_goc_human_lane_actor(
    actor_raw: str,
    *,
    human_actor_id: str,
    selected_player_role: str,
) -> bool:
    """True when this actor id/alias is the selected human role or human_actor_id."""
    actor_canon = canonicalize_goc_actor_id(str(actor_raw or "").strip())
    if not actor_canon:
        return False
    if human_actor_id:
        h = canonicalize_goc_actor_id(str(human_actor_id).strip())
        if h and actor_canon == h:
            return True
    if selected_player_role:
        r = canonicalize_goc_actor_id(str(selected_player_role).strip())
        if r and actor_canon == r:
            return True
    return False


def _opening_shape_requires_actor_backfill(blocks: list[dict[str, Any]]) -> bool:
    """OPEN-ACTOR-BLOCK-PROJECTION-01: first three blocks narrator but no actor at index >= 3."""
    if len(blocks) < 3:
        return False

    def _bt(b: dict[str, Any]) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    if not all(_bt(blocks[i]) == "narrator" for i in range(3)):
        return False
    first_actor = next(
        (i for i, b in enumerate(blocks) if _bt(b) in {"actor_line", "actor_action"}),
        None,
    )
    return first_actor is None


def _actor_block_projection_count(blocks: list[dict[str, Any]]) -> int:
    def _bt(b: dict[str, Any]) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    return sum(1 for b in blocks if isinstance(b, dict) and _bt(b) in {"actor_line", "actor_action"})


def _maybe_backfill_opening_actor_from_structured(
    blocks: list[dict[str, Any]],
    *,
    structured_output: dict[str, Any],
    runtime_projection: dict[str, Any] | None,
    turn_number: int,
    human_actor_id: str,
    selected_player_role: str,
    delivery_fn: Any,
    actor_label_fn: Any,
    story_runtime_experience: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, str | None]:
    """Append first safe NPC actor block from structured lanes. Returns (blocks, source, filter_reason)."""
    if turn_number != 0 or not _opening_shape_requires_actor_backfill(blocks):
        return blocks, "none", None

    inner_blocks: list[dict[str, Any]] = list(blocks)

    def _append(t: str, text: str, *, speaker_label: str, actor_id: str | None = None) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        inner_blocks.append(
            {
                "id": f"turn-{turn_number}-live-block-{len(inner_blocks) + 1}",
                "block_type": t,
                "speaker_label": speaker_label,
                "actor_id": actor_id,
                "target_actor_id": None,
                "text": clean,
                "delivery": delivery_fn(),
                "source": "live_runtime_graph",
            }
        )

    src = _try_spoken_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
    )
    if src:
        return inner_blocks, src, None
    _flags = goc_transcript_policy_flags(story_runtime_experience)
    _action_bt = "actor_line" if _flags["map_action_lines_to_actor_line_lane"] else "actor_action"
    src = _try_action_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
        action_block_type=_action_bt,
    )
    if src:
        return inner_blocks, src, None
    src = _try_initiative_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
    )
    if src:
        return inner_blocks, src, None

    sl, al = _structured_lane_dict_counts(structured_output)
    initiative_ct = len([x for x in (structured_output.get("initiative_events") or []) if isinstance(x, dict)])
    if (sl or al or initiative_ct) and runtime_projection is not None:
        return inner_blocks, "none", "actor_block_missing_due_to_human_actor_filter"
    return inner_blocks, "none", None


def _try_spoken_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
) -> str | None:
    spoken = structured_output.get("spoken_lines")
    if not isinstance(spoken, list):
        return None
    for row in spoken:
        if not isinstance(row, dict):
            continue
        speaker_id = str(row.get("speaker_id") or "").strip()
        line = str(row.get("text") or row.get("line") or "").strip()
        if not line:
            continue
        if runtime_projection is not None:
            if not speaker_id:
                continue
            if _is_goc_human_lane_actor(
                speaker_id,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            ):
                continue
        append_fn(
            "actor_line",
            line,
            speaker_label=actor_label_fn(speaker_id),
            actor_id=speaker_id or None,
        )
        return "spoken_lines"
    return None


def _try_action_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
    action_block_type: str = "actor_action",
) -> str | None:
    actions = structured_output.get("action_lines")
    if not isinstance(actions, list):
        return None
    for row in actions:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("actor_id") or "").strip()
        line = str(row.get("text") or row.get("line") or "").strip()
        if not line:
            continue
        if runtime_projection is not None:
            if not aid:
                continue
            if _is_goc_human_lane_actor(
                aid,
                human_actor_id=human_actor_id,
                selected_player_role=selected_player_role,
            ):
                continue
        bt = str(action_block_type or "actor_action").strip().lower()
        if bt not in {"actor_action", "actor_line"}:
            bt = "actor_action"
        append_fn(
            bt,
            line,
            speaker_label=actor_label_fn(aid),
            actor_id=aid or None,
        )
        return "action_lines"
    return None


def _try_initiative_with_blocks(
    *,
    append_fn: Any,
    actor_label_fn: Any,
    runtime_projection: dict[str, Any] | None,
    human_actor_id: str,
    selected_player_role: str,
    structured_output: dict[str, Any],
) -> str | None:
    events = structured_output.get("initiative_events")
    if not isinstance(events, list):
        return None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        aid = str(ev.get("actor_id") or "").strip()
        ev_type = str(ev.get("type") or "").strip().lower()
        if ev_type not in {"interrupt", "counter", "seize_initiative"}:
            continue
        line = str(ev.get("text") or ev.get("line") or ev.get("summary") or "").strip()
        if not line or not aid:
            continue
        if runtime_projection is not None and _is_goc_human_lane_actor(
            aid,
            human_actor_id=human_actor_id,
            selected_player_role=selected_player_role,
        ):
            continue
        append_fn(
            "actor_action",
            line,
            speaker_label=actor_label_fn(aid),
            actor_id=aid or None,
        )
        return "initiative_events"
    return None


def _append_canonical_signal(signals: list[str], signal: str) -> None:
    if signal not in DEGRADATION_SIGNAL_VALUES:
        return
    if signal not in signals:
        signals.append(signal)


def _canonical_quality_fields_from_surfaces(
    *,
    runtime_governance_surface: dict[str, Any],
    authority_summary: dict[str, Any],
) -> tuple[str, list[str], str]:
    quality = str(runtime_governance_surface.get("quality_class") or "").strip().lower()
    signals = runtime_governance_surface.get("degradation_signals")
    signal_list: list[str] = []
    if isinstance(signals, list):
        for signal in signals:
            _append_canonical_signal(signal_list, str(signal).strip())

    if not signal_list:
        validation_status = str(authority_summary.get("validation_status") or "").strip().lower()
        validation_reason = str(runtime_governance_surface.get("validation_reason") or "").strip().lower()
        fallback_stage = str(runtime_governance_surface.get("fallback_stage_reached") or "").strip().lower()
        transition_pattern = str(runtime_governance_surface.get("transition_pattern") or "").strip().lower()
        if fallback_stage and fallback_stage != "primary_only":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_FALLBACK_USED)
        if bool(runtime_governance_surface.get("mock_output_flag")):
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_FALLBACK_USED)
        if transition_pattern == "diagnostics_only":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_NON_FACTUAL_STAGING)
        if validation_reason == "degraded_commit_after_retries":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_DEGRADED_COMMIT)
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_RETRY_EXHAUSTED)
        if validation_reason == "opening_leniency_approved":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY)
        if runtime_governance_surface.get("dramatic_quality_gate") == "effect_gate_weak_signal":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED)
        rationale_codes = runtime_governance_surface.get("dramatic_effect_rationale_codes")
        if isinstance(rationale_codes, list) and "actor_lanes_thin_prose_override" in [str(x) for x in rationale_codes]:
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE)
        actor_lane_status = str(runtime_governance_surface.get("actor_lane_validation_status") or "").strip().lower()
        if actor_lane_status == "rejected":
            _append_canonical_signal(signal_list, DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED)
        if validation_status and validation_status != "approved" and quality != QUALITY_CLASS_FAILED:
            quality = QUALITY_CLASS_FAILED

    if quality not in QUALITY_CLASS_VALUES:
        validation_status = str(authority_summary.get("validation_status") or "").strip().lower()
        quality = canonical_quality_class(
            validation_outcome={"status": validation_status},
            commit_applied=bool(authority_summary.get("commit_applied")),
            degradation_signals=signal_list,
        )

    summary = str(runtime_governance_surface.get("degradation_summary") or "").strip()
    if not summary:
        summary = ", ".join(signal_list) if signal_list else "none"
    return quality, signal_list, summary


def _build_actor_turn_summary(
    *,
    graph_state: dict[str, Any],
    visible_output_bundle: dict[str, Any] | None,
    dramatic_context_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    bundle = visible_output_bundle if isinstance(visible_output_bundle, dict) else {}
    context = dramatic_context_summary if isinstance(dramatic_context_summary, dict) else {}
    responder = context.get("responder") if isinstance(context.get("responder"), dict) else {}
    responder_scope = responder.get("responder_scope") if isinstance(responder.get("responder_scope"), list) else []
    primary_responder_id = (
        str(graph_state.get("responder_id") or "").strip()
        or str(responder.get("responder_id") or "").strip()
        or None
    )
    secondary_responder_ids = [
        str(x).strip()
        for x in responder_scope
        if str(x).strip() and str(x).strip() != (primary_responder_id or "")
    ]
    spoken_line_count = _actor_line_count(bundle.get("spoken_lines"))
    action_line_count = _actor_line_count(bundle.get("action_lines"))

    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    metadata = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = metadata.get("structured_output") if isinstance(metadata.get("structured_output"), dict) else {}
    initiative_events = structured.get("initiative_events") if isinstance(structured.get("initiative_events"), list) else []
    initiative_types: list[str] = []
    initiative_actors: list[str] = []
    for event in initiative_events:
        if not isinstance(event, dict):
            continue
        raw_type = event.get("type")
        raw_actor = event.get("actor_id")
        event_type = str(raw_type).strip() if isinstance(raw_type, str) else ""
        actor_id = str(raw_actor).strip() if isinstance(raw_actor, str) else ""
        if event_type and event_type not in initiative_types:
            initiative_types.append(event_type)
        if actor_id and actor_id not in initiative_actors:
            initiative_actors.append(actor_id)
    initiative_summary = {
        "event_count": len([x for x in initiative_events if isinstance(x, dict)]),
        "event_types": initiative_types,
        "actors": initiative_actors,
    }

    validation = (
        graph_state.get("validation_outcome")
        if isinstance(graph_state.get("validation_outcome"), dict)
        else {}
    )
    actor_lane_validation = (
        validation.get("actor_lane_validation")
        if isinstance(validation.get("actor_lane_validation"), dict)
        else {}
    )
    social_outcome = str(graph_state.get("social_outcome") or "").strip()
    dramatic_direction = str(graph_state.get("dramatic_direction") or "").strip()
    summary_parts: list[str] = []
    if primary_responder_id:
        summary_parts.append(f"primary_responder={primary_responder_id}")
    summary_parts.append(f"spoken_lines={spoken_line_count}")
    summary_parts.append(f"action_lines={action_line_count}")
    if initiative_summary["event_count"]:
        summary_parts.append(f"initiative_events={initiative_summary['event_count']}")
    if social_outcome:
        summary_parts.append(f"social_outcome={social_outcome}")
    if dramatic_direction:
        summary_parts.append(f"dramatic_direction={dramatic_direction}")

    return {
        "contract": "actor_turn_summary.v1",
        "primary_responder_id": primary_responder_id,
        "secondary_responder_ids": secondary_responder_ids,
        "spoken_line_count": spoken_line_count,
        "action_line_count": action_line_count,
        "initiative_summary": initiative_summary,
        "actor_lane_validation_status": actor_lane_validation.get("status"),
        "last_actor_outcome_summary": ", ".join(summary_parts) if summary_parts else None,
    }


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _short_text(value: Any, *, limit: int = 500) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _infer_execution_tier_for_pytest() -> str:
    current = str(os.environ.get("PYTEST_CURRENT_TEST") or "").lower()
    if not current:
        return "diagnostic"
    if "integration" in current:
        return "integration_test"
    if "contract" in current:
        return "contract_test"
    if "fixture" in current:
        return "fixture"
    return "contract_test"


def _goc_shell_actor_firstname(actor_id: str) -> str:
    aid = str(canonicalize_goc_actor_id(str(actor_id).strip()) or str(actor_id).strip()).strip()
    return goc_shell_actor_firstname(aid)


def _goc_npc_shell_legal_name(responder_id: str) -> str:
    rid = str(canonicalize_goc_actor_id(str(responder_id).strip()) or str(responder_id).strip()).strip()
    return goc_npc_shell_legal_name(rid)


def _goc_greeting_imperative_addressee_fragment(raw: str, *, lang: str) -> str | None:
    """If ``raw`` is a greet-X imperative (DE/EN), return the tail after the verb; else ``None``."""
    return greeting_imperative_addressee_fragment(
        raw,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
    )


def _goc_addressee_shell_firstname(fragment: str) -> str:
    """Map a free-text addressee token to the same shell first-name spelling we use for NPC labels."""
    frag = str(fragment or "").strip()
    if not frag:
        return ""
    first = frag.split()[0] if frag.split() else frag
    first = first.strip(".,;:!?")
    canon = str(canonicalize_goc_actor_id(first) or first).strip()
    return _goc_shell_actor_firstname(canon)


def _goc_greeting_imperative_visible_pair(
    *,
    raw: str,
    player_shell_name: str,
    lang: str,
) -> tuple[str, str] | None:
    """Return (verbatim_player_typing, diegetic_attributed_line) for greet-X imperatives.

    Used when the player typed an imperative greeting to a named actor rather than
    direct in-scene speech. The story window emits two scene blocks.
    """
    tail = _goc_greeting_imperative_addressee_fragment(raw, lang=lang)
    if not tail:
        return None
    addressee = _goc_addressee_shell_firstname(tail)
    if not addressee:
        return None
    return greeting_imperative_visible_pair(
        raw,
        addressee=addressee,
        player_shell_name=player_shell_name,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
    )


def _goc_player_attributed_visible_text(
    *,
    raw_input: str,
    human_actor_id: str,
    session_output_language: str,
    interpreted_input: dict[str, Any] | None,
) -> tuple[str, str]:
    """Return (speaker_label, full_visible_line) for a committed human player line."""
    raw = str(raw_input or "").strip()
    lang = str(session_output_language or "de").strip().lower()[:2] or "de"
    name = _goc_shell_actor_firstname(human_actor_id)
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    # Prefer fine-grained player_input_kind (set by classification rules) over coarse input_kind.
    pik_fine = str(interp.get("player_input_kind") or "").strip().lower()
    ik = pik_fine or str(interp.get("input_kind") or interp.get("kind") or "speech").strip().lower()
    pk = str(interp.get("projection_key") or "").strip() or None
    pc = interp.get("projection_captures") if isinstance(interp.get("projection_captures"), dict) else {}
    line = build_player_attributed_visible_line(
        name=name,
        raw=raw,
        input_kind=ik,
        lang=lang,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        content_modules_root=_goc_content_modules_root(),
        projection_key=pk,
        projection_captures=pc,
    )
    return name, line


def _infer_generation_mode(path_summary_seed: dict[str, Any]) -> str:
    adapter = str(path_summary_seed.get("adapter") or "").strip().lower()
    final_adapter = str(path_summary_seed.get("final_adapter") or "").strip().lower()
    invocation_mode = str(path_summary_seed.get("adapter_invocation_mode") or "").strip().lower()
    fallback_mode = str(path_summary_seed.get("final_adapter_invocation_mode") or "").strip().lower()

    if adapter == "mock" or final_adapter == "mock":
        return "mock_only"
    if "ldss_fallback" in adapter or "ldss_fallback" in final_adapter:
        return "ldss_fallback"
    if "fixture" in invocation_mode or "fixture" in fallback_mode:
        return "deterministic_fixture"
    return "live_openai"


def _compose_resolved_target_status(
    player_action_frame: dict[str, Any],
    affordance_status: str | None,
) -> str | None:
    """Single operator-facing token for target + affordance (P0 evidence lane)."""
    rid = str(player_action_frame.get("resolved_target_id") or "").strip()
    aff = str(affordance_status or "").strip().lower()
    if rid:
        return f"{rid}:{aff}" if aff else rid
    if aff:
        return aff
    return "unresolved" if player_action_frame else None


def _build_p0_action_resolution_evidence(
    *,
    event: dict[str, Any],
    graph_state: dict[str, Any],
    interpreted_input: dict[str, Any],
    validation: dict[str, Any],
    committed_result: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic P0 player-action audit fields for real player turns only.

    Opening traces (``turn_number == 0``) set ``p0_player_action_evidence_applicable`` false
    and omit player-action payload so Langfuse scores/metadata are not misread as P0 proof.
    """
    turn_number = int(event.get("turn_number") or 0)
    p0_applicable = turn_number > 0
    intent_surface_diag = (
        validation.get("intent_surface_diagnostics")
        if isinstance(validation.get("intent_surface_diagnostics"), dict)
        else {}
    )
    npc_narrated_violation = bool(
        validation.get("npc_narrated_player_action_violation")
        or intent_surface_diag.get("npc_narrated_player_action_violation")
    )
    if not p0_applicable:
        return {
            "contract": "p0_action_resolution_evidence.v1",
            "p0_player_action_evidence_applicable": False,
            "p0_excluded_reason": "opening_turn_not_player_action_evidence_lane",
            "raw_player_input": None,
            "player_action_frame": None,
            "resolved_target_status": None,
            "affordance_status": None,
            "action_commit_policy": None,
            "action_commit_status": None,
            "player_speech_committed": None,
            "player_action_committed": None,
            "narrator_response_expected": None,
            "npc_response_expected": None,
            "npc_committed_player_action": None,
            "turn_status": event.get("turn_status"),
            "http_status": event.get("http_status"),
        }

    paf = graph_state.get("player_action_frame") if isinstance(graph_state.get("player_action_frame"), dict) else {}
    inner_aff = paf.get("affordance_resolution") if isinstance(paf.get("affordance_resolution"), dict) else {}
    top_aff = (
        graph_state.get("affordance_resolution") if isinstance(graph_state.get("affordance_resolution"), dict) else {}
    )
    aff_src = inner_aff or top_aff
    aff_st = str(aff_src.get("affordance_status") or paf.get("affordance_status") or "").strip() or None
    pol = str(aff_src.get("action_commit_policy") or "").strip() or None
    paa = (
        committed_result.get("player_action_authority")
        if isinstance(committed_result.get("player_action_authority"), dict)
        else {}
    )
    action_commit_status = str(paa.get("action_commit_status") or "").strip() or None

    p_frame = {
        "raw_text": paf.get("raw_text"),
        "input_kind": paf.get("input_kind") or paf.get("player_input_kind"),
        "action_kind": paf.get("action_kind"),
        "verb": paf.get("verb"),
        "target_query": paf.get("target_query"),
    }

    return {
        "contract": "p0_action_resolution_evidence.v1",
        "p0_player_action_evidence_applicable": True,
        "p0_excluded_reason": None,
        "raw_player_input": str(event.get("raw_input") or graph_state.get("player_input") or "").strip() or None,
        "player_action_frame": p_frame,
        "resolved_target_status": _compose_resolved_target_status(paf, aff_st),
        "affordance_status": aff_st,
        "action_commit_policy": pol,
        "action_commit_status": action_commit_status,
        "player_speech_committed": interpreted_input.get("player_speech_committed"),
        "player_action_committed": interpreted_input.get("player_action_committed"),
        "narrator_response_expected": interpreted_input.get("narrator_response_expected"),
        "npc_response_expected": interpreted_input.get("npc_response_expected"),
        "npc_committed_player_action": npc_narrated_violation,
        "turn_status": event.get("turn_status"),
        "http_status": event.get("http_status"),
    }


def _build_langfuse_path_summary(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    nodes = _str_list(graph_state.get("nodes_executed"))
    routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    interpreted_input = (
        graph_state.get("interpreted_input")
        if isinstance(graph_state.get("interpreted_input"), dict)
        else {}
    )
    semantic_move_record = (
        graph_state.get("semantic_move_record")
        if isinstance(graph_state.get("semantic_move_record"), dict)
        else {}
    )
    scene_plan_record = (
        graph_state.get("scene_plan_record")
        if isinstance(graph_state.get("scene_plan_record"), dict)
        else {}
    )
    scene_assessment = (
        graph_state.get("scene_assessment")
        if isinstance(graph_state.get("scene_assessment"), dict)
        else {}
    )
    multi_pressure_resolution = (
        scene_assessment.get("multi_pressure_resolution")
        if isinstance(scene_assessment.get("multi_pressure_resolution"), dict)
        else {}
    )
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    validation = (
        graph_state.get("validation_outcome")
        if isinstance(graph_state.get("validation_outcome"), dict)
        else {}
    )
    actor_lane_validation = (
        validation.get("actor_lane_validation")
        if isinstance(validation.get("actor_lane_validation"), dict)
        else {}
    )
    committed = (
        graph_state.get("committed_result")
        if isinstance(graph_state.get("committed_result"), dict)
        else {}
    )
    telemetry = (
        graph_state.get("actor_survival_telemetry")
        if isinstance(graph_state.get("actor_survival_telemetry"), dict)
        else {}
    )
    vitality = (
        telemetry.get("vitality_telemetry_v1")
        if isinstance(telemetry.get("vitality_telemetry_v1"), dict)
        else {}
    )
    passivity = (
        telemetry.get("passivity_diagnosis_v1")
        if isinstance(telemetry.get("passivity_diagnosis_v1"), dict)
        else {}
    )
    governance = (
        event.get("runtime_governance_surface")
        if isinstance(event.get("runtime_governance_surface"), dict)
        else {}
    )
    human_input_attribution = (
        event.get("human_input_attribution")
        if isinstance(event.get("human_input_attribution"), dict)
        else {}
    )
    retrieval = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
    structured = gen_meta.get("structured_output")
    if structured is None:
        structured = generation.get("structured_output")
    graph_errors = _str_list(graph_state.get("graph_errors"))
    _ledger_src = (
        graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else None
    )
    turn_aspect_ledger = normalize_runtime_aspect_ledger(_ledger_src) if isinstance(_ledger_src, dict) else None
    usage_details = gen_meta.get("usage_details") if isinstance(gen_meta.get("usage_details"), dict) else {}
    _u_in = int(usage_details.get("input") or gen_meta.get("tokens_prompt") or 0)
    _u_out = int(usage_details.get("output") or gen_meta.get("tokens_completion") or 0)
    _u_tot = int(usage_details.get("total") or gen_meta.get("tokens_total") or 0)
    if _u_tot <= 0 and (_u_in > 0 or _u_out > 0):
        _u_tot = _u_in + _u_out
    usage_total = _u_tot
    _graph_pkg = event.get("graph") if isinstance(event.get("graph"), dict) else {}
    _graph_name = str(_graph_pkg.get("graph_name") or "").strip() or None
    _route_id = str(routing.get("route_id") or "").strip()
    _route_family = str(routing.get("route_family") or "").strip()
    _langfuse_prompt_parts = [p for p in (_route_id, _route_family, _graph_name) if p]
    _langfuse_prompt_name = "/".join(_langfuse_prompt_parts) if _langfuse_prompt_parts else None
    _lat_raw = gen_meta.get("generation_latency_ms")
    _lat_ms = float(_lat_raw) if isinstance(_lat_raw, (int, float)) else None
    _tps_out: float | None = None
    if _lat_ms is not None and _lat_ms > 0 and _u_out > 0:
        _tps_out = round(_u_out / (_lat_ms / 1000.0), 4)
    _streaming = gen_meta.get("llm_invocation_streaming")
    _ttft_ms: float | None = None
    if _lat_ms is not None and _lat_ms >= 0:
        # Non-streaming HTTP completions: no true first-token boundary; use full call latency.
        if _streaming is False:
            _ttft_ms = round(_lat_ms, 3)
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    provenance = session.content_provenance if isinstance(session.content_provenance, dict) else {}
    trace_classification = (
        provenance.get("trace_classification")
        if isinstance(provenance.get("trace_classification"), dict)
        else {}
    )
    runtime_mode = str(
        trace_classification.get("runtime_mode")
        or projection.get("runtime_mode")
        or "solo_story"
    ).strip() or "solo_story"
    trace_origin = str(trace_classification.get("trace_origin") or "").strip() or "unknown"
    execution_tier = str(trace_classification.get("execution_tier") or "").strip()
    if not execution_tier:
        execution_tier = _infer_execution_tier_for_pytest() if trace_origin == "pytest" else "diagnostic"
    canonical_player_flow = bool(trace_classification.get("canonical_player_flow", False))
    test_case_id = trace_classification.get("test_case_id")
    environment = _observability_environment_for_session(session)

    _spr = (
        str((session.runtime_projection or {}).get("selected_player_role") or "").strip()
        if isinstance(session.runtime_projection, dict)
        else ""
    )
    _player_input_kind = str(interpreted_input.get("player_input_kind") or "").strip().lower()
    _semantic_move_kind = str(semantic_move_record.get("move_type") or "").strip()
    _subtext_record = (
        semantic_move_record.get("subtext")
        if isinstance(semantic_move_record.get("subtext"), dict)
        else {}
    )
    _subtext_contract_pass = True
    if semantic_move_record:
        _subtext_contract_pass = (
            (not _semantic_move_kind or _semantic_move_kind in SEMANTIC_MOVE_TYPES)
            and bool(str(_subtext_record.get("surface_mode") or "").strip())
            and bool(str(_subtext_record.get("hidden_intent_hypothesis") or "").strip())
            and bool(str(_subtext_record.get("subtext_function") or "").strip())
            and bool(str(_subtext_record.get("sincerity_band") or "").strip())
        )
    _intent_surface_contract_pass = True
    if _player_input_kind:
        _intent_surface_contract_pass = (
            _player_input_kind in PLAYER_INPUT_KINDS
            and isinstance(interpreted_input.get("player_action_committed"), bool)
            and isinstance(interpreted_input.get("player_speech_committed"), bool)
            and isinstance(interpreted_input.get("narrator_response_expected"), bool)
            and isinstance(interpreted_input.get("npc_response_expected"), bool)
        )
    _player_input_attribution_pass = (
        bool(human_input_attribution.get("player_input_attribution_pass"))
        if "player_input_attribution_pass" in human_input_attribution
        else True
    )
    _semantic_move_alignment_pass = True
    if _semantic_move_kind:
        _semantic_move_alignment_pass = True
    if is_question_punctuation_probe_guarded(_player_input_kind) and _semantic_move_kind:
        _semantic_move_alignment_pass = (
            _semantic_move_alignment_pass
            and _semantic_move_kind not in FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES
        )
    _npc_action_narration_boundary_pass = not bool(
        (
            validation.get("intent_surface_diagnostics")
            if isinstance(validation.get("intent_surface_diagnostics"), dict)
            else {}
        ).get("npc_narrated_player_action_violation")
    )
    _runtime_profile_id = (
        _runtime_profile_id_from_projection(projection)
        or (
            turn_aspect_ledger.get("runtime_profile_id")
            if isinstance(turn_aspect_ledger, dict)
            else None
        )
    )
    if isinstance(turn_aspect_ledger, dict) and _runtime_profile_id and not turn_aspect_ledger.get("runtime_profile_id"):
        turn_aspect_ledger = dict(turn_aspect_ledger)
        turn_aspect_ledger["runtime_profile_id"] = _runtime_profile_id
        turn_aspect_ledger = normalize_runtime_aspect_ledger(turn_aspect_ledger)
    self_correction = (
        graph_state.get("self_correction")
        if isinstance(graph_state.get("self_correction"), dict)
        else {}
    )
    _sc_attempts_raw = (
        self_correction.get("attempts")
        if isinstance(self_correction.get("attempts"), list)
        else []
    )
    _sc_attempts = [item for item in _sc_attempts_raw if isinstance(item, dict)]
    _first_sc = _sc_attempts[0] if _sc_attempts else {}
    _last_sc = _sc_attempts[-1] if _sc_attempts else {}
    _sc_attempted = gen_meta.get("self_correction_attempted")
    if _sc_attempted is None and self_correction:
        _sc_attempted = bool(_sc_attempts)
    _sc_attempt_count = gen_meta.get("self_correction_attempt_count")
    if _sc_attempt_count is None and self_correction:
        _sc_attempt_count = self_correction.get("attempt_count")
        if _sc_attempt_count is None:
            _sc_attempt_count = len(_sc_attempts)
    _sc_success = gen_meta.get("self_correction_success")
    if _sc_success is None and self_correction:
        _sc_success = (
            bool(_last_sc.get("success")) and not _last_sc.get("parser_error")
            if _last_sc
            else False
        )
    _sc_model = gen_meta.get("self_correction_model")
    if _sc_model is None and _last_sc:
        _sc_model = _last_sc.get("candidate_model")
    _sc_trigger_source = gen_meta.get("self_correction_trigger_source")
    if _sc_trigger_source is None and _first_sc:
        _sc_trigger_source = _first_sc.get("trigger_source")
    _runtime_aspect_failure_before_retry = gen_meta.get("runtime_aspect_failure_before_retry")
    if _runtime_aspect_failure_before_retry is None and _first_sc:
        _runtime_aspect_failure_before_retry = _first_sc.get("runtime_aspect_failure_before_retry")
    _capability_failure_before_retry = gen_meta.get("capability_failure_before_retry")
    if _capability_failure_before_retry is None and _first_sc:
        _capability_failure_before_retry = _first_sc.get("capability_failure_before_retry")
    _sc_resolved_failure = gen_meta.get("self_correction_resolved_failure")
    if _sc_resolved_failure is None and self_correction:
        _sc_resolved_failure = any(bool(item.get("resolved_failure")) for item in _sc_attempts)
    branching_forecast = (
        event.get("branching_forecast")
        if isinstance(event.get("branching_forecast"), dict)
        else graph_state.get("branching_forecast")
        if isinstance(graph_state.get("branching_forecast"), dict)
        else turn_aspect_ledger.get("branching_forecast")
        if isinstance(turn_aspect_ledger, dict) and isinstance(turn_aspect_ledger.get("branching_forecast"), dict)
        else {}
    )
    branch_option_count = int(branching_forecast.get("option_count") or 0) if branching_forecast else 0
    branching_forecast_present = (
        bool(branching_forecast)
        and str(branching_forecast.get("status") or "").strip() == "forecasted"
        and branch_option_count > 0
    )
    inactive_branches_non_authoritative = bool(
        branching_forecast
        and branching_forecast.get("forecast_only") is True
        and branching_forecast.get("authoritative") is False
        and branching_forecast.get("inactive_branches_authoritative") is False
        and branching_forecast.get("mutates_canonical_state") is False
    )
    summary = {
        "contract": "story_runtime_path_observability.v1",
        "session_id": session.session_id,
        "module_id": session.module_id,
        "runtime_profile_id": _runtime_profile_id,
        "environment": environment,
        "turn_number": event.get("turn_number"),
        "turn_kind": event.get("turn_kind"),
        "raw_player_input": str(event.get("raw_input") or graph_state.get("player_input") or "").strip() or None,
        "turn_aspect_ledger_present": bool(
            isinstance(turn_aspect_ledger, dict)
            and isinstance(turn_aspect_ledger.get("turn_aspect_ledger"), dict)
        ),
        "turn_aspect_ledger": turn_aspect_ledger,
        "branching_forecast": branching_forecast,
        "branching_forecast_status": branching_forecast.get("status") if branching_forecast else None,
        "branching_forecast_present": branching_forecast_present,
        "branch_option_count": branch_option_count,
        "branching_forecast_only": bool(branching_forecast.get("forecast_only")) if branching_forecast else False,
        "inactive_branches_non_authoritative": inactive_branches_non_authoritative,
        "inactive_branches_mutate_state": bool(branching_forecast.get("mutates_canonical_state"))
        if branching_forecast
        else False,
        "selected_player_role": _spr or None,
        "human_actor_id": (session.runtime_projection or {}).get("human_actor_id") if isinstance(session.runtime_projection, dict) else None,
        "player_role_display_name": goc_player_role_display_name(_spr or None),
        "session_output_language": getattr(session, "session_output_language", None) or "de",
        "npc_actor_ids": list((session.runtime_projection or {}).get("npc_actor_ids") or []) if isinstance(session.runtime_projection, dict) else [],
        "nodes_executed": nodes,
        "route_model_called": "route_model" in nodes or bool(routing),
        "invoke_model_called": "invoke_model" in nodes,
        "fallback_model_called": "fallback_model" in nodes or bool(generation.get("fallback_used")),
        "graph_fallback_node_called": "fallback_model" in nodes,
        "retrieval_called": "retrieve_context" in nodes or bool(retrieval),
        "validation_called": "validate_seam" in nodes or bool(validation),
        "commit_called": "commit_seam" in nodes or bool(committed),
        "render_visible_called": "render_visible" in nodes or isinstance(event.get("visible_output_bundle"), dict),
        "route_id": routing.get("route_id"),
        "route_family": routing.get("route_family"),
        "selected_provider": routing.get("selected_provider"),
        "selected_model": routing.get("selected_model"),
        "fallback_model": routing.get("fallback_model"),
        "fallback_chain": routing.get("fallback_chain"),
        "registered_adapter_providers": routing.get("registered_adapter_providers"),
        "generation_execution_mode": routing.get("generation_execution_mode"),
        "adapter": gen_meta.get("adapter"),
        "api_model": gen_meta.get("model"),
        "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
        # ADR-0033 §13.10 primary-vs-final clarity. ``adapter``/``api_model`` describe
        # the FINAL committed invocation (e.g. ldss_fallback after live opening failure).
        # The primary-attempt block surfaces what live route was tried first so
        # operators do not misread degraded fallback traces as healthy openai turns.
        "primary_attempt_adapter": gen_meta.get("primary_attempt_adapter"),
        "primary_attempt_model": gen_meta.get("primary_attempt_model"),
        "primary_attempt_provider": (
            gen_meta.get("primary_attempt_provider")
            or routing.get("selected_provider")
        ),
        "primary_attempt_selected_model": (
            gen_meta.get("primary_attempt_selected_model")
            or routing.get("selected_model")
        ),
        "primary_attempt_invocation_mode": gen_meta.get("primary_attempt_invocation_mode"),
        "final_adapter": gen_meta.get("final_adapter") or gen_meta.get("adapter"),
        "final_adapter_invocation_mode": (
            gen_meta.get("final_adapter_invocation_mode")
            or gen_meta.get("adapter_invocation_mode")
        ),
        "fallback_reason": gen_meta.get("fallback_reason") or routing.get("fallback_reason"),
        "ldss_fallback_after_live_opening_failure": bool(
            gen_meta.get("ldss_fallback_after_live_opening_failure")
        ),
        "generation_attempted": bool(generation.get("attempted")),
        "generation_success": generation.get("success"),
        "generation_error": _short_text(generation.get("error") or gen_meta.get("error")),
        "generation_fallback_used": bool(generation.get("fallback_used")),
        "parser_error": _short_text(gen_meta.get("langchain_parser_error") or generation.get("parser_error")),
        "structured_output_present": isinstance(structured, dict),
        "structured_output_keys": sorted(structured.keys()) if isinstance(structured, dict) else [],
        # PRIMARY-PARSER-EVIDENCE-01: primary attempt diagnosis fields.
        "primary_attempt_api_success": gen_meta.get("primary_attempt_api_success"),
        "primary_attempt_parser_error_present": gen_meta.get("primary_attempt_parser_error_present"),
        "primary_attempt_parser_error": gen_meta.get("primary_attempt_parser_error"),
        "primary_attempt_structured_output_present": gen_meta.get("primary_attempt_structured_output_present"),
        "primary_attempt_raw_output_sha256": gen_meta.get("primary_attempt_raw_output_sha256"),
        "primary_attempt_raw_output_excerpt": gen_meta.get("primary_attempt_raw_output_excerpt"),
        "self_correction_attempted": _sc_attempted,
        "self_correction_attempt_count": _sc_attempt_count,
        "self_correction_success": _sc_success,
        "self_correction_model": _sc_model,
        "self_correction_trigger_source": _sc_trigger_source,
        "runtime_aspect_failure_before_retry": _runtime_aspect_failure_before_retry,
        "capability_failure_before_retry": _capability_failure_before_retry,
        "self_correction_resolved_failure": _sc_resolved_failure,
        "usage_available": bool(gen_meta.get("usage_available")) or usage_total > 0,
        "usage_source": gen_meta.get("usage_source"),
        "usage_details": {
            "input": _u_in,
            "output": _u_out,
            "total": usage_total,
        },
        "langfuse_prompt_name": _langfuse_prompt_name,
        "provided_model_name": str(gen_meta.get("model") or "").strip() or None,
        "generation_latency_ms": round(_lat_ms, 3) if isinstance(_lat_ms, (int, float)) else None,
        "llm_invocation_streaming": _streaming,
        "time_to_first_token_ms": _ttft_ms,
        "time_to_first_token_note": (
            "non_streaming_latency_proxy" if _streaming is False and _ttft_ms is not None else None
        ),
        "tokens_per_second_output": _tps_out,
        "retrieval_status": retrieval.get("status"),
        "retrieval_route": retrieval.get("retrieval_route"),
        "retrieval_hit_count": retrieval.get("hit_count"),
        "retrieval_profile": retrieval.get("profile"),
        "retrieval_domain": retrieval.get("domain"),
        "retrieval_context_attached": bool(graph_state.get("context_text") or generation.get("retrieval_context_attached")),
        "retrieval_top_hit_score": retrieval.get("top_hit_score"),
        "retrieval_corpus_fingerprint": retrieval.get("corpus_fingerprint"),
        "retrieval_index_version": retrieval.get("index_version"),
        "retrieval_degradation_mode": retrieval.get("degradation_mode"),
        "retrieval_governance_summary": retrieval.get("retrieval_governance_summary"),
        "validation_status": validation.get("status"),
        "validation_reason": validation.get("reason"),
        "intent_surface_diagnostics": (
            validation.get("intent_surface_diagnostics")
            if isinstance(validation.get("intent_surface_diagnostics"), dict)
            else {}
        ),
        "npc_narrated_player_action_violation": bool(
            (
                validation.get("intent_surface_diagnostics")
                if isinstance(validation.get("intent_surface_diagnostics"), dict)
                else {}
            ).get("npc_narrated_player_action_violation")
        ),
        "actor_lane_validation_status": actor_lane_validation.get("status"),
        "actor_lane_validation_reason": actor_lane_validation.get("reason"),
        "commit_applied": bool(committed.get("commit_applied")),
        "player_input_kind": str(interpreted_input.get("player_input_kind") or "").strip().lower() or None,
        "player_input_kind_family": player_input_kind_family(_player_input_kind) if _player_input_kind else None,
        "intent_contract_version": INTENT_CONTRACT_VERSION,
        "player_action_committed": bool(interpreted_input.get("player_action_committed")),
        "player_speech_committed": bool(interpreted_input.get("player_speech_committed")),
        "narrator_response_expected": bool(interpreted_input.get("narrator_response_expected")),
        "npc_response_expected": bool(interpreted_input.get("npc_response_expected")),
        "player_action_frame_present": bool(
            graph_state.get("player_action_frame")
            if isinstance(graph_state.get("player_action_frame"), dict)
            else False
        ),
        "affordance_resolution_present": bool(
            graph_state.get("affordance_resolution")
            if isinstance(graph_state.get("affordance_resolution"), dict)
            else False
        ),
        "affordance_status": (
            str(
                (
                    graph_state.get("affordance_resolution")
                    if isinstance(graph_state.get("affordance_resolution"), dict)
                    else {}
                ).get("affordance_status")
                or ""
            ).strip()
            or None
        ),
        "action_commit_policy": (
            str(
                (
                    graph_state.get("affordance_resolution")
                    if isinstance(graph_state.get("affordance_resolution"), dict)
                    else {}
                ).get("action_commit_policy")
                or ""
            ).strip()
            or None
        ),
        "action_resolution_branch": routing.get("action_resolution_branch"),
        "action_resolution_short_path": bool(routing.get("action_resolution_short_path")),
        "action_resolution_short_path_reason": routing.get("action_resolution_short_path_reason"),
        "synthetic_short_path": bool(routing.get("action_resolution_short_path")),
        "authoritative_action_resolution_reason": (
            routing.get("action_resolution_short_path_reason")
            if routing.get("action_resolution_short_path")
            else None
        ),
        "generation_required": (
            bool(routing.get("generation_required"))
            if routing.get("generation_required") is not None
            else bool("invoke_model" in nodes or "fallback_model" in nodes)
        ),
        "semantic_move_kind": str(semantic_move_record.get("move_type") or "").strip() or None,
        "subtext_surface_mode": str(_subtext_record.get("surface_mode") or "").strip() or None,
        "subtext_hidden_intent_hypothesis": (
            str(_subtext_record.get("hidden_intent_hypothesis") or "").strip() or None
        ),
        "subtext_function": str(_subtext_record.get("subtext_function") or "").strip() or None,
        "subtext_sincerity_band": str(_subtext_record.get("sincerity_band") or "").strip() or None,
        "subtext_policy_source": str(_subtext_record.get("policy_source") or "").strip() or None,
        "subtext_policy_rule_id": str(_subtext_record.get("policy_rule_id") or "").strip() or None,
        "subtext_evidence_codes": list(_subtext_record.get("evidence_codes") or [])
        if isinstance(_subtext_record.get("evidence_codes"), list)
        else [],
        "scene_director_selection_source": (
            str(multi_pressure_resolution.get("selection_source") or "").strip()
            or str(scene_plan_record.get("selection_source") or "").strip()
            or None
        ),
        "planner_rationale_codes": list(scene_plan_record.get("planner_rationale_codes") or [])
        if isinstance(scene_plan_record.get("planner_rationale_codes"), list)
        else [],
        "scene_energy_target": (
            graph_state.get("scene_energy_target")
            if isinstance(graph_state.get("scene_energy_target"), dict)
            else scene_plan_record.get("scene_energy_target")
            if isinstance(scene_plan_record.get("scene_energy_target"), dict)
            else {}
        ),
        "scene_energy_transition": (
            graph_state.get("scene_energy_transition")
            if isinstance(graph_state.get("scene_energy_transition"), dict)
            else scene_plan_record.get("scene_energy_transition")
            if isinstance(scene_plan_record.get("scene_energy_transition"), dict)
            else {}
        ),
        "scene_energy_validation": (
            graph_state.get("scene_energy_validation")
            if isinstance(graph_state.get("scene_energy_validation"), dict)
            else {}
        ),
        "pacing_rhythm_state": (
            graph_state.get("pacing_rhythm_state")
            if isinstance(graph_state.get("pacing_rhythm_state"), dict)
            else scene_plan_record.get("pacing_rhythm_state")
            if isinstance(scene_plan_record.get("pacing_rhythm_state"), dict)
            else {}
        ),
        "pacing_rhythm_target": (
            graph_state.get("pacing_rhythm_target")
            if isinstance(graph_state.get("pacing_rhythm_target"), dict)
            else scene_plan_record.get("pacing_rhythm_target")
            if isinstance(scene_plan_record.get("pacing_rhythm_target"), dict)
            else {}
        ),
        "pacing_rhythm_validation": (
            graph_state.get("pacing_rhythm_validation")
            if isinstance(graph_state.get("pacing_rhythm_validation"), dict)
            else {}
        ),
        "legacy_keyword_scene_candidates_used": bool(
            multi_pressure_resolution.get("legacy_keyword_scene_candidates_used")
        ),
        "intent_surface_contract_pass": 1 if _intent_surface_contract_pass else 0,
        "player_input_attribution_pass": 1 if _player_input_attribution_pass else 0,
        "semantic_move_alignment_pass": 1 if _semantic_move_alignment_pass else 0,
        "subtext_contract_pass": 1 if _subtext_contract_pass else 0,
        "npc_action_narration_boundary_pass": 1 if _npc_action_narration_boundary_pass else 0,
        "quality_class": governance.get("quality_class") or graph_state.get("quality_class"),
        "degradation_signals": list(governance.get("degradation_signals") or graph_state.get("degradation_signals") or []),
        "degradation_summary": governance.get("degradation_summary") or graph_state.get("degradation_summary"),
        "live_opening_failure_reason": gen_meta.get("live_opening_failure_reason") or generation.get("live_opening_failure_reason"),
        "graph_errors": graph_errors,
        "failure_markers": _str_list(graph_state.get("failure_markers")),
        "primary_responder_id": (
            graph_state.get("primary_responder_id")
            or graph_state.get("responder_id")
            or (event.get("actor_turn_summary") or {}).get("primary_responder_id")
        ),
        "response_present": bool(vitality.get("response_present"))
        or _final_visible_actor_response_in_event(event),
        "initiative_present": vitality.get("initiative_present"),
        "multi_actor_realized": vitality.get("multi_actor_realized"),
        "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
        "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
        "why_turn_felt_passive": (
            list(governance.get("why_turn_felt_passive"))
            if isinstance(governance.get("why_turn_felt_passive"), list)
            else list(passivity.get("why_turn_felt_passive") or [])
        ),
        "primary_passivity_factors": (
            list(governance.get("primary_passivity_factors"))
            if isinstance(governance.get("primary_passivity_factors"), list)
            else list(passivity.get("primary_passivity_factors") or [])
        ),
        "trace_origin": trace_origin,
        "execution_tier": execution_tier,
        "langfuse_environment": environment,
        "canonical_player_flow": canonical_player_flow,
        "test_case_id": test_case_id,
        "runtime_mode": runtime_mode,
    }
    opening_norm = graph_state.get("_opening_narration_normalization")
    if isinstance(opening_norm, dict):
        for key in (
            "opening_narration_normalized",
            "opening_narration_source",
            "opening_narration_beat_count",
            "narration_summary_input_kind",
        ):
            if key in opening_norm:
                summary[key] = opening_norm[key]
    ev_proj = graph_state.get("_actor_block_projection_evidence")
    if isinstance(ev_proj, dict):
        for key in (
            "actor_block_source",
            "actor_block_filtered_reason",
            "actor_line_count_before_projection",
            "action_line_count_before_projection",
            "actor_block_count_after_projection",
        ):
            if key in ev_proj:
                summary[key] = ev_proj[key]
    vis_contract = graph_state.get("_visible_narrative_contract")
    if isinstance(vis_contract, dict):
        for key in (
            "visible_language_detected",
            "mixed_language_detected",
            "visible_language_contract_pass",
            "selected_role_visible_in_opening",
            "player_identity_anchor_present",
            "visible_narrative_contract_version",
            "name_only_actor_block_removed",
            "label_only_line_removed",
            "duplicate_actor_label_removed",
            "placeholder_action_removed",
            "actor_line_action_tail_stripped",
            "near_duplicate_visible_block_removed",
        ):
            if key in vis_contract:
                summary[key] = vis_contract[key]
    oh_diag = graph_state.get("_opening_handover_diagnostics")
    if isinstance(oh_diag, dict):
        for key, val in oh_diag.items():
            summary[key] = val
    if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
        actor_lane_context = StoryRuntimeManager._extract_actor_lane_context(session)
        knowledge_summary = build_knowledge_path_summary(
            graph_state=graph_state,
            event=event,
            actor_lane_context=actor_lane_context,
        )
        summary.update(knowledge_summary)
    _plc_gs = graph_state.get("player_local_context")
    summary["player_local_context"] = _plc_gs if isinstance(_plc_gs, dict) else None
    _lct_gs = graph_state.get("local_context_transition")
    summary["local_context_transition"] = _lct_gs if isinstance(_lct_gs, dict) else None
    _ncp_gs = graph_state.get("narrator_consequence_plan")
    summary["narrator_consequence_plan"] = _ncp_gs if isinstance(_ncp_gs, dict) else None
    _env_gs = graph_state.get("environment_state")
    summary["environment_state"] = _env_gs if isinstance(_env_gs, dict) else None
    _env_tr = graph_state.get("environment_transition")
    summary["environment_transition"] = _env_tr if isinstance(_env_tr, dict) else None
    summary["movement_return_intent"] = bool(interpreted_input.get("movement_return_intent"))
    if "speech_projection_allowed" in interpreted_input:
        summary["speech_projection_allowed"] = bool(interpreted_input.get("speech_projection_allowed"))
    _aff_gs = graph_state.get("affordance_resolution") if isinstance(graph_state.get("affordance_resolution"), dict) else {}
    summary["resolved_target_id"] = _aff_gs.get("resolved_target_id")
    summary["target_resolution_source"] = _aff_gs.get("target_resolution_source")
    summary["authoritative_action_surface"] = bool(
        gen_meta.get("authoritative_action_resolution") is True
        or str(gen_meta.get("adapter") or "").strip().lower() == "action_resolution_authoritative"
    )
    if (
        bool(interpreted_input.get("movement_return_intent"))
        and str(summary.get("affordance_status") or "").strip().lower() == "ambiguous"
        and str(summary.get("action_commit_policy") or "").strip().lower() == "needs_clarification"
    ):
        summary["turn_status"] = "needs_clarification"

    summary["p0_action_resolution_evidence"] = _build_p0_action_resolution_evidence(
        event=event,
        graph_state=graph_state,
        interpreted_input=interpreted_input,
        validation=validation,
        committed_result=committed,
    )
    summary["generation_mode"] = _infer_generation_mode(summary)
    tn = event.get("turn_number")
    summary["canonical_turn_id"] = _canonical_turn_id(session.session_id, int(tn or 0))
    return summary


def _langfuse_level_for_output(output: dict[str, Any]) -> str:
    error = str(output.get("error") or output.get("generation_error") or "").strip()
    if error:
        return "ERROR"
    if output.get("fallback_used") or output.get("quality_class") == "degraded":
        return "WARNING"
    if output.get("parser_error_present"):
        return "WARNING"
    return "DEFAULT"


def _langfuse_status_for_output(name: str, output: dict[str, Any]) -> str:
    if name == "story.graph.path_summary":
        return (
            f"route={output.get('route_model_called')} invoke={output.get('invoke_model_called')} "
            f"fallback={output.get('fallback_model_called')} validation={output.get('validation_called')} "
            f"commit={output.get('commit_called')} quality={output.get('quality_class')}"
        )
    if name == "story.phase.model_route":
        return (
            f"route={output.get('route_id') or 'unknown'} provider={output.get('selected_provider') or 'unknown'} "
            f"model={output.get('selected_model') or 'unknown'} mode={output.get('generation_execution_mode') or 'unknown'}"
        )
    if name == "story.phase.model_invoke":
        return (
            f"called={output.get('called')} attempted={output.get('attempted')} success={output.get('success')} "
            f"adapter={output.get('adapter') or 'unknown'} api_model={output.get('api_model') or 'unknown'} "
            f"error={output.get('error') or 'none'} parser_error={output.get('parser_error') or 'none'}"
        )
    if name == "story.phase.primary_parse":
        err = output.get("parser_error") or "none"
        short_err = (err[:80] + "...") if err != "none" and len(err) > 80 else err
        return (
            f"api_success={output.get('api_success')} "
            f"parser_error_present={output.get('parser_error_present')} "
            f"structured_output={output.get('structured_output_present')} "
            f"parser_error={short_err}"
        )
    if name == "story.phase.model_fallback":
        return (
            f"called={output.get('called')} fallback_used={output.get('fallback_used')} "
            f"fallback_model={output.get('fallback_model') or 'unknown'} error={output.get('generation_error') or 'none'}"
        )
    if name == "story.phase.retrieval":
        return (
            f"called={output.get('called')} status={output.get('status') or 'unknown'} "
            f"route={output.get('retrieval_route') or 'unknown'} hits={output.get('hit_count')} "
            f"profile={output.get('profile') or 'unknown'} context_attached={output.get('context_attached')}"
        )
    if name == "story.phase.validation":
        return (
            f"called={output.get('called')} status={output.get('status') or 'unknown'} "
            f"actor_lane={output.get('actor_lane_validation_status') or 'unknown'} "
            f"intent={output.get('player_input_kind') or 'unknown'} "
            f"sem={output.get('semantic_move_kind') or 'unknown'} "
            f"violation={output.get('npc_narrated_player_action_violation')}"
        )
    if name == "story.phase.commit":
        return (
            f"called={output.get('called')} commit_applied={output.get('commit_applied')} "
            f"quality={output.get('quality_class') or 'unknown'} degradation={output.get('degradation_summary') or 'none'} "
            f"selection={output.get('scene_director_selection_source') or 'unknown'}"
        )
    if name == "story.phase.intent_interpretation":
        return (
            f"kind={output.get('player_input_kind') or 'unknown'} "
            f"action={output.get('player_action_committed')} speech={output.get('player_speech_committed')} "
            f"narrator_expected={output.get('narrator_response_expected')} npc_expected={output.get('npc_response_expected')}"
        )
    return name


def _finish_langfuse_span(
    span: Any,
    *,
    output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    level: str = "DEFAULT",
    status_message: str | None = None,
) -> None:
    if span is None:
        return
    try:
        span.update(
            output=output,
            metadata=metadata or {},
            level=level,
            status_message=status_message,
        )
    except Exception:
        logger.debug("Langfuse span update failed", exc_info=True)
    try:
        span.end()
    except Exception:
        logger.debug("Langfuse span end failed", exc_info=True)


def _compute_action_consequence_diagnostics(path_summary: dict[str, Any]) -> dict[str, Any]:
    """Build the public action_consequence_diagnostics payload.

    STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: every player turn must
    expose deterministic numeric values for the action/local-context contract. Opening
    turns and pure-speech turns use ``not_applicable``; degraded/fallback paths use
    ``evaluated_degraded`` but still emit real numeric values.
    """
    turn_number = int(path_summary.get("turn_number") or 0)
    if turn_number == 0:
        return {
            "status": "not_applicable",
            "reason": "opening_turn",
            "local_context_transition_present": 1.0,
            "narrator_consequence_present": 1.0,
            "new_location_established": 1.0,
            "perception_result_present": 1.0,
            "action_consequence_contract_pass": 1.0,
            "npc_consequence_takeover_absent": 1.0,
        }
    intent_kind = str(path_summary.get("player_input_kind") or "").strip().lower()
    action_intents = {"action", "perception", "object_interaction", "physical_action", "movement_action", "perception_action"}
    is_action_resolution = intent_kind in action_intents and bool(
        path_summary.get("authoritative_action_surface") or path_summary.get("player_action_frame_present")
    )
    lct = path_summary.get("local_context_transition") if isinstance(path_summary.get("local_context_transition"), dict) else None
    ncp = path_summary.get("narrator_consequence_plan") if isinstance(path_summary.get("narrator_consequence_plan"), dict) else None
    quality_class = str(path_summary.get("quality_class") or "").strip().lower()
    fallback_used = bool(path_summary.get("generation_fallback_used")) or quality_class in {"degraded", "failed"}
    if intent_kind not in action_intents:
        return {
            "status": "not_applicable",
            "reason": f"intent_kind:{intent_kind or 'unknown'}",
            "local_context_transition_present": 1.0,
            "narrator_consequence_present": 1.0,
            "new_location_established": 1.0,
            "perception_result_present": 1.0,
            "action_consequence_contract_pass": 1.0,
            "npc_consequence_takeover_absent": 1.0,
        }
    local_context_transition_present = 1.0 if lct else 0.0
    narrator_consequence_present = 1.0 if (ncp and ncp.get("consequence_text")) else 0.0
    new_area_established = bool(lct and lct.get("new_area_established")) if lct else False
    movement_turn = bool(lct and str(lct.get("transition_type") or "").startswith("move")) if lct else False
    new_location_established = 1.0 if (new_area_established or not movement_turn) else 0.0
    perception_turn = bool(lct and str(lct.get("transition_type") or "") == "perception") if lct else False
    perception_result_present = 1.0 if (not perception_turn or (ncp and ncp.get("consequence_text"))) else 0.0
    consequence_contract_pass = bool(
        lct
        and ncp
        and (
            ncp.get("consequence_text")
            or ncp.get("consequence_type") not in {None, "generic"}
        )
    )
    action_consequence_contract_pass = 1.0 if consequence_contract_pass else 0.0
    # npc_consequence_takeover_absent: on action/perception turns, if responder set contains a
    # non-narrator actor and the visible bundle includes an NPC line that conveys the perception
    # result instead of the narrator, the score drops to 0. Heuristic: if visible NPC lines exist
    # on a perception or movement turn AND no narrator consequence_text was produced, NPC took over.
    npc_lines = int(path_summary.get("npc_visible_line_count") or 0)
    if npc_lines == 0:
        npc_takeover_absent = 1.0
    else:
        npc_takeover_absent = 0.0 if (movement_turn or perception_turn) and narrator_consequence_present == 0.0 else 1.0
    status = "evaluated"
    if not is_action_resolution:
        status = "evaluated_degraded"
    elif fallback_used:
        status = "evaluated_degraded"

    movement_return_intent = bool(path_summary.get("movement_return_intent"))
    aff_pol = str(path_summary.get("action_commit_policy") or "").strip().lower()
    aff_st = str(path_summary.get("affordance_status") or "").strip().lower()
    if movement_return_intent and aff_pol == "needs_clarification" and aff_st == "ambiguous":
        status = "needs_clarification"
        local_context_transition_present = 0.0
        narrator_consequence_present = 0.0
        new_location_established = 0.0
        action_consequence_contract_pass = 0.0

    tgt_src = path_summary.get("target_resolution_source")
    res_tgt = path_summary.get("resolved_target_id")
    if movement_return_intent and status == "needs_clarification" and not res_tgt:
        tgt_src = tgt_src or "missing_previous_location_id"

    out: dict[str, Any] = {
        "status": status,
        "local_context_transition_present": local_context_transition_present,
        "narrator_consequence_present": narrator_consequence_present,
        "new_location_established": new_location_established,
        "perception_result_present": perception_result_present,
        "action_consequence_contract_pass": action_consequence_contract_pass,
        "npc_consequence_takeover_absent": npc_takeover_absent,
    }
    if movement_return_intent:
        out["movement_return_intent"] = True
    if res_tgt:
        out["resolved_target_id"] = res_tgt
    if tgt_src:
        out["target_resolution_source"] = str(tgt_src)
    if "speech_projection_allowed" in path_summary:
        out["speech_projection_allowed"] = bool(path_summary.get("speech_projection_allowed"))
    return out


def _emit_langfuse_path_spans(path_summary: dict[str, Any]) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for path spans", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    base_input = {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "trace_origin": path_summary.get("trace_origin"),
        "execution_tier": path_summary.get("execution_tier"),
        "environment": path_summary.get("environment"),
        "canonical_player_flow": path_summary.get("canonical_player_flow"),
        "runtime_mode": path_summary.get("runtime_mode"),
        "generation_mode": path_summary.get("generation_mode"),
        "player_input_kind": path_summary.get("player_input_kind"),
        "semantic_move_kind": path_summary.get("semantic_move_kind"),
        "subtext_function": path_summary.get("subtext_function"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
    }

    span_specs = [
        (
            "story.graph.path_summary",
            {
                "canonical_turn_id": path_summary.get("canonical_turn_id"),
                "nodes_executed": path_summary.get("nodes_executed"),
                "route_model_called": path_summary.get("route_model_called"),
                "invoke_model_called": path_summary.get("invoke_model_called"),
                "fallback_model_called": path_summary.get("fallback_model_called"),
                "graph_fallback_node_called": path_summary.get("graph_fallback_node_called"),
                "validation_called": path_summary.get("validation_called"),
                "commit_called": path_summary.get("commit_called"),
                "render_visible_called": path_summary.get("render_visible_called"),
                "retrieval_called": path_summary.get("retrieval_called"),
                "retrieval_status": path_summary.get("retrieval_status"),
                "retrieval_hit_count": path_summary.get("retrieval_hit_count"),
                "quality_class": path_summary.get("quality_class"),
                "degradation_signals": path_summary.get("degradation_signals"),
                "trace_origin": path_summary.get("trace_origin"),
                "execution_tier": path_summary.get("execution_tier"),
                "environment": path_summary.get("environment"),
                "canonical_player_flow": path_summary.get("canonical_player_flow"),
                "runtime_mode": path_summary.get("runtime_mode"),
                "generation_mode": path_summary.get("generation_mode"),
                "turn_aspect_ledger_present": path_summary.get("turn_aspect_ledger_present"),
                "branching_forecast_present": path_summary.get("branching_forecast_present"),
                "branch_option_count": path_summary.get("branch_option_count"),
                "inactive_branches_non_authoritative": path_summary.get(
                    "inactive_branches_non_authoritative"
                ),
                "raw_player_input": path_summary.get("raw_player_input"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
                "subtext_hidden_intent_hypothesis": path_summary.get(
                    "subtext_hidden_intent_hypothesis"
                ),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_sincerity_band": path_summary.get("subtext_sincerity_band"),
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
                "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
                "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
                "subtext_contract_pass": path_summary.get("subtext_contract_pass"),
                "npc_action_narration_boundary_pass": path_summary.get(
                    "npc_action_narration_boundary_pass"
                ),
                "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
                "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
                "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
                "p0_player_action_evidence_applicable": (
                    (path_summary.get("p0_action_resolution_evidence") or {}).get(
                        "p0_player_action_evidence_applicable"
                    )
                ),
                "p0_action_resolution_evidence": path_summary.get("p0_action_resolution_evidence"),
            },
        ),
        (
            "story.phase.intent_interpretation",
            {
                "called": True,
                "player_input_kind": path_summary.get("player_input_kind"),
                "player_action_committed": path_summary.get("player_action_committed"),
                "player_speech_committed": path_summary.get("player_speech_committed"),
                "narrator_response_expected": path_summary.get("narrator_response_expected"),
                "npc_response_expected": path_summary.get("npc_response_expected"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
                "subtext_hidden_intent_hypothesis": path_summary.get(
                    "subtext_hidden_intent_hypothesis"
                ),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
            },
        ),
        (
            "story.phase.model_route",
            {
                "called": path_summary.get("route_model_called"),
                "route_id": path_summary.get("route_id"),
                "route_family": path_summary.get("route_family"),
                "selected_provider": path_summary.get("selected_provider"),
                "selected_model": path_summary.get("selected_model"),
                "fallback_model": path_summary.get("fallback_model"),
                "fallback_chain": path_summary.get("fallback_chain"),
                "registered_adapter_providers": path_summary.get("registered_adapter_providers"),
                "generation_execution_mode": path_summary.get("generation_execution_mode"),
            },
        ),
        (
            "story.phase.model_invoke",
            {
                "called": path_summary.get("invoke_model_called"),
                "attempted": path_summary.get("generation_attempted"),
                "success": path_summary.get("generation_success"),
                "error": path_summary.get("generation_error"),
                "adapter": path_summary.get("adapter"),
                "api_model": path_summary.get("api_model"),
                "adapter_invocation_mode": path_summary.get("adapter_invocation_mode"),
                "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
                "primary_attempt_model": path_summary.get("primary_attempt_model"),
                "primary_attempt_invocation_mode": path_summary.get(
                    "primary_attempt_invocation_mode"
                ),
                "final_adapter": path_summary.get("final_adapter"),
                "final_adapter_invocation_mode": path_summary.get(
                    "final_adapter_invocation_mode"
                ),
                "parser_error": path_summary.get("parser_error"),
                "structured_output_present": path_summary.get("structured_output_present"),
                "structured_output_keys": path_summary.get("structured_output_keys"),
                # PRIMARY-PARSER-EVIDENCE-01
                "primary_attempt_api_success": path_summary.get("primary_attempt_api_success"),
                "primary_attempt_parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
                "primary_attempt_parser_error": path_summary.get("primary_attempt_parser_error"),
                "primary_attempt_structured_output_present": path_summary.get("primary_attempt_structured_output_present"),
                "primary_attempt_raw_output_sha256": path_summary.get("primary_attempt_raw_output_sha256"),
                "primary_attempt_raw_output_excerpt": path_summary.get("primary_attempt_raw_output_excerpt"),
                "self_correction_attempted": path_summary.get("self_correction_attempted"),
                "self_correction_attempt_count": path_summary.get("self_correction_attempt_count"),
                "self_correction_success": path_summary.get("self_correction_success"),
                "self_correction_model": path_summary.get("self_correction_model"),
                "self_correction_trigger_source": path_summary.get("self_correction_trigger_source"),
                "runtime_aspect_failure_before_retry": path_summary.get(
                    "runtime_aspect_failure_before_retry"
                ),
                "capability_failure_before_retry": path_summary.get("capability_failure_before_retry"),
                "self_correction_resolved_failure": path_summary.get(
                    "self_correction_resolved_failure"
                ),
            },
        ),
        (
            "story.phase.primary_parse",
            {
                "called": path_summary.get("invoke_model_called"),
                "api_success": path_summary.get("primary_attempt_api_success"),
                "parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
                "parser_error": path_summary.get("primary_attempt_parser_error"),
                "structured_output_present": path_summary.get("primary_attempt_structured_output_present"),
                "raw_output_sha256": path_summary.get("primary_attempt_raw_output_sha256"),
                "raw_output_excerpt": path_summary.get("primary_attempt_raw_output_excerpt"),
                "adapter": path_summary.get("primary_attempt_adapter"),
                "model": path_summary.get("primary_attempt_model"),
                "invocation_mode": path_summary.get("primary_attempt_invocation_mode"),
            },
        ),
        (
            "story.phase.model_fallback",
            {
                "called": path_summary.get("fallback_model_called"),
                "fallback_used": path_summary.get("generation_fallback_used"),
                "fallback_model": path_summary.get("fallback_model"),
                "fallback_reason": path_summary.get("fallback_reason"),
                "final_adapter": path_summary.get("final_adapter"),
                "final_adapter_invocation_mode": path_summary.get(
                    "final_adapter_invocation_mode"
                ),
                "ldss_fallback_after_live_opening_failure": path_summary.get(
                    "ldss_fallback_after_live_opening_failure"
                ),
                "live_opening_failure_reason": path_summary.get("live_opening_failure_reason"),
                "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
                "primary_attempt_model": path_summary.get("primary_attempt_model"),
                "generation_error": path_summary.get("generation_error"),
                "graph_errors": path_summary.get("graph_errors"),
            },
        ),
        (
            "story.phase.retrieval",
            {
                "called": path_summary.get("retrieval_called"),
                "status": path_summary.get("retrieval_status"),
                "retrieval_route": path_summary.get("retrieval_route"),
                "hit_count": path_summary.get("retrieval_hit_count"),
                "profile": path_summary.get("retrieval_profile"),
                "domain": path_summary.get("retrieval_domain"),
                "context_attached": path_summary.get("retrieval_context_attached"),
                "top_hit_score": path_summary.get("retrieval_top_hit_score"),
                "corpus_fingerprint": path_summary.get("retrieval_corpus_fingerprint"),
                "index_version": path_summary.get("retrieval_index_version"),
                "degradation_mode": path_summary.get("retrieval_degradation_mode"),
                "governance_summary": path_summary.get("retrieval_governance_summary"),
            },
        ),
        (
            "story.phase.validation",
            {
                "called": path_summary.get("validation_called"),
                "status": path_summary.get("validation_status"),
                "reason": path_summary.get("validation_reason"),
                "actor_lane_validation_status": path_summary.get("actor_lane_validation_status"),
                "actor_lane_validation_reason": path_summary.get("actor_lane_validation_reason"),
                "response_present": path_summary.get("response_present"),
                "why_turn_felt_passive": path_summary.get("why_turn_felt_passive"),
                "primary_passivity_factors": path_summary.get("primary_passivity_factors"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "player_action_committed": path_summary.get("player_action_committed"),
                "player_speech_committed": path_summary.get("player_speech_committed"),
                "narrator_response_expected": path_summary.get("narrator_response_expected"),
                "npc_response_expected": path_summary.get("npc_response_expected"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
                "subtext_hidden_intent_hypothesis": path_summary.get(
                    "subtext_hidden_intent_hypothesis"
                ),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_contract_pass": path_summary.get("subtext_contract_pass"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
                "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
                "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
                "npc_action_narration_boundary_pass": path_summary.get(
                    "npc_action_narration_boundary_pass"
                ),
                "npc_narrated_player_action_violation": path_summary.get(
                    "npc_narrated_player_action_violation"
                ),
                "intent_surface_diagnostics": path_summary.get("intent_surface_diagnostics"),
                "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
                "opening_missing_event_ids": path_summary.get("opening_missing_event_ids"),
                "opening_missing_must_establish": path_summary.get("opening_missing_must_establish"),
                "opening_handover_to_scene_phase_expected": path_summary.get(
                    "opening_handover_to_scene_phase_expected"
                ),
                "opening_handover_to_scene_phase_actual": path_summary.get(
                    "opening_handover_to_scene_phase_actual"
                ),
                "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
                "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
                "hard_forbidden_detection": path_summary.get("hard_forbidden_detection"),
            },
        ),
        (
            "story.phase.commit",
            {
                "called": path_summary.get("commit_called"),
                "commit_applied": path_summary.get("commit_applied"),
                "quality_class": path_summary.get("quality_class"),
                "degradation_summary": path_summary.get("degradation_summary"),
                "failure_markers": path_summary.get("failure_markers"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "npc_narrated_player_action_violation": path_summary.get(
                    "npc_narrated_player_action_violation"
                ),
            },
        ),
        (
            "story.branch.forecast",
            {
                "called": bool(path_summary.get("branching_forecast")),
                "status": path_summary.get("branching_forecast_status"),
                "forecast_present": path_summary.get("branching_forecast_present"),
                "option_count": path_summary.get("branch_option_count"),
                "forecast_only": path_summary.get("branching_forecast_only"),
                "inactive_branches_non_authoritative": path_summary.get(
                    "inactive_branches_non_authoritative"
                ),
                "inactive_branches_mutate_state": path_summary.get("inactive_branches_mutate_state"),
                "forecast": path_summary.get("branching_forecast"),
            },
        ),
    ]

    for name, output in span_specs:
        level = _langfuse_level_for_output(output)
        status_message = _langfuse_status_for_output(name, output)
        try:
            span = adapter.create_child_span(
                name=name,
                input=base_input,
                output=output,
                metadata={
                    "phase": name.rsplit(".", 1)[-1],
                    "turn_number": path_summary.get("turn_number"),
                    "session_id": path_summary.get("session_id"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "called": bool(output.get("called", True)),
                    "quality_class": path_summary.get("quality_class"),
                    "degradation_summary": path_summary.get("degradation_summary"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                },
                level=level,
                status_message=status_message,
            )
        except Exception:
            logger.debug("Langfuse child span creation failed for %s", name, exc_info=True)
            continue
        _finish_langfuse_span(
            span,
            output=output,
            level=level,
            status_message=status_message,
        )


def _runtime_aspect_score_value(value: bool) -> float:
    return 1.0 if value else 0.0


def _runtime_aspect_score_metadata(
    *,
    ledger: dict[str, Any],
    aspect_name: str,
    score_name: str,
    value: float,
    path_summary: dict[str, Any],
) -> dict[str, Any]:
    meta = aspect_score_metadata(
        ledger=ledger,
        aspect_name=aspect_name,
        score_name=score_name,
    )
    meta.update(
        {
            "aspect_score": True,
            "score_value": value,
            "session_id": meta.get("session_id") or path_summary.get("session_id"),
            "turn_number": meta.get("turn_number") or path_summary.get("turn_number"),
            "canonical_turn_id": path_summary.get("canonical_turn_id")
            or (
                _canonical_turn_id(
                    str(path_summary.get("session_id") or ledger.get("session_id") or ""),
                    int(path_summary.get("turn_number") or ledger.get("turn_number") or 0),
                )
                if (path_summary.get("session_id") or ledger.get("session_id"))
                else None
            ),
            "raw_player_input": path_summary.get("raw_player_input"),
            "turn_kind": path_summary.get("turn_kind"),
            "module_id": path_summary.get("module_id") or ledger.get("module_id"),
            "runtime_profile_id": path_summary.get("runtime_profile_id") or ledger.get("runtime_profile_id"),
            "environment": path_summary.get("environment"),
        }
    )
    if value < 1.0 and not meta.get("failure_reason"):
        meta["failure_reason"] = "aspect_score_failed"
    return meta


def _emit_langfuse_runtime_aspect_observability(path_summary: dict[str, Any]) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for runtime aspect observability", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    ledger_src = path_summary.get("turn_aspect_ledger")
    ledger_present = bool(
        isinstance(ledger_src, dict)
        and isinstance(ledger_src.get("turn_aspect_ledger"), dict)
    )
    ledger = normalize_runtime_aspect_ledger(ledger_src if isinstance(ledger_src, dict) else {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "turn_aspect_ledger": {},
    })
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}

    def _rec(aspect: str) -> dict[str, Any]:
        row = aspects.get(aspect)
        return row if isinstance(row, dict) else {}

    def _expected(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("expected")
        return row if isinstance(row, dict) else {}

    def _selected(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("selected")
        return row if isinstance(row, dict) else {}

    def _actual(aspect: str) -> dict[str, Any]:
        row = _rec(aspect).get("actual")
        return row if isinstance(row, dict) else {}

    def _known(aspect: str) -> bool:
        return str(_rec(aspect).get("status") or "").strip() not in {"", "missing"}

    def _span_level(record: dict[str, Any]) -> str:
        status = str(record.get("status") or "").strip()
        if status == "failed":
            return "ERROR"
        if status in {"partial", "missing"}:
            return "WARNING"
        return "DEFAULT"

    def _span_status(aspect: str, record: dict[str, Any]) -> str:
        reason = str(record.get("failure_reason") or "").strip() or "none"
        return f"aspect={aspect} status={record.get('status') or 'missing'} reason={reason}"

    base_input = {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "runtime_profile_id": ledger.get("runtime_profile_id") or path_summary.get("runtime_profile_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "raw_player_input": path_summary.get("raw_player_input"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
        "environment": path_summary.get("environment"),
    }
    beat = _rec(ASPECT_BEAT)
    beat_selected = _selected(ASPECT_BEAT)
    beat_actual = _actual(ASPECT_BEAT)
    scene_energy_selected = _selected(ASPECT_SCENE_ENERGY)
    scene_energy_actual = _actual(ASPECT_SCENE_ENERGY)
    pacing_rhythm_selected = _selected(ASPECT_PACING_RHYTHM)
    pacing_rhythm_actual = _actual(ASPECT_PACING_RHYTHM)
    cap_selected = _selected(ASPECT_CAPABILITY_SELECTION)
    disclosure_selected = _selected(ASPECT_INFORMATION_DISCLOSURE)
    disclosure_actual = _actual(ASPECT_INFORMATION_DISCLOSURE)
    dramatic_irony_selected = _selected(ASPECT_DRAMATIC_IRONY)
    dramatic_irony_actual = _actual(ASPECT_DRAMATIC_IRONY)
    narrative_selected = _selected(ASPECT_NARRATIVE_ASPECT)
    narrative_actual = _actual(ASPECT_NARRATIVE_ASPECT)
    memory_selected = _selected(ASPECT_HIERARCHICAL_MEMORY)
    memory_actual = _actual(ASPECT_HIERARCHICAL_MEMORY)
    voice_expected = _expected(ASPECT_VOICE_CONSISTENCY)
    voice_actual = _actual(ASPECT_VOICE_CONSISTENCY)
    span_specs: list[tuple[str, str, dict[str, Any]]] = [
        ("story.aspect.input", ASPECT_INPUT, _rec(ASPECT_INPUT)),
        ("story.action.resolve", ASPECT_ACTION_RESOLUTION, _rec(ASPECT_ACTION_RESOLUTION)),
        (
            "story.affordance.evaluate",
            ASPECT_ACTION_RESOLUTION,
            {
                "affordance_status": _actual(ASPECT_ACTION_RESOLUTION).get("affordance_status"),
                "resolved_target_status": _actual(ASPECT_ACTION_RESOLUTION).get("resolved_target_status"),
                "action_commit_policy": _actual(ASPECT_ACTION_RESOLUTION).get("action_commit_policy"),
                "aspect_record": _rec(ASPECT_ACTION_RESOLUTION),
            },
        ),
        ("story.capability.select", ASPECT_CAPABILITY_SELECTION, _rec(ASPECT_CAPABILITY_SELECTION)),
        (
            "story.capability.realize",
            ASPECT_CAPABILITY_SELECTION,
            {
                "selected": cap_selected,
                "actual": _actual(ASPECT_CAPABILITY_SELECTION),
                "aspect_record": _rec(ASPECT_CAPABILITY_SELECTION),
            },
        ),
        (
            "story.beat.state",
            ASPECT_BEAT,
            {
                "prior_beat_id": _expected(ASPECT_BEAT).get("prior_beat_id"),
                "candidate_beats": _expected(ASPECT_BEAT).get("candidate_beats"),
                "aspect_record": beat,
            },
        ),
        ("story.beat.select", ASPECT_BEAT, {"selected": beat_selected, "aspect_record": beat}),
        ("story.beat.realize", ASPECT_BEAT, {"actual": beat_actual, "aspect_record": beat}),
        (
            "story.scene_energy.target",
            ASPECT_SCENE_ENERGY,
            {
                "selected": scene_energy_selected,
                "aspect_record": _rec(ASPECT_SCENE_ENERGY),
            },
        ),
        (
            "story.scene_energy.validate",
            ASPECT_SCENE_ENERGY,
            {
                "actual": scene_energy_actual,
                "aspect_record": _rec(ASPECT_SCENE_ENERGY),
            },
        ),
        (
            "story.pacing_rhythm.target",
            ASPECT_PACING_RHYTHM,
            {
                "selected": pacing_rhythm_selected,
                "aspect_record": _rec(ASPECT_PACING_RHYTHM),
            },
        ),
        (
            "story.pacing_rhythm.validate",
            ASPECT_PACING_RHYTHM,
            {
                "actual": pacing_rhythm_actual,
                "aspect_record": _rec(ASPECT_PACING_RHYTHM),
            },
        ),
        (
            "story.information_disclosure.select",
            ASPECT_INFORMATION_DISCLOSURE,
            {
                "selected": disclosure_selected,
                "aspect_record": _rec(ASPECT_INFORMATION_DISCLOSURE),
            },
        ),
        (
            "story.information_disclosure.validate",
            ASPECT_INFORMATION_DISCLOSURE,
            {
                "actual": disclosure_actual,
                "aspect_record": _rec(ASPECT_INFORMATION_DISCLOSURE),
            },
        ),
        (
            "story.dramatic_irony.select",
            ASPECT_DRAMATIC_IRONY,
            {
                "selected": dramatic_irony_selected,
                "aspect_record": _rec(ASPECT_DRAMATIC_IRONY),
            },
        ),
        (
            "story.dramatic_irony.validate",
            ASPECT_DRAMATIC_IRONY,
            {
                "actual": dramatic_irony_actual,
                "aspect_record": _rec(ASPECT_DRAMATIC_IRONY),
            },
        ),
        ("story.authority.narrator", ASPECT_NARRATOR_AUTHORITY, _rec(ASPECT_NARRATOR_AUTHORITY)),
        ("story.authority.npc", ASPECT_NPC_AUTHORITY, _rec(ASPECT_NPC_AUTHORITY)),
        (
            "story.npc_agency.plan",
            ASPECT_NPC_AGENCY,
            {
                "expected": _expected(ASPECT_NPC_AGENCY),
                "selected": _selected(ASPECT_NPC_AGENCY),
                "aspect_record": _rec(ASPECT_NPC_AGENCY),
            },
        ),
        (
            "story.npc_agency.realize",
            ASPECT_NPC_AGENCY,
            {
                "actual": _actual(ASPECT_NPC_AGENCY),
                "aspect_record": _rec(ASPECT_NPC_AGENCY),
            },
        ),
        (
            "story.narrative_aspect.select",
            ASPECT_NARRATIVE_ASPECT,
            {"selected": narrative_selected, "aspect_record": _rec(ASPECT_NARRATIVE_ASPECT)},
        ),
        (
            "story.narrative_aspect.validate",
            ASPECT_NARRATIVE_ASPECT,
            {"actual": narrative_actual, "aspect_record": _rec(ASPECT_NARRATIVE_ASPECT)},
        ),
        (
            "story.voice.classify",
            ASPECT_VOICE_CONSISTENCY,
            {
                "expected": voice_expected,
                "actual": voice_actual,
                "aspect_record": _rec(ASPECT_VOICE_CONSISTENCY),
            },
        ),
        (
            "story.voice.validate",
            ASPECT_VOICE_CONSISTENCY,
            {
                "findings": voice_actual.get("findings") or [],
                "semantic_classifications": voice_actual.get("semantic_classifications") or [],
                "aspect_record": _rec(ASPECT_VOICE_CONSISTENCY),
            },
        ),
        (
            "story.memory.write",
            ASPECT_HIERARCHICAL_MEMORY,
            {"selected": memory_selected, "actual": memory_actual, "aspect_record": _rec(ASPECT_HIERARCHICAL_MEMORY)},
        ),
        (
            "story.memory.project",
            ASPECT_HIERARCHICAL_MEMORY,
            {"actual": memory_actual, "aspect_record": _rec(ASPECT_HIERARCHICAL_MEMORY)},
        ),
        ("story.validation.contract", ASPECT_VALIDATION, _rec(ASPECT_VALIDATION)),
        ("story.commit.apply", ASPECT_COMMIT, _rec(ASPECT_COMMIT)),
        ("story.visible.project", ASPECT_VISIBLE_PROJECTION, _rec(ASPECT_VISIBLE_PROJECTION)),
        (
            "story.turn.aspect_summary",
            ASPECT_INPUT,
            {
                "turn_aspect_ledger_present": ledger_present,
                "canonical_turn_id": path_summary.get("canonical_turn_id"),
                "aspect_statuses": {
                    aspect_name: (_rec(aspect_name).get("status") or "missing")
                    for aspect_name in (
                        ASPECT_INPUT,
                        ASPECT_ACTION_RESOLUTION,
                        ASPECT_BEAT,
                        ASPECT_SCENE_ENERGY,
                        ASPECT_PACING_RHYTHM,
                        ASPECT_INFORMATION_DISCLOSURE,
                        ASPECT_CAPABILITY_SELECTION,
                        ASPECT_NARRATOR_AUTHORITY,
                        ASPECT_NPC_AUTHORITY,
                        ASPECT_NPC_AGENCY,
                        ASPECT_NARRATIVE_ASPECT,
                        ASPECT_VOICE_CONSISTENCY,
                        ASPECT_HIERARCHICAL_MEMORY,
                        ASPECT_VALIDATION,
                        ASPECT_COMMIT,
                        ASPECT_VISIBLE_PROJECTION,
                    )
                },
            },
        ),
    ]
    for name, aspect, output in span_specs:
        record = _rec(aspect)
        level = _span_level(record)
        status_message = _span_status(aspect, record)
        try:
            span = adapter.create_child_span(
                name=name,
                input=base_input,
                output=output,
                metadata={
                    "phase": "runtime_aspect",
                    "runtime_aspect": aspect,
                    "module_id": path_summary.get("module_id"),
                    "runtime_profile_id": ledger.get("runtime_profile_id") or path_summary.get("runtime_profile_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "session_id": path_summary.get("session_id"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "selected_beat_id": beat_selected.get("selected_beat_id"),
                    "selected_capabilities": cap_selected.get("selected_capabilities") or [],
                    "authority_policy": _expected(ASPECT_NPC_AUTHORITY).get("policy"),
                    "status": record.get("status"),
                    "failure_reason": record.get("failure_reason"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                },
                level=level,
                status_message=status_message,
            )
        except Exception:
            logger.debug("Langfuse runtime aspect span creation failed for %s", name, exc_info=True)
            continue
        _finish_langfuse_span(span, output=output, level=level, status_message=status_message)

    input_actual = _actual(ASPECT_INPUT)
    action_actual = _actual(ASPECT_ACTION_RESOLUTION)
    narrator_expected = _expected(ASPECT_NARRATOR_AUTHORITY)
    narrator_actual = _actual(ASPECT_NARRATOR_AUTHORITY)
    npc_actual = _actual(ASPECT_NPC_AUTHORITY)
    npc_agency_actual = _actual(ASPECT_NPC_AGENCY)
    dramatic_irony_expected = _expected(ASPECT_DRAMATIC_IRONY)
    dramatic_irony_actual = _actual(ASPECT_DRAMATIC_IRONY)
    cap_actual = _actual(ASPECT_CAPABILITY_SELECTION)
    visible_actual = _actual(ASPECT_VISIBLE_PROJECTION)
    narrative_expected = _expected(ASPECT_NARRATIVE_ASPECT)
    memory_expected = _expected(ASPECT_HIERARCHICAL_MEMORY)
    voice_expected = _expected(ASPECT_VOICE_CONSISTENCY)
    voice_actual = _actual(ASPECT_VOICE_CONSISTENCY)
    validation_actual = _actual(ASPECT_VALIDATION)
    beat_transition_allowed = _selected(ASPECT_BEAT).get("transition_allowed")
    scene_energy_target = (
        scene_energy_selected.get("target")
        if isinstance(scene_energy_selected.get("target"), dict)
        else scene_energy_selected
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
    disclosure_failure_codes = disclosure_actual.get("failure_codes") or []
    if not isinstance(disclosure_failure_codes, list):
        disclosure_failure_codes = []
    dramatic_irony_violation_codes = dramatic_irony_actual.get("violation_codes") or []
    if not isinstance(dramatic_irony_violation_codes, list):
        dramatic_irony_violation_codes = []
    npc_failure_reason = str(_rec(ASPECT_NPC_AUTHORITY).get("failure_reason") or "")
    violated_capabilities = cap_actual.get("violated_capabilities") or []
    if not isinstance(violated_capabilities, list):
        violated_capabilities = []
    turn_number = int(path_summary.get("turn_number") or ledger.get("turn_number") or 0)
    input_kind = str(
        action_actual.get("input_kind")
        or input_actual.get("player_input_kind")
        or input_actual.get("input_kind")
        or ""
    ).strip().lower()
    action_requires_narrator = turn_number > 0 and input_kind in {
        "action",
        "perception",
        "mixed",
        "movement_action",
        "perception_action",
    }
    narrator_required = bool(narrator_expected.get("required"))
    missing_required_capabilities = cap_actual.get("missing_required_capabilities") or []
    if not isinstance(missing_required_capabilities, list):
        missing_required_capabilities = []
    selected_theme_aspects = narrative_actual.get("selected_theme_aspects") or []
    if not isinstance(selected_theme_aspects, list):
        selected_theme_aspects = []
    narrative_semantic_classification_count = int(
        narrative_actual.get("semantic_classification_count") or 0
    )
    narrative_semantic_required_weak_alignment_count = int(
        narrative_actual.get("semantic_required_weak_alignment_count") or 0
    )
    voice_spoken_line_count = int(voice_actual.get("spoken_line_count") or 0)
    voice_semantic_classification_count = int(
        voice_actual.get("semantic_classification_count") or 0
    )
    voice_drift_counts = (
        voice_actual.get("drift_class_counts")
        if isinstance(voice_actual.get("drift_class_counts"), dict)
        else {}
    )
    voice_forbidden_marker_count = int(
        voice_drift_counts.get("forbidden_language_marker") or 0
    )
    voice_cross_actor_count = int(
        voice_actual.get("semantic_cross_actor_confusion_count")
        or voice_drift_counts.get("cross_actor_voice_confusion")
        or 0
    )
    recoverable_turn = bool(validation_actual.get("recoverable_rejection")) or str(
        path_summary.get("turn_status") or ""
    ).strip().lower() in {"rejected_recoverable", "player_rejected_recoverable"}
    http_status = int(path_summary.get("http_status") or 200)
    visible_output_for_recovery = bool(
        visible_actual.get("visible_output_present")
        or visible_actual.get("visible_block_origin_present")
        or int(visible_actual.get("scene_block_count") or 0) > 0
    )
    scores: list[tuple[str, str, float]] = [
        ("turn_aspect_ledger_present", ASPECT_INPUT, _runtime_aspect_score_value(ledger_present)),
        (
            "beat_selected",
            ASPECT_BEAT,
            _runtime_aspect_score_value(bool(beat_selected.get("selected_beat_id") or beat_selected.get("selected_scene_function"))),
        ),
        ("beat_realized", ASPECT_BEAT, _runtime_aspect_score_value(beat_actual.get("realized") is True)),
        (
            "beat_realization_visible",
            ASPECT_BEAT,
            _runtime_aspect_score_value(beat_actual.get("realized") is True and beat_actual.get("visible") is True),
        ),
        (
            "beat_transition_valid",
            ASPECT_BEAT,
            _runtime_aspect_score_value(beat_transition_allowed is not False),
        ),
        (
            "beat_contract_pass",
            ASPECT_BEAT,
            _runtime_aspect_score_value(_rec(ASPECT_BEAT).get("status") == "passed"),
        ),
        (
            "scene_energy_target_present",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(bool(scene_energy_target)),
        ),
        (
            "scene_energy_contract_pass",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(
                _rec(ASPECT_SCENE_ENERGY).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "scene_energy_transition_allowed",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(scene_energy_actual.get("transition_allowed") is not False),
        ),
        (
            "scene_energy_pressure_realized",
            ASPECT_SCENE_ENERGY,
            _runtime_aspect_score_value(
                "scene_energy_missing_required_pressure" not in scene_energy_failure_codes
            ),
        ),
        (
            "pacing_rhythm_target_present",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(bool(pacing_rhythm_target)),
        ),
        (
            "pacing_rhythm_contract_pass",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                _rec(ASPECT_PACING_RHYTHM).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "pacing_rhythm_density_respected",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                "pacing_rhythm_visible_density_exceeded" not in pacing_rhythm_failure_codes
            ),
        ),
        (
            "pacing_rhythm_pause_respected",
            ASPECT_PACING_RHYTHM,
            _runtime_aspect_score_value(
                "pacing_rhythm_pause_obligation_lost" not in pacing_rhythm_failure_codes
                and "pacing_rhythm_forced_speech_violation" not in pacing_rhythm_failure_codes
            ),
        ),
        (
            "information_disclosure_policy_present",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                bool(_expected(ASPECT_INFORMATION_DISCLOSURE).get("policy_present"))
            ),
        ),
        (
            "information_disclosure_target_selected",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(bool(disclosure_selected.get("selected_unit_ids"))),
        ),
        (
            "information_disclosure_budget_pass",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                "information_disclosure_over_budget" not in disclosure_failure_codes
            ),
        ),
        (
            "information_disclosure_premature_reveal_absent",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                "information_disclosure_forbidden_unit" not in disclosure_failure_codes
            ),
        ),
        (
            "information_disclosure_contract_pass",
            ASPECT_INFORMATION_DISCLOSURE,
            _runtime_aspect_score_value(
                _rec(ASPECT_INFORMATION_DISCLOSURE).get("status")
                in {"passed", "not_applicable"}
                and disclosure_actual.get("contract_pass") is not False
                and not disclosure_failure_codes
            ),
        ),
        (
            "dramatic_irony_policy_present",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(bool(dramatic_irony_expected.get("policy_present"))),
        ),
        (
            "dramatic_irony_opportunity_present",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(bool(dramatic_irony_actual.get("opportunity_count"))),
        ),
        (
            "dramatic_irony_contract_pass",
            ASPECT_DRAMATIC_IRONY,
            _runtime_aspect_score_value(
                _rec(ASPECT_DRAMATIC_IRONY).get("status")
                in {"passed", "not_applicable"}
                and dramatic_irony_actual.get("contract_pass") is not False
                and not dramatic_irony_violation_codes
            ),
        ),
        (
            "narrator_authority_contract_present",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(_known(ASPECT_NARRATOR_AUTHORITY)),
        ),
        (
            "narrator_required_when_expected",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value((not action_requires_narrator) or narrator_required),
        ),
        (
            "narrator_owns_consequence",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(
                (not narrator_required)
                or (
                    _rec(ASPECT_NARRATOR_AUTHORITY).get("status") == "passed"
                    and narrator_actual.get("actual_owner") == "narrator"
                    and narrator_actual.get("consequence_realized") is True
                )
            ),
        ),
        (
            "narrator_consequence_present",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value((not narrator_required) or narrator_actual.get("consequence_realized") is True),
        ),
        (
            "narrator_authority_contract_pass",
            ASPECT_NARRATOR_AUTHORITY,
            _runtime_aspect_score_value(_rec(ASPECT_NARRATOR_AUTHORITY).get("status") == "passed"),
        ),
        (
            "npc_authority_contract_present",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(_known(ASPECT_NPC_AUTHORITY)),
        ),
        (
            "npc_takeover_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(not bool(npc_actual.get("npc_takeover_detected"))),
        ),
        (
            "npc_policy_realized",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(_rec(ASPECT_NPC_AUTHORITY).get("status") == "passed"),
        ),
        (
            "npc_agency_plan_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(_known(ASPECT_NPC_AGENCY)),
        ),
        (
            "npc_independent_planning_used",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("independent_planning_used"))),
        ),
        (
            "npc_long_horizon_state_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("long_horizon_state_present"))),
        ),
        (
            "npc_private_plan_resolution_present",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("private_plan_resolution_present"))),
        ),
        (
            "npc_private_plan_visibility_respected",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                npc_agency_actual.get("private_plan_visibility_respected") is not False
                and not bool(npc_agency_actual.get("unrealized_selected_private_plan_actor_ids"))
            ),
        ),
        (
            "npc_intention_threads_carried_forward",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                int(npc_agency_actual.get("intention_threads_carried_forward") or 0) > 0
                or int(npc_agency_actual.get("intention_threads_active") or 0)
                > len(npc_agency_actual.get("candidate_actor_ids") or [])
            ),
        ),
        (
            "npc_required_initiatives_realized",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(not bool(npc_agency_actual.get("missing_required_actor_ids"))),
        ),
        (
            "multi_npc_initiative_realized",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(bool(npc_agency_actual.get("multi_npc_initiative_realized"))),
        ),
        (
            "npc_carry_forward_closed",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                not bool(npc_agency_actual.get("carry_forward_actor_ids"))
                and not bool(npc_agency_actual.get("missing_required_actor_ids"))
            ),
        ),
        (
            "npc_forbidden_actor_absent",
            ASPECT_NPC_AGENCY,
            _runtime_aspect_score_value(
                not bool(npc_agency_actual.get("forbidden_planned_actor_ids"))
                and not bool(npc_agency_actual.get("forbidden_realized_actor_ids"))
            ),
        ),
        (
            "npc_consequence_takeover_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(not bool(npc_actual.get("npc_takeover_detected"))),
        ),
        (
            "npc_exposition_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value("narrated_player_perception" not in npc_failure_reason and "explained_environment" not in npc_failure_reason),
        ),
        (
            "player_agency_violation_absent",
            ASPECT_NPC_AUTHORITY,
            _runtime_aspect_score_value(
                "ai_controlled_human_actor" not in npc_failure_reason
                and "npc.force_player_speech.forbidden" not in violated_capabilities
            ),
        ),
        (
            "capability_selection_present",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_known(ASPECT_CAPABILITY_SELECTION)),
        ),
        (
            "capability_selection_valid",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_rec(ASPECT_CAPABILITY_SELECTION).get("status") != "failed"),
        ),
        (
            "forbidden_capability_absent",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(not bool(cap_actual.get("forbidden_capability_realized"))),
        ),
        (
            "selected_capabilities_realized",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(not missing_required_capabilities),
        ),
        (
            "dramatic_capability_contract_pass",
            ASPECT_CAPABILITY_SELECTION,
            _runtime_aspect_score_value(_rec(ASPECT_CAPABILITY_SELECTION).get("status") == "passed"),
        ),
        (
            "visible_block_origin_present",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(bool(visible_actual.get("visible_block_origin_present"))),
        ),
        (
            "required_visible_origin_preserved",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(bool(visible_actual.get("required_visible_origin_preserved"))),
        ),
        (
            "visible_projection_contract_pass",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value(_rec(ASPECT_VISIBLE_PROJECTION).get("status") == "passed"),
        ),
        (
            "narrative_aspect_policy_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_expected.get("policy_present"))),
        ),
        (
            "narrative_aspect_selected",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_selected.get("selected_aspects"))),
        ),
        (
            "narrative_aspect_visible_when_required",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(narrative_actual.get("visible_when_required") is not False),
        ),
        (
            "narrative_aspect_contract_pass",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(_rec(ASPECT_NARRATIVE_ASPECT).get("status") in {"passed", "not_applicable"}),
        ),
        (
            "theme_tracking_policy_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(narrative_expected.get("theme_tracking_policy_present"))),
        ),
        (
            "theme_tracking_selected",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(bool(selected_theme_aspects)),
        ),
        (
            "theme_semantic_classification_present",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(
                (
                    not bool(narrative_expected.get("semantic_tracking_enabled"))
                    or not selected_theme_aspects
                    or narrative_semantic_classification_count >= len(selected_theme_aspects)
                )
            ),
        ),
        (
            "theme_weak_alignment_absent",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(narrative_semantic_required_weak_alignment_count == 0),
        ),
        (
            "theme_tracking_contract_pass",
            ASPECT_NARRATIVE_ASPECT,
            _runtime_aspect_score_value(
                _rec(ASPECT_NARRATIVE_ASPECT).get("status") in {"passed", "not_applicable"}
                and narrative_semantic_required_weak_alignment_count == 0
            ),
        ),
        (
            "voice_consistency_policy_present",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(bool(voice_expected.get("policy_present"))),
        ),
        (
            "voice_semantic_classification_present",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(
                (
                    not bool(voice_expected.get("semantic_classification_enabled"))
                    or voice_spoken_line_count <= 0
                    or voice_semantic_classification_count >= voice_spoken_line_count
                )
            ),
        ),
        (
            "voice_cross_actor_confusion_absent",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(voice_cross_actor_count == 0),
        ),
        (
            "voice_forbidden_markers_absent",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(voice_forbidden_marker_count == 0),
        ),
        (
            "voice_consistency_contract_pass",
            ASPECT_VOICE_CONSISTENCY,
            _runtime_aspect_score_value(
                _rec(ASPECT_VOICE_CONSISTENCY).get("status")
                in {"passed", "not_applicable"}
            ),
        ),
        (
            "hierarchical_memory_present",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(bool(memory_actual.get("memory_present"))),
        ),
        (
            "memory_policy_applied",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(
                (not bool(memory_expected.get("policy_present")))
                or _rec(ASPECT_HIERARCHICAL_MEMORY).get("status") in {"passed", "not_applicable"}
            ),
        ),
        (
            "memory_write_from_committed_turn",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(not bool(memory_actual.get("uncommitted_write_detected"))),
        ),
        (
            "memory_context_bounded",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(bool(memory_actual.get("context_bounded")) or not bool(memory_expected.get("policy_present"))),
        ),
        (
            "hierarchical_memory_contract_pass",
            ASPECT_HIERARCHICAL_MEMORY,
            _runtime_aspect_score_value(_rec(ASPECT_HIERARCHICAL_MEMORY).get("status") in {"passed", "not_applicable"}),
        ),
        (
            "recoverable_turn_http_200",
            ASPECT_VALIDATION,
            _runtime_aspect_score_value((not recoverable_turn) or http_status == 200),
        ),
        (
            "recoverable_turn_visible_output_present",
            ASPECT_VISIBLE_PROJECTION,
            _runtime_aspect_score_value((not recoverable_turn) or visible_output_for_recovery),
        ),
    ]
    for score_name, aspect_name, score_value in scores:
        try:
            adapter.add_score(
                name=score_name,
                value=score_value,
                comment="deterministic runtime aspect evidence",
                metadata=_runtime_aspect_score_metadata(
                    ledger=ledger,
                    aspect_name=aspect_name,
                    score_name=score_name,
                    value=score_value,
                    path_summary=path_summary,
                ),
            )
        except Exception:
            logger.debug("Langfuse runtime aspect score write failed for %s", score_name, exc_info=True)
    branching_forecast = (
        path_summary.get("branching_forecast")
        if isinstance(path_summary.get("branching_forecast"), dict)
        else {}
    )
    if branching_forecast:
        branch_status = str(branching_forecast.get("status") or "").strip()
        branch_option_count = int(branching_forecast.get("option_count") or 0)
        branch_meta = {
            "branching_forecast_score": True,
            "aspect_name": "branching_forecast",
            "session_id": path_summary.get("session_id"),
            "module_id": path_summary.get("module_id"),
            "runtime_profile_id": path_summary.get("runtime_profile_id"),
            "turn_number": path_summary.get("turn_number"),
            "turn_kind": path_summary.get("turn_kind"),
            "canonical_turn_id": path_summary.get("canonical_turn_id"),
            "status": branch_status,
            "forecast_only": bool(branching_forecast.get("forecast_only")),
            "authoritative": bool(branching_forecast.get("authoritative")),
            "inactive_branches_authoritative": bool(
                branching_forecast.get("inactive_branches_authoritative")
            ),
            "mutates_canonical_state": bool(branching_forecast.get("mutates_canonical_state")),
            "trigger_reasons": list(branching_forecast.get("trigger_reasons") or []),
            "option_count": branch_option_count,
            "environment": path_summary.get("environment"),
        }
        branch_scores = [
            ("branching_forecast_present", _runtime_aspect_score_value(bool(branching_forecast))),
            ("branch_options_count", float(branch_option_count)),
            (
                "inactive_branches_non_authoritative",
                _runtime_aspect_score_value(
                    branching_forecast.get("forecast_only") is True
                    and branching_forecast.get("authoritative") is False
                    and branching_forecast.get("inactive_branches_authoritative") is False
                    and branching_forecast.get("mutates_canonical_state") is False
                ),
            ),
        ]
        for score_name, score_value in branch_scores:
            try:
                adapter.add_score(
                    name=score_name,
                    value=score_value,
                    comment="deterministic branching forecast evidence",
                    metadata={**branch_meta, "score_name": score_name, "score_value": score_value},
                )
            except Exception:
                logger.debug("Langfuse branching forecast score write failed for %s", score_name, exc_info=True)


def _build_canonical_degradation_signals(path_summary: dict[str, Any]) -> list[str]:
    """Filter ``path_summary['degradation_signals']`` to canonical values only.

    The canonical contract (``DEGRADATION_SIGNAL_VALUES``) is consumed by
    diagnostics / operator-history aggregation. Score metadata uses this filtered
    view so that the canonical surface stays stable regardless of what
    ``_ldss_opening_fallback_state`` or visibility-marker pipelines append.
    """
    raw = path_summary.get("degradation_signals") or []
    if not isinstance(raw, list):
        return []
    canonical: list[str] = []
    for entry in raw:
        token = str(entry).strip()
        if token and token in DEGRADATION_SIGNAL_VALUES and token not in canonical:
            canonical.append(token)
    return canonical


def _build_degradation_chain(path_summary: dict[str, Any]) -> list[str]:
    """Build the operator-facing causation chain for score metadata.

    Order convention (cause -> action -> consequence):
    1. ``live_opening_failure_reason`` (root cause, e.g. ``dramatic_effect_reject_empty_fluency``)
    2. Whatever ``path_summary['degradation_signals']`` exposes, in original order
       (this typically holds the runtime decision marker
       ``ldss_fallback_after_live_opening_failure`` followed by the visibility
       consequence ``non_factual_staging``).

    Duplicates are collapsed; empty / non-string entries are dropped.
    """
    chain: list[str] = []
    live_reason = path_summary.get("live_opening_failure_reason")
    if isinstance(live_reason, str):
        token = live_reason.strip()
        if token:
            chain.append(token)
    raw_signals = path_summary.get("degradation_signals") or []
    if isinstance(raw_signals, list):
        for entry in raw_signals:
            token = str(entry).strip()
            if token and token not in chain:
                chain.append(token)
    return chain


def _build_degradation_prose_summary(path_summary: dict[str, Any]) -> str:
    """Compose a human-readable summary describing the operational degradation.

    The prose is operator-facing (alert / dashboard surface). It does not feed
    the live-gate booleans or any canonical contract; ``path_summary['degradation_summary']``
    keeps its existing raw-token semantics for the root span statusMessage.
    """
    live_reason = ""
    raw_reason = path_summary.get("live_opening_failure_reason")
    if isinstance(raw_reason, str):
        live_reason = raw_reason.strip()
    raw_signals = path_summary.get("degradation_signals") or []
    raw_signals = [str(s).strip() for s in raw_signals if str(s).strip()] if isinstance(raw_signals, list) else []
    if not live_reason and not raw_signals:
        return "none"

    has_ldss_fallback = "ldss_fallback_after_live_opening_failure" in raw_signals
    has_non_factual = "non_factual_staging" in raw_signals
    has_fallback_used = "fallback_used" in raw_signals

    parts: list[str] = []
    if "dramatic_effect_reject" in live_reason:
        parts.append("Live opening failed dramatic-effect validation")
    elif "actor_lane" in live_reason:
        parts.append(f"Live opening failed actor-lane validation ({live_reason})")
    elif live_reason:
        parts.append(f"Live opening failed validation ({live_reason})")

    if has_ldss_fallback:
        parts.append("and fell back to LDSS" if parts else "Live opening fell back to LDSS")
    elif has_fallback_used and not parts:
        parts.append("Operational degradation (fallback used)")

    if not parts:
        parts.append("Operational degradation observed")

    base = " ".join(parts)
    if has_ldss_fallback or has_non_factual:
        return f"{base}; visible output exists but is degraded/fallback."
    if raw_signals:
        return f"{base}; canonical signals: {', '.join(raw_signals)}."
    return f"{base}."


def _emit_langfuse_evidence_observations(
    *,
    path_summary: dict[str, Any],
    graph_state: dict[str, Any],
    event: dict[str, Any],
) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for evidence observations", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    generation = (
        (event.get("model_route") or {}).get("generation")
        if isinstance(event.get("model_route"), dict)
        else {}
    )
    if not isinstance(generation, dict):
        generation = {}
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    adapter_name = str(gen_meta.get("adapter") or "").strip()
    usage_details = path_summary.get("usage_details") if isinstance(path_summary.get("usage_details"), dict) else {}
    _ud_in = int(usage_details.get("input") or 0)
    _ud_out = int(usage_details.get("output") or 0)
    _ud_tot = int(usage_details.get("total") or 0)
    if _ud_tot <= 0 and (_ud_in > 0 or _ud_out > 0):
        _ud_tot = _ud_in + _ud_out
    usage_for_lf = (
        {"input": _ud_in, "output": _ud_out, "total": _ud_tot} if (_ud_in or _ud_out or _ud_tot) else None
    )
    model_name = str(path_summary.get("api_model") or path_summary.get("selected_model") or gen_meta.get("model") or "unknown").strip()
    provider = str(path_summary.get("selected_provider") or adapter_name or "unknown").strip()
    _lat_ev = path_summary.get("generation_latency_ms")
    _lat_ev_f = float(_lat_ev) if isinstance(_lat_ev, (int, float)) else None
    _tps_ev = path_summary.get("tokens_per_second_output")
    _tps_ev_f = float(_tps_ev) if isinstance(_tps_ev, (int, float)) else None
    _ttft_ev = path_summary.get("time_to_first_token_ms")
    _ttft_ev_f = float(_ttft_ev) if isinstance(_ttft_ev, (int, float)) else None
    _provided = str(path_summary.get("provided_model_name") or gen_meta.get("model") or model_name).strip()
    _prompt_name_ev = path_summary.get("langfuse_prompt_name")
    if adapter_name and adapter_name not in {"mock", "ldss_fallback", "ldss_deterministic"}:
        try:
            adapter.record_generation(
                name="story.model.generation",
                model=model_name,
                provider=provider,
                prompt=str(graph_state.get("model_prompt") or "")[:20000],
                completion=str(generation.get("model_raw_text") or generation.get("content") or "")[:20000],
                usage_details=usage_for_lf,
                provided_model_name=_provided or None,
                prompt_name=str(_prompt_name_ev).strip() if _prompt_name_ev else None,
                latency_ms=_lat_ev_f,
                time_to_first_token_ms=_ttft_ev_f,
                tokens_per_second=_tps_ev_f,
                metadata={
                    "session_id": path_summary.get("session_id"),
                    "module_id": path_summary.get("module_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "opening_turn": int(path_summary.get("turn_number") or 0) == 0,
                    "turn_kind": path_summary.get("turn_kind"),
                    "adapter": adapter_name,
                    "adapter_invocation_mode": path_summary.get("adapter_invocation_mode"),
                    "route_id": path_summary.get("route_id"),
                    "route_family": path_summary.get("route_family"),
                    "selected_model": path_summary.get("selected_model"),
                    "fallback_model": path_summary.get("fallback_model"),
                    "fallback_used": path_summary.get("generation_fallback_used"),
                    "structured_output_present": path_summary.get("structured_output_present"),
                    "parser_error": path_summary.get("parser_error"),
                    "retrieval_context_attached": path_summary.get("retrieval_context_attached"),
                    "usage_available": path_summary.get("usage_available"),
                    "usage_source": path_summary.get("usage_source"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                    "input_tokens": _ud_in,
                    "output_tokens": _ud_out,
                    "total_tokens": _ud_tot,
                    "time_to_first_token_note": path_summary.get("time_to_first_token_note"),
                },
            )
        except Exception:
            logger.debug("Langfuse generation observation failed", exc_info=True)

    retrieval = event.get("retrieval") if isinstance(event.get("retrieval"), dict) else {}
    sources = retrieval.get("sources") if isinstance(retrieval.get("sources"), list) else []
    documents: list[dict[str, Any]] = []
    for source in sources[:8]:
        if not isinstance(source, dict):
            continue
        documents.append(
            {
                "id": source.get("chunk_id") or source.get("source_path"),
                "content": source.get("snippet"),
                "score": source.get("score"),
                "metadata": {
                    "source_path": source.get("source_path"),
                    "content_class": source.get("content_class"),
                    "pack_role": source.get("pack_role"),
                    "source_evidence_lane": source.get("source_evidence_lane"),
                    "policy_note": source.get("policy_note"),
                },
            }
        )
    if retrieval:
        try:
            adapter.record_retrieval(
                name="story.rag.retrieval",
                query=str(retrieval.get("query") or event.get("raw_input") or "")[:4000],
                documents=documents,
                metadata={
                    "session_id": path_summary.get("session_id"),
                    "module_id": path_summary.get("module_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "status": path_summary.get("retrieval_status"),
                    "retrieval_route": path_summary.get("retrieval_route"),
                    "hit_count": path_summary.get("retrieval_hit_count"),
                    "profile": path_summary.get("retrieval_profile"),
                    "domain": path_summary.get("retrieval_domain"),
                    "context_attached": path_summary.get("retrieval_context_attached"),
                    "top_hit_score": path_summary.get("retrieval_top_hit_score"),
                    "corpus_fingerprint": path_summary.get("retrieval_corpus_fingerprint"),
                    "index_version": path_summary.get("retrieval_index_version"),
                    "degradation_mode": path_summary.get("retrieval_degradation_mode"),
                    "governance_summary": path_summary.get("retrieval_governance_summary"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                },
            )
        except Exception:
            logger.debug("Langfuse retrieval observation failed", exc_info=True)

    # Align with player-visible truth: opening turns often have gm_narration / generation text
    # before scene_blocks projection; counting only scene_blocks yields false 0 (see Langfuse traces).
    has_visible_surface = bool(_scene_blocks_from_turn_event(event)) or bool(
        _visible_lines_from_turn_event(event)
    )
    _authoritative_action_surface = adapter_name in {
        "action_resolution_authoritative",
        "action_resolution_synthetic",
    }
    deterministic_scores = {
        "non_mock_generation_pass": (
            1.0
            if _authoritative_action_surface
            or adapter_name not in {"", "mock", "ldss_fallback", "ldss_deterministic"}
            else 0.0
        ),
        "visible_output_present": 1.0 if has_visible_surface else 0.0,
        "actor_lane_safety_pass": 1.0 if path_summary.get("actor_lane_validation_status") in {"approved", None} else 0.0,
        "fallback_absent": 0.0 if path_summary.get("generation_fallback_used") else 1.0,
        "usage_present": 1.0 if int(usage_details.get("total") or 0) > 0 or _authoritative_action_surface else 0.0,
        "rag_context_attached": 1.0 if path_summary.get("retrieval_context_attached") else 0.0,
    }
    intent_kind = str(path_summary.get("player_input_kind") or "").strip().lower()
    semantic_move_kind = str(path_summary.get("semantic_move_kind") or "").strip()
    semantic_alignment_pass = True
    if semantic_move_kind:
        semantic_alignment_pass = True
    if is_question_punctuation_probe_guarded(intent_kind) and semantic_move_kind:
        semantic_alignment_pass = (
            semantic_alignment_pass
            and semantic_move_kind not in FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES
        )
    npc_action_narration_boundary_pass = not bool(
        path_summary.get("npc_narrated_player_action_violation")
    )
    player_input_attribution = path_summary.get("player_input_attribution_pass")
    player_input_attribution_pass = (
        True if player_input_attribution is None else bool(player_input_attribution)
    )
    intent_surface_contract_pass = True
    if intent_kind:
        intent_surface_contract_pass = (
            intent_kind in PLAYER_INPUT_KINDS
            and isinstance(path_summary.get("player_action_committed"), bool)
            and isinstance(path_summary.get("player_speech_committed"), bool)
            and isinstance(path_summary.get("narrator_response_expected"), bool)
            and isinstance(path_summary.get("npc_response_expected"), bool)
        )
    deterministic_scores["intent_surface_contract_pass"] = 1.0 if intent_surface_contract_pass else 0.0
    deterministic_scores["player_input_attribution_pass"] = 1.0 if player_input_attribution_pass else 0.0
    deterministic_scores["semantic_move_alignment_pass"] = 1.0 if semantic_alignment_pass else 0.0
    subtext_contract_raw = path_summary.get("subtext_contract_pass")
    if subtext_contract_raw is None:
        subtext_fields_present = any(
            path_summary.get(key)
            for key in (
                "subtext_surface_mode",
                "subtext_hidden_intent_hypothesis",
                "subtext_function",
                "subtext_sincerity_band",
            )
        )
        subtext_contract_pass = True
        if subtext_fields_present:
            subtext_contract_pass = all(
                bool(str(path_summary.get(key) or "").strip())
                for key in (
                    "subtext_surface_mode",
                    "subtext_hidden_intent_hypothesis",
                    "subtext_function",
                    "subtext_sincerity_band",
                )
            )
    else:
        subtext_contract_pass = bool(subtext_contract_raw)
    deterministic_scores["subtext_contract_pass"] = 1.0 if subtext_contract_pass else 0.0
    deterministic_scores["npc_action_narration_boundary_pass"] = (
        1.0 if npc_action_narration_boundary_pass else 0.0
    )
    # OPEN-SCORE-SPLIT-01:
    # - opening_shape_contract_pass: purely visible opening-shape quality (can pass in fixtures/mocks).
    # - live_opening_contract_pass: strict live-only success marker for canonical live_ui opening.
    # ``opening_contract_pass`` is kept as a compatibility alias to opening_shape_contract_pass.
    # Turn > 0 trivially passes the shape check (opening-only structural contract).
    _turn_number = int(path_summary.get("turn_number") or 0)
    _opening_blocks: list[dict[str, Any]] = []
    _opening_shape_subgates: dict[str, bool] = {}
    _opening_shape_failure_reasons: list[str] = []
    _scene_block_summary: list[dict[str, Any]] = []
    first_actor_block_index_val: int | None = None
    narrator_block_count_val = 0
    structured_narration_summary_kind: str | None = None
    if _turn_number == 0:
        _opening_blocks = _scene_blocks_from_turn_event(event)
        opening_shape_pass = (
            1.0 if _opening_block_contract_satisfied(_opening_blocks) else 0.0
        )
        # OPEN-SHAPE-EVIDENCE-01: Decompose the contract into auditable subgates and
        # capture a small scene-block excerpt so dashboards can answer "why did
        # opening_shape_contract_pass fail?" without re-fetching the trace body.
        _opening_shape_subgates, _opening_shape_failure_reasons = (
            _compute_opening_shape_subgates(_opening_blocks)
        )
        _scene_block_summary = _compact_scene_block_summary(_opening_blocks)

        def _bt_ev(b: dict) -> str:
            return str(b.get("block_type") or b.get("type") or "").strip().lower()

        narrator_block_count_val = sum(1 for b in _opening_blocks if _bt_ev(b) == "narrator")
        for i, b in enumerate(_opening_blocks):
            if _bt_ev(b) in {"actor_line", "actor_action"}:
                first_actor_block_index_val = i
                break
        gen_ev = ((event.get("model_route") or {}).get("generation") or {}) if isinstance(event.get("model_route"), dict) else {}
        meta_ev = gen_ev.get("metadata") if isinstance(gen_ev.get("metadata"), dict) else {}
        struct_ev = meta_ev.get("structured_output") if isinstance(meta_ev.get("structured_output"), dict) else None
        if struct_ev is None and isinstance(gen_ev.get("structured_output"), dict):
            struct_ev = gen_ev["structured_output"]
        if isinstance(struct_ev, dict):
            ns_ev = struct_ev.get("narration_summary")
            if isinstance(ns_ev, str) and ns_ev.strip():
                structured_narration_summary_kind = "str"
            elif isinstance(ns_ev, list):
                structured_narration_summary_kind = "list"
            else:
                structured_narration_summary_kind = "absent"
        else:
            structured_narration_summary_kind = "missing_structured"
        if (
            opening_shape_pass < 1.0
            and structured_narration_summary_kind == "str"
            and "narration_summary_single_string" not in _opening_shape_failure_reasons
        ):
            _opening_shape_failure_reasons = list(_opening_shape_failure_reasons) + [
                "narration_summary_single_string"
            ]
    else:
        opening_shape_pass = 1.0
    deterministic_scores["opening_shape_contract_pass"] = opening_shape_pass
    deterministic_scores["opening_contract_pass"] = opening_shape_pass
    # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P6: promote role_anchor_present
    # to its own top-level numeric score so dashboards can filter without nested metadata joins.
    if _turn_number == 0:
        deterministic_scores["opening_role_anchor_pass"] = (
            1.0 if _opening_shape_subgates.get("role_anchor_present") else 0.0
        )
    else:
        deterministic_scores["opening_role_anchor_pass"] = 1.0
    deterministic_scores["hard_forbidden_absent"] = (
        1.0 if path_summary.get("hard_forbidden_absent", True) else 0.0
    )
    deterministic_scores["opening_summary_only_absent"] = (
        1.0 if path_summary.get("opening_summary_only_absent", True) else 0.0
    )
    deterministic_scores["opening_event_coverage_pass"] = (
        1.0 if (_turn_number > 0 or path_summary.get("opening_event_coverage_pass", True)) else 0.0
    )
    # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P0.3/P0.4: per-category absent-scores derived
    # from hard_forbidden_detection.detected detection_keys. Deterministic 1.0 / 0.0.
    _hfd_for_scores = path_summary.get("hard_forbidden_detection") if isinstance(path_summary.get("hard_forbidden_detection"), dict) else {}
    _detected_keys: set[str] = set()
    for _hit in (_hfd_for_scores.get("detected") or []):
        if isinstance(_hit, dict):
            _key = str(_hit.get("detection_key") or "").strip()
            if _key:
                _detected_keys.add(_key)
    _absent_score_map = {
        "opening_player_speech_absent": "forced_player_speech",
        "opening_npc_exposition_absent": "npc_world_explanation",
        "npc_exposition_absent": "npc_world_explanation",
        "player_agency_violation_absent": "player_agency_violation",
        "meta_runtime_language_absent": "meta_runtime_language",
        "stage_direction_labels_absent": "stage_direction_labels",
        "source_reproduction_absent": "source_text_reproduction",
    }
    for _score_name, _detection_key in _absent_score_map.items():
        deterministic_scores[_score_name] = 0.0 if _detection_key in _detected_keys else 1.0
    if _turn_number == 0:
        _handover_diag_for_scores = compute_opening_handover_from_scene_blocks(
            _opening_blocks,
            human_actor_id=str(path_summary.get("human_actor_id") or "").strip() or None,
            selected_player_role=str(path_summary.get("selected_player_role") or "").strip() or None,
        )
        deterministic_scores["opening_handover_contract_pass"] = (
            1.0 if _handover_diag_for_scores.get("opening_handover_contract_pass") else 0.0
        )
    else:
        _handover_diag_for_scores = {}
        deterministic_scores["opening_handover_contract_pass"] = 1.0
    _p0_player_turn_langfuse_scores = frozenset(
        {
            "player_action_frame_present",
            "affordance_resolution_present",
            "affordance_status_valid",
            "action_commit_policy_present",
        }
    )
    live_contract_pass = all(
        value == 1.0
        for key, value in deterministic_scores.items()
        if _turn_number > 0 or key not in _p0_player_turn_langfuse_scores
    ) and path_summary.get("quality_class") not in {"degraded", "failed"}
    deterministic_scores["live_runtime_contract_pass"] = 1.0 if live_contract_pass else 0.0
    # Player-visible path only (excludes mock/usage/RAG gates). Stays green in mock_only when UI output is present.
    qc = path_summary.get("quality_class")
    surface_ok = (
        deterministic_scores["visible_output_present"] == 1.0
        and deterministic_scores["actor_lane_safety_pass"] == 1.0
        and deterministic_scores["fallback_absent"] == 1.0
        and qc not in {"degraded", "failed"}
    )
    deterministic_scores["live_runtime_visible_surface_pass"] = 1.0 if surface_ok else 0.0
    _valid_aff = frozenset(
        {"allowed", "allowed_offscreen", "partial", "ambiguous", "blocked", "unknown_target", "unsafe"}
    )
    _aff_st_ev = str(path_summary.get("affordance_status") or "").strip().lower()
    _aff_pres_ev = bool(path_summary.get("affordance_resolution_present"))
    # P0 player-action Langfuse scores apply only to real player turns (``turn_number > 0``).
    # Opening traces must not contribute ``player_action_frame_present`` / affordance scores
    # that could be mistaken for P0 correctness evidence.
    if _turn_number > 0:
        deterministic_scores["player_action_frame_present"] = (
            1.0 if bool(path_summary.get("player_action_frame_present")) else 0.0
        )
        deterministic_scores["affordance_resolution_present"] = 1.0 if _aff_pres_ev else 0.0
        deterministic_scores["affordance_status_valid"] = (
            1.0 if (not _aff_pres_ev or _aff_st_ev in _valid_aff) else 0.0
        )
        deterministic_scores["action_commit_policy_present"] = (
            1.0 if str(path_summary.get("action_commit_policy") or "").strip() else 0.0
        )
        # PLAYER-LOCAL-CONTEXT-AND-NARRATOR-CONSEQUENCE-01 scores (action-resolution short-path only).
        _lct = path_summary.get("local_context_transition") if isinstance(path_summary.get("local_context_transition"), dict) else None
        _ncp = path_summary.get("narrator_consequence_plan") if isinstance(path_summary.get("narrator_consequence_plan"), dict) else None
        _intent_kind_for_consequence = str(path_summary.get("player_input_kind") or "").strip().lower()
        _is_action_resolution_turn = _authoritative_action_surface and _intent_kind_for_consequence in {
            "action",
            "perception",
            "object_interaction",
            "physical_action",
            "movement_action",
            "perception_action",
        }
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: emit deterministic
        # action-context scores on every player turn — not only the authoritative action
        # short-path — so dashboards observe degraded/fallback behaviour rather than gaps.
        _action_diag = _compute_action_consequence_diagnostics(path_summary)
        for _name in (
            "local_context_transition_present",
            "narrator_consequence_present",
            "new_location_established",
            "perception_result_present",
            "action_consequence_contract_pass",
            "npc_consequence_takeover_absent",
        ):
            _value = _action_diag.get(_name)
            if isinstance(_value, (int, float)):
                deterministic_scores[_name] = float(_value)
    # live_opening_contract_pass is only meaningful on the opening turn (turn 0).
    # Writing it on subsequent turns would produce false negatives that pollute
    # the trace score history and make passing openings appear to have failed.
    _live_subgates: dict[str, bool] = {}
    _live_failure_reasons: list[str] = []
    if _turn_number == 0:
        final_adapter = str(path_summary.get("final_adapter") or path_summary.get("adapter") or "").strip().lower()
        trace_origin = str(path_summary.get("trace_origin") or "").strip().lower()
        execution_tier = str(path_summary.get("execution_tier") or "").strip().lower()
        canonical_player_flow = bool(path_summary.get("canonical_player_flow"))
        _live_subgates = {
            "turn_0": True,
            "trace_origin_live_ui": trace_origin == "live_ui",
            "execution_tier_live": execution_tier == "live",
            "canonical_player_flow": canonical_player_flow,
            "opening_shape_pass": deterministic_scores["opening_shape_contract_pass"] == 1.0,
            "opening_handover_pass": deterministic_scores.get("opening_handover_contract_pass", 1.0) == 1.0,
            "live_runtime_pass": deterministic_scores["live_runtime_contract_pass"] == 1.0,
            "not_ldss_fallback": final_adapter not in {"ldss_fallback"},
            "fallback_absent": deterministic_scores["fallback_absent"] == 1.0,
            "non_mock_generation": deterministic_scores["non_mock_generation_pass"] == 1.0,
            "quality_class_ok": qc not in {"degraded", "failed"},
        }
        _live_failure_reasons = [k for k, v in _live_subgates.items() if not v]
        live_opening_ok = all(_live_subgates.values())
        deterministic_scores["live_opening_contract_pass"] = 1.0 if live_opening_ok else 0.0
    canonical_signals = _build_canonical_degradation_signals(path_summary)
    degradation_chain = _build_degradation_chain(path_summary)
    degradation_prose_summary = _build_degradation_prose_summary(path_summary)
    live_opening_failure_reason = path_summary.get("live_opening_failure_reason")
    score_metadata_base = {
        "session_id": path_summary.get("session_id"),
        "turn_number": path_summary.get("turn_number"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
        "selected_player_role": path_summary.get("selected_player_role"),
        "human_actor_id": path_summary.get("human_actor_id"),
        "quality_class": path_summary.get("quality_class"),
        "degradation_signals": canonical_signals,
        "degradation_chain": degradation_chain,
        "degradation_summary": degradation_prose_summary,
        "player_input_kind": path_summary.get("player_input_kind"),
        "player_input_kind_family": path_summary.get("player_input_kind_family")
        or player_input_kind_family(path_summary.get("player_input_kind")),
        "intent_contract_version": path_summary.get("intent_contract_version")
        or INTENT_CONTRACT_VERSION,
        "player_action_committed": path_summary.get("player_action_committed"),
        "player_speech_committed": path_summary.get("player_speech_committed"),
        "narrator_response_expected": path_summary.get("narrator_response_expected"),
        "npc_response_expected": path_summary.get("npc_response_expected"),
        "p0_action_resolution_evidence": path_summary.get("p0_action_resolution_evidence"),
        "semantic_move_kind": path_summary.get("semantic_move_kind"),
        "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
        "subtext_hidden_intent_hypothesis": path_summary.get(
            "subtext_hidden_intent_hypothesis"
        ),
        "subtext_function": path_summary.get("subtext_function"),
        "subtext_sincerity_band": path_summary.get("subtext_sincerity_band"),
        "subtext_policy_source": path_summary.get("subtext_policy_source"),
        "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
        "subtext_evidence_codes": path_summary.get("subtext_evidence_codes"),
        "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
        "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
        "legacy_keyword_scene_candidates_used": path_summary.get(
            "legacy_keyword_scene_candidates_used"
        ),
        "npc_narrated_player_action_violation": path_summary.get(
            "npc_narrated_player_action_violation"
        ),
        "intent_surface_contract_pass": deterministic_scores.get("intent_surface_contract_pass"),
        "player_input_attribution_pass": deterministic_scores.get("player_input_attribution_pass"),
        "semantic_move_alignment_pass": deterministic_scores.get("semantic_move_alignment_pass"),
        "subtext_contract_pass": deterministic_scores.get("subtext_contract_pass"),
        "npc_action_narration_boundary_pass": deterministic_scores.get(
            "npc_action_narration_boundary_pass"
        ),
        "live_opening_failure_reason": live_opening_failure_reason,
        "live_opening_subgates": _live_subgates,
        "live_opening_failure_reasons": _live_failure_reasons,
        # OPEN-SHAPE-EVIDENCE-01: opening_shape_contract_pass subgate decomposition
        # + truncated scene_block excerpts. Surfaced on every score row to mirror
        # the live_opening_* pattern; only populated on turn 0 (empty otherwise).
        "opening_shape_subgates": _opening_shape_subgates,
        "opening_shape_failure_reasons": _opening_shape_failure_reasons,
        "scene_block_summary": _scene_block_summary,
        "first_actor_block_index": first_actor_block_index_val,
        "narrator_block_count": narrator_block_count_val,
        "structured_narration_summary_kind": structured_narration_summary_kind,
        "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
        "opening_missing_event_ids": path_summary.get("opening_missing_event_ids"),
        "opening_missing_must_establish": path_summary.get("opening_missing_must_establish"),
        "opening_handover_to_scene_phase_expected": path_summary.get(
            "opening_handover_to_scene_phase_expected"
        ),
        "opening_handover_to_scene_phase_actual": path_summary.get(
            "opening_handover_to_scene_phase_actual"
        ),
        "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
        "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
        "hard_forbidden_detection": path_summary.get("hard_forbidden_detection"),
        # ADR-0033 §13.10 primary-vs-final clarity (metadata only; no gate semantics).
        "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
        "primary_attempt_model": path_summary.get("primary_attempt_model"),
        "primary_attempt_provider": path_summary.get("primary_attempt_provider"),
        "primary_attempt_invocation_mode": path_summary.get("primary_attempt_invocation_mode"),
        "final_adapter": path_summary.get("final_adapter"),
        "final_adapter_invocation_mode": path_summary.get("final_adapter_invocation_mode"),
        "fallback_reason": path_summary.get("fallback_reason"),
        "ldss_fallback_after_live_opening_failure": path_summary.get(
            "ldss_fallback_after_live_opening_failure"
        ),
        "trace_origin": path_summary.get("trace_origin"),
        "execution_tier": path_summary.get("execution_tier"),
        "canonical_player_flow": path_summary.get("canonical_player_flow"),
        "test_case_id": path_summary.get("test_case_id"),
        "runtime_mode": path_summary.get("runtime_mode"),
        "generation_mode": path_summary.get("generation_mode"),
        # PRIMARY-PARSER-EVIDENCE-01: primary attempt diagnosis (score context only; no gate semantics).
        "primary_attempt_api_success": path_summary.get("primary_attempt_api_success"),
        "primary_attempt_parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
        "self_correction_attempted": path_summary.get("self_correction_attempted"),
        "self_correction_attempt_count": path_summary.get("self_correction_attempt_count"),
        "self_correction_success": path_summary.get("self_correction_success"),
        "self_correction_model": path_summary.get("self_correction_model"),
        "self_correction_trigger_source": path_summary.get("self_correction_trigger_source"),
        "runtime_aspect_failure_before_retry": path_summary.get(
            "runtime_aspect_failure_before_retry"
        ),
        "capability_failure_before_retry": path_summary.get("capability_failure_before_retry"),
        "self_correction_resolved_failure": path_summary.get("self_correction_resolved_failure"),
        # OPEN-ACTOR-BLOCK-PROJECTION-01: structured lane → scene_blocks audit fields.
        "actor_block_source": path_summary.get("actor_block_source"),
        "actor_block_filtered_reason": path_summary.get("actor_block_filtered_reason"),
        "actor_line_count_before_projection": path_summary.get("actor_line_count_before_projection"),
        "action_line_count_before_projection": path_summary.get("action_line_count_before_projection"),
        "actor_block_count_after_projection": path_summary.get("actor_block_count_after_projection"),
        # VISIBLE-NARRATIVE-CONTRACT-01 (metadata only; not part of deterministic_scores gates).
        "visible_language_detected": path_summary.get("visible_language_detected"),
        "mixed_language_detected": path_summary.get("mixed_language_detected"),
        "visible_language_contract_pass": path_summary.get("visible_language_contract_pass"),
        "selected_role_visible_in_opening": path_summary.get("selected_role_visible_in_opening"),
        "player_identity_anchor_present": path_summary.get("player_identity_anchor_present"),
        "visible_narrative_contract_version": path_summary.get("visible_narrative_contract_version"),
        "name_only_actor_block_removed": path_summary.get("name_only_actor_block_removed"),
        "label_only_line_removed": path_summary.get("label_only_line_removed"),
        "duplicate_actor_label_removed": path_summary.get("duplicate_actor_label_removed"),
        "placeholder_action_removed": path_summary.get("placeholder_action_removed"),
        "actor_line_action_tail_stripped": path_summary.get("actor_line_action_tail_stripped"),
        "near_duplicate_visible_block_removed": path_summary.get("near_duplicate_visible_block_removed"),
        "player_role_display_name": path_summary.get("player_role_display_name"),
        "session_output_language": path_summary.get("session_output_language"),
        **_handover_diag_for_scores,
    }
    for name, value in deterministic_scores.items():
        try:
            adapter.add_score(
                name=name,
                value=value,
                comment="deterministic live story runtime evidence gate",
                metadata=dict(score_metadata_base),
            )
        except Exception:
            logger.debug("Langfuse score write failed for %s", name, exc_info=True)


def _visible_lines_from_turn_event(event: dict[str, Any]) -> list[str]:
    bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
    lines = _coerce_visible_text_lines(bundle.get("gm_narration"))
    if lines:
        return lines

    generation = ((event.get("model_route") or {}).get("generation") or {}) if isinstance(event.get("model_route"), dict) else {}
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    if structured is None and isinstance(generation.get("structured_output"), dict):
        structured = generation["structured_output"]
    if isinstance(structured, dict):
        for key in (
            "narrative_response",
            "narration_summary",
            "opening_narration",
            "scene_description",
            "narrative_summary",
        ):
            lines = _coerce_visible_text_lines(structured.get(key))
            if lines:
                return lines
        for lane_key in ("spoken_lines", "action_lines"):
            lane = structured.get(lane_key)
            if not isinstance(lane, list):
                continue
            lane_lines: list[str] = []
            for row in lane:
                if isinstance(row, dict):
                    text = str(row.get("text") or row.get("line") or "").strip()
                    if text:
                        lane_lines.append(text)
                elif str(row).strip():
                    lane_lines.append(str(row).strip())
            if lane_lines:
                return lane_lines

    lines = _coerce_visible_text_lines(generation.get("content") or generation.get("model_raw_text"))
    if lines:
        return lines

    commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
    status = str(commit.get("situation_status") or "").strip()
    return [status] if status else []


def _scene_blocks_from_turn_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
    scene_blocks = bundle.get("scene_blocks")
    if isinstance(scene_blocks, list):
        return [dict(block) for block in scene_blocks if isinstance(block, dict)]

    scene_turn_envelope = (
        event.get("scene_turn_envelope")
        if isinstance(event.get("scene_turn_envelope"), dict)
        else {}
    )
    visible_scene_output = (
        scene_turn_envelope.get("visible_scene_output")
        if isinstance(scene_turn_envelope.get("visible_scene_output"), dict)
        else {}
    )
    blocks = visible_scene_output.get("blocks")
    if isinstance(blocks, list):
        return [dict(block) for block in blocks if isinstance(block, dict)]
    return []


def _opening_block_contract_satisfied(scene_blocks: list[dict[str, Any]]) -> bool:
    """OPEN-GATE-01: Turn 0 must start with 3 narrator blocks before any actor_line/action."""
    if len(scene_blocks) < 4:
        return False

    def _bt(b: dict) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    if _bt(scene_blocks[0]) != "narrator":
        return False
    if _bt(scene_blocks[1]) != "narrator":
        return False
    if _bt(scene_blocks[2]) != "narrator":
        return False
    first_actor = next(
        (i for i, b in enumerate(scene_blocks) if _bt(b) in {"actor_line", "actor_action"}),
        None,
    )
    return first_actor is not None and first_actor >= 3


def _compute_opening_shape_subgates(
    scene_blocks: list[dict[str, Any]],
) -> tuple[dict[str, bool], list[str]]:
    """OPEN-SHAPE-EVIDENCE-01: Decompose ``_opening_block_contract_satisfied`` into
    auditable per-subgate truth values + ordered failure-reason tokens.

    The aggregate truth of the returned subgates is functionally equivalent to
    ``_opening_block_contract_satisfied(scene_blocks)`` — the helper exists only
    to surface *why* the contract failed for Langfuse score metadata. It must
    not introduce any new gate semantics.

    Subgates (all booleans):
        block_count_ok           — at least 4 visible blocks
        narrator_intro_present   — block[0].block_type == "narrator"
        role_anchor_present      — block[1].block_type == "narrator"
        scene_setup_present      — block[2].block_type == "narrator"
        first_three_are_narrator — narrator_intro AND role_anchor AND scene_setup
        first_actor_after_intro  — first actor_line/actor_action appears at idx >= 3

    Failure reasons (ordered, lowercase tokens) match the operator vocabulary
    captured during the 2026-05-08 audit so dashboards can correlate score rows
    with the audit narrative without bespoke joins.
    """

    def _bt(b: dict) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    block_count = len(scene_blocks)
    types = [_bt(b) for b in scene_blocks]
    first_actor_idx = next(
        (i for i, t in enumerate(types) if t in {"actor_line", "actor_action"}),
        None,
    )

    narrator_intro_present = block_count >= 1 and types[0] == "narrator"
    role_anchor_present = block_count >= 2 and types[1] == "narrator"
    scene_setup_present = block_count >= 3 and types[2] == "narrator"
    first_three_are_narrator = (
        narrator_intro_present and role_anchor_present and scene_setup_present
    )
    first_actor_after_intro = first_actor_idx is not None and first_actor_idx >= 3
    block_count_ok = block_count >= 4

    subgates = {
        "block_count_ok": block_count_ok,
        "narrator_intro_present": narrator_intro_present,
        "role_anchor_present": role_anchor_present,
        "scene_setup_present": scene_setup_present,
        "first_three_are_narrator": first_three_are_narrator,
        "first_actor_after_intro": first_actor_after_intro,
    }

    failure_reasons: list[str] = []
    if block_count == 0:
        failure_reasons.append("no_visible_scene_blocks")
    if not block_count_ok:
        failure_reasons.append("block_count_lt_4")
    if not narrator_intro_present:
        failure_reasons.append("narrator_intro_missing")
    if not role_anchor_present:
        failure_reasons.append("role_anchor_missing")
    if not scene_setup_present:
        failure_reasons.append("scene_setup_missing")
    if first_actor_idx is None:
        failure_reasons.append("no_actor_block_present")
    elif not first_actor_after_intro:
        failure_reasons.append("actor_block_before_intro")

    return subgates, failure_reasons


def _compact_scene_block_summary(
    scene_blocks: list[dict[str, Any]],
    *,
    max_count: int = 6,
    text_excerpt_chars: int = 120,
) -> list[dict[str, Any]]:
    """OPEN-SHAPE-EVIDENCE-01: Build a small, score-metadata-safe scene_block excerpt list.

    Caps at ``max_count`` blocks and truncates each ``text`` field to
    ``text_excerpt_chars`` characters with an ellipsis. Keeps payload <= ~1KB
    so attaching it to every score row in ``score_metadata_base`` does not
    bloat Langfuse score storage.
    """
    out: list[dict[str, Any]] = []
    for idx, block in enumerate(scene_blocks[:max_count]):
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or block.get("type") or "").strip().lower() or None
        actor_id = block.get("actor_id") or block.get("speaker_id")
        actor_id_str = str(actor_id).strip() if actor_id else None
        raw_text = str(block.get("text") or "").strip().replace("\r", " ").replace("\n", " ")
        if len(raw_text) > text_excerpt_chars:
            text_excerpt = raw_text[: max(0, text_excerpt_chars - 1)] + "\u2026"
        else:
            text_excerpt = raw_text
        out.append(
            {
                "index": idx,
                "block_type": block_type,
                "actor_id": actor_id_str,
                "text_excerpt": text_excerpt,
            }
        )
    return out


def _actor_response_visible_in_scene_blocks(blocks: list[dict[str, Any]]) -> bool:
    for block in blocks:
        if not isinstance(block, dict):
            continue
        bt = str(block.get("block_type") or block.get("type") or "").strip()
        if bt in {"actor_line", "actor_action"}:
            return True
    return False


def _final_visible_actor_response_in_event(event: dict[str, Any]) -> bool:
    return _actor_response_visible_in_scene_blocks(_scene_blocks_from_turn_event(event))


def _reconcile_governance_passivity_with_final_projection(event: dict[str, Any]) -> None:
    """Drop ``no_visible_actor_response`` when final projected blocks show actor output."""
    if not _final_visible_actor_response_in_event(event):
        return

    def _without_no_visible(seq: Any) -> list[str]:
        if not isinstance(seq, list):
            return []
        return [str(x) for x in seq if str(x) != "no_visible_actor_response"]

    gov = event.get("runtime_governance_surface")
    if isinstance(gov, dict):
        gov["why_turn_felt_passive"] = _without_no_visible(gov.get("why_turn_felt_passive"))
        gov["primary_passivity_factors"] = _without_no_visible(gov.get("primary_passivity_factors"))
        pd = gov.get("passivity_diagnosis_v1")
        if isinstance(pd, dict):
            pd["why_turn_felt_passive"] = _without_no_visible(pd.get("why_turn_felt_passive"))
            pd["primary_passivity_factors"] = _without_no_visible(pd.get("primary_passivity_factors"))

    # Play shell / routes_play read passivity from actor_survival_telemetry, not gov alone.
    tel = event.get("actor_survival_telemetry")
    if isinstance(tel, dict):
        pd = tel.get("passivity_diagnosis_v1")
        if isinstance(pd, dict):
            pd["why_turn_felt_passive"] = _without_no_visible(pd.get("why_turn_felt_passive"))
            pd["primary_passivity_factors"] = _without_no_visible(pd.get("primary_passivity_factors"))
        vit = tel.get("vitality_telemetry_v1")
        if isinstance(vit, dict):
            vit["response_present"] = True


def _effective_story_runtime_experience_slice(
    graph_state: dict[str, Any] | None,
    explicit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve governed experience flags (effective slice) for GoC transcript policy."""
    if isinstance(explicit, dict) and explicit:
        return dict(explicit)
    if isinstance(graph_state, dict):
        sre = graph_state.get("story_runtime_experience")
        if isinstance(sre, dict):
            eff = sre.get("effective")
            if isinstance(eff, dict) and eff:
                return dict(eff)
            if any(
                k in sre
                for k in (
                    "experience_mode",
                    "goc_transcript_merge_consecutive_same_actor",
                    "goc_map_action_lines_to_actor_line_lane",
                )
            ):
                return dict(sre)
    return {}


def _live_scene_blocks_from_visible_bundle(
    visible_output_bundle: dict[str, Any] | None,
    *,
    turn_number: int,
    structured_output: dict[str, Any] | None = None,
    runtime_projection: dict[str, Any] | None = None,
    graph_state: dict[str, Any] | None = None,
    session_output_language: str = "de",
    player_input: str | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if graph_state is not None and turn_number != 0:
        graph_state.pop("_actor_block_projection_evidence", None)
        graph_state.pop("_opening_handover_diagnostics", None)
    bundle = visible_output_bundle if isinstance(visible_output_bundle, dict) else {}
    proj = runtime_projection if isinstance(runtime_projection, dict) else None
    human_id = str((proj or {}).get("human_actor_id") or "").strip()
    role = str((proj or {}).get("selected_player_role") or "").strip()
    _exp_eff = _effective_story_runtime_experience_slice(graph_state, story_runtime_experience)
    _goc_action_block_type = (
        "actor_line"
        if goc_transcript_policy_flags(_exp_eff)["map_action_lines_to_actor_line_lane"]
        else "actor_action"
    )
    _exp_lang = str(session_output_language or "de").strip().lower()[:2] or "de"
    echo_strings: list[str] = []
    pi = str(player_input or "").strip()
    if pi:
        echo_strings.append(pi)
    ledger = (
        graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state, dict) and isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else {}
    )
    beat_record = (
        (ledger.get("turn_aspect_ledger") or {}).get("beat")
        if isinstance(ledger.get("turn_aspect_ledger"), dict)
        else {}
    )
    selected_beat_id = None
    canonical_turn_id = None
    if isinstance(beat_record, dict):
        selected_beat_id = (
            (beat_record.get("selected") or {}).get("selected_beat_id")
            if isinstance(beat_record.get("selected"), dict)
            else None
        ) or (
            (beat_record.get("actual") or {}).get("selected_beat_id")
            if isinstance(beat_record.get("actual"), dict)
            else None
        )
    if isinstance(ledger, dict):
        canonical_turn_id = (
            ledger.get("canonical_turn_id")
            or ledger.get("turn_id")
            or ledger.get("turn_record_id")
        )

    def origin_metadata(block_type: str, actor_id: str | None = None) -> dict[str, Any]:
        bt = str(block_type or "").strip().lower()
        if bt == "narrator":
            frame = graph_state.get("player_action_frame") if isinstance(graph_state, dict) and isinstance(graph_state.get("player_action_frame"), dict) else {}
            pik = str(frame.get("player_input_kind") or "").strip().lower()
            action_kind = str(frame.get("action_kind") or "").strip().lower()
            capability = NARRATOR_ACTION_CONSEQUENCE_DESCRIBE
            if is_perception_like_player_input_kind(pik):
                capability = NARRATOR_PERCEPTION_RESULT_DESCRIBE
            elif action_kind == "movement":
                capability = NARRATOR_LOCATION_TRANSITION_DESCRIBE
            elif action_kind == "object_interaction":
                capability = NARRATOR_OBJECT_STATE_DESCRIBE
            elif turn_number == 0:
                capability = NARRATOR_OPENING_EVENT_REALIZE
            return {
                "origin_aspect": "narrator_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": capability,
                "authority_owner": "narrator",
                "expected_owner": "narrator",
                "actual_owner": "narrator",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_REQUIRED,
            }
        if bt == "actor_line":
            interp = graph_state.get("interpreted_input") if isinstance(graph_state, dict) and isinstance(graph_state.get("interpreted_input"), dict) else {}
            pik = str(interp.get("player_input_kind") or "").strip().lower()
            return {
                "origin_aspect": "npc_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": NPC_DIRECT_ANSWER_ALLOWED
                if is_speech_like_player_input_kind(pik)
                else NPC_SOCIAL_REACTION_OPTIONAL,
                "authority_owner": "npc" if actor_id else "runtime",
                "expected_owner": "npc" if actor_id else "system",
                "actual_owner": "npc" if actor_id else "system",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_SUPPORTING,
            }
        if bt == "actor_action":
            return {
                "origin_aspect": "npc_authority",
                "origin_beat_id": selected_beat_id,
                "origin_capability": NPC_ACTION_GESTURE_OPTIONAL,
                "authority_owner": "npc" if actor_id else "runtime",
                "expected_owner": "npc" if actor_id else "system",
                "actual_owner": "npc" if actor_id else "system",
                "canonical_turn_id": canonical_turn_id,
                "evidence_role": EVIDENCE_SUPPORTING,
            }
        return {
            "origin_aspect": "visible_projection",
            "origin_beat_id": selected_beat_id,
            "origin_capability": None,
            "authority_owner": "runtime",
            "expected_owner": "system",
            "actual_owner": "system",
            "canonical_turn_id": canonical_turn_id,
            "evidence_role": EVIDENCE_SUPPORTING,
        }

    def with_origin(block: dict[str, Any]) -> dict[str, Any]:
        out = dict(block)
        meta = origin_metadata(
            str(out.get("block_type") or out.get("type") or ""),
            str(out.get("actor_id") or "").strip() or None,
        )
        for key, value in meta.items():
            out.setdefault(key, value)
        return out

    existing = bundle.get("scene_blocks")
    if isinstance(existing, list) and existing:
        blocks = [with_origin(block) for block in existing if isinstance(block, dict)]
        blocks, vis_diag = _finalize_visible_blocks_with_goc_actor_split(
            blocks,
            expected_language=_exp_lang,
            human_actor_id=human_id or None,
            selected_player_role=role or None,
            turn_number=turn_number,
            player_input_echo_strings=echo_strings or None,
            runtime_projection=proj,
            story_runtime_experience=_exp_eff,
        )
        if graph_state is not None:
            graph_state["_visible_narrative_contract"] = vis_diag
        if turn_number == 0 and graph_state is not None:
            blocks, _polished = polish_first_opening_actor_block(blocks, output_language=_exp_lang)
            graph_state["_opening_handover_diagnostics"] = compute_opening_handover_from_scene_blocks(
                blocks,
                human_actor_id=human_id or None,
                selected_player_role=role or None,
            )
        return blocks

    def delivery() -> dict[str, Any]:
        return {
            "mode": "typewriter",
            "characters_per_second": 44,
            "pause_before_ms": 150,
            "pause_after_ms": 650,
            "skippable": True,
        }

    blocks: list[dict[str, Any]] = []

    def append_block(block_type: str, text: str, *, speaker_label: str, actor_id: str | None = None) -> None:
        raw = str(text or "").strip()
        if not raw:
            return
        clean, _partial = sanitize_visible_block_text(
            raw,
            block_type=str(block_type or ""),
            speaker_label=str(speaker_label or ""),
            actor_id=str(actor_id).strip() if actor_id else None,
            expected_language=_exp_lang,
        )
        if not clean:
            return
        blocks.append(
            {
                "id": f"turn-{turn_number}-live-block-{len(blocks) + 1}",
                "block_type": block_type,
                "speaker_label": speaker_label,
                "actor_id": actor_id,
                "target_actor_id": None,
                "text": clean,
                "delivery": delivery(),
                "source": "live_runtime_graph",
                **origin_metadata(block_type, actor_id),
            }
        )

    def actor_label(actor_id: str) -> str:
        aid = str(actor_id or "").strip()
        display_names = proj.get("actor_display_names") if isinstance(proj.get("actor_display_names"), dict) else {}
        if aid and display_names.get(aid):
            return str(display_names.get(aid))
        roster = proj.get("actor_roster") if isinstance(proj.get("actor_roster"), dict) else {}
        roster_row = roster.get(aid) if aid and isinstance(roster.get(aid), dict) else {}
        label = str(roster_row.get("display_name") or roster_row.get("name") or "").strip()
        if label:
            return label
        return aid.replace("_", " ").strip().title() or "Actor"

    def append_json_blocks(raw: str) -> bool:
        text = str(raw or "").strip()
        if not text.startswith("{"):
            return False
        try:
            parsed = json.loads(text)
        except Exception:
            return False
        if not isinstance(parsed, dict):
            return False
        emitted = False
        summary = str(parsed.get("narration_summary") or parsed.get("narrative_response") or "").strip()
        if summary:
            append_block("narrator", summary, speaker_label="Narrator")
            emitted = True
        spoken = parsed.get("spoken_lines")
        if isinstance(spoken, list):
            for row in spoken:
                if not isinstance(row, dict):
                    continue
                speaker_id = str(row.get("speaker_id") or "").strip()
                line = str(row.get("text") or row.get("line") or "").strip()
                if not line:
                    continue
                if proj is not None:
                    if not speaker_id:
                        continue
                    if _is_goc_human_lane_actor(
                        speaker_id,
                        human_actor_id=human_id,
                        selected_player_role=role,
                    ):
                        continue
                append_block("actor_line", line, speaker_label=actor_label(speaker_id), actor_id=speaker_id or None)
                emitted = True
        actions = parsed.get("action_lines")
        if isinstance(actions, list):
            for row in actions:
                if not isinstance(row, dict):
                    continue
                actor_id = str(row.get("actor_id") or "").strip()
                line = str(row.get("text") or row.get("line") or "").strip()
                if not line:
                    continue
                if proj is not None:
                    if not actor_id:
                        continue
                    if _is_goc_human_lane_actor(
                        actor_id,
                        human_actor_id=human_id,
                        selected_player_role=role,
                    ):
                        continue
                append_block(
                    _goc_action_block_type,
                    line,
                    speaker_label=actor_label(actor_id),
                    actor_id=actor_id or None,
                )
                emitted = True
        return emitted

    for line in _coerce_visible_text_lines(bundle.get("gm_narration")):
        if append_json_blocks(line):
            continue
        append_block("narrator", line, speaker_label="Narrator")

    for item in bundle.get("spoken_lines") or []:
        if isinstance(item, dict):
            speaker_id = str(item.get("speaker_id") or "").strip()
            line = str(item.get("text") or item.get("line") or "").strip()
            if not line:
                continue
            if proj is not None:
                if not speaker_id:
                    continue
                if _is_goc_human_lane_actor(
                    speaker_id,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block("actor_line", line, speaker_label=actor_label(speaker_id), actor_id=speaker_id or None)
            continue
        for line in _coerce_visible_text_lines(item):
            label = "Actor"
            text = line
            if ":" in line:
                maybe_label, maybe_text = line.split(":", 1)
                if maybe_label.strip() and maybe_text.strip():
                    label = maybe_label.strip()
                    text = maybe_text.strip()
            if proj is not None:
                lane_key = canonicalize_goc_actor_id(label) or label.strip().lower()
                if lane_key and _is_goc_human_lane_actor(
                    lane_key,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block("actor_line", text, speaker_label=label)

    for item in bundle.get("action_lines") or []:
        if isinstance(item, dict):
            aid = str(item.get("actor_id") or "").strip()
            line = str(item.get("text") or item.get("line") or "").strip()
            if not line:
                continue
            if proj is not None:
                if not aid:
                    continue
                if _is_goc_human_lane_actor(
                    aid,
                    human_actor_id=human_id,
                    selected_player_role=role,
                ):
                    continue
            append_block(_goc_action_block_type, line, speaker_label=actor_label(aid), actor_id=aid or None)
            continue
        for line in _coerce_visible_text_lines(item):
            append_block(_goc_action_block_type, line, speaker_label="Action")

    if graph_state is not None and turn_number == 0:
        sl_n, al_n = _structured_lane_dict_counts(structured_output if isinstance(structured_output, dict) else None)
        count_before_backfill = _actor_block_projection_count(blocks)
        bf_src = "none"
        bf_filt: str | None = None
        if isinstance(structured_output, dict) and structured_output:
            blocks, bf_src, bf_filt = _maybe_backfill_opening_actor_from_structured(
                blocks,
                structured_output=structured_output,
                runtime_projection=proj,
                turn_number=turn_number,
                human_actor_id=human_id,
                selected_player_role=role,
                delivery_fn=delivery,
                actor_label_fn=actor_label,
                story_runtime_experience=_exp_eff,
            )
        actor_src = bf_src
        filt_out = bf_filt
        if actor_src == "none" and count_before_backfill > 0:
            for b in blocks[3:]:
                if not isinstance(b, dict):
                    continue
                bt = str(b.get("block_type") or "").strip().lower()
                if bt == "actor_line":
                    actor_src = "spoken_lines"
                    break
                if bt == "actor_action":
                    actor_src = "action_lines"
                    break
        graph_state["_actor_block_projection_evidence"] = {
            "actor_line_count_before_projection": sl_n,
            "action_line_count_before_projection": al_n,
            "actor_block_count_after_projection": _actor_block_projection_count(blocks),
            "actor_block_source": actor_src,
            "actor_block_filtered_reason": filt_out,
        }

    blocks, vis_diag = _finalize_visible_blocks_with_goc_actor_split(
        blocks,
        expected_language=_exp_lang,
        human_actor_id=human_id or None,
        selected_player_role=role or None,
        turn_number=turn_number,
        player_input_echo_strings=echo_strings or None,
        runtime_projection=proj,
        story_runtime_experience=_exp_eff,
    )
    if graph_state is not None:
        graph_state["_visible_narrative_contract"] = vis_diag
        ev_post = graph_state.get("_actor_block_projection_evidence")
        if turn_number == 0 and isinstance(ev_post, dict):
            ev_post["actor_block_count_after_projection"] = _actor_block_projection_count(blocks)

    if turn_number == 0 and graph_state is not None:
        blocks, _polished = polish_first_opening_actor_block(blocks, output_language=_exp_lang)
        graph_state["_opening_handover_diagnostics"] = compute_opening_handover_from_scene_blocks(
            blocks,
            human_actor_id=human_id or None,
            selected_player_role=role or None,
        )

    return blocks


def _build_live_scene_turn_envelope(
    *,
    session: StorySession,
    graph_state: dict[str, Any],
    scene_blocks: list[dict[str, Any]],
    turn_number: int,
) -> dict[str, Any]:
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    selected_player_role = str(proj.get("selected_player_role") or "").strip()
    human_actor_id = str(proj.get("human_actor_id") or "").strip()
    npc_actor_ids = [
        str(actor_id)
        for actor_id in (proj.get("npc_actor_ids") or [])
        if str(actor_id).strip()
    ]
    ai_allowed_actor_ids: set[str] = set()
    for actor_id in npc_actor_ids:
        ai_allowed_actor_ids.update(expand_goc_actor_id_aliases(actor_id))
    ai_forbidden_actor_ids = sorted(expand_goc_actor_id_aliases(human_actor_id))
    responders = graph_state.get("selected_responder_set")
    responder_ids = [
        str(row.get("actor_id") or row.get("responder_id") or "").strip()
        for row in (responders if isinstance(responders, list) else [])
        if isinstance(row, dict) and str(row.get("actor_id") or row.get("responder_id") or "").strip()
    ]
    primary_responder_id = responder_ids[0] if responder_ids else ""
    secondary_responder_ids = responder_ids[1:]
    visible_actor_response_present = any(
        str(block.get("block_type") or "") in {"actor_line", "actor_action"}
        for block in scene_blocks
        if isinstance(block, dict)
    ) or bool(primary_responder_id)

    initiatives = []
    if primary_responder_id:
        initiatives.append(
            {
                "actor_id": primary_responder_id,
                "intent": "live_runtime_generated_response",
                "allowed_block_types": ["actor_line", "actor_action"],
                "target_actor_id": human_actor_id or None,
                "passivity_risk": "low",
            }
        )
    for actor_id in secondary_responder_ids:
        initiatives.append(
            {
                "actor_id": actor_id,
                "intent": "live_runtime_secondary_response",
                "allowed_block_types": ["actor_line", "actor_action"],
                "target_actor_id": human_actor_id or None,
                "passivity_risk": "low",
            }
        )

    return {
        "contract": "scene_turn_envelope.v2",
        "content_module_id": session.module_id,
        "runtime_profile_id": str(_runtime_profile_id_from_projection(proj) or session.module_id),
        "runtime_module_id": str(proj.get("runtime_module_id") or "solo_story_runtime"),
        "session_output_language": session.session_output_language,
        "player_role_display_name": _role_display_name(
            human_actor_id=human_actor_id or None,
            selected_player_role=selected_player_role or None,
        ),
        "selected_player_role": selected_player_role,
        "human_actor_id": human_actor_id,
        "npc_actor_ids": sorted(npc_actor_ids),
        "npc_agency_plan": {
            "contract": "npc_agency_plan.v1",
            "turn_number": turn_number,
            "primary_responder_id": primary_responder_id,
            "secondary_responder_ids": secondary_responder_ids,
            "npc_initiatives": initiatives,
        },
        "visible_scene_output": {
            "contract": "visible_scene_output.blocks.v1",
            "blocks": [dict(block) for block in scene_blocks],
        },
        "diagnostics": {
            "live_dramatic_scene_simulator": {
                "status": "not_invoked_live_graph_primary",
                "invoked": False,
                "entrypoint": "story.turn.execute",
                "decision_count": 0,
                "output_contract": "visible_scene_output.blocks.v1",
                "scene_block_count": len(scene_blocks),
                "visible_actor_response_present": visible_actor_response_present,
                "legacy_blob_used": False,
                "story_session_id": session.session_id,
                "turn_number": turn_number,
                "input_hash": "",
                "output_hash": "",
            },
            "npc_agency": {
                "primary_responder_id": primary_responder_id,
                "secondary_responder_ids": secondary_responder_ids,
                "visible_actor_response_present": visible_actor_response_present,
                "npc_agency_plan_count": len(initiatives),
            },
            "actor_lane_enforcement": {
                "human_actor_id": human_actor_id,
                "ai_allowed_actor_ids": sorted(ai_allowed_actor_ids),
                "ai_forbidden_actor_ids": ai_forbidden_actor_ids,
                "validation_ran_before_commit": True,
            },
            "phase_cost": {
                "phase": "live_runtime_graph_projection",
                "billing_mode": "included_in_model_invoke",
                "token_source": "model_generation",
                "billable": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "provider": "world_engine",
                "model": "live_runtime_graph_projection",
                "currency": "USD",
                "pricing_source": "included_in_model_invoke",
                "latency_ms": None,
                "decision_count": 0,
                "scene_block_count": len(scene_blocks),
                "visible_actor_response_present": visible_actor_response_present,
            },
        },
    }


def _player_input_scene_blocks_for_story_window(
    *,
    session_id: str,
    turn_number: Any,
    raw_input: str,
    session_output_language: str,
    human_actor_id: str | None = None,
    interpreted_input: dict[str, Any] | None = None,
    module_id: str | None = None,
) -> list[dict[str, Any]]:
    """MVP5 cumulative transcript: visible player line for the story shell.

    When ``human_actor_id`` is bound (canonical solo path), **always** emit **two**
    cards: ``player_input`` (verbatim typing, italic shell lane) then
    ``player_input_outcome`` (diegetic attributed line for the selected human actor).

    Imperative greetings to a named actor still use the scripted polite
    outcome line for the second card; all other inputs use ``_goc_player_attributed_visible_text``.

    Without a human actor id (legacy / non-solo), a single ``player_input`` block
    with speaker *Du* / *You* is emitted.

    Player text is not part of runtime ``spoken_lines`` (human lane is filtered from
    scene envelope). Story-window entries must still carry ``scene_blocks`` so backend
    ``_cumulative_scene_blocks_from_story_window`` can replay the full transcript.
    """
    text = str(raw_input or "").strip()
    if not text:
        return []
    lang = str(session_output_language or "de").strip().lower()
    exp_lang = lang[:2] or "de"
    mid = (module_id or GOD_OF_CARNAGE_MODULE_ID).strip()
    root = _goc_content_modules_root()
    turn_token = str(turn_number).strip() if turn_number is not None else "0"
    hid = str(human_actor_id or "").strip()
    if hid:
        canon = str(canonicalize_goc_actor_id(hid) or hid).strip()
        name = _goc_shell_actor_firstname(canon)
        interp = interpreted_input if isinstance(interpreted_input, dict) else {}
        # Prefer fine-grained player_input_kind (from rules) over coarse input_kind.
        pik_fine = str(interp.get("player_input_kind") or "").strip().lower()
        ik = pik_fine or str(interp.get("input_kind") or interp.get("kind") or "speech").strip().lower()
        # intent_only / reaction are verbal — keep as speech. ambiguous must NOT become speech.
        if ik in ("intent_only", "reaction"):
            ik = "speech"
        verbatim_line = text
        outcome_line: str
        pair = _goc_greeting_imperative_visible_pair(raw=text, player_shell_name=name, lang=exp_lang)
        if pair and ik in {"speech", "action", "social_nonverbal_action"}:
            verbatim_line, outcome_line = pair[0], pair[1]
        else:
            _, outcome_line = _goc_player_attributed_visible_text(
                raw_input=text,
                human_actor_id=canon,
                session_output_language=exp_lang,
                interpreted_input=interpreted_input,
            )
        delivery = {
            "mode": "typewriter",
            "characters_per_second": 44,
            "pause_before_ms": 0,
            "pause_after_ms": 120,
            "skippable": True,
        }
        pik_lane = str(interp.get("player_input_kind") or interp.get("kind") or "speech").strip().lower()
        render_hints = {"player_input_kind": pik_lane}
        player_capability = {
            "action": PLAYER_ACTION_REQUEST,
            "movement_action": PLAYER_MOVEMENT_REQUEST,
            "object_interaction": PLAYER_OBJECT_INTERACTION_REQUEST,
            "perception": PLAYER_PERCEPTION_REQUEST,
            "perception_action": PLAYER_PERCEPTION_REQUEST,
            "mixed": PLAYER_ACTION_REQUEST,
            "question": PLAYER_SPEECH_REQUEST,
            "speech": PLAYER_SPEECH_REQUEST,
        }.get(pik_lane, "player.input")
        out_blocks: list[dict[str, Any]] = []
        for suffix, line, bt in (
            ("", verbatim_line, "player_input"),
            ("-outcome", outcome_line, "player_input_outcome"),
        ):
            cleaned, _partial = sanitize_visible_block_text(
                line,
                block_type=bt,
                speaker_label=name,
                actor_id=canon,
                expected_language=exp_lang,
            )
            if cleaned:
                out_blocks.append(
                    {
                        "id": f"{session_id}-turn-{turn_token}-player-input{suffix}",
                        "block_type": bt,
                        "speaker_label": name,
                        "actor_id": canon,
                        "target_actor_id": None,
                        "text": cleaned,
                        "delivery": delivery,
                        "source": "player_input",
                        "render_hints": render_hints,
                        "origin_aspect": ASPECT_INPUT,
                        "origin_beat_id": None,
                        "origin_capability": player_capability,
                        "authority_owner": "player",
                        "expected_owner": "player",
                        "actual_owner": "player",
                        "canonical_turn_id": f"{session_id}:turn:{turn_token}",
                        "evidence_role": EVIDENCE_SUPPORTING,
                    }
                )
        if out_blocks:
            return out_blocks
    speaker_label = resolve_string(mid, "player_shell.second_person", exp_lang, content_modules_root=root)
    return [
        {
            "id": f"{session_id}-turn-{turn_token}-player-input",
            "block_type": "player_input",
            "speaker_label": speaker_label,
            "actor_id": None,
            "target_actor_id": None,
            "text": text,
            "delivery": {
                "mode": "typewriter",
                "characters_per_second": 44,
                "pause_before_ms": 0,
                "pause_after_ms": 120,
                "skippable": True,
            },
            "source": "player_commit",
            "origin_aspect": ASPECT_INPUT,
            "origin_beat_id": None,
            "origin_capability": "player.input",
            "authority_owner": "player",
            "expected_owner": "player",
            "actual_owner": "player",
            "canonical_turn_id": f"{session_id}:turn:{turn_token}",
            "evidence_role": EVIDENCE_SUPPORTING,
        }
    ]


def _story_window_entries_for_session(session: StorySession) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for event in session.diagnostics:
        if not isinstance(event, dict):
            continue
        turn_number = event.get("turn_number")
        turn_kind = str(event.get("turn_kind") or "player").strip() or "player"
        commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
        consequences = commit.get("committed_consequences")
        consequence_lines = [str(item) for item in consequences] if isinstance(consequences, list) else []
        bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
        spoken_lines = _coerce_visible_text_lines(bundle.get("spoken_lines"))
        action_lines = _coerce_visible_text_lines(bundle.get("action_lines"))
        render_support = bundle.get("render_support") if isinstance(bundle.get("render_support"), dict) else None
        authority = event.get("committed_turn_authority") if isinstance(event.get("committed_turn_authority"), dict) else {}
        validation = event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {}
        runtime_governance_surface = (
            event.get("runtime_governance_surface")
            if isinstance(event.get("runtime_governance_surface"), dict)
            else {}
        )
        planner = commit.get("planner_truth") if isinstance(commit.get("planner_truth"), dict) else {}
        social_summary = (
            planner.get("social_state_summary")
            if isinstance(planner.get("social_state_summary"), dict)
            else {}
        )
        dramatic_context = (
            event.get("dramatic_context_summary")
            if isinstance(event.get("dramatic_context_summary"), dict)
            else {}
        )
        story_dramatic_context = _story_window_dramatic_context(dramatic_context)
        actor_turn_summary = (
            event.get("actor_turn_summary")
            if isinstance(event.get("actor_turn_summary"), dict)
            else {}
        )
        if not actor_turn_summary and story_dramatic_context:
            actor_turn_summary = {
                "contract": "actor_turn_summary.v1",
                "primary_responder_id": story_dramatic_context.get("responder_id"),
                "secondary_responder_ids": story_dramatic_context.get("secondary_responder_ids") or [],
                "spoken_line_count": story_dramatic_context.get("spoken_line_count") or len(spoken_lines),
                "action_line_count": story_dramatic_context.get("action_line_count") or len(action_lines),
                "initiative_summary": story_dramatic_context.get("initiative_summary") or {},
                "last_actor_outcome_summary": story_dramatic_context.get("last_actor_outcome_summary"),
            }
        authority_summary = {
            "authority_record_version": authority.get("authority_record_version"),
            "committed_scene_id": authority.get("committed_scene_id") or commit.get("committed_scene_id"),
            "validation_status": authority.get("validation_status") or validation.get("status"),
            "commit_applied": authority.get("commit_applied"),
            "quality_class": authority.get("quality_class"),
            "degradation_signals": authority.get("degradation_signals") or [],
            "degradation_summary": authority.get("degradation_summary"),
            "selected_scene_function": event.get("selected_scene_function"),
            "experiment_preview": event.get("experiment_preview"),
            "visibility_class_markers": event.get("visibility_class_markers") or [],
            "failure_markers": event.get("failure_markers") or [],
            "social_state_fingerprint": social_summary.get("fingerprint"),
            "social_risk_band": social_summary.get("social_risk_band"),
            "social_continuity_status": social_summary.get("social_continuity_status"),
            "dramatic_context": story_dramatic_context,
        }

        if turn_kind != "opening":
            raw_input = str(event.get("raw_input") or "").strip()
            if raw_input:
                proj_sw = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
                hid_sw = str(proj_sw.get("human_actor_id") or "").strip()
                interp_sw = event.get("interpreted_input") if isinstance(event.get("interpreted_input"), dict) else {}
                role_sw = str(proj_sw.get("selected_player_role") or "").strip()
                pdn = goc_player_role_display_name(role_sw) if role_sw else None
                player_blocks = _player_input_scene_blocks_for_story_window(
                    session_id=session.session_id,
                    turn_number=turn_number,
                    raw_input=raw_input,
                    session_output_language=session.session_output_language,
                    human_actor_id=hid_sw or None,
                    interpreted_input=interp_sw,
                    module_id=session.module_id,
                )
                _mid_sw = str(session.module_id or GOD_OF_CARNAGE_MODULE_ID).strip() or GOD_OF_CARNAGE_MODULE_ID
                _lang_sw = str(session.session_output_language or "de").strip().lower()[:2] or "de"
                _second = resolve_string(
                    _mid_sw,
                    "player_shell.second_person",
                    _lang_sw,
                    content_modules_root=_goc_content_modules_root(),
                )
                player_entry: dict[str, Any] = {
                    "entry_id": f"{session.session_id}:{turn_number}:player",
                    "kind": "player_turn",
                    "role": "player",
                    "speaker": pdn if pdn else _second,
                    "turn_number": turn_number,
                    "text": raw_input,
                    "source": "player_input",
                }
                if player_blocks:
                    player_entry["scene_blocks"] = player_blocks
                    player_entry["text"] = str(player_blocks[0].get("text") or raw_input).strip() or raw_input
                entries.append(player_entry)

        visible_lines = _visible_lines_from_turn_event(event)
        scene_blocks = _scene_blocks_from_turn_event(event)
        quality_class, degradation_signals, degradation_summary = _canonical_quality_fields_from_surfaces(
            runtime_governance_surface=runtime_governance_surface,
            authority_summary=authority_summary,
        )
        degraded = quality_class in {QUALITY_CLASS_DEGRADED, QUALITY_CLASS_FAILED}
        degraded_reasons = list(degradation_signals)
        actor_survival_telemetry = (
            event.get("actor_survival_telemetry")
            if isinstance(event.get("actor_survival_telemetry"), dict)
            else {}
        )
        vitality = (
            actor_survival_telemetry.get("vitality_telemetry_v1")
            if isinstance(actor_survival_telemetry.get("vitality_telemetry_v1"), dict)
            else {}
        )
        operator_hints = (
            actor_survival_telemetry.get("operator_diagnostic_hints")
            if isinstance(actor_survival_telemetry.get("operator_diagnostic_hints"), dict)
            else {}
        )
        passivity_diagnosis = (
            actor_survival_telemetry.get("passivity_diagnosis_v1")
            if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
            else operator_hints
        )
        vitality_summary = {
            "response_present": bool(vitality.get("response_present")),
            "initiative_present": bool(vitality.get("initiative_present")),
            "multi_actor_realized": bool(vitality.get("multi_actor_realized")),
            "sparse_input_recovery_applied": bool(vitality.get("sparse_input_recovery_applied")),
            "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
            "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
        }

        if not visible_lines and not spoken_lines and not action_lines and not consequence_lines:
            continue
        runtime_entry = {
            "entry_id": f"{session.session_id}:{turn_number}:{turn_kind}",
            "kind": "opening" if turn_kind == "opening" else "runtime_response",
            "role": "runtime",
            "speaker": "World of Shadows",
            "turn_number": turn_number,
            "text": "\n\n".join(visible_lines),
            "spoken_lines": spoken_lines,
            "action_lines": action_lines,
            "committed_consequences": consequence_lines,
            "responder_id": story_dramatic_context.get("responder_id"),
            "validation_status": authority_summary.get("validation_status"),
            "quality_class": quality_class,
            "degradation_signals": degradation_signals,
            "degradation_summary": degradation_summary,
            "degraded": degraded,
            "degraded_reasons": degraded_reasons,
            "actor_turn_summary": actor_turn_summary,
            "actor_survival_telemetry": actor_survival_telemetry,
            "vitality_summary": vitality_summary,
            "why_turn_felt_passive": list(passivity_diagnosis.get("why_turn_felt_passive") or []),
            "primary_passivity_factors": list(passivity_diagnosis.get("primary_passivity_factors") or []),
            "source": "authoritative_story_runtime",
            "runtime_governance_surface": runtime_governance_surface,
            "authority_summary": authority_summary,
        }
        if scene_blocks:
            runtime_entry["scene_blocks"] = scene_blocks
        if render_support:
            runtime_entry["render_support"] = render_support
        if story_dramatic_context:
            runtime_entry["dramatic_context_summary"] = story_dramatic_context
        entries.append(runtime_entry)
    return entries


def _beat_to_dramatic_signature(beat: BeatProgression | None) -> dict[str, str] | None:
    """Project a committed beat identity into the graph's prior_dramatic_signature kwarg.

    Values are short strings — the graph treats this as an opaque advisory
    signal, not a full continuity record. When no prior beat exists (first turn
    in a session) the return value is ``None`` so the graph keeps its existing
    first-turn behavior.
    """
    if beat is None:
        return None
    sig: dict[str, str] = {"prior_beat_id": beat.beat_id}
    if beat.pressure_state:
        sig["prior_pressure_state"] = beat.pressure_state
    if beat.pacing_carry_forward:
        sig["prior_pacing_mode"] = beat.pacing_carry_forward
    if beat.advancement_reason:
        sig["prior_beat_advancement_reason"] = beat.advancement_reason
    return sig


def _prior_beat_from_session(session: "StorySession") -> BeatProgression | None:
    """Read the most recent committed BeatProgression from the session's history.

    The commit resolver needs the prior beat to decide whether this turn
    carries continuity forward or advances the beat. History entries are
    ``committed_record`` dicts shaped by ``_finalize_committed_turn``; the
    beat lives on the embedded narrative_commit payload.
    """
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        beat_payload = commit.get("beat_progression")
        if not isinstance(beat_payload, dict):
            continue
        try:
            return BeatProgression.model_validate(beat_payload)
        except Exception:
            continue
    return None


def _prior_social_state_record_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed social-state record from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        summary = planner.get("social_state_summary")
        if not isinstance(summary, dict):
            continue
        record = summary.get("record")
        if isinstance(record, dict) and record:
            return dict(record)
        # Back-compat for any in-progress commit that stored the record fields
        # directly under social_state_summary before the nested "record" shape.
        if {"scene_pressure_state", "social_risk_band"} <= set(summary.keys()):
            return dict(summary)
    return None


def _prior_planner_truth_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest bounded planner-truth snapshot for graph rehydration."""
    allowed_keys = {
        "selected_scene_function",
        "responder_id",
        "primary_responder_id",
        "secondary_responder_ids",
        "responder_scope",
        "function_type",
        "pacing_mode",
        "silence_mode",
        "scene_energy_target",
        "scene_energy_transition",
        "scene_energy_validation",
        "scene_energy_level",
        "pacing_rhythm_state",
        "pacing_rhythm_target",
        "pacing_rhythm_validation",
        "spoken_line_count",
        "action_line_count",
        "initiative_summary",
        "last_actor_outcome_summary",
        "scene_assessment_core",
        "social_outcome",
        "dramatic_direction",
        "social_state_summary",
        "continuity_impacts",
        "realized_secondary_responder_ids",
        "interruption_actor_id",
        "spoken_actor_summaries",
        "action_actor_summaries",
        "social_pressure_shift",
        "carry_forward_tension_notes",
        "initiative_seizer_id",
        "initiative_loser_id",
        "initiative_pressure_label",
        "npc_agency_simulation",
        "npc_long_horizon_state",
        "npc_private_plans",
        "npc_plan_conflict_resolution",
        "npc_agency_closure",
        "unresolved_npc_initiatives",
        "carried_forward_npc_initiatives",
    }
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        snapshot = {
            key: planner.get(key)
            for key in allowed_keys
            if planner.get(key) not in (None, "", [], {})
        }
        if snapshot:
            return snapshot
    return None


def _prior_pacing_rhythm_state_from_session(session: "StorySession") -> dict[str, Any] | None:
    """Read the latest committed pacing-rhythm state from planner truth."""
    for entry in reversed(session.history or []):
        if not isinstance(entry, dict):
            continue
        commit = entry.get("narrative_commit")
        if not isinstance(commit, dict):
            continue
        planner = commit.get("planner_truth")
        if not isinstance(planner, dict):
            continue
        state = planner.get("pacing_rhythm_state")
        if isinstance(state, dict) and state:
            return dict(state)
    return None


def _prior_narrative_thread_state_from_session(
    session: "StorySession",
    *,
    graph_threads: list[dict[str, Any]] | None,
    graph_summary: str | None,
) -> dict[str, Any] | None:
    """Project committed session thread continuity into graph director input."""
    metrics = thread_continuity_metrics(session.narrative_threads)
    if metrics.get("thread_count", 0) <= 0 and not graph_summary and not graph_threads:
        return None
    return {
        "feedback_contract": "narrative_thread_feedback.v1",
        "source": "session.narrative_threads",
        "thread_count": metrics.get("thread_count", 0),
        "dominant_thread_kind": metrics.get("dominant_thread_kind"),
        "thread_pressure_level": metrics.get("thread_pressure_level", 0),
        "thread_pressure_summary": graph_summary or "",
        "active_threads": list(graph_threads or []),
    }


def _compact_context_str(value: Any, *, max_chars: int = 220) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if not text:
        return None
    return text[:max_chars].rstrip()


def _compact_context_list(value: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _compact_context_str(str(item), max_chars=80)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _build_committed_dramatic_context_summary(
    *,
    graph_state: dict[str, Any],
    narrative_commit_payload: dict[str, Any],
    thread_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Merge packaged runtime context with committed planner truth."""
    base = (
        graph_state.get("dramatic_context_summary")
        if isinstance(graph_state.get("dramatic_context_summary"), dict)
        else {}
    )
    planner = (
        narrative_commit_payload.get("planner_truth")
        if isinstance(narrative_commit_payload.get("planner_truth"), dict)
        else {}
    )
    scene_assessment = (
        planner.get("scene_assessment_core")
        if isinstance(planner.get("scene_assessment_core"), dict)
        else {}
    )
    social_summary = (
        planner.get("social_state_summary")
        if isinstance(planner.get("social_state_summary"), dict)
        else {}
    )
    beat = (
        narrative_commit_payload.get("beat_progression")
        if isinstance(narrative_commit_payload.get("beat_progression"), dict)
        else {}
    )
    retrieval = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
    continuity_query = (
        retrieval.get("continuity_query_signal")
        if isinstance(retrieval.get("continuity_query_signal"), dict)
        else {}
    )
    base_responder = base.get("responder") if isinstance(base.get("responder"), dict) else {}
    base_pacing = base.get("pacing") if isinstance(base.get("pacing"), dict) else {}
    base_scene_energy = (
        base.get("scene_energy")
        if isinstance(base.get("scene_energy"), dict)
        else {}
    )
    base_pacing_rhythm = (
        base.get("pacing_rhythm")
        if isinstance(base.get("pacing_rhythm"), dict)
        else {}
    )
    base_scene = (
        base.get("scene_assessment")
        if isinstance(base.get("scene_assessment"), dict)
        else {}
    )
    committed_context = dict(base)
    committed_context.update(
        {
            "contract": "bounded_dramatic_context.v1",
            "source": "narrative_commit.planner_truth+runtime_turn_state",
            "committed_scene_id": narrative_commit_payload.get("committed_scene_id"),
            "commit_reason_code": narrative_commit_payload.get("commit_reason_code"),
            "selected_scene_function": planner.get("selected_scene_function")
            or base.get("selected_scene_function"),
            "function_type": planner.get("function_type") or base.get("function_type"),
            "responder": {
                "responder_id": planner.get("responder_id")
                or planner.get("primary_responder_id")
                or base_responder.get("responder_id"),
                "responder_scope": _compact_context_list(
                    planner.get("responder_scope") or base_responder.get("responder_scope")
                ),
                "secondary_responder_ids": _compact_context_list(
                    planner.get("secondary_responder_ids")
                ),
            },
            "pacing": {
                "pacing_mode": planner.get("pacing_mode") or base_pacing.get("pacing_mode"),
                "silence_mode": planner.get("silence_mode") or base_pacing.get("silence_mode"),
            },
            "scene_energy": {
                "target": planner.get("scene_energy_target")
                if isinstance(planner.get("scene_energy_target"), dict)
                else base_scene_energy.get("target") or {},
                "transition": planner.get("scene_energy_transition")
                if isinstance(planner.get("scene_energy_transition"), dict)
                else base_scene_energy.get("transition") or {},
                "validation_status": (
                    planner.get("scene_energy_validation", {}).get("status")
                    if isinstance(planner.get("scene_energy_validation"), dict)
                    else base_scene_energy.get("validation_status")
                ),
            },
            "pacing_rhythm": {
                "state": planner.get("pacing_rhythm_state")
                if isinstance(planner.get("pacing_rhythm_state"), dict)
                else base_pacing_rhythm.get("state") or {},
                "target": planner.get("pacing_rhythm_target")
                if isinstance(planner.get("pacing_rhythm_target"), dict)
                else base_pacing_rhythm.get("target") or {},
                "validation_status": (
                    planner.get("pacing_rhythm_validation", {}).get("status")
                    if isinstance(planner.get("pacing_rhythm_validation"), dict)
                    else base_pacing_rhythm.get("validation_status")
                ),
            },
            "scene_assessment": {
                "pressure_state": scene_assessment.get("pressure_state")
                or base_scene.get("pressure_state"),
                "thread_pressure_state": scene_assessment.get("thread_pressure_state")
                or base_scene.get("thread_pressure_state"),
                "assessment_summary": _compact_context_str(
                    scene_assessment.get("assessment_summary") or base_scene.get("assessment_summary")
                ),
            },
            "social_state": {
                "fingerprint": social_summary.get("fingerprint"),
                "social_risk_band": social_summary.get("social_risk_band"),
                "responder_asymmetry_code": social_summary.get("responder_asymmetry_code"),
                "social_continuity_status": social_summary.get("social_continuity_status"),
                "prior_social_state_fingerprint": social_summary.get("prior_social_state_fingerprint"),
            },
            "dramatic_outcome": {
                "social_outcome": planner.get("social_outcome"),
                "dramatic_direction": planner.get("dramatic_direction"),
                "continuity_classes": _compact_context_list(
                    [
                        item.get("class") or item.get("continuity_class")
                        for item in (planner.get("continuity_impacts") or [])
                        if isinstance(item, dict)
                    ]
                ),
                "spoken_line_count": planner.get("spoken_line_count"),
                "action_line_count": planner.get("action_line_count"),
                "initiative_summary": planner.get("initiative_summary")
                if isinstance(planner.get("initiative_summary"), dict)
                else {},
                "last_actor_outcome_summary": planner.get("last_actor_outcome_summary"),
            },
            "beat": {
                "beat_id": beat.get("beat_id"),
                "beat_slot": beat.get("beat_slot"),
                "advanced": beat.get("advanced"),
                "advancement_reason": beat.get("advancement_reason"),
                "pressure_state": beat.get("pressure_state"),
            },
            "narrative_threads": {
                "thread_count": thread_metrics.get("thread_count", 0),
                "dominant_thread_kind": thread_metrics.get("dominant_thread_kind"),
                "thread_pressure_level": thread_metrics.get("thread_pressure_level", 0),
            },
            "retrieval_context": {
                "continuity_query_attached": bool(continuity_query.get("attached")),
                "continuity_query_sources": _compact_context_list(continuity_query.get("sources")),
                "retrieval_status": retrieval.get("status"),
                "retrieval_route": retrieval.get("retrieval_route"),
            },
        }
    )
    return committed_context


def _story_window_dramatic_context(dramatic_context: dict[str, Any] | None) -> dict[str, Any]:
    """Project committed dramatic context into the story-window surface."""
    if not isinstance(dramatic_context, dict):
        return {}
    responder = dramatic_context.get("responder") if isinstance(dramatic_context.get("responder"), dict) else {}
    pacing = dramatic_context.get("pacing") if isinstance(dramatic_context.get("pacing"), dict) else {}
    scene_energy = (
        dramatic_context.get("scene_energy")
        if isinstance(dramatic_context.get("scene_energy"), dict)
        else {}
    )
    pacing_rhythm = (
        dramatic_context.get("pacing_rhythm")
        if isinstance(dramatic_context.get("pacing_rhythm"), dict)
        else {}
    )
    scene_energy_target = (
        scene_energy.get("target") if isinstance(scene_energy.get("target"), dict) else {}
    )
    pacing_rhythm_target = (
        pacing_rhythm.get("target") if isinstance(pacing_rhythm.get("target"), dict) else {}
    )
    scene = dramatic_context.get("scene_assessment") if isinstance(dramatic_context.get("scene_assessment"), dict) else {}
    social = dramatic_context.get("social_state") if isinstance(dramatic_context.get("social_state"), dict) else {}
    outcome = dramatic_context.get("dramatic_outcome") if isinstance(dramatic_context.get("dramatic_outcome"), dict) else {}
    beat = dramatic_context.get("beat") if isinstance(dramatic_context.get("beat"), dict) else {}
    threads = dramatic_context.get("narrative_threads") if isinstance(dramatic_context.get("narrative_threads"), dict) else {}
    return {
        "contract": "story_window_dramatic_context.v1",
        "selected_scene_function": dramatic_context.get("selected_scene_function"),
        "function_type": dramatic_context.get("function_type"),
        "responder_id": responder.get("responder_id"),
        "secondary_responder_ids": _compact_context_list(
            responder.get("secondary_responder_ids"), limit=4
        ),
        "pacing_mode": pacing.get("pacing_mode"),
        "pacing_rhythm_cadence": pacing_rhythm_target.get("cadence"),
        "pacing_rhythm_response_shape": pacing_rhythm_target.get("response_shape"),
        "scene_energy_level": scene_energy_target.get("energy_level"),
        "scene_energy_transition": scene_energy_target.get("target_transition"),
        "pressure_state": scene.get("pressure_state"),
        "thread_pressure_state": scene.get("thread_pressure_state"),
        "social_risk_band": social.get("social_risk_band"),
        "social_outcome": outcome.get("social_outcome"),
        "dramatic_direction": outcome.get("dramatic_direction"),
        "spoken_line_count": outcome.get("spoken_line_count"),
        "action_line_count": outcome.get("action_line_count"),
        "initiative_summary": outcome.get("initiative_summary")
        if isinstance(outcome.get("initiative_summary"), dict)
        else {},
        "last_actor_outcome_summary": outcome.get("last_actor_outcome_summary"),
        "continuity_classes": _compact_context_list(outcome.get("continuity_classes"), limit=4),
        "beat_id": beat.get("beat_id"),
        "thread_pressure_level": threads.get("thread_pressure_level"),
        "player_visible": False,
    }


def _player_shell_context_from_dramatic_context(
    dramatic_context: dict[str, Any] | None,
    *,
    session: "StorySession" | None = None,
) -> dict[str, Any]:
    """Project a small player-shell slice from committed dramatic context plus session identity."""
    out: dict[str, Any] = {}
    if isinstance(dramatic_context, dict):
        story_context = _story_window_dramatic_context(dramatic_context)
        if story_context:
            out = {
                "contract": "player_shell_dramatic_context.v1",
                "selected_scene_function": story_context.get("selected_scene_function"),
                "responder_id": story_context.get("responder_id"),
                "secondary_responder_ids": story_context.get("secondary_responder_ids") or [],
                "pacing_mode": story_context.get("pacing_mode"),
                "pacing_rhythm_cadence": story_context.get("pacing_rhythm_cadence"),
                "pressure_state": story_context.get("pressure_state"),
                "thread_pressure_state": story_context.get("thread_pressure_state"),
                "social_risk_band": story_context.get("social_risk_band"),
                "social_outcome": story_context.get("social_outcome"),
                "spoken_line_count": story_context.get("spoken_line_count"),
                "action_line_count": story_context.get("action_line_count"),
                "initiative_summary": story_context.get("initiative_summary") or {},
                "last_actor_outcome_summary": story_context.get("last_actor_outcome_summary"),
                "continuity_classes": story_context.get("continuity_classes") or [],
                "thread_pressure_level": story_context.get("thread_pressure_level"),
                "surface_note": "bounded_player_shell_context_not_operator_diagnostics",
            }
    if session is not None:
        proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        role = str(proj.get("selected_player_role") or "").strip()
        out["session_output_language"] = getattr(session, "session_output_language", None) or "de"
        if role:
            out["selected_player_role"] = role
        pdn = goc_player_role_display_name(role)
        if pdn:
            out["player_role_display_name"] = pdn
        lang = str(out.get("session_output_language") or "de").strip().lower()[:2]
        mid = str(getattr(session, "module_id", None) or GOD_OF_CARNAGE_MODULE_ID).strip() or GOD_OF_CARNAGE_MODULE_ID
        root = _goc_content_modules_root()
        out["npc_responder_label"] = resolve_string(
            mid, "player_shell.npc_responder_label", lang, content_modules_root=root
        )
        if pdn:
            out["player_identity_line"] = resolve_string(
                mid, "player_shell.player_identity_line", lang, content_modules_root=root, role=pdn
            )
        else:
            out["player_identity_line"] = None
        rid = str(out.get("responder_id") or "").strip()
        if rid:
            out["npc_responder_display_name"] = _goc_npc_shell_legal_name(rid)
    return out


def _build_committed_turn_authority(
    *,
    narrative_commit_payload: dict[str, Any],
    graph_state: dict[str, Any],
    committed_scene_id: str,
    turn_number: int,
    dramatic_context_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the bounded single authority record for one committed story turn."""
    graph_commit = graph_state.get("committed_result") if isinstance(graph_state.get("committed_result"), dict) else {}
    validation = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
    continuity = graph_state.get("continuity_impacts") if isinstance(graph_state.get("continuity_impacts"), list) else []
    record = {
        "authority_record_version": "committed_turn_authority.v1",
        "authority": "world_engine_story_runtime",
        "turn_number": turn_number,
        "committed_scene_id": committed_scene_id,
        "validation_status": validation.get("status"),
        "commit_applied": bool(graph_commit.get("commit_applied")),
        "quality_class": graph_state.get("quality_class"),
        "degradation_signals": list(graph_state.get("degradation_signals") or []),
        "degradation_summary": graph_state.get("degradation_summary"),
        "graph_commit": graph_commit,
        "narrative_commit": narrative_commit_payload,
        "continuity_impacts": continuity,
        "truth_sources": {
            "scene_progression": "narrative_commit",
            "dramatic_effects": "graph_commit",
            "social_state": "narrative_commit.planner_truth.social_state_summary",
            "dramatic_context": "dramatic_context_summary",
            "player_visibility": "visible_output_bundle",
        },
    }
    if isinstance(dramatic_context_summary, dict) and dramatic_context_summary:
        record["dramatic_context_summary"] = dramatic_context_summary
    return record


def _build_ldss_scene_envelope(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    player_input: str,
    turn_number: int,
) -> dict[str, Any] | None:
    """Build SceneTurnEnvelope.v2 for God of Carnage solo sessions via LDSS.

    Called from _finalize_committed_turn after actor-lane validation and commit
    have already completed. Returns None for non-solo sessions.
    """
    proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    human_actor_id = str(proj.get("human_actor_id") or "").strip()
    if not human_actor_id:
        return None

    npc_ids = proj.get("npc_actor_ids")
    npc_actor_ids = sorted(
        str(a) for a in (npc_ids or []) if isinstance(a, str) and a.strip()
    )
    selected_player_role = str(proj.get("selected_player_role") or "").strip()

    ldss_input = build_ldss_input_from_session(
        session_id=session.session_id,
        module_id=session.module_id,
        turn_number=turn_number,
        selected_player_role=selected_player_role or human_actor_id,
        human_actor_id=human_actor_id,
        npc_actor_ids=npc_actor_ids,
        player_input=player_input,
        current_scene_id=session.current_scene_id,
        runtime_profile_id=str(_runtime_profile_id_from_projection(proj) or session.module_id),
        content_module_id=session.module_id,
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: pass session output
        # language so the deterministic fallback renders locale-correct opening text.
        session_output_language=getattr(session, "session_output_language", "de") or "de",
    )

    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id=session.session_id,
        turn_number=turn_number,
        runtime_module_id=str(proj.get("runtime_module_id") or "solo_story_runtime"),
    )
    graph_state.setdefault("phase_costs", {})["ldss"] = dict(ldss_output.phase_cost)
    return envelope.to_dict()


# MVP3: NarrativeRuntimeAgent orchestration helpers (called from _finalize_committed_turn)
def _orchestrate_narrative_agent(
    manager: "StoryRuntimeManager",
    session_id: str,
    ldss_output: dict[str, Any] | None,
    runtime_state: dict[str, Any],
    dramatic_signature: dict[str, Any],
    narrative_threads: list[dict[str, Any]],
    turn_number: int,
    trace_id: str | None = None,
    narrator_packet: dict[str, Any] | None = None,
) -> bool:
    """
    Start NarrativeRuntimeAgent streaming narrator blocks (Phase 3).

    Called after LDSS execution. Creates agent, marks streaming as active.
    Returns True if orchestration started, False if LDSS output not available.
    """
    if not ldss_output or not ldss_output.get("npc_agency_plan"):
        return False

    npc_agency_plan = ldss_output.get("npc_agency_plan", {})

    # Create agent input from committed state
    agent_input = NarrativeRuntimeAgentInput(
        runtime_state=runtime_state,
        npc_agency_plan=npc_agency_plan,
        dramatic_signature=dramatic_signature,
        narrative_threads=narrative_threads or [],
        session_id=session_id,
        turn_number=turn_number,
        trace_id=trace_id,
        enable_langfuse_tracing=manager._get_tracing_config(session_id),
        narrator_packet=dict(narrator_packet) if isinstance(narrator_packet, dict) else {},
    )

    # Create and store agent with input for streaming endpoint to access
    agent = NarrativeRuntimeAgent()
    agent.current_input = agent_input  # Store for streaming endpoint
    manager.narrative_agents[session_id] = agent
    manager.input_queues[session_id] = []
    manager._narrative_streaming_active[session_id] = True

    return True


def _check_ruhepunkt_signal(
    manager: "StoryRuntimeManager",
    session_id: str,
    agent: NarrativeRuntimeAgent | None = None,
) -> bool:
    """
    Check if NarrativeRuntimeAgent has signaled ruhepunkt (rest point).

    Ruhepunkt = remaining NPC initiatives = 0, input can be processed.
    Returns True if ruhepunkt reached, False otherwise.
    """
    if not agent:
        agent = manager.narrative_agents.get(session_id)

    if not agent:
        return False

    # In MVP3, ruhepunkt is signaled when motivation analysis shows 0 remaining initiatives
    # This is a simplified check - full implementation in Phase 4-5 involves
    # streaming state from the agent
    return manager._narrative_streaming_active.get(session_id, False) is False


def _process_input_queue(
    manager: "StoryRuntimeManager",
    session_id: str,
) -> list[str]:
    """
    Process queued player inputs after ruhepunkt signal.

    Returns list of queued inputs that should be processed next.
    Clears queue after returning.
    """
    queue = manager.input_queues.get(session_id, [])
    if queue:
        manager.input_queues[session_id] = []
    return queue


class StoryRuntimeManager:
    def __init__(
        self,
        *,
        registry: ModelRegistry | None = None,
        adapters: dict[str, BaseModelAdapter] | None = None,
        retriever: Any | None = None,
        context_assembler: Any | None = None,
        session_store: JsonStorySessionStore | None = None,
        branching_tree_store: JsonBranchingTreeStore | None = None,
        branch_timeline_store: JsonBranchTimelineStore | None = None,
        callback_web_store: JsonCallbackWebStore | None = None,
        consequence_cascade_store: JsonConsequenceCascadeStore | None = None,
        governed_runtime_config: dict[str, Any] | None = None,
        metrics: StoryRuntimeMetrics | None = None,
    ) -> None:
        self.sessions: dict[str, StorySession] = {}
        self._session_store = session_store
        self._branching_tree_store = branching_tree_store
        self._branch_timeline_store = branch_timeline_store
        self._callback_web_store = callback_web_store
        self._consequence_cascade_store = consequence_cascade_store
        self._branching_trees: dict[str, dict[str, Any]] = {}
        self._branch_timelines: dict[str, dict[str, Any]] = {}
        self._callback_webs: dict[str, dict[str, Any]] = {}
        self._consequence_cascades: dict[str, dict[str, Any]] = {}
        self._branching_simulation_session_ids: set[str] = set()
        self._session_turn_locks: dict[str, threading.Lock] = {}
        self._session_locks_guard = threading.Lock()
        self.repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
        self.metrics = metrics or StoryRuntimeMetrics()
        self._governed_runtime_config: dict[str, Any] | None = None
        # ``_authority_version`` increments every time runtime components are
        # (re)applied — on initial construction and on ``reload_runtime_config``.
        # Each committed turn records the authority version it ran under, so
        # operators can prove that reload / promotion / rollback actually
        # reached the live turn path rather than merely refreshing loader state.
        self._authority_version: int = 0
        self._authority_applied_at_iso: str | None = None
        self._runtime_config_status: dict[str, Any] = {
            "source": "default_registry",
            "config_version": None,
            "last_reload_ok": None,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": False,
        }
        self.turn_graph: RuntimeTurnGraphExecutor | None = None
        # MVP3: Narrative agent orchestration (streaming narrator blocks)
        self.narrative_agents: dict[str, NarrativeRuntimeAgent] = {}
        self.input_queues: dict[str, list[str]] = {}  # session_id -> list of queued player inputs
        self._narrative_streaming_active: dict[str, bool] = {}  # session_id -> is narrator streaming?
        # Isolated tests inject custom adapters/registry; skip Turn-0 graph opening there (fixtures are not
        # full GoC-shaped). Production and API tests construct the manager without injected adapters.
        self._skip_graph_opening_on_create = registry is not None or adapters is not None
        if registry is not None and adapters is not None:
            self.registry = registry
            self.routing = RoutingPolicy(self.registry)
            self.adapters = adapters
            self._runtime_config_status = {
                "source": "injected_test_components",
                "config_version": None,
                "last_reload_ok": True,
                "route_count": 0,
                "model_count": len(self.registry.all()),
                "live_execution_blocked": False,
            }
        elif adapters is not None:
            # Tests often pass custom adapters without a registry; do not let
            # ``_apply_runtime_components`` overwrite them with defaults.
            components = build_governed_story_runtime_components(governed_runtime_config)
            if components is not None:
                reg, rout, _ = components
                self.registry = reg
                self.routing = rout
                self.adapters = adapters
                self._governed_runtime_config = dict(governed_runtime_config or {})
                self._runtime_config_status = {
                    "source": "governed_runtime_config_with_injected_adapters",
                    "config_version": (governed_runtime_config or {}).get("config_version"),
                    "last_reload_ok": True,
                    "route_count": len((governed_runtime_config or {}).get("routes") or []),
                    "model_count": len(self.registry.all()),
                    "live_execution_blocked": False,
                }
            elif governed_runtime_config is None:
                self.registry = build_default_registry()
                self.routing = RoutingPolicy(self.registry)
                self.adapters = adapters
                self._runtime_config_status = {
                    "source": "injected_test_components",
                    "config_version": None,
                    "last_reload_ok": True,
                    "route_count": 0,
                    "model_count": len(self.registry.all()),
                    "live_execution_blocked": False,
                }
            else:
                self._governed_runtime_config = (
                    dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
                )
                # Escape hatch removed: always fail-closed when config is invalid/missing
                self.registry = ModelRegistry()
                self.routing = BlockedLiveStoryRoutingPolicy()
                self.adapters = adapters
                self._runtime_config_status = {
                    "source": "governed_config_invalid_or_missing",
                    "config_version": self._governed_runtime_config.get("config_version")
                    if isinstance(self._governed_runtime_config, dict)
                    else None,
                    "last_reload_ok": False,
                    "route_count": 0,
                    "model_count": 0,
                    "live_execution_blocked": True,
                    "live_execution_block_reason": "injected_adapters_without_governed_config",
                }
        else:
            self._apply_runtime_components(governed_runtime_config)
        # Record the initial authority binding that will shape the first live turn.
        self._bump_authority_version()
        if retriever is None or context_assembler is None:
            default_retriever, default_assembler, corpus = build_runtime_retriever(self.repo_root)
            self.retriever = retriever or default_retriever
            self.context_assembler = context_assembler or default_assembler
            self.retrieval_corpus = corpus
        else:
            self.retriever = retriever
            self.context_assembler = context_assembler
            self.retrieval_corpus = None
        self.capability_registry = create_default_capability_registry(
            retriever=self.retriever,
            assembler=self.context_assembler,
            repo_root=self.repo_root,
        )
        # Injected adapters imply an isolated test or custom stack that expects
        # the full retrieve→model path (e.g. RAG + CaptureAdapter). Production
        # sessions use governed components only (adapters parameter None).
        self._action_resolution_short_path_enabled = adapters is None
        self._rebuild_turn_graph()
        if self._session_store is not None:
            for _sid, raw in self._session_store.load_all_raw().items():
                try:
                    loaded = story_session_from_payload(raw)
                    self.sessions[loaded.session_id] = loaded
                    with self._session_locks_guard:
                        self._session_turn_locks.setdefault(loaded.session_id, threading.Lock())
                except Exception:
                    continue
        if self._branching_tree_store is not None:
            for tree_id, raw in self._branching_tree_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._branching_trees[tree_id] = raw
        if self._branch_timeline_store is not None:
            for timeline_id, raw in self._branch_timeline_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._branch_timelines[timeline_id] = raw
        if self._callback_web_store is not None:
            for callback_web_id, raw in self._callback_web_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._callback_webs[callback_web_id] = raw
        if self._consequence_cascade_store is not None:
            for cascade_id, raw in self._consequence_cascade_store.load_all_raw().items():
                if isinstance(raw, dict):
                    self._consequence_cascades[cascade_id] = raw

    def _session_turn_lock(self, session_id: str) -> threading.Lock:
        with self._session_locks_guard:
            return self._session_turn_locks.setdefault(session_id, threading.Lock())

    def _persist_session(self, session: StorySession) -> None:
        if session.session_id in self._branching_simulation_session_ids:
            return
        if self._session_store is None:
            return
        self._session_store.save(session.session_id, story_session_to_payload(session))

    def _persist_branching_tree_record(self, record: dict[str, Any]) -> dict[str, Any]:
        tree_id = str(record.get("tree_id") or "").strip()
        if not tree_id:
            raise ValueError("branching_tree_missing_id")
        self._branching_trees[tree_id] = copy.deepcopy(record)
        if self._branching_tree_store is not None:
            self._branching_tree_store.save(tree_id, record)
        return copy.deepcopy(record)

    def _persist_branch_timeline_record(self, record: dict[str, Any]) -> dict[str, Any]:
        timeline_id = str(record.get("timeline_id") or "").strip()
        if not timeline_id:
            raise ValueError("branch_timeline_missing_id")
        self._branch_timelines[timeline_id] = copy.deepcopy(record)
        if self._branch_timeline_store is not None:
            self._branch_timeline_store.save(timeline_id, record)
        return copy.deepcopy(record)

    def _persist_callback_web_record(self, record: dict[str, Any]) -> dict[str, Any]:
        callback_web_id = str(record.get("callback_web_id") or "").strip()
        if not callback_web_id:
            raise ValueError("callback_web_missing_id")
        self._callback_webs[callback_web_id] = copy.deepcopy(record)
        if self._callback_web_store is not None:
            self._callback_web_store.save(callback_web_id, record)
        return copy.deepcopy(record)

    def _persist_consequence_cascade_record(self, record: dict[str, Any]) -> dict[str, Any]:
        cascade_id = str(record.get("cascade_id") or "").strip()
        if not cascade_id:
            raise ValueError("consequence_cascade_missing_id")
        self._consequence_cascades[cascade_id] = copy.deepcopy(record)
        sid = str(record.get("story_session_id") or "").strip()
        if sid in self._branching_simulation_session_ids:
            return copy.deepcopy(record)
        if self._consequence_cascade_store is not None:
            self._consequence_cascade_store.save(cascade_id, record)
        return copy.deepcopy(record)

    # MVP3: Narrative agent configuration and input queue management
    def _get_tracing_config(self, session_id: str) -> bool:
        """Get Langfuse tracing readiness from the runtime adapter."""
        try:
            return LangfuseAdapter.get_instance().is_enabled()
        except Exception:
            logger.debug("Langfuse tracing config unavailable for session %s", session_id, exc_info=True)
            return False

    def queue_player_input(self, session_id: str, player_input: str) -> None:
        """Queue player input while narrator is streaming."""
        if session_id not in self.input_queues:
            self.input_queues[session_id] = []
        self.input_queues[session_id].append(player_input)

    def get_queued_inputs(self, session_id: str) -> list[str]:
        """Get and clear queued player inputs after ruhepunkt signal."""
        queue = self.input_queues.get(session_id, [])
        if queue:
            self.input_queues[session_id] = []
        return queue

    def is_narrative_streaming(self, session_id: str) -> bool:
        """Check if narrator is currently streaming for session."""
        return self._narrative_streaming_active.get(session_id, False)

    def _max_self_correction_attempts(self) -> int:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        try:
            v = int(settings.get("max_self_correction_attempts", settings.get("max_retry_attempts", 3)))
            return max(0, v)
        except Exception:
            return 3

    def _allow_degraded_commit_after_retries(self) -> bool:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        return bool(settings.get("allow_degraded_commit_after_retries", True))

    def _validation_execution_mode(self) -> str:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        mode = str(
            (self._governed_runtime_config or {}).get("validation_execution_mode")
            or settings.get("validation_execution_mode")
            or "schema_plus_semantic"
        ).strip().lower()
        if mode not in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}:
            return "schema_plus_semantic"
        return mode

    def _opening_retry_count(self) -> int:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        try:
            return max(0, int(settings.get("opening_retry_attempts", 2)))
        except Exception:
            return 2

    def _story_runtime_experience_policy(self):
        """Resolve the active Story Runtime Experience policy from governed config.

        Always returns a policy — if the resolved config is missing or the
        section has not been seeded yet (first boot), canonical defaults are
        used so the runtime still packages truthfully in recap mode.
        """
        from ai_stack.story_runtime_experience import (
            extract_policy_from_resolved_config,
        )

        return extract_policy_from_resolved_config(self._governed_runtime_config)

    def _apply_experience_packaging(self, raw_bundle, policy):
        if not isinstance(raw_bundle, dict):
            return raw_bundle
        try:
            from ai_stack.story_runtime_experience_packaging import (
                package_bundle_with_policy,
            )

            return package_bundle_with_policy(raw_bundle, policy)
        except Exception:  # noqa: BLE001 — packaging must not break the turn
            return raw_bundle

    def _apply_runtime_components(self, governed_runtime_config: dict[str, Any] | None) -> None:
        components = build_governed_story_runtime_components(governed_runtime_config)
        if components is not None:
            reg, rout, adp = components
            self.registry = reg
            self.routing = rout
            self.adapters = adp
            self._governed_runtime_config = dict(governed_runtime_config or {})
            self._runtime_config_status = {
                "source": "governed_runtime_config",
                "config_version": (governed_runtime_config or {}).get("config_version"),
                "last_reload_ok": True,
                "route_count": len((governed_runtime_config or {}).get("routes") or []),
                "model_count": len((governed_runtime_config or {}).get("models") or []),
                "live_execution_blocked": False,
            }
            self.metrics.incr(
                "runtime_config_apply_success",
                source="governed_runtime_config",
                config_version=(governed_runtime_config or {}).get("config_version"),
            )
            return
        # Escape hatch removed: always fail-closed when config is invalid/missing
        reason = "resolved_config_unusable"
        if not isinstance(governed_runtime_config, dict):
            reason = "resolved_config_missing"
        elif not is_governed_resolved_config_operational(governed_runtime_config):
            reason = "resolved_config_incomplete_or_invalid"
        self._apply_blocked_runtime_components(governed_runtime_config, reason_code=reason)

    def _apply_blocked_runtime_components(
        self, governed_runtime_config: dict[str, Any] | None, *, reason_code: str
    ) -> None:
        """Fail-closed posture: no default registry, no hidden live-capable adapters."""
        self._governed_runtime_config = dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
        self.registry = ModelRegistry()
        self.routing = BlockedLiveStoryRoutingPolicy()
        self.adapters = {}
        self._runtime_config_status = {
            "source": "governed_config_invalid_or_missing",
            "config_version": (governed_runtime_config or {}).get("config_version")
            if isinstance(governed_runtime_config, dict)
            else None,
            "last_reload_ok": False,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": True,
            "live_execution_block_reason": reason_code,
        }
        self.metrics.incr(
            "runtime_config_apply_blocked",
            source="governed_config_invalid_or_missing",
            reason=reason_code,
            config_version=self._runtime_config_status.get("config_version"),
        )

    def _rebuild_turn_graph(self) -> None:
        gen_mode = None
        retrieval_cfg = None
        if isinstance(self._governed_runtime_config, dict):
            gen_mode = str(self._governed_runtime_config.get("generation_execution_mode") or "").strip() or None
            retrieval_cfg = retrieval_config_from_governed(self._governed_runtime_config)
        self.turn_graph = RuntimeTurnGraphExecutor(
            interpreter=interpret_player_input,
            routing=self.routing,
            registry=self.registry,
            adapters=self.adapters,
            retriever=self.retriever,
            assembler=self.context_assembler,
            capability_registry=self.capability_registry,
            max_self_correction_attempts=self._max_self_correction_attempts(),
            allow_degraded_commit_after_retries=self._allow_degraded_commit_after_retries(),
            generation_execution_mode=gen_mode,
            retrieval_config=retrieval_cfg,
            action_resolution_short_path_enabled=getattr(
                self, "_action_resolution_short_path_enabled", True
            ),
        )

    def _bump_authority_version(self) -> None:
        self._authority_version += 1
        self._authority_applied_at_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def reload_runtime_config(self, governed_runtime_config: dict[str, Any] | None) -> dict[str, Any]:
        self._apply_runtime_components(governed_runtime_config)
        self._rebuild_turn_graph()
        self._bump_authority_version()
        return self.runtime_config_status()

    def runtime_config_status(self) -> dict[str, Any]:
        src = str(self._runtime_config_status.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        # Publish a runtime-truth surface so operators can inspect the actual
        # runtime mode, authority source, generation mode, graph mode,
        # validator-lane posture, and prompt-template / commit / schema contract
        # versions. Loader or package state is explicitly not part of this
        # surface (see ``_compose_runtime_truth_surface``).
        truth_surface = self._compose_runtime_truth_surface(governed=governed)
        return {
            **self._runtime_config_status,
            "governed_runtime_active": governed and not bool(self._runtime_config_status.get("live_execution_blocked")),
            "legacy_default_registry_path": src == "default_registry",
            "max_self_correction_attempts": self._max_self_correction_attempts(),
            "allow_degraded_commit_after_retries": self._allow_degraded_commit_after_retries(),
            "metrics": self.metrics.summary(),
            # Authority-binding identity. Monotonically increments on every
            # successful or blocked apply so post-reload live turns can prove
            # they ran under the new authority rather than stale registry /
            # routing components.
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
            "runtime_truth_surface": truth_surface,
            # Story Runtime Experience truth surface: configured vs effective,
            # degradation markers, and packaging contract version. Operators
            # rely on this rather than the configured row to know whether the
            # requested mode is actually honored.
            "story_runtime_experience": self._story_runtime_experience_policy().to_truth_surface(),
        }

    def _compose_runtime_truth_surface(self, *, governed: bool) -> dict[str, Any]:
        """Describe the *active* runtime lane for operator diagnostics.

        Unlike the top-level governance fields on ``runtime_config_status()``,
        which describe the governed configuration state, this block describes
        what is actually running: the authority source, the generation and
        graph modes, the active route family, the live validator lane, and
        the commit / schema contract versions. Each key answers one operator
        question directly; nothing here reports loaded or preview state.
        """
        langgraph_available = True
        langgraph_import_error: str | None = None
        try:
            from ai_stack.langgraph_runtime import LANGGRAPH_IMPORT_ERROR

            if LANGGRAPH_IMPORT_ERROR is not None:
                langgraph_available = False
                langgraph_import_error = type(LANGGRAPH_IMPORT_ERROR).__name__
        except Exception as exc:  # pragma: no cover — defensive
            langgraph_available = False
            langgraph_import_error = type(exc).__name__

        graph = self.turn_graph
        graph_executor_class = type(graph).__name__ if graph is not None else None
        runtime_graph_mode = (
            "langgraph_runtime_turn_graph" if graph_executor_class == "RuntimeTurnGraphExecutor" else
            "injected_test_graph" if graph is not None else
            "no_graph"
        )

        cfg = self._governed_runtime_config if isinstance(self._governed_runtime_config, dict) else {}
        raw_gen_mode = str(cfg.get("generation_execution_mode") or "").strip().lower()
        generation_execution_mode = raw_gen_mode or ("governed_default_mock_only" if governed else "unknown")
        expected_live_route_family = "narrative_live_generation_global"
        routes = cfg.get("routes") if isinstance(cfg.get("routes"), list) else []
        active_route_ids = sorted(
            {
                str(r.get("route_id") or "").strip()
                for r in routes
                if isinstance(r, dict) and str(r.get("route_id") or "").strip()
            }
        )
        expected_route_available = expected_live_route_family in active_route_ids

        authority_source = (
            "governed_resolved_runtime_config" if governed else
            ("blocked_no_authoritative_config" if self._runtime_config_status.get("live_execution_blocked") else "injected_test_components")
        )

        # Prompt-template source — which catalog produced the live prompt.
        prompt_template_source = "unknown"
        prompt_template_fallback = False
        try:
            from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog  # noqa: F401

            prompt_template_source = "canonical_prompt_catalog"
        except Exception:
            prompt_template_source = "hardcoded_bridges_fallback"
            prompt_template_fallback = True

        return {
            "authority_source": authority_source,
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
            "runtime_graph_mode": runtime_graph_mode,
            "graph_executor_class": graph_executor_class,
            "langgraph_available": langgraph_available,
            "langgraph_import_error_class": langgraph_import_error,
            "generation_execution_mode": generation_execution_mode,
            "expected_live_route_family": expected_live_route_family,
            "expected_live_route_available": expected_route_available,
            "active_route_ids": active_route_ids,
            "prompt_template_source": prompt_template_source,
            "prompt_template_fallback_in_effect": prompt_template_fallback,
            "commit_contract_version": "story_narrative_commit_record.v4",
            "runtime_output_schema_version": "runtime_turn_structured_output_v2",
            "live_player_governance_enforced": self._live_governance_enforced_for_player_paths(),
            "module_scope_advertised": f"module_specific_{GOD_OF_CARNAGE_MODULE_ID}_only",
            "module_scope_truth": _module_scope_truth(),
            # The canonical live validator lane. The operator endpoint
            # POST /internal/narrative/runtime/validate-and-recover is a
            # separate introspection lane (it reports
            # validator_lane="operator_introspection_validate_and_recover")
            # and is deliberately not part of the live player-turn path.
            "live_validator_lane": "goc_rule_engine_v1",
            "live_validator_stages": [
                "run_validation_seam",
                "dramatic_effect_gate",
                "decide_playability_recovery",
                "self_correction_loop",
            ],
            "operator_introspection_validator_endpoint": "/api/internal/narrative/runtime/validate-and-recover",
            "truth_surface_note": (
                "These fields describe the active live runtime lane. Loaded package "
                "or preview state is not live authority; see "
                "/api/internal/narrative/runtime/state for loader state."
            ),
        }

    def _live_governance_enforced_for_player_paths(self) -> bool:
        # Escape hatch removed: governance always enforced except for test injection paths
        src = str(self._runtime_config_status.get("source") or "")
        if (
            os.getenv("FLASK_ENV") == "test"
            and self.turn_graph is not None
            and not isinstance(self.turn_graph, RuntimeTurnGraphExecutor)
        ):
            return False
        return not src.startswith("injected")

    def _assert_live_player_governance(self) -> None:
        if not self._live_governance_enforced_for_player_paths():
            return
        st = self._runtime_config_status
        src = str(st.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        if st.get("live_execution_blocked") or not governed:
            raise LiveStoryGovernanceError(
                f"LIVE_STORY_RUNTIME_BLOCKED: runtime_source={src!r} live_execution_blocked={st.get('live_execution_blocked')!r}"
            )
        if not str(st.get("config_version") or "").strip():
            raise LiveStoryGovernanceError("LIVE_STORY_RUNTIME_BLOCKED: config_version is missing on governed runtime surface.")

    @staticmethod
    def _extract_actor_lane_context(session: StorySession) -> dict[str, Any] | None:
        """Extract MVP2 actor-lane enforcement context from session runtime_projection.

        Returns a dict with human_actor_id and ai_forbidden_actor_ids when the
        session's runtime_projection includes actor ownership (set by the backend
        when creating a solo story session with a selected_player_role).
        Returns None when actor ownership is absent (non-solo or legacy sessions).
        """
        proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        human_actor_id = str(proj.get("human_actor_id") or "").strip()
        if not human_actor_id:
            return None
        npc_actor_ids = proj.get("npc_actor_ids")
        ai_forbidden = sorted(expand_goc_actor_id_aliases(human_actor_id))
        ai_allowed_set: set[str] = set()
        for actor_id in (npc_actor_ids or []):
            if isinstance(actor_id, str) and actor_id.strip():
                ai_allowed_set.update(expand_goc_actor_id_aliases(actor_id))
        ai_allowed = sorted(ai_allowed_set)
        npc_ids = [str(x).strip() for x in (npc_actor_ids or []) if isinstance(x, str) and str(x).strip()]
        return {
            "human_actor_id": human_actor_id,
            "ai_forbidden_actor_ids": ai_forbidden,
            "ai_allowed_actor_ids": ai_allowed,
            "npc_actor_ids": npc_ids,
            "selected_player_role": str(proj.get("selected_player_role") or "").strip(),
            "actor_lanes": proj.get("actor_lanes") or {},
        }

    def _build_opening_prompt(self, session: StorySession) -> str:
        projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
        scene_id = str(projection.get("start_scene_id") or session.current_scene_id or "opening")
        scenes = projection.get("scenes") if isinstance(projection.get("scenes"), list) else []
        scene_row = next(
            (
                row
                for row in scenes
                if isinstance(row, dict) and str(row.get("scene_id") or row.get("id") or "") == scene_id
            ),
            {},
        )
        scene_name = str(scene_row.get("name") or scene_id)
        scene_desc = str(scene_row.get("description") or "")
        chars = projection.get("character_ids") if isinstance(projection.get("character_ids"), list) else []
        cast = ", ".join(str(c) for c in chars[:8]) if chars else "unknown"
        lang_label = "German" if session.session_output_language == "de" else "English"
        lang_instruction = (
            f"IMPORTANT: Write ALL player-visible narrative in {lang_label}. "
            "Do not switch to French unless quoting in-world French text explicitly marked as a quotation. "
        )
        base = (
            lang_instruction
            + f"Opening turn for module {session.module_id}. "
            f"Establish the starting situation in scene {scene_name} ({scene_id}). "
            f"Scene description: {scene_desc or 'n/a'}. Cast: {cast}. "
            "Write vivid but grounded opening narration within canonical module boundaries. "
            "Set initial dramatic pressure, social posture, and opening narrative threads."
        )
        runtime_profile_id = _runtime_profile_id_from_projection(projection)
        opening_scene_sequence_id = ""
        opening_event_ids: list[str] = []
        opening_must_establish: list[str] = []
        hard_forbidden_reject_on: list[str] = []
        hard_forbidden_recover_on: list[str] = []
        handover = ""
        anchor = "configured opening location and social premise"
        try:
            policy = load_module_runtime_policy(
                module_id=session.module_id,
                runtime_profile_id=runtime_profile_id,
            )
            policy_dict = policy.to_dict()
            opening_policy = (
                policy_dict.get("opening_policy")
                if isinstance(policy_dict.get("opening_policy"), dict)
                else {}
            )
            location_model = (
                policy_dict.get("location_model")
                if isinstance(policy_dict.get("location_model"), dict)
                else {}
            )
            anchor = str(
                location_model.get("narrative_anchor_area_id")
                or location_model.get("setting_id")
                or anchor
            ).strip() or anchor
            opening_scene_sequence_id = str(opening_policy.get("id") or "").strip()
            contract = (
                opening_policy.get("opening_contract")
                if isinstance(opening_policy.get("opening_contract"), dict)
                else {}
            )
            if isinstance(contract, dict):
                opening_must_establish = [
                    str(item).strip()
                    for item in (contract.get("must_establish") or [])
                    if str(item).strip()
                ]
            narrative_events = (
                opening_policy.get("narrative_events")
                if isinstance(opening_policy.get("narrative_events"), list)
                else []
            )
            if isinstance(narrative_events, list):
                opening_event_ids = [
                    str(row.get("id") or "").strip()
                    for row in narrative_events
                    if isinstance(row, dict) and str(row.get("id") or "").strip()
                ]
                for row in narrative_events:
                    if isinstance(row, dict) and row.get("handover_to_scene_phase"):
                        handover = str(row.get("handover_to_scene_phase") or handover).strip() or handover
                        break
            hard_forbidden_policy = (
                policy_dict.get("hard_forbidden_policy")
                if isinstance(policy_dict.get("hard_forbidden_policy"), dict)
                else {}
            )
            detection = (
                hard_forbidden_policy.get("hard_forbidden_detection")
                if isinstance(hard_forbidden_policy.get("hard_forbidden_detection"), dict)
                else {}
            )
            hard_forbidden_reject_on = [
                str(item).strip() for item in (detection.get("reject_on") or []) if str(item).strip()
            ]
            hard_forbidden_recover_on = [
                str(item).strip() for item in (detection.get("recover_on") or []) if str(item).strip()
            ]
        except Exception:
            pass
        human_actor_id = str(projection.get("human_actor_id") or "").strip()
        role_label = human_actor_id if human_actor_id else "the player character"
        handover_clause = (
            f"After the required opening evidence, hand over to scene phase {handover}. "
            if handover
            else "After the required opening evidence, hand over to the configured starting scene. "
        )
        return (
            f"{base}\n\n"
            f"Session opening uses the module runtime policy. Anchor: {anchor}. "
            "Narrator owns opening scenic establishment, role placement, and local context before NPC speech. "
            f"Place {role_label} in the scene without forcing speech, decisions, or private conclusions. "
            "Use separate narrator-visible blocks for distinct opening functions when the policy expects visible evidence. "
            f"{handover_clause}"
            f"Opening knowledge contract {opening_scene_sequence_id or 'opening_scene_sequence'} requires events "
            f"{opening_event_ids} "
            f"and must_establish {opening_must_establish}. "
            'Return "narration_summary" as a list of exactly three strings so opening evidence can be projected into visible blocks. '
            'Emit structured coverage evidence as "opening_event_ids" with the covered event ids; '
            'semantic rule hits, when present, must use "runtime_gate_detections" ids. '
            f"Hard forbidden detection: reject_on={hard_forbidden_reject_on}, recover_on={hard_forbidden_recover_on}. "
            "Apply hard-forbidden rules by their authored ids; narrator owns spatial/premise establishment."
        )

    def _opening_commit_acceptable(self, graph_state: dict[str, Any]) -> bool:
        # Bootstrap policy for opening-turn validation.
        # Opening turns are engine-generated (not player-prompted) and do not require
        # the same committed_result contract as subsequent turns. We enforce validation
        # status and preview placeholder checks, but defer strict commit enforcement.
        # This leniency is surfaced as a degradation signal in canonical_degradation_signals()
        # and impacts quality_class assessment accordingly.
        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            # Log rejection reason for debugging
            self.metrics.incr("opening_rejected", reason=f"status_{val.get('status', 'unknown')}")
            return False

        # Check for preview placeholder (always enforced)
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list):
            joined = "\n".join(str(x) for x in gm)
            if opening_text_contains_preview_placeholder(joined):
                self.metrics.incr("opening_rejected", reason="preview_placeholder")
                return False

        # Accept if validation passed (defer strict commit enforcement)
        self.metrics.incr("opening_accepted")
        return True

    def _visible_narration_present(self, graph_state: dict[str, Any]) -> bool:
        gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
        raw = str(gen.get("content") or gen.get("model_raw_text") or "").strip()
        if raw:
            return True
        bundle = graph_state.get("visible_output_bundle") if isinstance(graph_state.get("visible_output_bundle"), dict) else {}
        gm = bundle.get("gm_narration")
        if isinstance(gm, list) and any(str(x).strip() for x in gm):
            return True
        return False

    def _ldss_opening_fallback_state(
        self,
        graph_state: dict[str, Any],
        *,
        reason: str,
    ) -> dict[str, Any]:
        fallback = dict(graph_state)
        generation = dict(fallback.get("generation") if isinstance(fallback.get("generation"), dict) else {})
        metadata = dict(generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {})
        # Capture primary attempt before LDSS overwrites adapter metadata so operators can
        # tell from trace metadata: primary live route was attempted (e.g. openai
        # gpt-5-mini), it failed (dramatic-effect rejection / no visible narration),
        # the FINAL committed adapter is ldss_fallback. ADR-0033 §13.10.
        prior_adapter = str(metadata.get("adapter") or "").strip()
        primary_metadata: dict[str, Any] = {}
        if prior_adapter and prior_adapter not in {"ldss_fallback", "ldss_deterministic", ""}:
            primary_metadata["primary_attempt_adapter"] = prior_adapter
            prior_model = metadata.get("model")
            if prior_model:
                primary_metadata["primary_attempt_model"] = prior_model
            prior_mode = metadata.get("adapter_invocation_mode")
            if prior_mode:
                primary_metadata["primary_attempt_invocation_mode"] = prior_mode
        routing_state = (
            graph_state.get("routing")
            if isinstance(graph_state.get("routing"), dict)
            else {}
        )
        prior_provider = routing_state.get("selected_provider")
        if prior_provider and "primary_attempt_provider" not in primary_metadata:
            primary_metadata["primary_attempt_provider"] = prior_provider
        prior_selected_model = routing_state.get("selected_model")
        if prior_selected_model and "primary_attempt_selected_model" not in primary_metadata:
            primary_metadata["primary_attempt_selected_model"] = prior_selected_model
        # PRIMARY-PARSER-EVIDENCE-01: pull parser/raw-output evidence from the state key
        # captured in _invoke_model. This survives self-correction overwriting generation.
        pae = graph_state.get("primary_attempt_evidence")
        if isinstance(pae, dict):
            for _k in (
                "primary_attempt_api_success",
                "primary_attempt_parser_error_present",
                "primary_attempt_parser_error",
                "primary_attempt_structured_output_present",
                "primary_attempt_raw_output_sha256",
                "primary_attempt_raw_output_excerpt",
            ):
                if _k in pae:
                    primary_metadata[_k] = pae[_k]
        # Self-correction evidence: attempt_count / final model tried.
        sc = graph_state.get("self_correction")
        if isinstance(sc, dict):
            sc_attempts = sc.get("attempts") or []
            primary_metadata["self_correction_attempted"] = bool(sc_attempts)
            primary_metadata["self_correction_attempt_count"] = len(sc_attempts)
            if sc_attempts:
                first_sc = sc_attempts[0] if isinstance(sc_attempts[0], dict) else {}
                last_sc = sc_attempts[-1] if isinstance(sc_attempts[-1], dict) else {}
                primary_metadata["self_correction_trigger_source"] = first_sc.get("trigger_source")
                primary_metadata["runtime_aspect_failure_before_retry"] = first_sc.get(
                    "runtime_aspect_failure_before_retry"
                )
                primary_metadata["capability_failure_before_retry"] = first_sc.get(
                    "capability_failure_before_retry"
                )
                primary_metadata["self_correction_resolved_failure"] = any(
                    bool(item.get("resolved_failure"))
                    for item in sc_attempts
                    if isinstance(item, dict)
                )
                primary_metadata["self_correction_model"] = last_sc.get("candidate_model")
                primary_metadata["self_correction_success"] = (
                    bool(last_sc.get("success")) and not last_sc.get("parser_error")
                )
            else:
                primary_metadata["self_correction_resolved_failure"] = False
                primary_metadata["self_correction_success"] = False
        fallback["force_ldss_scene_fallback"] = True
        fallback["generation"] = {
            **generation,
            "success": True,
            "error": None,
            "fallback_used": True,
            "metadata": {
                **metadata,
                **primary_metadata,
                "adapter": "ldss_fallback",
                "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                "final_adapter": "ldss_fallback",
                "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                "fallback_reason": reason,
                "ldss_fallback_after_live_opening_failure": True,
                "structured_output": None,
                "live_opening_failure_reason": reason,
            },
        }
        prior_val = (
            graph_state.get("validation_outcome")
            if isinstance(graph_state.get("validation_outcome"), dict)
            else {}
        )
        prior_lane: dict[str, Any] = {}
        nested_lane = prior_val.get("actor_lane_validation")
        if isinstance(nested_lane, dict) and nested_lane:
            prior_lane = dict(nested_lane)
        elif isinstance(graph_state.get("actor_lane_validation"), dict) and graph_state.get(
            "actor_lane_validation"
        ):
            # Graph may publish actor lane on state root as well as under validation_outcome.
            top_lane = graph_state.get("actor_lane_validation")
            if isinstance(top_lane, dict) and top_lane:
                prior_lane = dict(top_lane)
        opening_fallback_validation: dict[str, Any] = {
            "status": "approved",
            "reason": "ldss_fallback_after_live_opening_failure",
            "validator_lane": "opening_fallback_policy_v1",
            "live_opening_failure_reason": reason,
        }
        if prior_lane:
            opening_fallback_validation["actor_lane_validation"] = prior_lane
        fallback["validation_outcome"] = opening_fallback_validation
        fallback["committed_result"] = {
            "commit_applied": True,
            "committed_effects": [
                {
                    "effect_type": "opening_fallback",
                    "description": "LDSS fallback opening used after live opening failed validation.",
                }
            ],
            "reason": "ldss_fallback_after_live_opening_failure",
        }
        fallback_ledger = initialize_runtime_aspect_ledger(
            session_id=str(graph_state.get("session_id") or ""),
            module_id=str(graph_state.get("module_id") or GOD_OF_CARNAGE_MODULE_ID),
            turn_number=int(graph_state.get("turn_number") or 0),
            turn_kind=str(graph_state.get("turn_input_class") or "opening"),
            raw_player_input=None,
            input_kind="opening_fallback",
            trace_id=str(graph_state.get("trace_id") or "") or None,
            runtime_profile_id=str(graph_state.get("runtime_profile_id") or "") or None,
        )
        fallback_ledger = set_aspect_record(
            fallback_ledger,
            ASPECT_VALIDATION,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"ldss_opening_fallback_policy": True},
                actual={
                    "validation_status": "approved",
                    "reason": "ldss_fallback_after_live_opening_failure",
                    "live_opening_failure_reason": reason,
                },
                reasons=["ldss_fallback_after_live_opening_failure"],
                source="opening_fallback_policy",
            ),
        )
        fallback_ledger = set_aspect_record(
            fallback_ledger,
            ASPECT_COMMIT,
            make_aspect_record(
                applicable=True,
                status="passed",
                expected={"commit_allowed_after_opening_fallback": True},
                actual={
                    "commit_applied": True,
                    "reason": "ldss_fallback_after_live_opening_failure",
                },
                reasons=["ldss_fallback_after_live_opening_failure"],
                source="opening_fallback_policy",
            ),
        )
        fallback["turn_aspect_ledger"] = fallback_ledger
        fallback["visible_output_bundle"] = {}
        fallback["quality_class"] = QUALITY_CLASS_DEGRADED
        signals = list(fallback.get("degradation_signals") or [])
        if "ldss_fallback_after_live_opening_failure" not in signals:
            signals.append("ldss_fallback_after_live_opening_failure")
        fallback["degradation_signals"] = signals
        fallback["degradation_summary"] = reason
        return fallback

    def _emit_observability_path_for_event(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        """Langfuse path summary and evidence hooks for any turn-shaped event (ADR-0038 Phase C)."""
        path_summary = _build_langfuse_path_summary(
            session=session,
            graph_state=graph_state,
            event=event,
        )
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: build public
        # action/local-context diagnostics so degraded/fallback paths still expose numeric
        # values rather than silent None.
        diag = _compute_action_consequence_diagnostics(path_summary)
        path_summary["action_consequence_diagnostics"] = diag
        event["observability_path_summary"] = path_summary
        event["action_consequence_diagnostics"] = diag
        event["knowledge_runtime_gates"] = {
            "contract": path_summary.get("knowledge_runtime_gates_contract"),
            "opening_scene_sequence_id": path_summary.get("opening_scene_sequence_id"),
            "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
            "opening_missing_event_ids": path_summary.get("opening_missing_event_ids"),
            "opening_missing_must_establish": path_summary.get("opening_missing_must_establish"),
            "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
            "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
            "hard_forbidden_detection": path_summary.get("hard_forbidden_detection"),
        }
        _emit_langfuse_path_spans(path_summary)
        _emit_langfuse_runtime_aspect_observability(path_summary)
        _emit_langfuse_evidence_observations(
            path_summary=path_summary,
            graph_state=graph_state,
            event=event,
        )

    def _finalize_committed_turn(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        trace_id: str | None,
        commit_turn_number: int,
        player_input: str,
        turn_kind: str | None,
        prior_scene_id: str,
        history_tail: list,
        graph_threads: list[dict[str, Any]] | None,
        graph_summary: str | None,
        host_experience_template: dict[str, Any] | None,
        prior_ci: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        prior_narrative_threads_for_rollback = copy.deepcopy(session.narrative_threads)
        prior_thread_update_trace_for_rollback = copy.deepcopy(session.last_thread_update_trace)
        prior_continuity_impacts_for_rollback = copy.deepcopy(session.prior_continuity_impacts)
        goc_append_continuity_impacts(session.module_id, session.prior_continuity_impacts, graph_state)
        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}
        validation_outcome = (
            graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        )
        turn_lc = TurnLifecycleChain()
        turn_lc.advance("received")
        turn_lc.advance("interpreted")
        prior_beat = _prior_beat_from_session(session)
        narrative_commit = resolve_narrative_commit(
            turn_number=commit_turn_number,
            prior_scene_id=prior_scene_id,
            player_input=player_input,
            interpreted_input=interpreted_input,
            generation=gen,
            runtime_projection=session.runtime_projection,
            graph_state=graph_state,
            prior_beat_progression=prior_beat,
        )
        model_ok = gen.get("success") is True
        turn_lc.advance("generated_or_resolved")
        turn_lc.advance("validated")
        session.current_scene_id = narrative_commit.committed_scene_id
        if isinstance(graph_state.get("environment_state"), dict):
            session.environment_state = dict(graph_state["environment_state"])
        session.narrative_threads, session.last_thread_update_trace = update_narrative_threads(
            prior=session.narrative_threads,
            latest_commit=narrative_commit,
            history_tail=history_tail,
            committed_scene_id=narrative_commit.committed_scene_id,
            turn_number=commit_turn_number,
        )
        turn_lc.advance("committed")
        outcome = "ok" if model_ok and not errors else "degraded"
        actor_survival_telemetry = (
            graph_state.get("actor_survival_telemetry")
            if isinstance(graph_state.get("actor_survival_telemetry"), dict)
            else {}
        )
        vitality_telemetry_v1 = (
            actor_survival_telemetry.get("vitality_telemetry_v1")
            if isinstance(actor_survival_telemetry.get("vitality_telemetry_v1"), dict)
            else None
        )
        passivity_diagnosis_v1 = (
            actor_survival_telemetry.get("passivity_diagnosis_v1")
            if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
            else None
        )

        # Build LLM invocation details from graph_state
        routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
        gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        self_correction = graph_state.get("self_correction") if isinstance(graph_state.get("self_correction"), dict) else {}
        llm_invocation_details = {
            "selected_provider": routing.get("selected_provider"),
            "selected_model": routing.get("selected_model"),
            "adapter_used": gen_meta.get("adapter"),
            "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
            "fallback_stage_reached": routing.get("fallback_stage_reached") or ("graph_fallback_executed" if "fallback_model" in (graph_state.get("nodes_executed") or []) else "primary_only"),
            "fallback_reason": routing.get("fallback_reason"),
            "retry_attempt_count": self_correction.get("attempt_count"),
            "parser_error": gen.get("parser_error"),
            "structured_output_present": gen.get("structured_output") is not None,
            "model_success": model_ok,
        }

        # Build validation details
        validation_details = {
            "status": validation_outcome.get("status"),
            "reason": validation_outcome.get("reason"),
            "dramatic_quality_gate": validation_outcome.get("dramatic_quality_gate"),
        }
        actor_lane_validation = validation_outcome.get("actor_lane_validation") if isinstance(validation_outcome.get("actor_lane_validation"), dict) else {}
        if actor_lane_validation:
            validation_details["actor_lane_validation_status"] = actor_lane_validation.get("status")
            validation_details["actor_lane_validation_reason"] = actor_lane_validation.get("reason")

        # Build commit details
        commit_details = {
            "committed": narrative_commit is not None,
            "degraded": outcome == "degraded",
            "degradation_reason": str(errors[0]) if errors else None,
        }

        # Build retrieval details if available
        retrieval_status = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
        retrieval_details = {
            "status": retrieval_status.get("status"),
            "hit_count": retrieval_status.get("hit_count"),
            "documents_used": retrieval_status.get("documents_used"),
            "retrieval_route": retrieval_status.get("retrieval_route"),
            "profile": retrieval_status.get("profile"),
            "domain": retrieval_status.get("domain"),
            "top_hit_score": retrieval_status.get("top_hit_score"),
            "corpus_fingerprint": retrieval_status.get("corpus_fingerprint"),
            "index_version": retrieval_status.get("index_version"),
        } if retrieval_status else None

        log_story_turn_event(
            trace_id=trace_id,
            story_session_id=session.session_id,
            module_id=session.module_id,
            turn_number=commit_turn_number,
            player_input=player_input,
            outcome=outcome,
            graph_error_count=len(errors),
            quality_class=str(graph_state.get("quality_class") or "") or None,
            degradation_signals=list(graph_state.get("degradation_signals") or []),
            vitality_telemetry=vitality_telemetry_v1,
            passivity_diagnosis=passivity_diagnosis_v1,
            llm_invocation_details=llm_invocation_details,
            validation_details=validation_details,
            commit_details=commit_details,
            retrieval_details=retrieval_details,
        )
        narrative_commit_payload = narrative_commit.model_dump(mode="json")
        beat_payload = (
            narrative_commit_payload.get("beat_progression")
            if isinstance(narrative_commit_payload.get("beat_progression"), dict)
            else {}
        )
        if isinstance(graph_state.get("turn_aspect_ledger"), dict) and beat_payload:
            ledger_for_beat_commit = normalize_runtime_aspect_ledger(graph_state.get("turn_aspect_ledger"))
            aspects_for_beat = ledger_for_beat_commit.get("turn_aspect_ledger")
            beat_record = aspects_for_beat.get(ASPECT_BEAT) if isinstance(aspects_for_beat, dict) else {}
            if isinstance(beat_record, dict):
                graph_state["turn_aspect_ledger"] = set_aspect_record(
                    ledger_for_beat_commit,
                    ASPECT_BEAT,
                    make_aspect_record(
                        applicable=True,
                        status=str(beat_record.get("status") or "partial"),
                        expected=beat_record.get("expected")
                        if isinstance(beat_record.get("expected"), dict)
                        else {},
                        selected=beat_record.get("selected")
                        if isinstance(beat_record.get("selected"), dict)
                        else {"selected_beat_id": beat_payload.get("beat_id")},
                        actual={
                            **(beat_record.get("actual") if isinstance(beat_record.get("actual"), dict) else {}),
                            "committed": True,
                            "committed_beat_id": beat_payload.get("beat_id"),
                            "beat_slot": beat_payload.get("beat_slot"),
                            "advanced": beat_payload.get("advanced"),
                            "advancement_reason": beat_payload.get("advancement_reason"),
                        },
                        reasons=beat_record.get("reasons") if isinstance(beat_record.get("reasons"), list) else [],
                        source="commit",
                        selected_beat=beat_payload.get("beat_id"),
                    ),
                )
        turn_thread_metrics = thread_continuity_metrics(session.narrative_threads)
        dramatic_context_summary = _build_committed_dramatic_context_summary(
            graph_state=graph_state,
            narrative_commit_payload=narrative_commit_payload,
            thread_metrics=turn_thread_metrics,
        )
        committed_turn_authority = _build_committed_turn_authority(
            narrative_commit_payload=narrative_commit_payload,
            graph_state=graph_state,
            committed_scene_id=session.current_scene_id,
            turn_number=commit_turn_number,
            dramatic_context_summary=dramatic_context_summary,
        )
        r_src = str(self._runtime_config_status.get("source") or "")
        governed_active = r_src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"} and not bool(
            self._runtime_config_status.get("live_execution_blocked")
        )
        gov: dict[str, Any] = {
            "source": self._runtime_config_status.get("source"),
            "config_version": self._runtime_config_status.get("config_version"),
            "governed_runtime_active": governed_active,
            "legacy_default_registry_path": r_src == "default_registry",
            "live_execution_blocked": bool(self._runtime_config_status.get("live_execution_blocked")),
            # The authority version records which authority binding shaped this
            # committed turn. ``reload_runtime_config`` bumps the version; a
            # turn committed after reload shows the new value, making the live
            # binding auditable rather than inferred.
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
        }
        routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
        gov["primary_route_selection"] = {
            "selected_model_id": routing.get("selected_model"),
            "selected_provider_id": routing.get("selected_provider"),
            "route_reason_code": routing.get("route_reason_code"),
            "fallback_chain": routing.get("fallback_chain"),
            "route_id": routing.get("route_id"),
            "route_family": routing.get("route_family"),
            "route_family_expected": routing.get("route_family_expected"),
            "route_substitution_occurred": bool(routing.get("route_substitution_occurred")),
        }
        gov["fallback_stage_reached"] = routing.get("fallback_stage_reached") or (
            "graph_fallback_executed" if "fallback_model" in (graph_state.get("nodes_executed") or []) else "primary_only"
        )
        gen_meta = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
        gov["final_model_invocation"] = {
            "adapter": gen_meta.get("adapter"),
            "api_model": gen_meta.get("model"),
            "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
        }
        gov["route_selected_model"] = routing.get("selected_model")
        gov["route_selected_provider"] = routing.get("selected_provider")
        gov["route_reason_code"] = routing.get("route_reason_code")
        gov["adapter"] = gen_meta.get("adapter")
        gov["api_model"] = gen_meta.get("model")
        self_correction = graph_state.get("self_correction") if isinstance(graph_state.get("self_correction"), dict) else {}
        gov["self_correction_attempt_count"] = self_correction.get("attempt_count")
        val = validation_outcome
        gov["validation_reason"] = val.get("reason")
        gov["mock_output_flag"] = bool(str(gen.get("content") or "").strip().startswith("[mock]"))
        gov["transition_pattern"] = graph_state.get("transition_pattern")
        gov["dramatic_quality_gate"] = val.get("dramatic_quality_gate")
        gate_outcome = val.get("dramatic_effect_gate_outcome") if isinstance(val.get("dramatic_effect_gate_outcome"), dict) else {}
        gov["dramatic_effect_rationale_codes"] = (
            list(gate_outcome.get("effect_rationale_codes") or [])
            if isinstance(gate_outcome, dict)
            else []
        )
        actor_lane_validation = val.get("actor_lane_validation") if isinstance(val.get("actor_lane_validation"), dict) else {}
        gov["actor_lane_validation_status"] = actor_lane_validation.get("status")
        gov["actor_lane_validation_reason"] = actor_lane_validation.get("reason")
        gov["quality_class"] = graph_state.get("quality_class")
        gov["degradation_signals"] = list(graph_state.get("degradation_signals") or [])
        gov["degradation_summary"] = graph_state.get("degradation_summary")
        # The live player-turn path always routes through ``run_validation_seam``
        # inside the graph, which populates ``validator_lane``. Publishing it
        # here makes the "which validator ran" question auditable per turn and
        # distinguishes the canonical live lane from the operator endpoint at
        # /api/internal/narrative/runtime/validate-and-recover.
        gov["validator_lane"] = val.get("validator_lane")
        gov["validator_layers_used"] = narrative_commit.planner_truth.validator_layers_used
        reconciliation = graph_state.get("responder_reconciliation")
        if isinstance(reconciliation, dict):
            gov["responder_reconciliation"] = reconciliation
        social_summary = narrative_commit.planner_truth.social_state_summary
        if social_summary:
            gov["social_state_truth"] = {
                "committed": True,
                "fingerprint": social_summary.get("fingerprint"),
                "validated": social_summary.get("validated"),
                "social_risk_band": social_summary.get("social_risk_band"),
                "responder_asymmetry_code": social_summary.get("responder_asymmetry_code"),
                "social_continuity_status": social_summary.get("social_continuity_status"),
                "prior_social_state_fingerprint": social_summary.get("prior_social_state_fingerprint"),
            }
        # Publish the committed beat identity and the advancement decision on
        # the per-turn governance surface so continuity is observable turn by
        # turn, alongside authority, routing, and validator truth.
        if narrative_commit.beat_progression is not None:
            bp = narrative_commit.beat_progression
            gov["beat_progression"] = {
                "beat_id": bp.beat_id,
                "beat_slot": bp.beat_slot,
                "advanced": bp.advanced,
                "advancement_reason": bp.advancement_reason,
                "continuity_carry_forward_reason": bp.continuity_carry_forward_reason,
                "prior_beat_id": bp.prior_beat_id,
                "pressure_state": bp.pressure_state,
            }
        gov["dramatic_context_summary"] = dramatic_context_summary
        if isinstance(graph_state.get("scene_energy_target"), dict):
            gov["scene_energy_target"] = graph_state.get("scene_energy_target")
        if isinstance(graph_state.get("scene_energy_transition"), dict):
            gov["scene_energy_transition"] = graph_state.get("scene_energy_transition")
        if isinstance(graph_state.get("scene_energy_validation"), dict):
            gov["scene_energy_validation"] = graph_state.get("scene_energy_validation")
        if isinstance(graph_state.get("pacing_rhythm_state"), dict):
            gov["pacing_rhythm_state"] = graph_state.get("pacing_rhythm_state")
        if isinstance(graph_state.get("pacing_rhythm_target"), dict):
            gov["pacing_rhythm_target"] = graph_state.get("pacing_rhythm_target")
        if isinstance(graph_state.get("pacing_rhythm_validation"), dict):
            gov["pacing_rhythm_validation"] = graph_state.get("pacing_rhythm_validation")
        if isinstance(session.environment_state, dict) and session.environment_state:
            gov["environment_state"] = session.environment_state
        # Story Runtime Experience packaging: re-pack the visible bundle
        # according to the governed experience policy. The policy is a real
        # first-class runtime value pulled from the resolved config, so
        # recap / dramatic_turn / live modes differ in packaging truth, not
        # only in prompt wording.
        raw_bundle = graph_state.get("visible_output_bundle")
        experience_policy = self._story_runtime_experience_policy()
        packaged_bundle = self._apply_experience_packaging(raw_bundle, experience_policy)
        packaged_bundle = _finalize_visible_bundle_opening_gm_narration(
            session=session,
            graph_state=graph_state,
            packaged_bundle=packaged_bundle,
            commit_turn_number=commit_turn_number,
        )
        visible_bundle_for_summary = (
            packaged_bundle if isinstance(packaged_bundle, dict) else raw_bundle if isinstance(raw_bundle, dict) else {}
        )
        actor_turn_summary = _build_actor_turn_summary(
            graph_state=graph_state,
            visible_output_bundle=visible_bundle_for_summary,
            dramatic_context_summary=dramatic_context_summary,
        )
        selected_responder_set = (
            graph_state.get("selected_responder_set")
            if isinstance(graph_state.get("selected_responder_set"), list)
            else []
        )
        if selected_responder_set:
            gov["selected_responder_set"] = selected_responder_set
            gov["selected_responder_ids"] = [
                str(row.get("actor_id") or row.get("responder_id") or "").strip()
                for row in selected_responder_set
                if isinstance(row, dict)
                and str(row.get("actor_id") or row.get("responder_id") or "").strip()
            ]
        if vitality_telemetry_v1:
            gov["vitality_telemetry_v1"] = vitality_telemetry_v1
            gov["realized_actor_ids"] = list(vitality_telemetry_v1.get("realized_actor_ids") or [])
            gov["rendered_actor_ids"] = list(vitality_telemetry_v1.get("rendered_actor_ids") or [])
            passivity_diagnosis = (
                actor_survival_telemetry.get("passivity_diagnosis_v1")
                if isinstance(actor_survival_telemetry.get("passivity_diagnosis_v1"), dict)
                else {}
            )
            operator_hints = (
                actor_survival_telemetry.get("operator_diagnostic_hints")
                if isinstance(actor_survival_telemetry.get("operator_diagnostic_hints"), dict)
                else {}
            )
            canonical_diagnosis = passivity_diagnosis if passivity_diagnosis else operator_hints
            if passivity_diagnosis:
                gov["passivity_diagnosis_v1"] = passivity_diagnosis
            gov["why_turn_felt_passive"] = list(canonical_diagnosis.get("why_turn_felt_passive") or [])
            gov["primary_passivity_factors"] = list(canonical_diagnosis.get("primary_passivity_factors") or [])
        quality_class, degradation_signals, degradation_summary = _canonical_quality_fields_from_surfaces(
            runtime_governance_surface=gov,
            authority_summary={
                "validation_status": val.get("status"),
                "commit_applied": bool((graph_state.get("committed_result") or {}).get("commit_applied")),
            },
        )
        gov["quality_class"] = quality_class
        gov["degradation_signals"] = degradation_signals
        gov["degradation_summary"] = degradation_summary
        turn_aspect_ledger = (
            normalize_runtime_aspect_ledger(graph_state.get("turn_aspect_ledger"))
            if isinstance(graph_state.get("turn_aspect_ledger"), dict)
            else None
        )
        turn_aspect_ledger = ensure_runtime_aspect_ledger(
            turn_aspect_ledger,
            session_id=session.session_id,
            module_id=session.module_id,
            turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
            raw_player_input=player_input,
            input_kind=interpreted_input.get("player_input_kind") or interpreted_input.get("kind"),
            trace_id=trace_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        turn_aspect_ledger = _stamp_turn_aspect_ledger_identity(
            turn_aspect_ledger,
            session=session,
            commit_turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
        )
        canonical_turn_id = _canonical_turn_id(session.session_id, commit_turn_number)
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        branching_forecast = build_branching_forecast(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
            canonical_turn_id=canonical_turn_id,
            turn_number=commit_turn_number,
            turn_kind=turn_kind or "player",
            narrative_commit=narrative_commit_payload,
            narrative_threads=session.narrative_threads.model_dump(mode="json")
            if hasattr(session.narrative_threads, "model_dump")
            else session.narrative_threads,
            thread_metrics=turn_thread_metrics,
            selected_responder_set=selected_responder_set,
            actor_turn_summary=actor_turn_summary,
            graph_state=graph_state,
        )
        if isinstance(turn_aspect_ledger, dict):
            turn_aspect_ledger = dict(turn_aspect_ledger)
            turn_aspect_ledger["branching_forecast"] = branching_forecast
            turn_aspect_ledger = normalize_runtime_aspect_ledger(turn_aspect_ledger)
            graph_state["turn_aspect_ledger"] = turn_aspect_ledger
        graph_state["branching_forecast"] = branching_forecast
        gov["branching_forecast"] = {
            "status": branching_forecast.get("status"),
            "option_count": branching_forecast.get("option_count"),
            "forecast_only": branching_forecast.get("forecast_only"),
            "inactive_branches_authoritative": branching_forecast.get("inactive_branches_authoritative"),
            "mutates_canonical_state": branching_forecast.get("mutates_canonical_state"),
        }
        event: dict[str, Any] = {
            "turn_number": commit_turn_number,
            "canonical_turn_id": canonical_turn_id,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "raw_input": player_input,
            "turn_aspect_ledger": turn_aspect_ledger,
            "interpreted_input": interpreted_input,
            "narrative_commit": narrative_commit_payload,
            "retrieval": graph_state.get("retrieval", {}),
            "model_route": {**routing, "generation": gen},
            "graph": graph_diag,
            "visible_output_bundle": packaged_bundle if packaged_bundle is not None else raw_bundle,
            "story_runtime_experience": experience_policy.to_truth_surface(),
            "dramatic_context_summary": dramatic_context_summary,
            "diagnostics_refs": graph_state.get("diagnostics_refs"),
            "experiment_preview": graph_state.get("experiment_preview"),
            "validation_outcome": val,
            "committed_result": graph_state.get("committed_result"),
            "committed_turn_authority": committed_turn_authority,
            "environment_state": session.environment_state
            if isinstance(session.environment_state, dict)
            else {},
            "selected_scene_function": graph_state.get("selected_scene_function"),
            "scene_energy_target": graph_state.get("scene_energy_target"),
            "scene_energy_transition": graph_state.get("scene_energy_transition"),
            "scene_energy_validation": graph_state.get("scene_energy_validation"),
            "dramatic_irony_record": graph_state.get("dramatic_irony_record"),
            "dramatic_irony_validation": graph_state.get("dramatic_irony_validation"),
            "selected_responder_set": selected_responder_set,
            "visibility_class_markers": graph_state.get("visibility_class_markers"),
            "failure_markers": graph_state.get("failure_markers"),
            "self_correction": self_correction,
            "branching_forecast": branching_forecast,
            "actor_survival_telemetry": actor_survival_telemetry,
            "actor_turn_summary": actor_turn_summary,
            "runtime_governance_surface": gov,
        }
        projection_aspect_recorded = False

        def _recover_if_projection_gate_blocks_commit() -> dict[str, Any] | None:
            failure = _runtime_aspect_commit_blocking_failure(
                event.get("turn_aspect_ledger")
                if isinstance(event.get("turn_aspect_ledger"), dict)
                else graph_state.get("turn_aspect_ledger")
                if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                else None
            )
            if not failure:
                return None
            reason = str(failure.get("failure_reason") or "runtime_aspect_projection_failure")
            session.current_scene_id = prior_scene_id
            session.narrative_threads = copy.deepcopy(prior_narrative_threads_for_rollback)
            session.last_thread_update_trace = copy.deepcopy(prior_thread_update_trace_for_rollback)
            session.prior_continuity_impacts = copy.deepcopy(prior_continuity_impacts_for_rollback)
            if str(turn_kind or "").strip().lower() == "opening":
                raise RuntimeError(f"Opening projection contract failure: {reason}")

            message = _recoverable_turn_message(session=session, reason=reason)
            turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
                session_id=session.session_id,
                module_id=session.module_id,
                turn_number=commit_turn_number,
                turn_kind="player_projection_rejected_recoverable",
                player_input=player_input,
                trace_id=trace_id,
                reason=reason,
                validation_status="rejected",
                existing_ledger=event.get("turn_aspect_ledger")
                if isinstance(event.get("turn_aspect_ledger"), dict)
                else graph_state.get("turn_aspect_ledger")
                if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                else None,
                visible_output_present=True,
            )
            val_projection: dict[str, Any] = {
                "status": "rejected",
                "reason": reason,
                "validator_lane": "runtime_aspect_projection_gate_v1",
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
                "runtime_aspect_failure": failure,
            }
            recoverable_event = _recoverable_playable_turn_envelope(
                session=session,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                trace_id=trace_id,
                turn_kind="player_projection_rejected_recoverable",
                interpreted_input=interpreted_input,
                narrative_commit={
                    "situation_status": "continue",
                    "allowed": False,
                    "commit_reason_code": "runtime_aspect_projection_gate",
                    "committed_scene_id": prior_scene_id,
                    "proposed_scene_id": prior_scene_id,
                    "selected_candidate_source": "runtime_aspect_projection_gate",
                    "is_terminal": False,
                },
                validation_outcome=val_projection,
                message=message,
                turn_aspect_ledger=turn_aspect_ledger,
                reason=reason,
                diagnostics_extras={
                    "failure_class": failure.get("failure_class"),
                    "runtime_aspect_failure": failure,
                },
            )
            graph_state["turn_aspect_ledger"] = turn_aspect_ledger
            graph_state["validation_outcome"] = val_projection
            graph_state["visible_output_bundle"] = recoverable_event["visible_output_bundle"]
            graph_state["committed_result"] = {
                "commit_applied": False,
                "committed_effects": [],
                "reason": reason,
                "runtime_aspect_failure": failure,
            }
            return self._persist_player_visible_turn_event(
                session=session,
                graph_state=graph_state,
                event=recoverable_event,
                trace_id=trace_id,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                turn_outcome="recoverable_projection_failure",
            )
        if session.module_id != GOD_OF_CARNAGE_MODULE_ID:
            generic_scene_blocks = _scene_blocks_from_visible_bundle(
                event.get("visible_output_bundle")
                if isinstance(event.get("visible_output_bundle"), dict)
                else None
            )
            if generic_scene_blocks:
                event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                    ledger=event.get("turn_aspect_ledger")
                    if isinstance(event.get("turn_aspect_ledger"), dict)
                    else graph_state.get("turn_aspect_ledger")
                    if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                    else None,
                    session_id=session.session_id,
                    module_id=session.module_id,
                    turn_number=commit_turn_number,
                    turn_kind=turn_kind or "player",
                    raw_player_input=player_input,
                    trace_id=trace_id,
                    scene_blocks=generic_scene_blocks,
                )
                projection_aspect_recorded = True
                graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]
                blocked_projection_event = _recover_if_projection_gate_blocks_commit()
                if blocked_projection_event is not None:
                    return blocked_projection_event
        # Build SceneTurnEnvelope.v2 for God of Carnage solo sessions.
        # Live graph/model output is primary. LDSS is reserved as the final
        # deterministic fallback when the live path cannot produce scene blocks.
        scene_turn_envelope: dict[str, Any] | None = None
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            live_scene_blocks = []
            if gen.get("success") is True and not graph_state.get("force_ldss_scene_fallback"):
                gen_meta_for_blocks = gen.get("metadata") if isinstance(gen.get("metadata"), dict) else {}
                structured_for_projection = (
                    gen_meta_for_blocks.get("structured_output")
                    if isinstance(gen_meta_for_blocks.get("structured_output"), dict)
                    else None
                )
                if structured_for_projection is None and isinstance(gen.get("structured_output"), dict):
                    structured_for_projection = gen["structured_output"]
                live_scene_blocks = _live_scene_blocks_from_visible_bundle(
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else {},
                    turn_number=commit_turn_number,
                    structured_output=structured_for_projection,
                    runtime_projection=session.runtime_projection
                    if isinstance(session.runtime_projection, dict)
                    else None,
                    graph_state=graph_state,
                    session_output_language=session.session_output_language,
                    player_input=player_input,
                    story_runtime_experience=experience_policy.effective,
                )
                live_scene_blocks = _maybe_split_goc_opening_into_two_movements(
                    live_scene_blocks,
                    commit_turn_number=commit_turn_number,
                )
                _annotate_goc_opening_narration_beats(
                    live_scene_blocks,
                    module_id=session.module_id,
                    turn_number=commit_turn_number,
                )
            if live_scene_blocks:
                event_bundle = (
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else {}
                )
                event["visible_output_bundle"] = {
                    **event_bundle,
                    "scene_blocks": [dict(block) for block in live_scene_blocks],
                }
                event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                    ledger=event.get("turn_aspect_ledger")
                    if isinstance(event.get("turn_aspect_ledger"), dict)
                    else graph_state.get("turn_aspect_ledger")
                    if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                    else None,
                    session_id=session.session_id,
                    module_id=session.module_id,
                    turn_number=commit_turn_number,
                    turn_kind=turn_kind or "player",
                    raw_player_input=player_input,
                    trace_id=trace_id,
                    scene_blocks=[dict(block) for block in live_scene_blocks if isinstance(block, dict)],
                )
                projection_aspect_recorded = True
                graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]
                scene_turn_envelope = _build_live_scene_turn_envelope(
                    session=session,
                    graph_state=graph_state,
                    scene_blocks=live_scene_blocks,
                    turn_number=commit_turn_number,
                )
                graph_state.setdefault("phase_costs", {})["live_scene_projection"] = build_deterministic_phase_cost(
                    phase="live_scene_projection",
                    provider="world_engine",
                    model="live_runtime_graph_projection",
                    scene_block_count=len(live_scene_blocks),
                    visible_actor_response_present=bool(
                        scene_turn_envelope.get("diagnostics", {})
                        .get("npc_agency", {})
                        .get("visible_actor_response_present")
                    ),
                )
            else:
                ldss_span = None
                try:
                    from app.observability.langfuse_adapter import LangfuseAdapter
                    adapter = LangfuseAdapter.get_instance()
                    if adapter and adapter.is_enabled():
                        logger.info(f"[MANAGER] Creating LDSS fallback span for session {session.session_id}, turn {commit_turn_number}")
                        ldss_span = adapter.create_child_span(
                            name="story.phase.ldss_fallback",
                            input={
                                "session_id": session.session_id,
                                "turn_number": commit_turn_number,
                                "player_input_length": len(player_input) if player_input else 0,
                                "fallback_reason": "live_scene_blocks_missing",
                            },
                            metadata={
                                "phase": "ldss_fallback",
                                "turn_number": commit_turn_number,
                                "session_id": session.session_id,
                            }
                        )
                except Exception as e:
                    logger.error(f"[MANAGER] Exception creating LDSS fallback span: {e}", exc_info=True)

                try:
                    scene_turn_envelope = _build_ldss_scene_envelope(
                        session=session,
                        graph_state=graph_state,
                        player_input=player_input,
                        turn_number=commit_turn_number,
                    )
                    if scene_turn_envelope and ldss_span:
                        ldss_phase_cost = {}
                        if isinstance(scene_turn_envelope, dict):
                            diagnostics = scene_turn_envelope.get("diagnostics")
                            if isinstance(diagnostics, dict) and isinstance(diagnostics.get("phase_cost"), dict):
                                ldss_phase_cost = diagnostics["phase_cost"]
                        if not ldss_phase_cost:
                            raw_costs = graph_state.get("phase_costs")
                            if isinstance(raw_costs, dict) and isinstance(raw_costs.get("ldss"), dict):
                                ldss_phase_cost = raw_costs["ldss"]
                        ldss_span.update(
                            output={
                                "block_count": len(scene_turn_envelope.get("visible_scene_output", {}).get("blocks", [])) if isinstance(scene_turn_envelope.get("visible_scene_output"), dict) else 0,
                                "decision_count": scene_turn_envelope.get("decision_count", 0) if isinstance(scene_turn_envelope, dict) else 0,
                                "status": "approved"
                            },
                            metadata={
                                **ldss_phase_cost,
                                "phase_cost": dict(ldss_phase_cost),
                            }
                        )
                finally:
                    if ldss_span:
                        logger.info(f"[MANAGER] Ending LDSS fallback span")
                        ldss_span.end()

            if scene_turn_envelope:
                event["scene_turn_envelope"] = scene_turn_envelope
                visible_scene_output = (
                    scene_turn_envelope.get("visible_scene_output")
                    if isinstance(scene_turn_envelope.get("visible_scene_output"), dict)
                    else {}
                )
                blocks = visible_scene_output.get("blocks")
                if isinstance(blocks, list) and blocks:
                    raw_scene_blocks = [dict(block) for block in blocks if isinstance(block, dict)]
                    projected_scene_blocks = _live_scene_blocks_from_visible_bundle(
                        {"scene_blocks": raw_scene_blocks},
                        turn_number=commit_turn_number,
                        structured_output=None,
                        runtime_projection=session.runtime_projection
                        if isinstance(session.runtime_projection, dict)
                        else None,
                        graph_state=graph_state,
                        session_output_language=session.session_output_language,
                        player_input=player_input,
                        story_runtime_experience=experience_policy.effective,
                    )
                    if not projected_scene_blocks:
                        projected_scene_blocks = raw_scene_blocks
                    visible_scene_output["blocks"] = [
                        dict(block) for block in projected_scene_blocks if isinstance(block, dict)
                    ]
                    event_bundle = (
                        event.get("visible_output_bundle")
                        if isinstance(event.get("visible_output_bundle"), dict)
                        else {}
                    )
                    event["visible_output_bundle"] = _ensure_gm_narration_from_narrator_scene_blocks(
                        {
                            **event_bundle,
                            "scene_blocks": [
                                dict(block)
                                for block in projected_scene_blocks
                                if isinstance(block, dict)
                            ],
                        }
                    )
                    event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                        ledger=event.get("turn_aspect_ledger")
                        if isinstance(event.get("turn_aspect_ledger"), dict)
                        else graph_state.get("turn_aspect_ledger")
                        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                        else None,
                        session_id=session.session_id,
                        module_id=session.module_id,
                        turn_number=commit_turn_number,
                        turn_kind=turn_kind or "player",
                        raw_player_input=player_input,
                        trace_id=trace_id,
                        scene_blocks=[
                            dict(block)
                            for block in projected_scene_blocks
                            if isinstance(block, dict)
                        ],
                    )
                    projection_aspect_recorded = True
                    graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]

            if not projection_aspect_recorded:
                generic_scene_blocks = _scene_blocks_from_visible_bundle(
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else None
                )
                if generic_scene_blocks:
                    event["turn_aspect_ledger"] = _record_visible_projection_aspect(
                        ledger=event.get("turn_aspect_ledger")
                        if isinstance(event.get("turn_aspect_ledger"), dict)
                        else graph_state.get("turn_aspect_ledger")
                        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
                        else None,
                        session_id=session.session_id,
                        module_id=session.module_id,
                        turn_number=commit_turn_number,
                        turn_kind=turn_kind or "player",
                        raw_player_input=player_input,
                        trace_id=trace_id,
                        scene_blocks=generic_scene_blocks,
                    )
                    projection_aspect_recorded = True
                    graph_state["turn_aspect_ledger"] = event["turn_aspect_ledger"]

            blocked_projection_event = _recover_if_projection_gate_blocks_commit()
            if blocked_projection_event is not None:
                return blocked_projection_event

            # MVP3: Orchestrate NarrativeRuntimeAgent streaming (after LDSS produces NPCAgencyPlan)
            runtime_state = {
                "session_id": session.session_id,
                "current_scene_id": session.current_scene_id,
                "actor_positions": graph_state.get("actor_positions", {}),
                "narrative_threads": [t.model_dump() if hasattr(t, 'model_dump') else t
                                     for t in (session.narrative_threads.active if hasattr(session.narrative_threads, 'active') else [])],
            }
            dramatic_context = (
                graph_state.get("dramatic_context_summary", {})
                if isinstance(graph_state.get("dramatic_context_summary"), dict)
                else {}
            )
            narrator_packet = build_narrator_packet(
                opening_scene_sequence=graph_state.get("opening_scene_sequence")
                if isinstance(graph_state.get("opening_scene_sequence"), dict)
                else None,
                hard_forbidden_rules=graph_state.get("hard_forbidden_rules")
                if isinstance(graph_state.get("hard_forbidden_rules"), dict)
                else None,
                actor_lane_context=self._extract_actor_lane_context(session),
                session_output_language=session.session_output_language,
                story_runtime_experience=experience_policy.effective,
            )
            runtime_state["narrator_packet"] = narrator_packet
            narrative_threads_list = [t.model_dump() if hasattr(t, 'model_dump') else t
                                     for t in (session.narrative_threads.active if hasattr(session.narrative_threads, 'active') else [])]

            # MVP4: Create child span for Narrator phase
            narrator_span = None
            previous_active_span = None
            adapter = None
            try:
                from app.observability.langfuse_adapter import LangfuseAdapter
                adapter = LangfuseAdapter.get_instance()
                if adapter and adapter.is_enabled():
                    logger.info(f"[MANAGER] Creating Narrator phase span for session {session.session_id}, turn {commit_turn_number}")
                    narrator_span = adapter.create_child_span(
                        name="story.phase.narrator",
                        input={
                            "session_id": session.session_id,
                            "turn_number": commit_turn_number,
                            "npc_agency_plan": scene_turn_envelope.get("npc_agency_plan") if isinstance(scene_turn_envelope, dict) else None,
                            "narrator_packet": narrator_packet,
                        },
                        metadata={
                            "phase": "narrator",
                            "turn_number": commit_turn_number,
                            "session_id": session.session_id,
                        }
                    )
                    # Set as active span so NarrativeRuntimeAgent can create child spans
                    if narrator_span:
                        logger.info(f"[MANAGER] Narrator phase span created, setting as active context")
                        previous_active_span = adapter.get_active_span()
                        adapter.set_active_span(narrator_span)
                    else:
                        logger.warning(f"[MANAGER] Narrator phase span creation returned None")
            except Exception as e:
                logger.error(f"[MANAGER] Exception creating Narrator phase span: {e}", exc_info=True)

            try:
                streaming_started = _orchestrate_narrative_agent(
                    manager=self,
                    session_id=session.session_id,
                    ldss_output=scene_turn_envelope,
                    runtime_state=runtime_state,
                    dramatic_signature=dramatic_context,
                    narrative_threads=narrative_threads_list,
                    turn_number=commit_turn_number,
                    trace_id=trace_id,
                    narrator_packet=narrator_packet,
                )

                if streaming_started:
                    narrator_phase_cost = build_deterministic_phase_cost(
                        phase="narrator",
                        provider="world_engine",
                        model="narrative_runtime_agent_scheduled",
                        streaming_started=True,
                    )
                    graph_state.setdefault("phase_costs", {})["narrator"] = narrator_phase_cost

                if streaming_started and narrator_span:
                    narrator_span.update(
                        output={
                            "status": "streaming_started"
                        },
                        metadata={
                            **narrator_phase_cost,
                            "phase_cost": dict(narrator_phase_cost),
                        },
                    )
            finally:
                if narrator_span:
                    logger.info(f"[MANAGER] Ending Narrator phase span")
                    narrator_span.end()
                    logger.info(f"[MANAGER] Narrator phase span ended")
                if adapter is not None and narrator_span is not None:
                    adapter.set_active_span(previous_active_span)

            if streaming_started:
                event["narrative_agent_started"] = True
                event["narrator_streaming"] = {
                    "status": "streaming",
                    "session_id": session.session_id,
                }

        # MVP4: Build DiagnosticsEnvelope from committed state only.
        # Never exposes raw AI proposals as committed truth.
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            try:
                # Phase B: Collect degradation events
                degradation_events = []
                signals = graph_state.get("degradation_signals") or []
                for signal in signals:
                    severity = "critical" if signal in ("execution_error", "graph_error") \
                               else "moderate" if "fallback" in signal \
                               else "minor"
                    degradation_events.append(DegradationEvent(
                        marker=signal.upper(),
                        severity=severity,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        recovery_successful=graph_state.get("committed_result", {}).get("commit_applied", False),
                        context_snapshot={"turn_number": commit_turn_number},
                    ))

                cost_summary = aggregate_phase_costs(graph_state.get("phase_costs", {}))

                diag_envelope = build_diagnostics_envelope(
                    session_id=session.session_id,
                    turn_number=commit_turn_number,
                    trace_id=trace_id or "",
                    player_input=player_input,
                    runtime_projection=session.runtime_projection,
                    graph_state=graph_state,
                    scene_turn_envelope=scene_turn_envelope,
                    langfuse_trace_id=get_langfuse_trace_id() or "",
                    langfuse_enabled=self._get_tracing_config(session.session_id),
                    degradation_events=degradation_events,
                )
                # Update cost_summary in the envelope
                diag_envelope.cost_summary = cost_summary
                event["diagnostics_envelope"] = diag_envelope.to_dict()
            except Exception as exc:
                log_story_runtime_failure(
                    trace_id=trace_id or "",
                    story_session_id=session.session_id,
                    operation="diagnostics_envelope",
                    message=str(exc),
                    failure_class="diagnostics_construction_error",
                )
                raise

        # Langfuse path summary and evidence scores must run after live projection
        # populates ``scene_blocks`` (GoC); otherwise ``visible_output_present`` is 0.
        if event.get("turn_status") is None:
            tk_final = str(turn_kind or "").strip().lower()
            if tk_final == "opening":
                event["turn_status"] = "opening_committed"
            else:
                event["turn_status"] = "committed" if outcome == "ok" else "committed_degraded"
        event.setdefault("http_status", 200)
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            human_att = _build_human_input_attribution_record(
                session=session,
                graph_state=graph_state,
                interpreted_input=interpreted_input,
                selected_responder_set=selected_responder_set,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
            )
            graph_state["human_input_attribution"] = human_att
            event["human_input_attribution"] = human_att
        _reconcile_governance_passivity_with_final_projection(event)
        memory_source_turn = {
            "canonical_turn_id": event.get("canonical_turn_id"),
            "module_id": session.module_id,
            "runtime_profile_id": _runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_turn_authority": committed_turn_authority,
            "dramatic_context_summary": dramatic_context_summary,
            "actor_turn_summary": actor_turn_summary,
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        _record_hierarchical_memory_aspect(
            session=session,
            graph_state=graph_state,
            event=event,
            committed_turn=memory_source_turn,
            allow_write=True,
        )
        turn_lc.advance("projected")

        committed_record = {
            "canonical_turn_id": event.get("canonical_turn_id"),
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_turn_authority": committed_turn_authority,
            "dramatic_context_summary": dramatic_context_summary,
            "actor_turn_summary": actor_turn_summary,
            "branching_forecast": event.get("branching_forecast"),
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "scene_energy_target": event.get("scene_energy_target"),
            "scene_energy_transition": event.get("scene_energy_transition"),
            "scene_energy_validation": event.get("scene_energy_validation"),
            "human_input_attribution": event.get("human_input_attribution"),
            "hierarchical_memory_update": event.get("hierarchical_memory"),
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        if isinstance(event.get("narrator_streaming"), dict):
            committed_record["narrator_streaming"] = event["narrator_streaming"]
        turn_lc.advance("persisted")
        committed_record["lifecycle_state"] = "observed"
        event["lifecycle_state"] = "observed"
        session.history.append(committed_record)
        self._refresh_callback_web_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._refresh_consequence_cascade_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._emit_observability_path_for_event(session=session, graph_state=graph_state, event=event)
        session.diagnostics.append(event)
        turn_lc.advance("observed")
        self._persist_session(session)
        return event

    def _execute_opening_locked(self, session_id: str, trace_id: str | None) -> dict[str, Any]:
        session = self.get_session(session_id)
        prompt = self._build_opening_prompt(session)
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template = (
            goc_host_experience_template(session.runtime_projection)
            if session.module_id == GOD_OF_CARNAGE_MODULE_ID
            else None
        )
        prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
        actor_lane_ctx = self._extract_actor_lane_context(session)
        prior_callback_web_state = self._prior_callback_web_state_for_graph(session)
        prior_consequence_cascade_state = self._prior_consequence_cascade_state_for_graph(session)
        prior_pacing_rhythm_state = _prior_pacing_rhythm_state_from_session(session)

        try:
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=prompt,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
                active_narrative_threads=graph_threads or None,
                thread_pressure_summary=graph_summary,
                host_experience_template=host_experience_template,
                prior_continuity_impacts=prior_ci if prior_ci else None,
                prior_callback_web_state=prior_callback_web_state,
                prior_consequence_cascade_state=prior_consequence_cascade_state,
                prior_pacing_rhythm_state=prior_pacing_rhythm_state,
                turn_number=0,
                turn_initiator_type="engine",
                turn_input_class="opening",
                live_player_truth_surface=True,
                actor_lane_context=actor_lane_ctx,
                session_output_language=session.session_output_language,
                story_runtime_experience=self._story_runtime_experience_policy().effective,
                validation_execution_mode=self._validation_execution_mode(),
                environment_state=session.environment_state
                if isinstance(session.environment_state, dict)
                else None,
            )
        except Exception as exc:
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_opening",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            raise
        opening_fallback_reason = ""
        if not self._opening_commit_acceptable(graph_state):
            validation = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
            opening_fallback_reason = str(validation.get("reason") or "opening_validation_not_approved")
            self.metrics.incr("opening_ldss_fallback", reason=opening_fallback_reason)
            graph_state = self._ldss_opening_fallback_state(
                graph_state,
                reason=opening_fallback_reason,
            )
        elif not self._visible_narration_present(graph_state):
            gen = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
            gen_error = gen.get("error") or (gen.get("metadata") or {}).get("error") or "no error details available"
            opening_fallback_reason = f"no_visible_narration:{gen_error}"
            self.metrics.incr("opening_ldss_fallback", reason="no_visible_narration")
            graph_state = self._ldss_opening_fallback_state(
                graph_state,
                reason=opening_fallback_reason,
            )

        session.updated_at = datetime.now(timezone.utc)
        return self._finalize_committed_turn(
            session=session,
            graph_state=graph_state,
            trace_id=trace_id,
            commit_turn_number=0,
            player_input=prompt,
            turn_kind="opening",
            prior_scene_id=prior_scene_id,
            history_tail=history_tail,
            graph_threads=graph_threads,
            graph_summary=graph_summary,
            host_experience_template=host_experience_template,
            prior_ci=prior_ci,
        )

    def create_session(
        self,
        *,
        module_id: str,
        runtime_projection: dict[str, Any],
        session_output_language: str = "de",
        content_provenance: dict[str, Any] | None = None,
        trace_id: str | None = None,
        session_id: str | None = None,
    ) -> StorySession:
        _validate_runtime_projection_contract(module_id, runtime_projection)
        session_id = str(session_id or uuid4().hex).strip() or uuid4().hex
        # Generate trace_id if not provided for audit trail correlation
        if not trace_id:
            trace_id = uuid4().hex
        current_scene_id = str(runtime_projection.get("start_scene_id") or "")
        prov = dict(content_provenance) if isinstance(content_provenance, dict) else {}
        if not prov:
            mid = runtime_projection.get("module_id")
            ver = runtime_projection.get("module_version")
            if isinstance(mid, str) and mid.strip():
                prov.setdefault("runtime_projection_module_id", mid.strip())
            if isinstance(ver, str) and ver.strip():
                prov.setdefault("runtime_projection_module_version", ver.strip())
        session = StorySession(
            session_id=session_id,
            module_id=module_id,
            runtime_projection=runtime_projection,
            current_scene_id=current_scene_id,
            session_output_language=session_output_language,
            content_provenance=prov,
        )
        env_model = build_environment_model(
            module_id=module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(runtime_projection),
        )
        session.environment_state = normalize_environment_state(
            None,
            module_id=module_id,
            environment_model=env_model,
            runtime_projection=runtime_projection,
            actor_lane_context=self._extract_actor_lane_context(session),
            turn_number=0,
        )
        self.sessions[session_id] = session
        with self._session_locks_guard:
            self._session_turn_locks.setdefault(session_id, threading.Lock())
        self._persist_session(session)
        if self._skip_graph_opening_on_create:
            return session
        self._assert_live_player_governance()
        attempts = self._opening_retry_count() + 1
        last_exc: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                with self._session_turn_lock(session_id):
                    self._execute_opening_locked(session_id, trace_id=trace_id)
                self.metrics.incr("story_opening_success", module_id=module_id, session_id=session_id, attempt=attempt)
                return session
            except BaseException as exc:
                last_exc = exc
                self.metrics.incr(
                    "story_opening_retry",
                    module_id=module_id,
                    session_id=session_id,
                    attempt=attempt,
                    error=str(exc)[:300],
                )
        self.sessions.pop(session_id, None)
        if self._session_store is not None:
            try:
                self._session_store.delete(session_id)
            except Exception:
                pass
        log_story_runtime_failure(
            trace_id=None,
            story_session_id=session_id,
            operation="create_session_opening",
            message=str(last_exc)[:500] if last_exc else "opening_failed",
            failure_class="opening_generation_failed",
        )
        raise RuntimeError(f"Opening generation failed for module {module_id}: {last_exc}") from last_exc

    def execute_turn(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        with self._session_turn_lock(session_id):
            return self._execute_turn_locked(
                session_id=session_id, player_input=player_input, trace_id=trace_id
            )

    def build_branching_simulation_tree(
        self,
        *,
        session_id: str,
        max_depth: int | None = None,
        max_branching: int | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a bounded multi-turn branching simulation on isolated clones.

        The active story session is copied once under its turn lock. Every
        simulated future turn runs through the normal manager turn pipeline on
        a temporary clone session id, with durable persistence disabled and the
        clone removed afterwards. The returned tree is diagnostic evidence only.
        """

        depth_limit, branching_limit, node_limit = clamp_simulation_limits(
            max_depth=max_depth,
            max_branching=max_branching,
        )
        with self._session_turn_lock(session_id):
            active_session = self.get_session(session_id)
            root_snapshot = story_session_from_payload(story_session_to_payload(active_session))

        root_session_fingerprint = self._branching_session_fingerprint(root_snapshot)
        root_forecast = self._latest_branching_forecast_from_session(root_snapshot)
        root_turn = root_snapshot.history[-1] if root_snapshot.history else {}
        root_canonical_turn_id = (
            root_turn.get("canonical_turn_id") if isinstance(root_turn, dict) else None
        )
        root_turn_number = (
            int(root_turn.get("turn_number"))
            if isinstance(root_turn, dict) and root_turn.get("turn_number") is not None
            else root_snapshot.turn_counter
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            root_snapshot.runtime_projection if isinstance(root_snapshot.runtime_projection, dict) else None
        )
        sim_trace_id = trace_id or f"branching-simulation-{uuid4().hex}"
        tree = make_simulation_tree(
            story_session_id=root_snapshot.session_id,
            module_id=root_snapshot.module_id,
            runtime_profile_id=runtime_profile_id,
            root_canonical_turn_id=root_canonical_turn_id,
            root_turn_number=root_turn_number,
            root_branching_forecast=root_forecast,
            max_depth=depth_limit,
            max_branching=branching_limit,
            max_nodes=node_limit,
            trace_id=sim_trace_id,
        )
        tree["root_session_fingerprint"] = root_session_fingerprint
        tree["scope"] = "active"
        if depth_limit <= 0 or branching_limit <= 0 or not forecast_has_options(root_forecast):
            return finalize_simulation_tree(tree)

        root_node_id = str(tree.get("root_node_id") or "")
        queue: list[tuple[StorySession, dict[str, Any], str, int, list[str]]] = [
            (root_snapshot, root_forecast, root_node_id, 1, [])
        ]
        while queue:
            base_snapshot, forecast, parent_node_id, depth, path_option_ids = queue.pop(0)
            options = (
                forecast.get("options")
                if isinstance(forecast.get("options"), list)
                else []
            )
            for option_index, option_raw in enumerate(options[:branching_limit]):
                if len(tree.get("nodes") or []) >= node_limit:
                    tree["truncated"] = True
                    tree["truncation_reason"] = "max_nodes"
                    return finalize_simulation_tree(tree)
                option = option_raw if isinstance(option_raw, dict) else {}
                option_id = str(option.get("option_id") or f"option_{option_index}").strip()
                next_path = [*path_option_ids, option_id]
                simulated_input = simulated_input_for_branch_option(option, depth=depth)
                clone_session_id = self._branching_simulation_clone_session_id(
                    root_session_id=root_snapshot.session_id,
                    path_option_ids=next_path,
                )
                simulated_event, simulated_snapshot, error = self._execute_branching_simulation_turn_on_clone(
                    base_session_snapshot=base_snapshot,
                    clone_session_id=clone_session_id,
                    simulated_input=simulated_input,
                    trace_id=sim_trace_id,
                    path_option_ids=next_path,
                )
                child_forecast = (
                    simulated_event.get("branching_forecast")
                    if isinstance(simulated_event, dict)
                    and isinstance(simulated_event.get("branching_forecast"), dict)
                    else {}
                )
                stop_reason = self._branching_simulation_stop_reason(
                    depth=depth,
                    max_depth=depth_limit,
                    simulated_event=simulated_event,
                    child_forecast=child_forecast,
                    error=error,
                )
                node = make_simulated_turn_node(
                    tree=tree,
                    parent_node_id=parent_node_id,
                    depth=depth,
                    option=option,
                    option_index=option_index,
                    path_option_ids=next_path,
                    simulated_input=simulated_input,
                    simulated_event=simulated_event,
                    stop_reason=stop_reason,
                    error=error,
                )
                append_simulation_node(tree, node)
                if stop_reason is None and simulated_snapshot is not None:
                    queue.append((simulated_snapshot, child_forecast, str(node.get("node_id")), depth + 1, next_path))
        return finalize_simulation_tree(tree)

    def create_branching_tree(
        self,
        *,
        session_id: str,
        max_depth: int | None = None,
        max_branching: int | None = None,
        trace_id: str | None = None,
        scope: str = "active",
        preview: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a selectable bounded branch tree record."""

        if scope != "active":
            raise ValueError("branching_preview_scope_not_implemented")
        simulation_tree = self.build_branching_simulation_tree(
            session_id=session_id,
            max_depth=max_depth,
            max_branching=max_branching,
            trace_id=trace_id,
        )
        with self._session_turn_lock(session_id):
            session = self.get_session(session_id)
            current_fingerprint = self._branching_session_fingerprint(session)
        root_fingerprint = (
            simulation_tree.get("root_session_fingerprint")
            if isinstance(simulation_tree.get("root_session_fingerprint"), dict)
            else current_fingerprint
        )
        record = make_branch_tree_record(
            simulation_tree=simulation_tree,
            root_session_fingerprint=root_fingerprint,
            current_session_fingerprint=current_fingerprint,
            trace_id=trace_id,
            scope=scope,
            preview=preview,
        )
        if not branch_tree_is_fresh(record, current_fingerprint):
            record = mark_branch_tree_stale(
                record,
                reason="session_changed_during_simulation",
                current_session_fingerprint=current_fingerprint,
            )
        persisted = self._persist_branching_tree_record(record)
        self._append_branch_timeline_event_for_session(
            session_id=session_id,
            event_type=BRANCHING_TIMELINE_EVENT_TREE_CREATED,
            tree_id=str(persisted.get("tree_id") or ""),
            session_fingerprint=current_fingerprint,
            details=self._branch_timeline_tree_details(persisted),
        )
        self._enforce_branch_timeline_tree_bounds(
            session_id=session_id,
            current_session_fingerprint=current_fingerprint,
        )
        return persisted

    def list_branching_trees(self, *, session_id: str) -> list[dict[str, Any]]:
        self.get_session(session_id)
        rows = [
            self._refresh_branching_tree_freshness(record)
            for record in self._branching_trees.values()
            if record.get("story_session_id") == session_id
        ]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return [copy.deepcopy(row) for row in rows]

    def get_branching_tree(self, *, session_id: str, tree_id: str) -> dict[str, Any]:
        self.get_session(session_id)
        record = self._branching_trees.get(tree_id)
        if not isinstance(record, dict) or record.get("story_session_id") != session_id:
            raise KeyError(tree_id)
        return copy.deepcopy(self._refresh_branching_tree_freshness(record))

    def expire_branching_tree(
        self,
        *,
        session_id: str,
        tree_id: str,
        reason: str = "operator_expired",
    ) -> dict[str, Any]:
        self.get_session(session_id)
        record = self._branching_trees.get(tree_id)
        if not isinstance(record, dict) or record.get("story_session_id") != session_id:
            raise KeyError(tree_id)
        expired = mark_branch_tree_expired(record, reason=reason)
        persisted = self._persist_branching_tree_record(expired)
        session = self.get_session(session_id)
        self._append_branch_timeline_event(
            session=session,
            event_type=BRANCHING_TIMELINE_EVENT_TREE_EXPIRED,
            tree_id=tree_id,
            session_fingerprint=self._branching_session_fingerprint(session),
            details={"reason": reason, **self._branch_timeline_tree_details(persisted)},
        )
        return persisted

    def get_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        return copy.deepcopy(timeline)

    def list_branch_timeline_events(self, *, session_id: str) -> list[dict[str, Any]]:
        timeline = self.get_branch_timeline(session_id=session_id)
        events = timeline.get("events") if isinstance(timeline.get("events"), list) else []
        return [copy.deepcopy(event) for event in events if isinstance(event, dict)]

    def compact_branch_timeline(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        compacted = compact_branch_timeline(timeline)
        return self._persist_branch_timeline_record(compacted)

    def archive_branch_timeline(
        self,
        *,
        session_id: str,
        reason: str = "operator_archived",
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        archived = archive_branch_timeline(timeline, reason=reason)
        return self._persist_branch_timeline_record(archived)

    def get_callback_web(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        callback_web_id = stable_callback_web_id(story_session_id=session.session_id)
        existing = self._callback_webs.get(callback_web_id)
        if isinstance(existing, dict):
            return copy.deepcopy(existing)
        return self.rebuild_callback_web(session_id=session_id)

    def list_callback_web_edges(self, *, session_id: str) -> list[dict[str, Any]]:
        record = self.get_callback_web(session_id=session_id)
        edges = record.get("edges") if isinstance(record.get("edges"), list) else []
        return [copy.deepcopy(edge) for edge in edges if isinstance(edge, dict)]

    def rebuild_callback_web(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        branch_timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        existing = self._callback_webs.get(stable_callback_web_id(story_session_id=session.session_id))
        callback_policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        record = build_callback_web_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            history=[dict(row) for row in session.history if isinstance(row, dict)],
            narrative_threads=session.narrative_threads.model_dump(mode="json")
            if hasattr(session.narrative_threads, "model_dump")
            else session.narrative_threads,
            branch_timeline=branch_timeline,
            current_session_fingerprint=self._branching_session_fingerprint(session),
            bounds=callback_web_bounds_from_policy(callback_policy),
            created_at=existing.get("created_at") if isinstance(existing, dict) else None,
        )
        return self._persist_callback_web_record(record)

    def _prior_callback_web_state_for_graph(self, session: StorySession) -> dict[str, Any] | None:
        policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        if not policy.get("enabled"):
            return None
        try:
            record = self.get_callback_web(session_id=session.session_id)
        except Exception:
            return None
        return build_graph_callback_web_export(
            record,
            max_edges=int(policy.get("max_graph_edges") or 4),
        )

    def _refresh_callback_web_after_commit(
        self,
        *,
        session: StorySession,
        event: dict[str, Any],
        graph_state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        gs = graph_state if isinstance(graph_state, dict) else {}
        policy = _load_module_callback_web_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        try:
            record = self.rebuild_callback_web(session_id=session.session_id)
        except Exception:
            logger.debug("Callback web refresh failed", exc_info=True)
            return None
        snapshot = copy.deepcopy(record.get("snapshot") if isinstance(record.get("snapshot"), dict) else {})
        event["callback_web"] = snapshot
        graph_export = build_graph_callback_web_export(
            record,
            max_edges=int(policy.get("max_graph_edges") or 4),
        )
        validation = validate_callback_web_record(record, policy=policy)
        event["callback_web_feedback"] = graph_export
        event["callback_web_validation"] = validation
        gov = event.get("runtime_governance_surface")
        if isinstance(gov, dict):
            gov["callback_web"] = {
                "status": validation.get("status"),
                "contract_pass": validation.get("contract_pass"),
                "failure_codes": validation.get("failure_codes") or [],
                "edge_count": snapshot.get("edge_count"),
                "observation_count": snapshot.get("observation_count"),
                "selected_callback_kind": (
                    graph_export.get("selected_callback_kind")
                    if isinstance(graph_export, dict)
                    else None
                ),
            }
        if gs:
            _record_callback_web_aspect(
                session=session,
                graph_state=gs,
                event=event,
                record=record,
                graph_export=graph_export,
                validation=validation,
                policy=policy,
            )
        if isinstance(event.get("diagnostics"), dict):
            event["diagnostics"]["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
            event["diagnostics"]["callback_web"] = snapshot
            event["diagnostics"]["callback_web_validation"] = validation
        if session.history and isinstance(session.history[-1], dict):
            session.history[-1]["callback_web_summary"] = snapshot
            session.history[-1]["callback_web_feedback"] = graph_export
            session.history[-1]["callback_web_validation"] = validation
            if isinstance(event.get("turn_aspect_ledger"), dict):
                session.history[-1]["turn_aspect_ledger"] = event["turn_aspect_ledger"]
        return record

    def get_consequence_cascade(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        cascade_id = stable_consequence_cascade_id(story_session_id=session.session_id)
        existing = self._consequence_cascades.get(cascade_id)
        if isinstance(existing, dict):
            return copy.deepcopy(existing)
        return self.rebuild_consequence_cascade(session_id=session_id)

    def list_consequence_cascade_edges(self, *, session_id: str) -> list[dict[str, Any]]:
        record = self.get_consequence_cascade(session_id=session_id)
        edges = record.get("edges") if isinstance(record.get("edges"), list) else []
        return [copy.deepcopy(edge) for edge in edges if isinstance(edge, dict)]

    def rebuild_consequence_cascade(self, *, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        branch_timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=self._branching_session_fingerprint(session),
        )
        existing = self._consequence_cascades.get(
            stable_consequence_cascade_id(story_session_id=session.session_id)
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        cascade_policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
        )
        callback_web: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
        except Exception:
            callback_web = None
        record = build_consequence_cascade_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=runtime_profile_id,
            history=[dict(row) for row in session.history if isinstance(row, dict)],
            narrative_threads=session.narrative_threads.model_dump(mode="json")
            if hasattr(session.narrative_threads, "model_dump")
            else session.narrative_threads,
            branch_timeline=branch_timeline,
            callback_web=callback_web,
            bounds=consequence_cascade_bounds_from_policy(cascade_policy),
            created_at=existing.get("created_at") if isinstance(existing, dict) else None,
        )
        return self._persist_consequence_cascade_record(record)

    def _prior_consequence_cascade_state_for_graph(self, session: StorySession) -> dict[str, Any] | None:
        policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        if not policy.get("enabled"):
            return None
        try:
            record = self.get_consequence_cascade(session_id=session.session_id)
        except Exception:
            return None
        return build_graph_consequence_cascade_export(
            record,
            max_items=int(policy.get("max_graph_items") or 5),
        )

    def _refresh_consequence_cascade_after_commit(
        self,
        *,
        session: StorySession,
        event: dict[str, Any],
        graph_state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        gs = graph_state if isinstance(graph_state, dict) else {}
        policy = _load_module_consequence_cascade_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        try:
            record = self.rebuild_consequence_cascade(session_id=session.session_id)
        except Exception:
            logger.debug("Consequence cascade refresh failed", exc_info=True)
            return None
        snapshot = copy.deepcopy(record.get("snapshot") if isinstance(record.get("snapshot"), dict) else {})
        event["consequence_cascade"] = snapshot
        graph_export = build_graph_consequence_cascade_export(
            record,
            max_items=int(policy.get("max_graph_items") or 5),
        )
        validation = validate_consequence_cascade_record(record, policy=policy)
        event["consequence_cascade_feedback"] = graph_export
        event["consequence_cascade_validation"] = validation
        gov = event.get("runtime_governance_surface")
        if isinstance(gov, dict):
            gov["consequence_cascade"] = {
                "status": validation.get("status"),
                "contract_pass": validation.get("contract_pass"),
                "failure_codes": validation.get("failure_codes") or [],
                "atom_count": snapshot.get("atom_count"),
                "edge_count": snapshot.get("edge_count"),
                "active_atom_count": snapshot.get("active_atom_count"),
                "selected_continuity_classes": (
                    graph_export.get("selected_continuity_classes")
                    if isinstance(graph_export, dict)
                    else []
                ),
            }
        if gs:
            _record_consequence_cascade_aspect(
                session=session,
                graph_state=gs,
                event=event,
                record=record,
                graph_export=graph_export,
                validation=validation,
                policy=policy,
            )
        if isinstance(event.get("diagnostics"), dict):
            event["diagnostics"]["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
            event["diagnostics"]["consequence_cascade"] = snapshot
            event["diagnostics"]["consequence_cascade_validation"] = validation
        if session.history and isinstance(session.history[-1], dict):
            session.history[-1]["consequence_cascade_summary"] = snapshot
            session.history[-1]["consequence_cascade_feedback"] = graph_export
            session.history[-1]["consequence_cascade_validation"] = validation
            if isinstance(event.get("turn_aspect_ledger"), dict):
                session.history[-1]["turn_aspect_ledger"] = event["turn_aspect_ledger"]
        return record

    def select_branching_tree_node(
        self,
        *,
        session_id: str,
        tree_id: str,
        node_id: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Replay a selected simulated path through the authoritative commit path."""

        with self._session_turn_lock(session_id):
            session = self.get_session(session_id)
            record = self._branching_trees.get(tree_id)
            if not isinstance(record, dict) or record.get("story_session_id") != session_id:
                raise KeyError(tree_id)
            status = str(record.get("status") or "")
            if status in {BRANCHING_TREE_STATUS_EXPIRED, BRANCHING_TREE_STATUS_COMMITTED}:
                raise ValueError(f"branching_tree_not_selectable:{status}")
            current_fingerprint = self._branching_session_fingerprint(session)
            if not branch_tree_is_fresh(record, current_fingerprint):
                stale = mark_branch_tree_stale(
                    record,
                    reason="session_changed_since_tree_creation",
                    current_session_fingerprint=current_fingerprint,
                )
                self._persist_branching_tree_record(stale)
                self._append_branch_timeline_event(
                    session=session,
                    event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                    tree_id=tree_id,
                    session_fingerprint=current_fingerprint,
                    details={
                        "reason": "session_changed_since_tree_creation",
                        **self._branch_timeline_tree_details(stale),
                    },
                )
                raise ValueError("branching_tree_stale")
            if status not in {BRANCHING_TREE_STATUS_SIMULATED, BRANCHING_TREE_STATUS_NOT_APPLICABLE}:
                raise ValueError(f"branching_tree_not_selectable:{status}")
            node = find_branch_tree_node(record, node_id)
            if not isinstance(node, dict):
                raise KeyError(node_id)
            selectable = set(str(item) for item in (record.get("selectable_node_ids") or []))
            if node_id not in selectable:
                raise ValueError("branching_node_not_selectable")
            path_nodes = branch_tree_path_nodes(record, node_id)
            if not path_nodes:
                raise ValueError("branching_node_path_empty")

            selection_trace_id = trace_id or f"branching-tree-select-{uuid4().hex}"
            selected_path_node_ids = [str(item.get("node_id")) for item in path_nodes if item.get("node_id")]
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
                tree_id=tree_id,
                node_id=node_id,
                session_fingerprint=current_fingerprint,
                details={
                    "selected_path_node_ids": selected_path_node_ids,
                    "selected_path_option_ids": list(node.get("path_option_ids") or []),
                    "uses_normal_commit_path": True,
                    "adopts_simulated_snapshot": False,
                },
            )
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
                tree_id=tree_id,
                node_id=node_id,
                session_fingerprint=current_fingerprint,
                details={
                    "selected_path_node_ids": selected_path_node_ids,
                    "trace_id": selection_trace_id,
                },
            )
            replayed_turns: list[dict[str, Any]] = []
            committed_events: list[dict[str, Any]] = []
            replay_conflicts: list[dict[str, Any]] = []
            try:
                for path_node in path_nodes:
                    simulated_input = str(path_node.get("simulated_input") or "").strip()
                    if not simulated_input:
                        raise ValueError("branching_node_missing_simulated_input")
                    event = self._execute_turn_locked(
                        session_id=session_id,
                        player_input=simulated_input,
                        trace_id=selection_trace_id,
                    )
                    committed_events.append(copy.deepcopy(event))
                    matched, mismatch_fields = self._branching_replay_matches_node(
                        event=event,
                        simulation_node=path_node,
                    )
                    replay_row = {
                        "node_id": path_node.get("node_id"),
                        "path_option_ids": list(path_node.get("path_option_ids") or []),
                        "simulated_turn_id": path_node.get("simulated_turn_id"),
                        "committed_canonical_turn_id": event.get("canonical_turn_id"),
                        "committed_turn_number": event.get("turn_number"),
                        "simulated_input": simulated_input,
                        "matched_simulation_preview": matched,
                        "mismatch_fields": mismatch_fields,
                    }
                    replayed_turns.append(replay_row)
                    if not matched:
                        replay_conflicts.append(replay_row)
                        break
            except Exception as exc:
                failure_fingerprint = self._branching_session_fingerprint(session)
                self._append_branch_timeline_event(
                    session=session,
                    event_type=BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT,
                    tree_id=tree_id,
                    node_id=node_id,
                    canonical_turn_id=(
                        str(committed_events[-1].get("canonical_turn_id"))
                        if committed_events and isinstance(committed_events[-1], dict)
                        else None
                    ),
                    session_fingerprint=failure_fingerprint,
                    details={
                        "selection_status": "branch_replay_exception",
                        "replayed_turn_count": len(replayed_turns),
                        "replay_conflict_count": len(replay_conflicts),
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:240],
                        "uses_normal_commit_path": True,
                        "adopts_simulated_snapshot": False,
                    },
                )
                raise

            after_fingerprint = self._branching_session_fingerprint(session)
            selection_status = "branch_replay_conflict" if replay_conflicts else "committed"
            selection = {
                "schema_version": "branching_tree_selection.v1",
                "status": selection_status,
                "tree_id": tree_id,
                "selected_node_id": node_id,
                "selected_path_node_ids": selected_path_node_ids,
                "selected_path_option_ids": list(node.get("path_option_ids") or []),
                "trace_id": selection_trace_id,
                "replayed_turn_count": len(replayed_turns),
                "replayed_turns": replayed_turns,
                "replay_conflicts": replay_conflicts,
                "uses_normal_commit_path": True,
                "adopts_simulated_snapshot": False,
            }
            committed_record = mark_branch_tree_committed(
                record,
                node_id=node_id,
                selection=selection,
                current_session_fingerprint=after_fingerprint,
            )
            self._persist_branching_tree_record(committed_record)
            final_event_type = (
                BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_CONFLICT
                if replay_conflicts
                else BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED
            )
            last_committed_event = committed_events[-1] if committed_events else {}
            self._append_branch_timeline_event(
                session=session,
                event_type=final_event_type,
                tree_id=tree_id,
                node_id=node_id,
                canonical_turn_id=(
                    str(last_committed_event.get("canonical_turn_id"))
                    if isinstance(last_committed_event, dict) and last_committed_event.get("canonical_turn_id")
                    else None
                ),
                session_fingerprint=after_fingerprint,
                details={
                    "selection_status": selection_status,
                    "replayed_turn_count": len(replayed_turns),
                    "replay_conflict_count": len(replay_conflicts),
                    "committed_canonical_turn_ids": [
                        str(event.get("canonical_turn_id"))
                        for event in committed_events
                        if isinstance(event, dict) and event.get("canonical_turn_id")
                    ],
                    "uses_normal_commit_path": True,
                    "adopts_simulated_snapshot": False,
                },
            )
            self._mark_branching_trees_stale_for_session(
                session_id=session_id,
                except_tree_id=tree_id,
                current_session_fingerprint=after_fingerprint,
                reason="session_advanced_by_branch_selection",
            )
            return {
                "session_id": session_id,
                "tree_id": tree_id,
                "selection": selection,
                "committed_events": committed_events,
                "branching_tree": copy.deepcopy(committed_record),
            }

    def _branch_timeline_for_session(
        self,
        *,
        session: StorySession,
        current_session_fingerprint: dict[str, Any],
        scope: str = BRANCHING_TIMELINE_SCOPE_ACTIVE,
        preview: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timeline_id = stable_branch_timeline_id(
            story_session_id=session.session_id,
            scope=scope,
            preview=preview,
        )
        existing = self._branch_timelines.get(timeline_id)
        if isinstance(existing, dict):
            updated = copy.deepcopy(existing)
            updated["current_session_fingerprint"] = copy.deepcopy(current_session_fingerprint)
            if not updated.get("module_id"):
                updated["module_id"] = session.module_id
            if not updated.get("runtime_profile_id"):
                updated["runtime_profile_id"] = _runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                )
            return self._persist_branch_timeline_record(updated)
        record = make_branch_timeline_record(
            story_session_id=session.session_id,
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
            scope=scope,
            root_session_fingerprint=current_session_fingerprint,
            preview=preview,
        )
        return self._persist_branch_timeline_record(record)

    def _append_branch_timeline_event_for_session(
        self,
        *,
        session_id: str,
        event_type: str,
        tree_id: str | None = None,
        node_id: str | None = None,
        canonical_turn_id: str | None = None,
        session_fingerprint: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        return self._append_branch_timeline_event(
            session=session,
            event_type=event_type,
            tree_id=tree_id,
            node_id=node_id,
            canonical_turn_id=canonical_turn_id,
            session_fingerprint=session_fingerprint,
            details=details,
        )

    def _append_branch_timeline_event(
        self,
        *,
        session: StorySession,
        event_type: str,
        tree_id: str | None = None,
        node_id: str | None = None,
        canonical_turn_id: str | None = None,
        session_fingerprint: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fingerprint = session_fingerprint or self._branching_session_fingerprint(session)
        timeline = self._branch_timeline_for_session(
            session=session,
            current_session_fingerprint=fingerprint,
        )
        event = make_branch_timeline_event(
            event_type=event_type,
            story_session_id=session.session_id,
            timeline_id=str(timeline.get("timeline_id") or ""),
            scope=str(timeline.get("scope") or BRANCHING_TIMELINE_SCOPE_ACTIVE),
            tree_id=tree_id,
            node_id=node_id,
            canonical_turn_id=canonical_turn_id,
            session_fingerprint=fingerprint,
            details=details,
        )
        updated = append_branch_timeline_event(timeline, event)
        updated["current_session_fingerprint"] = copy.deepcopy(fingerprint)
        return self._persist_branch_timeline_record(updated)

    def _branch_timeline_tree_details(self, record: dict[str, Any]) -> dict[str, Any]:
        summary = record.get("summary") if isinstance(record.get("summary"), dict) else {}
        return {
            "tree_status": record.get("status"),
            "schema_version": record.get("schema_version"),
            "root_canonical_turn_id": record.get("root_canonical_turn_id"),
            "root_turn_number": record.get("root_turn_number"),
            "selectable_node_count": int(summary.get("selectable_node_count") or 0),
            "simulated_turn_count": int(summary.get("simulated_turn_count") or 0),
            "max_depth_observed": int(summary.get("max_depth_observed") or 0),
            "selection_required_to_commit": bool(record.get("selection_required_to_commit")),
            "selection_replays_normal_commit_path": bool(record.get("selection_replays_normal_commit_path")),
            "adopts_simulated_snapshot": bool(record.get("adopts_simulated_snapshot")),
        }

    def _enforce_branch_timeline_tree_bounds(
        self,
        *,
        session_id: str,
        current_session_fingerprint: dict[str, Any],
    ) -> None:
        active_records = [
            record
            for record in self._branching_trees.values()
            if record.get("story_session_id") == session_id
            and str(record.get("status") or "")
            in {
                BRANCHING_TREE_STATUS_SIMULATED,
                BRANCHING_TREE_STATUS_NOT_APPLICABLE,
            }
        ]
        if len(active_records) <= BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES:
            return
        active_records.sort(key=lambda row: str(row.get("created_at") or row.get("updated_at") or ""))
        overflow = active_records[: max(0, len(active_records) - BRANCHING_TIMELINE_DEFAULT_MAX_ACTIVE_TREES)]
        session = self.get_session(session_id)
        for record in overflow:
            tree_id = str(record.get("tree_id") or "")
            stale = mark_branch_tree_stale(
                record,
                reason="branch_timeline_active_tree_bound",
                current_session_fingerprint=current_session_fingerprint,
            )
            self._persist_branching_tree_record(stale)
            self._append_branch_timeline_event(
                session=session,
                event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                tree_id=tree_id,
                session_fingerprint=current_session_fingerprint,
                details={
                    "reason": "branch_timeline_active_tree_bound",
                    **self._branch_timeline_tree_details(stale),
                },
            )

    def _branching_session_fingerprint(self, session: StorySession) -> dict[str, Any]:
        last_turn = session.history[-1] if session.history else {}
        last_canonical_turn_id = (
            last_turn.get("canonical_turn_id") if isinstance(last_turn, dict) else None
        )
        runtime_profile_id = _runtime_profile_id_from_projection(
            session.runtime_projection if isinstance(session.runtime_projection, dict) else None
        )
        payload = {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "runtime_profile_id": runtime_profile_id,
            "turn_counter": session.turn_counter,
            "history_count": len(session.history or []),
            "current_scene_id": session.current_scene_id,
            "last_canonical_turn_id": last_canonical_turn_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:24]
        return {
            **payload,
            "fingerprint": fingerprint,
            "content_provenance_hash": hashlib.sha256(
                json.dumps(session.content_provenance, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
            "runtime_projection_hash": hashlib.sha256(
                json.dumps(session.runtime_projection, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
        }

    def _refresh_branching_tree_freshness(self, record: dict[str, Any]) -> dict[str, Any]:
        status = str(record.get("status") or "")
        if status in {
            BRANCHING_TREE_STATUS_STALE,
            BRANCHING_TREE_STATUS_EXPIRED,
            BRANCHING_TREE_STATUS_COMMITTED,
        }:
            return record
        session_id = str(record.get("story_session_id") or "")
        try:
            current_fingerprint = self._branching_session_fingerprint(self.get_session(session_id))
        except KeyError:
            return record
        if branch_tree_is_fresh(record, current_fingerprint):
            return record
        stale = mark_branch_tree_stale(
            record,
            reason="session_changed_since_tree_creation",
            current_session_fingerprint=current_fingerprint,
        )
        persisted = self._persist_branching_tree_record(stale)
        try:
            self._append_branch_timeline_event_for_session(
                session_id=session_id,
                event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                tree_id=str(persisted.get("tree_id") or ""),
                session_fingerprint=current_fingerprint,
                details={
                    "reason": "session_changed_since_tree_creation",
                    **self._branch_timeline_tree_details(persisted),
                },
            )
        except KeyError:
            pass
        return persisted

    def _mark_branching_trees_stale_for_session(
        self,
        *,
        session_id: str,
        except_tree_id: str | None,
        current_session_fingerprint: dict[str, Any],
        reason: str,
    ) -> None:
        for tree_id, record in list(self._branching_trees.items()):
            if tree_id == except_tree_id:
                continue
            if record.get("story_session_id") != session_id:
                continue
            if str(record.get("status") or "") not in {
                BRANCHING_TREE_STATUS_SIMULATED,
                BRANCHING_TREE_STATUS_NOT_APPLICABLE,
            }:
                continue
            stale = mark_branch_tree_stale(
                record,
                reason=reason,
                current_session_fingerprint=current_session_fingerprint,
            )
            persisted = self._persist_branching_tree_record(stale)
            try:
                self._append_branch_timeline_event_for_session(
                    session_id=session_id,
                    event_type=BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
                    tree_id=str(persisted.get("tree_id") or ""),
                    session_fingerprint=current_session_fingerprint,
                    details={"reason": reason, **self._branch_timeline_tree_details(persisted)},
                )
            except KeyError:
                continue

    def _branching_replay_matches_node(
        self,
        *,
        event: dict[str, Any],
        simulation_node: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        preview_commit = (
            simulation_node.get("narrative_commit_preview")
            if isinstance(simulation_node.get("narrative_commit_preview"), dict)
            else {}
        )
        actual_commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
        mismatch_fields: list[str] = []
        for field_name in ("committed_scene_id", "situation_status", "commit_reason_code"):
            if preview_commit.get(field_name) != actual_commit.get(field_name):
                mismatch_fields.append(f"narrative_commit.{field_name}")
        preview_validation_status = simulation_node.get("validation_status")
        actual_validation = event.get("validation_outcome") if isinstance(event.get("validation_outcome"), dict) else {}
        if preview_validation_status and preview_validation_status != actual_validation.get("status"):
            mismatch_fields.append("validation_outcome.status")
        return not mismatch_fields, mismatch_fields

    def _latest_branching_forecast_from_session(self, session: StorySession) -> dict[str, Any]:
        for row in reversed(session.history or []):
            if not isinstance(row, dict):
                continue
            forecast = row.get("branching_forecast")
            if not isinstance(forecast, dict):
                ledger = row.get("turn_aspect_ledger")
                if isinstance(ledger, dict):
                    forecast = ledger.get("branching_forecast")
            if isinstance(forecast, dict):
                return copy.deepcopy(forecast)
        return {}

    def _branching_simulation_clone_session_id(
        self,
        *,
        root_session_id: str,
        path_option_ids: list[str],
    ) -> str:
        seed = "|".join([root_session_id, *path_option_ids])
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        return f"{root_session_id}:branch-sim:{digest}"

    def _branching_simulation_session_clone(
        self,
        *,
        base_session_snapshot: StorySession,
        clone_session_id: str,
        path_option_ids: list[str],
    ) -> StorySession:
        clone = story_session_from_payload(story_session_to_payload(base_session_snapshot))
        clone.session_id = clone_session_id
        clone.content_provenance = copy.deepcopy(clone.content_provenance)
        trace_classification = (
            clone.content_provenance.get("trace_classification")
            if isinstance(clone.content_provenance.get("trace_classification"), dict)
            else {}
        )
        trace_classification = {
            **trace_classification,
            "trace_origin": "branching_simulation",
            "execution_tier": "diagnostic",
            "canonical_player_flow": False,
        }
        clone.content_provenance["trace_classification"] = trace_classification
        clone.content_provenance["branching_simulation"] = {
            "source_session_id": base_session_snapshot.session_id,
            "path_option_ids": list(path_option_ids),
            "simulation_only": True,
            "mutates_active_session": False,
        }
        return clone

    def _execute_branching_simulation_turn_on_clone(
        self,
        *,
        base_session_snapshot: StorySession,
        clone_session_id: str,
        simulated_input: str,
        trace_id: str,
        path_option_ids: list[str],
    ) -> tuple[dict[str, Any] | None, StorySession | None, str | None]:
        clone = self._branching_simulation_session_clone(
            base_session_snapshot=base_session_snapshot,
            clone_session_id=clone_session_id,
            path_option_ids=path_option_ids,
        )
        had_session = clone_session_id in self.sessions
        prior_session = self.sessions.get(clone_session_id)
        with self._session_locks_guard:
            had_lock = clone_session_id in self._session_turn_locks
            prior_lock = self._session_turn_locks.get(clone_session_id)
            self._session_turn_locks[clone_session_id] = threading.Lock()
        try:
            self._branching_simulation_session_ids.add(clone_session_id)
            self.sessions[clone_session_id] = clone
            event = self._execute_turn_locked(
                session_id=clone_session_id,
                player_input=simulated_input,
                trace_id=trace_id,
            )
            simulated_snapshot = story_session_from_payload(
                story_session_to_payload(self.sessions[clone_session_id])
            )
            return event, simulated_snapshot, None
        except Exception as exc:
            logger.debug("Branching simulation clone turn failed", exc_info=True)
            return None, clone, str(exc)
        finally:
            self._branching_simulation_session_ids.discard(clone_session_id)
            if had_session and prior_session is not None:
                self.sessions[clone_session_id] = prior_session
            else:
                self.sessions.pop(clone_session_id, None)
            with self._session_locks_guard:
                if had_lock and prior_lock is not None:
                    self._session_turn_locks[clone_session_id] = prior_lock
                else:
                    self._session_turn_locks.pop(clone_session_id, None)

    def _branching_simulation_stop_reason(
        self,
        *,
        depth: int,
        max_depth: int,
        simulated_event: dict[str, Any] | None,
        child_forecast: dict[str, Any],
        error: str | None,
    ) -> str | None:
        if error:
            return "simulation_error"
        event = simulated_event if isinstance(simulated_event, dict) else {}
        narrative_commit = (
            event.get("narrative_commit")
            if isinstance(event.get("narrative_commit"), dict)
            else {}
        )
        if bool(narrative_commit.get("is_terminal")) or str(narrative_commit.get("situation_status") or "") == "terminal":
            return "terminal_turn"
        if depth >= max_depth:
            return "max_depth"
        if not forecast_has_options(child_forecast):
            return "no_branching_options"
        return None

    def _execute_turn_locked(self, *, session_id: str, player_input: str, trace_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        self._assert_live_player_governance()
        session.turn_counter += 1
        session.updated_at = datetime.now(timezone.utc)
        commit_turn_number = session.turn_counter
        prior_scene_id = session.current_scene_id
        history_tail = session.history[-(NARRATIVE_COMMIT_HISTORY_TAIL - 1) :]
        graph_threads, graph_summary = build_graph_thread_export(session.narrative_threads)
        host_experience_template = (
            goc_host_experience_template(session.runtime_projection)
            if session.module_id == GOD_OF_CARNAGE_MODULE_ID
            else None
        )
        try:
            prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
            # Feed the prior committed beat back into the graph so the director
            # can key pacing and responder decisions off a stable continuity
            # identity rather than the loose prior_continuity_impacts list.
            prior_beat = _prior_beat_from_session(session)
            prior_signature = _beat_to_dramatic_signature(prior_beat)
            prior_social_state_record = _prior_social_state_record_from_session(session)
            prior_planner_truth = _prior_planner_truth_from_session(session)
            prior_narrative_thread_state = _prior_narrative_thread_state_from_session(
                session,
                graph_threads=graph_threads,
                graph_summary=graph_summary,
            )
            prior_callback_web_state = self._prior_callback_web_state_for_graph(session)
            prior_consequence_cascade_state = self._prior_consequence_cascade_state_for_graph(session)
            prior_pacing_rhythm_state = _prior_pacing_rhythm_state_from_session(session)
            _, prior_memory_policy = _load_module_memory_policy(
                module_id=session.module_id,
                runtime_profile_id=_runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                ),
            )
            hierarchical_memory_context = project_hierarchical_memory_context(
                snapshot=session.hierarchical_memory
                if isinstance(session.hierarchical_memory, dict)
                else None,
                memory_policy=prior_memory_policy,
            )
            graph_state = self.turn_graph.run(
                session_id=session.session_id,
                module_id=session.module_id,
                current_scene_id=session.current_scene_id,
                player_input=player_input,
                trace_id=trace_id,
                host_versions={"world_engine_app_version": APP_VERSION},
                active_narrative_threads=graph_threads or None,
                thread_pressure_summary=graph_summary,
                host_experience_template=host_experience_template,
                prior_continuity_impacts=prior_ci if prior_ci else None,
                prior_dramatic_signature=prior_signature,
                prior_social_state_record=prior_social_state_record,
                prior_narrative_thread_state=prior_narrative_thread_state,
                prior_callback_web_state=prior_callback_web_state,
                prior_consequence_cascade_state=prior_consequence_cascade_state,
                prior_pacing_rhythm_state=prior_pacing_rhythm_state,
                prior_planner_truth=prior_planner_truth,
                hierarchical_memory_context=hierarchical_memory_context,
                turn_number=commit_turn_number,
                turn_initiator_type="player",
                live_player_truth_surface=True,
                actor_lane_context=self._extract_actor_lane_context(session),
                session_output_language=session.session_output_language,
                story_runtime_experience=self._story_runtime_experience_policy().effective,
                validation_execution_mode=self._validation_execution_mode(),
                environment_state=session.environment_state
                if isinstance(session.environment_state, dict)
                else None,
            )
        except Exception as exc:
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_turn",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            gmsg = _recoverable_turn_message(session=session, reason="graph_execution_exception")
            turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
                session_id=session.session_id,
                module_id=session.module_id,
                turn_number=commit_turn_number,
                turn_kind="player_graph_exception_playable",
                player_input=player_input,
                trace_id=trace_id,
                reason="graph_execution_exception",
                validation_status="rejected",
                visible_output_present=True,
            )
            val_graph_exc: dict[str, Any] = {
                "status": "rejected",
                "reason": "graph_execution_exception",
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
                "parser_or_model_failure": True,
            }
            event = _recoverable_playable_turn_envelope(
                session=session,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                trace_id=trace_id,
                turn_kind="player_graph_exception_playable",
                interpreted_input={},
                narrative_commit={
                    "situation_status": "continue",
                    "allowed": False,
                    "commit_reason_code": "graph_execution_exception",
                    "committed_scene_id": prior_scene_id,
                    "proposed_scene_id": prior_scene_id,
                    "selected_candidate_source": "runtime_exception_gate",
                    "is_terminal": False,
                },
                validation_outcome=val_graph_exc,
                message=gmsg,
                turn_aspect_ledger=turn_aspect_ledger,
                reason="graph_execution_exception",
                diagnostics_extras={
                    "failure_class": "graph_execution_exception",
                    "exception_type": type(exc).__name__,
                },
            )
            graph_state_recoverable = {
                "session_id": session.session_id,
                "module_id": session.module_id,
                "turn_number": commit_turn_number,
                "turn_kind": "player_graph_exception_playable",
                "player_input": player_input,
                "trace_id": trace_id,
                "interpreted_input": {},
                "generation": {
                    "success": False,
                    "error": str(exc),
                    "metadata": {"error": str(exc), "exception_type": type(exc).__name__},
                },
                "graph_errors": ["graph_execution_exception"],
                "validation_outcome": val_graph_exc,
                "visible_output_bundle": event["visible_output_bundle"],
                "turn_aspect_ledger": turn_aspect_ledger,
            }
            return self._persist_player_visible_turn_event(
                session=session,
                graph_state=graph_state_recoverable,
                event=event,
                trace_id=trace_id,
                commit_turn_number=commit_turn_number,
                player_input=player_input,
                turn_outcome="recoverable_graph_exception",
            )

        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            if is_hard_boundary_failure(val):
                session.turn_counter -= 1
                raise RuntimeError(f"Hard narrative boundary: {val.get('reason') or 'rejected'}")
            return self._build_recoverable_rejection_turn(
                session=session,
                graph_state=graph_state,
                trace_id=trace_id,
                attempted_turn_number=commit_turn_number,
                player_input=player_input,
                prior_scene_id=prior_scene_id,
                validation_outcome=val,
            )
        return self._finalize_committed_turn(
            session=session,
            graph_state=graph_state,
            trace_id=trace_id,
            commit_turn_number=commit_turn_number,
            player_input=player_input,
            turn_kind="player",
            prior_scene_id=prior_scene_id,
            history_tail=history_tail,
            graph_threads=graph_threads,
            graph_summary=graph_summary,
            host_experience_template=host_experience_template,
            prior_ci=prior_ci,
        )

    def _persist_player_visible_turn_event(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        event: dict[str, Any],
        trace_id: str | None,
        commit_turn_number: int,
        player_input: str,
        turn_outcome: str,
    ) -> dict[str, Any]:
        """Persist a player-visible non-approved outcome as a canonical turn."""
        event.setdefault("canonical_turn_id", _canonical_turn_id(session.session_id, commit_turn_number))
        event.setdefault("http_status", 200)
        event.setdefault("turn_status", "rejected_recoverable")
        event.setdefault("trace_id", trace_id or "")
        event.setdefault("raw_input", player_input)
        if isinstance(event.get("turn_aspect_ledger"), dict):
            event["turn_aspect_ledger"] = _stamp_turn_aspect_ledger_identity(
                event.get("turn_aspect_ledger"),
                session=session,
                commit_turn_number=commit_turn_number,
                turn_kind=str(event.get("turn_kind") or "player_rejected_recoverable"),
            )
        interpreted_input = (
            event.get("interpreted_input")
            if isinstance(event.get("interpreted_input"), dict)
            else graph_state.get("interpreted_input")
            if isinstance(graph_state.get("interpreted_input"), dict)
            else {}
        )
        selected_responder_set = (
            event.get("selected_responder_set")
            if isinstance(event.get("selected_responder_set"), list)
            else graph_state.get("selected_responder_set")
            if isinstance(graph_state.get("selected_responder_set"), list)
            else []
        )
        human_att = _build_human_input_attribution_record(
            session=session,
            graph_state=graph_state,
            interpreted_input=interpreted_input,
            selected_responder_set=selected_responder_set,
            commit_turn_number=commit_turn_number,
            player_input=player_input,
        )
        graph_state["human_input_attribution"] = human_att
        event["human_input_attribution"] = human_att
        retrieval = (
            graph_state.get("retrieval")
            if isinstance(graph_state.get("retrieval"), dict)
            else {}
        )
        routing = (
            graph_state.get("routing")
            if isinstance(graph_state.get("routing"), dict)
            else {}
        )
        generation = (
            graph_state.get("generation")
            if isinstance(graph_state.get("generation"), dict)
            else {}
        )
        graph_diag = (
            graph_state.get("graph_diagnostics")
            if isinstance(graph_state.get("graph_diagnostics"), dict)
            else {}
        )
        if retrieval:
            event.setdefault("retrieval", retrieval)
        if routing or generation:
            event.setdefault("model_route", {**routing, "generation": generation})
        if graph_diag:
            event.setdefault("graph", graph_diag)
        if graph_state.get("selected_scene_function") is not None:
            event.setdefault("selected_scene_function", graph_state.get("selected_scene_function"))
        if isinstance(graph_state.get("scene_energy_target"), dict):
            event.setdefault("scene_energy_target", graph_state.get("scene_energy_target"))
        if isinstance(graph_state.get("scene_energy_transition"), dict):
            event.setdefault("scene_energy_transition", graph_state.get("scene_energy_transition"))
        if isinstance(graph_state.get("scene_energy_validation"), dict):
            event.setdefault("scene_energy_validation", graph_state.get("scene_energy_validation"))
        if isinstance(graph_state.get("pacing_rhythm_state"), dict):
            event.setdefault("pacing_rhythm_state", graph_state.get("pacing_rhythm_state"))
        if isinstance(graph_state.get("pacing_rhythm_target"), dict):
            event.setdefault("pacing_rhythm_target", graph_state.get("pacing_rhythm_target"))
        if isinstance(graph_state.get("pacing_rhythm_validation"), dict):
            event.setdefault("pacing_rhythm_validation", graph_state.get("pacing_rhythm_validation"))
        if selected_responder_set:
            event.setdefault("selected_responder_set", selected_responder_set)
        actor_survival_telemetry = (
            graph_state.get("actor_survival_telemetry")
            if isinstance(graph_state.get("actor_survival_telemetry"), dict)
            else {}
        )
        if actor_survival_telemetry:
            event.setdefault("actor_survival_telemetry", actor_survival_telemetry)
        graph_state.setdefault("turn_aspect_ledger", event.get("turn_aspect_ledger"))
        graph_state.setdefault("validation_outcome", event.get("validation_outcome"))
        graph_state.setdefault("visible_output_bundle", event.get("visible_output_bundle"))
        graph_state.setdefault("interpreted_input", interpreted_input)
        _record_hierarchical_memory_aspect(
            session=session,
            graph_state=graph_state,
            event=event,
            committed_turn={
                "canonical_turn_id": event.get("canonical_turn_id"),
                "module_id": session.module_id,
                "runtime_profile_id": _runtime_profile_id_from_projection(
                    session.runtime_projection if isinstance(session.runtime_projection, dict) else None
                ),
                "turn_number": commit_turn_number,
                "turn_kind": event.get("turn_kind") or "player_rejected_recoverable",
                "turn_outcome": turn_outcome,
                "recoverable_outcome": True,
                "narrative_commit": event.get("narrative_commit"),
                "turn_aspect_ledger": event.get("turn_aspect_ledger"),
                "visible_output_bundle": event.get("visible_output_bundle"),
            },
            allow_write=False,
        )
        if isinstance(event.get("diagnostics"), dict):
            event["diagnostics"]["turn_aspect_ledger"] = event.get("turn_aspect_ledger")
            event["diagnostics"]["hierarchical_memory"] = event.get("hierarchical_memory")
        turn_lc = TurnLifecycleChain()
        turn_lc.advance("received")
        turn_lc.advance("interpreted")
        turn_lc.advance("generated_or_resolved")
        turn_lc.advance("validated")
        turn_lc.advance("committed")
        turn_lc.advance("projected")

        canonical_record = {
            "canonical_turn_id": event["canonical_turn_id"],
            "turn_number": commit_turn_number,
            "turn_kind": event.get("turn_kind") or "player_rejected_recoverable",
            "trace_id": trace_id or "",
            "turn_outcome": turn_outcome,
            "narrative_commit": event.get("narrative_commit"),
            "validation_outcome": event.get("validation_outcome"),
            "committed_result": event.get("committed_result")
            if isinstance(event.get("committed_result"), dict)
            else graph_state.get("committed_result"),
            "turn_aspect_ledger": event.get("turn_aspect_ledger"),
            "visible_output_bundle": event.get("visible_output_bundle"),
            "scene_energy_target": event.get("scene_energy_target"),
            "scene_energy_transition": event.get("scene_energy_transition"),
            "scene_energy_validation": event.get("scene_energy_validation"),
            "pacing_rhythm_state": event.get("pacing_rhythm_state"),
            "pacing_rhythm_target": event.get("pacing_rhythm_target"),
            "pacing_rhythm_validation": event.get("pacing_rhythm_validation"),
            "human_input_attribution": human_att,
            "hierarchical_memory_update": event.get("hierarchical_memory"),
            "recoverable_outcome": True,
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
            },
        }
        turn_lc.advance("persisted")
        canonical_record["lifecycle_state"] = "observed"
        event["lifecycle_state"] = "observed"
        session.history.append(canonical_record)
        self._refresh_callback_web_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._refresh_consequence_cascade_after_commit(
            session=session,
            event=event,
            graph_state=graph_state,
        )
        self._emit_observability_path_for_event(session=session, graph_state=graph_state, event=event)
        session.diagnostics.append(event)
        turn_lc.advance("observed")
        session.updated_at = datetime.now(timezone.utc)
        self._persist_session(session)
        return event

    def _build_recoverable_rejection_turn(
        self,
        *,
        session: StorySession,
        graph_state: dict[str, Any],
        trace_id: str | None,
        attempted_turn_number: int,
        player_input: str,
        prior_scene_id: str,
        validation_outcome: dict[str, Any],
    ) -> dict[str, Any]:
        reason = str(validation_outcome.get("reason") or "rejected")
        interpreted_input = (
            graph_state.get("interpreted_input")
            if isinstance(graph_state.get("interpreted_input"), dict)
            else {}
        )
        message = _recoverable_turn_message(session=session, reason=reason)
        turn_aspect_ledger = _recoverable_runtime_aspect_ledger(
            session_id=session.session_id,
            module_id=session.module_id,
            turn_number=attempted_turn_number,
            turn_kind="player_rejected_recoverable",
            player_input=player_input,
            trace_id=trace_id,
            reason=reason,
            validation_status=str(validation_outcome.get("status") or "rejected"),
            existing_ledger=graph_state.get("turn_aspect_ledger")
            if isinstance(graph_state.get("turn_aspect_ledger"), dict)
            else None,
            visible_output_present=True,
        )
        val_merged: dict[str, Any] = {
            **validation_outcome,
            "recoverable_rejection": True,
            "hard_boundary_failure": False,
        }
        event = _recoverable_playable_turn_envelope(
            session=session,
            commit_turn_number=attempted_turn_number,
            player_input=player_input,
            trace_id=trace_id,
            turn_kind="player_rejected_recoverable",
            interpreted_input=interpreted_input,
            narrative_commit={
                "situation_status": "continue",
                "allowed": False,
                "commit_reason_code": "recoverable_rejection",
                "committed_scene_id": prior_scene_id,
                "proposed_scene_id": prior_scene_id,
                "selected_candidate_source": "validation_gate",
                "is_terminal": False,
            },
            validation_outcome=val_merged,
            message=message,
            turn_aspect_ledger=turn_aspect_ledger,
            reason=reason,
        )
        graph_state["turn_aspect_ledger"] = turn_aspect_ledger
        graph_state["visible_output_bundle"] = event["visible_output_bundle"]
        graph_state["validation_outcome"] = event["validation_outcome"]
        return self._persist_player_visible_turn_event(
            session=session,
            graph_state=graph_state,
            event=event,
            trace_id=trace_id,
            commit_turn_number=attempted_turn_number,
            player_input=player_input,
            turn_outcome="recoverable_rejection",
        )

    def get_session(self, session_id: str) -> StorySession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def list_session_summaries(self) -> list[dict[str, Any]]:
        """Lightweight rows for admin/ops consoles (no full history or diagnostics)."""
        rows: list[dict[str, Any]] = []
        for sid, session in self.sessions.items():
            rows.append(
                {
                    "session_id": sid,
                    "module_id": session.module_id,
                    "turn_counter": session.turn_counter,
                    "current_scene_id": session.current_scene_id,
                    "content_provenance": session.content_provenance,
                    "updated_at": session.updated_at.isoformat(),
                    "created_at": session.created_at.isoformat(),
                }
            )
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows

    def get_state(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        last_narrative_commit: dict[str, Any] | None = None
        last_committed_turn_authority: dict[str, Any] | None = None
        last_dramatic_context_summary: dict[str, Any] | None = None
        last_actor_turn_summary: dict[str, Any] | None = None
        last_branching_forecast: dict[str, Any] | None = None
        last_committed_turn = session.history[-1] if session.history else None
        if isinstance(last_committed_turn, dict):
            nc = last_committed_turn.get("narrative_commit")
            if isinstance(nc, dict):
                last_narrative_commit = nc
            authority = last_committed_turn.get("committed_turn_authority")
            if isinstance(authority, dict):
                last_committed_turn_authority = authority
            dramatic_context = last_committed_turn.get("dramatic_context_summary")
            if isinstance(dramatic_context, dict):
                last_dramatic_context_summary = dramatic_context
            actor_summary = last_committed_turn.get("actor_turn_summary")
            if isinstance(actor_summary, dict):
                last_actor_turn_summary = actor_summary
            branching = last_committed_turn.get("branching_forecast")
            if not isinstance(branching, dict):
                ledger = last_committed_turn.get("turn_aspect_ledger")
                if isinstance(ledger, dict):
                    branching = ledger.get("branching_forecast")
            if isinstance(branching, dict):
                last_branching_forecast = branching

        summary: dict[str, Any] | None = None
        if isinstance(last_narrative_commit, dict):
            planner_truth = (
                last_narrative_commit.get("planner_truth")
                if isinstance(last_narrative_commit.get("planner_truth"), dict)
                else {}
            )
            if not last_actor_turn_summary and planner_truth:
                last_actor_turn_summary = {
                    "contract": "actor_turn_summary.v1",
                    "primary_responder_id": planner_truth.get("primary_responder_id")
                    or planner_truth.get("responder_id"),
                    "secondary_responder_ids": planner_truth.get("secondary_responder_ids") or [],
                    "spoken_line_count": planner_truth.get("spoken_line_count") or 0,
                    "action_line_count": planner_truth.get("action_line_count") or 0,
                    "initiative_summary": planner_truth.get("initiative_summary") or {},
                    "last_actor_outcome_summary": planner_truth.get("last_actor_outcome_summary"),
                }
            summary = {
                "situation_status": last_narrative_commit.get("situation_status"),
                "allowed": last_narrative_commit.get("allowed"),
                "commit_reason_code": last_narrative_commit.get("commit_reason_code"),
                "committed_scene_id": last_narrative_commit.get("committed_scene_id"),
                "proposed_scene_id": last_narrative_commit.get("proposed_scene_id"),
                "selected_candidate_source": last_narrative_commit.get("selected_candidate_source"),
                "is_terminal": last_narrative_commit.get("is_terminal"),
                "primary_responder_id": (
                    (last_actor_turn_summary or {}).get("primary_responder_id")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
                "spoken_line_count": (
                    (last_actor_turn_summary or {}).get("spoken_line_count")
                    if isinstance(last_actor_turn_summary, dict)
                    else 0
                ),
                "action_line_count": (
                    (last_actor_turn_summary or {}).get("action_line_count")
                    if isinstance(last_actor_turn_summary, dict)
                    else 0
                ),
                "initiative_summary": (
                    (last_actor_turn_summary or {}).get("initiative_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else {}
                ),
                "last_actor_outcome_summary": (
                    (last_actor_turn_summary or {}).get("last_actor_outcome_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
            }

        last_consequences: list[str] = []
        last_open_pressures: list[str] = []
        if isinstance(last_narrative_commit, dict):
            lc = last_narrative_commit.get("committed_consequences")
            if isinstance(lc, list):
                last_consequences = [str(x) for x in lc]
            op = last_narrative_commit.get("open_pressures")
            if isinstance(op, list):
                last_open_pressures = [str(x) for x in op]

        thread_metrics = thread_continuity_metrics(session.narrative_threads)
        module_scope_truth = _module_scope_truth(session.module_id)
        _, memory_policy = _load_module_memory_policy(
            module_id=session.module_id,
            runtime_profile_id=_runtime_profile_id_from_projection(
                session.runtime_projection if isinstance(session.runtime_projection, dict) else None
            ),
        )
        hierarchical_memory_context = project_hierarchical_memory_context(
            snapshot=session.hierarchical_memory
            if isinstance(session.hierarchical_memory, dict)
            else None,
            memory_policy=memory_policy,
        )
        last_thread_summary: str | None = None
        if session.last_thread_update_trace is not None:
            last_thread_summary = session.last_thread_update_trace.summary or None

        story_entries = _story_window_entries_for_session(session)
        player_shell_context = _player_shell_context_from_dramatic_context(
            last_dramatic_context_summary,
            session=session,
        )
        history_rows = session.history or []
        committed_canonical_turn_count = len(history_rows)
        opening_committed = any(
            isinstance(h, dict) and str(h.get("turn_kind") or "") == "opening" for h in history_rows
        )
        player_committed_turns = sum(
            1
            for h in history_rows
            if isinstance(h, dict) and str(h.get("turn_kind") or "") != "opening"
        )
        total_canonical_turns = committed_canonical_turn_count
        last_hist = history_rows[-1] if history_rows else None
        latest_canonical_turn_id: str | None = None
        if isinstance(last_hist, dict):
            lid = str(last_hist.get("canonical_turn_id") or "").strip()
            latest_canonical_turn_id = lid or None
        callback_web_snapshot: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
            snapshot = callback_web.get("snapshot") if isinstance(callback_web.get("snapshot"), dict) else {}
            callback_web_snapshot = copy.deepcopy(snapshot)
        except Exception:
            callback_web_snapshot = None
        consequence_cascade_snapshot: dict[str, Any] | None = None
        try:
            cascade = self.get_consequence_cascade(session_id=session.session_id)
            snapshot = cascade.get("snapshot") if isinstance(cascade.get("snapshot"), dict) else {}
            consequence_cascade_snapshot = copy.deepcopy(snapshot)
        except Exception:
            consequence_cascade_snapshot = None

        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "committed_canonical_turn_count": committed_canonical_turn_count,
            "opening_committed": opening_committed,
            "player_committed_turns": player_committed_turns,
            "total_canonical_turns": total_canonical_turns,
            "canonical_turn_count": total_canonical_turns,
            "latest_canonical_turn_id": latest_canonical_turn_id,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
            "history_count": len(history_rows),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "environment_state": session.environment_state
                if isinstance(session.environment_state, dict)
                else {},
                "last_narrative_commit": last_narrative_commit,
                "last_committed_turn_authority": last_committed_turn_authority,
                "last_dramatic_context_summary": last_dramatic_context_summary,
                "last_actor_turn_summary": last_actor_turn_summary,
                "last_branching_forecast": last_branching_forecast,
                "callback_web": callback_web_snapshot,
                "callback_web_continuity": callback_web_snapshot,
                "consequence_cascade": consequence_cascade_snapshot,
                "last_actor_outcome_summary": (
                    last_actor_turn_summary.get("last_actor_outcome_summary")
                    if isinstance(last_actor_turn_summary, dict)
                    else None
                ),
                "player_shell_context": player_shell_context,
                "module_scope_truth": module_scope_truth,
                "last_narrative_commit_summary": summary,
                "last_committed_consequences": last_consequences,
                "last_open_pressures": last_open_pressures,
                "narrative_thread_continuity": {
                    "narrative_threads": session.narrative_threads.model_dump(mode="json"),
                    "active_narrative_threads": [
                        t.model_dump(mode="json")
                        for t in session.narrative_threads.active
                        if t.status != "resolved"
                    ],
                    "thread_count": thread_metrics["thread_count"],
                    "dominant_thread_kind": thread_metrics["dominant_thread_kind"],
                    "thread_pressure_level": thread_metrics["thread_pressure_level"],
                    "last_narrative_thread_update_summary": last_thread_summary,
                },
                "hierarchical_memory": {
                    "snapshot": session.hierarchical_memory,
                    "context": hierarchical_memory_context,
                },
            },
            "module_scope_truth": module_scope_truth,
            "player_shell_context": player_shell_context,
            "branching_forecast": last_branching_forecast,
            "callback_web": callback_web_snapshot,
            "consequence_cascade": consequence_cascade_snapshot,
            "story_window": {
                "contract": "authoritative_story_window_v1",
                "source": "world_engine_story_runtime",
                "entries": story_entries,
                "entry_count": len(story_entries),
                "latest_entry": story_entries[-1] if story_entries else None,
            },
            "last_committed_turn": last_committed_turn,
            "updated_at": session.updated_at.isoformat(),
        }

    def get_diagnostics(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        committed_state = {
            "current_scene_id": session.current_scene_id,
            "turn_counter": session.turn_counter,
            "environment_state": session.environment_state
            if isinstance(session.environment_state, dict)
            else {},
        }
        trace_payload: dict[str, Any] | None = None
        if session.last_thread_update_trace is not None:
            trace_payload = session.last_thread_update_trace.model_dump(mode="json")
        callback_web_snapshot: dict[str, Any] | None = None
        try:
            callback_web = self.get_callback_web(session_id=session.session_id)
            if isinstance(callback_web.get("snapshot"), dict):
                callback_web_snapshot = copy.deepcopy(callback_web["snapshot"])
        except Exception:
            callback_web_snapshot = None
        consequence_cascade_snapshot: dict[str, Any] | None = None
        try:
            cascade = self.get_consequence_cascade(session_id=session.session_id)
            if isinstance(cascade.get("snapshot"), dict):
                consequence_cascade_snapshot = copy.deepcopy(cascade["snapshot"])
        except Exception:
            consequence_cascade_snapshot = None

        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "runtime_config_status": self.runtime_config_status(),
            "committed_state": committed_state,
            "diagnostics": session.diagnostics[-20:],
            "hierarchical_memory": session.hierarchical_memory,
            "callback_web": callback_web_snapshot,
            "consequence_cascade": consequence_cascade_snapshot,
            "envelope_kind": "full_turn_orchestration_includes_graph_retrieval_and_interpreted_input",
            "committed_truth_vs_diagnostics": (
                "Each diagnostics[] entry is a full orchestration envelope (graph, retrieval, model_route, "
                "interpreted_input). Authoritative committed story-runtime truth is session fields, "
                "history, and the bounded narrative_commit object (also embedded in each envelope for correlation). "
                "Narrative thread continuity lives in session.narrative_threads and get_state committed_state "
                "narrative_thread_continuity. Callback-web continuity is derived from committed history, "
                "narrative threads, and branch timelines; callback_web is bounded operator evidence, not a "
                "canonical-state mutation. Consequence-cascade continuity is also derived from committed history "
                "and branch timelines; consequence_cascade is bounded feedback, not a canonical-state mutation. "
                "Narrative_thread_diagnostics.last_update_trace is bounded operator "
                "reasoning only and is not an authority source."
            ),
            "authoritative_history_tail": session.history[-5:] if session.history else [],
            "narrative_thread_diagnostics": {
                "last_update_trace": trace_payload,
                "note": (
                    "Diagnostic trace for the latest thread update only; authoritative continuity is "
                    "get_state.committed_state.narrative_thread_continuity and session.narrative_threads."
                ),
            },
            "warnings": [
                "story_runtime_hosted_in_world_engine",
                "ai_proposals_require_authoritative_runtime_commit",
                "orchestration_lives_in_diagnostics_bounded_truth_lives_in_narrative_commit_and_history",
            ],
        }

    def get_last_diagnostics_envelope(self, session_id: str) -> dict[str, Any] | None:
        """Return the last DiagnosticsEnvelope for a session, or None."""
        session = self.get_session(session_id)
        for event in reversed(session.diagnostics):
            if isinstance(event, dict) and "diagnostics_envelope" in event:
                return event["diagnostics_envelope"]
        return None

    def get_narrative_gov_summary(self) -> dict[str, Any]:
        """Return a NarrativeGovSummary across all active GoC sessions."""
        last_session_id = ""
        last_turn = 0
        last_trace_id = ""
        last_ldss_status = "not_invoked"
        last_block_count = 0
        last_legacy_blob = False
        last_human_actor = ""
        last_npc_actors: list[str] = []
        last_quality = ""
        last_signals: list[str] = []

        for sid, session in self.sessions.items():
            if session.module_id != GOD_OF_CARNAGE_MODULE_ID:
                continue
            if session.turn_counter > last_turn:
                last_session_id = sid
                last_turn = session.turn_counter
                proj = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
                last_human_actor = str(proj.get("human_actor_id") or "").strip()
                last_npc_actors = [
                    str(a) for a in (proj.get("npc_actor_ids") or [])
                    if str(a).strip()
                ]
                for event in reversed(session.diagnostics):
                    if not isinstance(event, dict):
                        continue
                    envelope = event.get("diagnostics_envelope")
                    if isinstance(envelope, dict):
                        last_trace_id = str(envelope.get("trace_id") or "").strip()
                        last_ldss = envelope.get("live_dramatic_scene_simulator") or {}
                        last_ldss_status = str(last_ldss.get("status") or "not_invoked")
                        fc = envelope.get("frontend_render_contract") or {}
                        last_block_count = int(fc.get("scene_block_count") or 0)
                        last_legacy_blob = bool(fc.get("legacy_blob_used"))
                        last_quality = str(envelope.get("quality_class") or "")
                        last_signals = list(envelope.get("degradation_signals") or [])
                        break

        summary = build_narrative_gov_summary(
            last_story_session_id=last_session_id,
            last_turn_number=last_turn,
            last_trace_id=last_trace_id,
            ldss_status=last_ldss_status,
            scene_block_count=last_block_count,
            legacy_blob_used=last_legacy_blob,
            human_actor_id=last_human_actor,
            npc_actor_ids=last_npc_actors,
            quality_class=last_quality,
            degradation_signals=last_signals,
        )
        return summary.to_dict()
