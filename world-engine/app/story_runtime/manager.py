from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from story_runtime_core import ModelRegistry, RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from ai_stack import (
    RuntimeTurnGraphExecutor,
    build_runtime_retriever,
    create_default_capability_registry,
)
from ai_stack.rag_retrieval_dtos import retrieval_config_from_governed
from ai_stack.runtime_quality_semantics import canonical_quality_class
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
from ai_stack.goc_frozen_vocab import expand_goc_actor_id_aliases

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
from app.story_runtime.story_session_store import JsonStorySessionStore
from app.story_runtime.module_turn_hooks import (
    GOD_OF_CARNAGE_MODULE_ID,
    goc_append_continuity_impacts,
    goc_host_experience_template,
    goc_prior_continuity_for_graph,
)
from app.story_runtime.narrative_threads import (
    NARRATIVE_COMMIT_HISTORY_TAIL,
    StoryNarrativeThreadSet,
    ThreadUpdateTrace,
    build_graph_thread_export,
    thread_continuity_metrics,
    update_narrative_threads,
)

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
        content_provenance=provenance,
    )


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


def _build_langfuse_path_summary(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    nodes = _str_list(graph_state.get("nodes_executed"))
    routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
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
    retrieval = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
    structured = gen_meta.get("structured_output")
    if structured is None:
        structured = generation.get("structured_output")
    graph_errors = _str_list(graph_state.get("graph_errors"))
    usage_details = gen_meta.get("usage_details") if isinstance(gen_meta.get("usage_details"), dict) else {}
    usage_total = int(usage_details.get("total") or gen_meta.get("tokens_total") or 0)

    return {
        "contract": "story_runtime_path_observability.v1",
        "session_id": session.session_id,
        "module_id": session.module_id,
        "turn_number": event.get("turn_number"),
        "turn_kind": event.get("turn_kind"),
        "nodes_executed": nodes,
        "route_model_called": "route_model" in nodes or bool(routing),
        "invoke_model_called": "invoke_model" in nodes,
        "fallback_model_called": "fallback_model" in nodes or bool(generation.get("fallback_used")),
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
        "usage_available": bool(gen_meta.get("usage_available")) or usage_total > 0,
        "usage_source": gen_meta.get("usage_source"),
        "usage_details": {
            "input": int(usage_details.get("input") or gen_meta.get("tokens_prompt") or 0),
            "output": int(usage_details.get("output") or gen_meta.get("tokens_completion") or 0),
            "total": usage_total,
        },
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
        "actor_lane_validation_status": actor_lane_validation.get("status"),
        "actor_lane_validation_reason": actor_lane_validation.get("reason"),
        "commit_applied": bool(committed.get("commit_applied")),
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
    }


def _langfuse_level_for_output(output: dict[str, Any]) -> str:
    error = str(output.get("error") or output.get("generation_error") or "").strip()
    if error:
        return "ERROR"
    if output.get("fallback_used") or output.get("quality_class") == "degraded":
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
            f"passive_factors={len(output.get('primary_passivity_factors') or [])}"
        )
    if name == "story.phase.commit":
        return (
            f"called={output.get('called')} commit_applied={output.get('commit_applied')} "
            f"quality={output.get('quality_class') or 'unknown'} degradation={output.get('degradation_summary') or 'none'}"
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
    }

    span_specs = [
        (
            "story.graph.path_summary",
            {
                "nodes_executed": path_summary.get("nodes_executed"),
                "route_model_called": path_summary.get("route_model_called"),
                "invoke_model_called": path_summary.get("invoke_model_called"),
                "fallback_model_called": path_summary.get("fallback_model_called"),
                "validation_called": path_summary.get("validation_called"),
                "commit_called": path_summary.get("commit_called"),
                "render_visible_called": path_summary.get("render_visible_called"),
                "retrieval_called": path_summary.get("retrieval_called"),
                "retrieval_status": path_summary.get("retrieval_status"),
                "retrieval_hit_count": path_summary.get("retrieval_hit_count"),
                "quality_class": path_summary.get("quality_class"),
                "degradation_signals": path_summary.get("degradation_signals"),
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
                    "called": bool(output.get("called", True)),
                    "quality_class": path_summary.get("quality_class"),
                    "degradation_summary": path_summary.get("degradation_summary"),
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
    model_name = str(path_summary.get("api_model") or path_summary.get("selected_model") or gen_meta.get("model") or "unknown").strip()
    provider = str(path_summary.get("selected_provider") or adapter_name or "unknown").strip()
    if adapter_name and adapter_name not in {"mock", "ldss_fallback", "ldss_deterministic"}:
        try:
            adapter.record_generation(
                name="story.model.generation",
                model=model_name,
                provider=provider,
                prompt=str(graph_state.get("model_prompt") or "")[:20000],
                completion=str(generation.get("model_raw_text") or generation.get("content") or "")[:20000],
                usage_details=usage_details if usage_details.get("total") else None,
                metadata={
                    "session_id": path_summary.get("session_id"),
                    "module_id": path_summary.get("module_id"),
                    "turn_number": path_summary.get("turn_number"),
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
            )
        except Exception:
            logger.debug("Langfuse retrieval observation failed", exc_info=True)

    # Align with player-visible truth: opening turns often have gm_narration / generation text
    # before scene_blocks projection; counting only scene_blocks yields false 0 (see Langfuse traces).
    has_visible_surface = bool(_scene_blocks_from_turn_event(event)) or bool(
        _visible_lines_from_turn_event(event)
    )
    deterministic_scores = {
        "non_mock_generation_pass": 1.0 if adapter_name not in {"", "mock", "ldss_fallback", "ldss_deterministic"} else 0.0,
        "visible_output_present": 1.0 if has_visible_surface else 0.0,
        "actor_lane_safety_pass": 1.0 if path_summary.get("actor_lane_validation_status") in {"approved", None} else 0.0,
        "fallback_absent": 0.0 if path_summary.get("generation_fallback_used") else 1.0,
        "usage_present": 1.0 if int(usage_details.get("total") or 0) > 0 else 0.0,
        "rag_context_attached": 1.0 if path_summary.get("retrieval_context_attached") else 0.0,
    }
    live_contract_pass = all(value == 1.0 for value in deterministic_scores.values()) and path_summary.get("quality_class") not in {"degraded", "failed"}
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
    canonical_signals = _build_canonical_degradation_signals(path_summary)
    degradation_chain = _build_degradation_chain(path_summary)
    degradation_prose_summary = _build_degradation_prose_summary(path_summary)
    live_opening_failure_reason = path_summary.get("live_opening_failure_reason")
    score_metadata_base = {
        "session_id": path_summary.get("session_id"),
        "turn_number": path_summary.get("turn_number"),
        "quality_class": path_summary.get("quality_class"),
        "degradation_signals": canonical_signals,
        "degradation_chain": degradation_chain,
        "degradation_summary": degradation_prose_summary,
        "live_opening_failure_reason": live_opening_failure_reason,
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


def _live_scene_blocks_from_visible_bundle(
    visible_output_bundle: dict[str, Any] | None,
    *,
    turn_number: int,
) -> list[dict[str, Any]]:
    bundle = visible_output_bundle if isinstance(visible_output_bundle, dict) else {}
    existing = bundle.get("scene_blocks")
    if isinstance(existing, list) and existing:
        return [dict(block) for block in existing if isinstance(block, dict)]

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
        clean = str(text or "").strip()
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
            }
        )

    def actor_label(actor_id: str) -> str:
        aid = str(actor_id or "").strip()
        labels = {
            "veronique_vallon": "Veronique",
            "michel_longstreet": "Michel",
            "annette_reille": "Annette",
            "alain_reille": "Alain",
        }
        if aid in labels:
            return labels[aid]
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
                if line:
                    append_block("actor_line", line, speaker_label=actor_label(speaker_id), actor_id=speaker_id or None)
                    emitted = True
        actions = parsed.get("action_lines")
        if isinstance(actions, list):
            for row in actions:
                if not isinstance(row, dict):
                    continue
                actor_id = str(row.get("actor_id") or "").strip()
                line = str(row.get("text") or row.get("line") or "").strip()
                if line:
                    append_block("actor_action", line, speaker_label=actor_label(actor_id), actor_id=actor_id or None)
                    emitted = True
        return emitted

    for line in _coerce_visible_text_lines(bundle.get("gm_narration")):
        if append_json_blocks(line):
            continue
        append_block("narrator", line, speaker_label="Narrator")

    for line in _coerce_visible_text_lines(bundle.get("spoken_lines")):
        label = "Actor"
        text = line
        if ":" in line:
            maybe_label, maybe_text = line.split(":", 1)
            if maybe_label.strip() and maybe_text.strip():
                label = maybe_label.strip()
                text = maybe_text.strip()
        append_block("actor_line", text, speaker_label=label)

    for line in _coerce_visible_text_lines(bundle.get("action_lines")):
        append_block("actor_action", line, speaker_label="Action")

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
        "runtime_profile_id": str(proj.get("runtime_profile_id") or "god_of_carnage_solo"),
        "runtime_module_id": str(proj.get("runtime_module_id") or "solo_story_runtime"),
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
                entries.append(
                    {
                        "entry_id": f"{session.session_id}:{turn_number}:player",
                        "kind": "player_turn",
                        "role": "player",
                        "speaker": "You",
                        "turn_number": turn_number,
                        "text": raw_input,
                        "source": "player_input",
                    }
                )

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


def _player_shell_context_from_dramatic_context(dramatic_context: dict[str, Any] | None) -> dict[str, Any]:
    """Project a small player-shell slice from committed dramatic context."""
    if not isinstance(dramatic_context, dict):
        return {}
    story_context = _story_window_dramatic_context(dramatic_context)
    if not story_context:
        return {}
    return {
        "contract": "player_shell_dramatic_context.v1",
        "selected_scene_function": story_context.get("selected_scene_function"),
        "responder_id": story_context.get("responder_id"),
        "secondary_responder_ids": story_context.get("secondary_responder_ids") or [],
        "pacing_mode": story_context.get("pacing_mode"),
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
        runtime_profile_id=str(proj.get("runtime_profile_id") or "god_of_carnage_solo"),
        content_module_id=session.module_id,
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
        governed_runtime_config: dict[str, Any] | None = None,
        metrics: StoryRuntimeMetrics | None = None,
    ) -> None:
        self.sessions: dict[str, StorySession] = {}
        self._session_store = session_store
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

    def _session_turn_lock(self, session_id: str) -> threading.Lock:
        with self._session_locks_guard:
            return self._session_turn_locks.setdefault(session_id, threading.Lock())

    def _persist_session(self, session: StorySession) -> None:
        if self._session_store is None:
            return
        self._session_store.save(session.session_id, story_session_to_payload(session))

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
            "commit_contract_version": "story_narrative_commit_record.v3",
            "runtime_output_schema_version": "runtime_turn_structured_output_v2",
            "live_player_governance_enforced": self._live_governance_enforced_for_player_paths(),
            "module_scope_advertised": "module_specific_god_of_carnage_only",
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
        return {
            "human_actor_id": human_actor_id,
            "ai_forbidden_actor_ids": ai_forbidden,
            "ai_allowed_actor_ids": ai_allowed,
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
        if session.module_id != GOD_OF_CARNAGE_MODULE_ID:
            return base
        anchor = "Paris apartment, evening — hosts and guests meet after their children's incident"
        handover = "phase_1"
        try:
            from ai_stack.goc_yaml_authority import load_goc_opening_sequence_yaml

            osq = load_goc_opening_sequence_yaml()
            if isinstance(osq, dict):
                anchor = str(osq.get("setting_anchor") or anchor).strip() or anchor
                handover = str(osq.get("handover_to_scene_phase") or handover).strip() or handover
        except Exception:
            pass
        return (
            f"{base}\n\n"
            f"Session opening (canonical direction/opening_sequence.yaml; ADR-0035). Anchor: {anchor}. "
            "Deliver TWO beats in order: (1) background/premise of the incident and why these adults meet; "
            "(2) into the salon — room, ritual, social temperature. "
            "Use two narrator paragraphs (blank line between) or two gm_narration strings before NPC speech. "
            f"After handover, scene targets {handover}. Phase-1 civility — polite, non-accusatory NPC lines."
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
        fallback["visible_output_bundle"] = {}
        fallback["quality_class"] = QUALITY_CLASS_DEGRADED
        signals = list(fallback.get("degradation_signals") or [])
        if "ldss_fallback_after_live_opening_failure" not in signals:
            signals.append("ldss_fallback_after_live_opening_failure")
        fallback["degradation_signals"] = signals
        fallback["degradation_summary"] = reason
        return fallback

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
        goc_append_continuity_impacts(session.module_id, session.prior_continuity_impacts, graph_state)
        graph_diag = graph_state.get("graph_diagnostics", {}) if isinstance(graph_state.get("graph_diagnostics"), dict) else {}
        errors = graph_diag.get("errors", []) if isinstance(graph_diag.get("errors"), list) else []
        gen = graph_state.get("generation", {}) if isinstance(graph_state.get("generation"), dict) else {}
        interpreted_input = graph_state.get("interpreted_input", {})
        if not isinstance(interpreted_input, dict):
            interpreted_input = {}
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
        session.current_scene_id = narrative_commit.committed_scene_id
        session.narrative_threads, session.last_thread_update_trace = update_narrative_threads(
            prior=session.narrative_threads,
            latest_commit=narrative_commit,
            history_tail=history_tail,
            committed_scene_id=narrative_commit.committed_scene_id,
            turn_number=commit_turn_number,
        )
        model_ok = gen.get("success") is True
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
        validation_outcome = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
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
        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
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
        # Story Runtime Experience packaging: re-pack the visible bundle
        # according to the governed experience policy. The policy is a real
        # first-class runtime value pulled from the resolved config, so
        # recap / dramatic_turn / live modes differ in packaging truth, not
        # only in prompt wording.
        raw_bundle = graph_state.get("visible_output_bundle")
        experience_policy = self._story_runtime_experience_policy()
        packaged_bundle = self._apply_experience_packaging(raw_bundle, experience_policy)
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
        event: dict[str, Any] = {
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "raw_input": player_input,
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
            "selected_scene_function": graph_state.get("selected_scene_function"),
            "selected_responder_set": selected_responder_set,
            "visibility_class_markers": graph_state.get("visibility_class_markers"),
            "failure_markers": graph_state.get("failure_markers"),
            "self_correction": self_correction,
            "actor_survival_telemetry": actor_survival_telemetry,
            "actor_turn_summary": actor_turn_summary,
            "runtime_governance_surface": gov,
        }
        # Build SceneTurnEnvelope.v2 for God of Carnage solo sessions.
        # Live graph/model output is primary. LDSS is reserved as the final
        # deterministic fallback when the live path cannot produce scene blocks.
        scene_turn_envelope: dict[str, Any] | None = None
        if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
            live_scene_blocks = []
            if gen.get("success") is True and not graph_state.get("force_ldss_scene_fallback"):
                live_scene_blocks = _live_scene_blocks_from_visible_bundle(
                    event.get("visible_output_bundle")
                    if isinstance(event.get("visible_output_bundle"), dict)
                    else {},
                    turn_number=commit_turn_number,
                )
                live_scene_blocks = _maybe_split_goc_opening_into_two_movements(
                    live_scene_blocks,
                    commit_turn_number=commit_turn_number,
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
                    event_bundle = (
                        event.get("visible_output_bundle")
                        if isinstance(event.get("visible_output_bundle"), dict)
                        else {}
                    )
                    event["visible_output_bundle"] = _ensure_gm_narration_from_narrator_scene_blocks(
                        {
                            **event_bundle,
                            "scene_blocks": [dict(block) for block in blocks if isinstance(block, dict)],
                        }
                    )

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
        _reconcile_governance_passivity_with_final_projection(event)
        path_summary = _build_langfuse_path_summary(
            session=session,
            graph_state=graph_state,
            event=event,
        )
        event["observability_path_summary"] = path_summary
        _emit_langfuse_path_spans(path_summary)
        _emit_langfuse_evidence_observations(
            path_summary=path_summary,
            graph_state=graph_state,
            event=event,
        )

        committed_record = {
            "turn_number": commit_turn_number,
            "turn_kind": turn_kind or "player",
            "trace_id": trace_id or "",
            "turn_outcome": outcome,
            "narrative_commit": narrative_commit_payload,
            "committed_turn_authority": committed_turn_authority,
            "dramatic_context_summary": dramatic_context_summary,
            "actor_turn_summary": actor_turn_summary,
            "visible_output_bundle": event.get("visible_output_bundle"),
            "committed_state_after": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
            },
        }
        if isinstance(event.get("narrator_streaming"), dict):
            committed_record["narrator_streaming"] = event["narrator_streaming"]
        session.history.append(committed_record)
        session.diagnostics.append(event)
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
            if session.module_id == "god_of_carnage"
            else None
        )
        prior_ci = goc_prior_continuity_for_graph(session.module_id, session.prior_continuity_impacts)
        actor_lane_ctx = self._extract_actor_lane_context(session)

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
                turn_number=0,
                turn_initiator_type="engine",
                turn_input_class="opening",
                live_player_truth_surface=True,
                actor_lane_context=actor_lane_ctx,
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
            if session.module_id == "god_of_carnage"
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
                prior_planner_truth=prior_planner_truth,
                turn_number=commit_turn_number,
                turn_initiator_type="player",
                live_player_truth_surface=True,
                actor_lane_context=self._extract_actor_lane_context(session),
            )
        except Exception as exc:
            session.turn_counter -= 1
            log_story_runtime_failure(
                trace_id=trace_id,
                story_session_id=session_id,
                operation="execute_turn",
                message=str(exc),
                failure_class="graph_execution_exception",
            )
            raise

        val = graph_state.get("validation_outcome") if isinstance(graph_state.get("validation_outcome"), dict) else {}
        if val.get("status") != "approved":
            session.turn_counter -= 1
            if is_hard_boundary_failure(val):
                raise RuntimeError(f"Hard narrative boundary: {val.get('reason') or 'rejected'}")
            raise RuntimeError(f"Turn rejected after bounded recovery: {val.get('reason') or 'rejected'}")
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
        last_thread_summary: str | None = None
        if session.last_thread_update_trace is not None:
            last_thread_summary = session.last_thread_update_trace.summary or None

        story_entries = _story_window_entries_for_session(session)
        player_shell_context = _player_shell_context_from_dramatic_context(
            last_dramatic_context_summary
        )

        return {
            "session_id": session.session_id,
            "module_id": session.module_id,
            "turn_counter": session.turn_counter,
            "current_scene_id": session.current_scene_id,
            "content_provenance": session.content_provenance,
            "runtime_projection": session.runtime_projection,
            "history_count": len(session.history),
            "committed_state": {
                "current_scene_id": session.current_scene_id,
                "turn_counter": session.turn_counter,
                "last_narrative_commit": last_narrative_commit,
                "last_committed_turn_authority": last_committed_turn_authority,
                "last_dramatic_context_summary": last_dramatic_context_summary,
                "last_actor_turn_summary": last_actor_turn_summary,
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
            },
            "module_scope_truth": module_scope_truth,
            "player_shell_context": player_shell_context,
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
        }
        trace_payload: dict[str, Any] | None = None
        if session.last_thread_update_trace is not None:
            trace_payload = session.last_thread_update_trace.model_dump(mode="json")

        return {
            "session_id": session.session_id,
            "turn_counter": session.turn_counter,
            "runtime_config_status": self.runtime_config_status(),
            "committed_state": committed_state,
            "diagnostics": session.diagnostics[-20:],
            "envelope_kind": "full_turn_orchestration_includes_graph_retrieval_and_interpreted_input",
            "committed_truth_vs_diagnostics": (
                "Each diagnostics[] entry is a full orchestration envelope (graph, retrieval, model_route, "
                "interpreted_input). Authoritative committed story-runtime truth is session fields, "
                "history, and the bounded narrative_commit object (also embedded in each envelope for correlation). "
                "Narrative thread continuity lives in session.narrative_threads and get_state committed_state "
                "narrative_thread_continuity; narrative_thread_diagnostics.last_update_trace is bounded operator "
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
