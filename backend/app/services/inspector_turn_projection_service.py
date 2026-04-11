"""Canonical read-only Inspector Suite projection assembly for one turn."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_turn_seams import build_operator_canonical_turn_record

from app.contracts.inspector_turn_projection import build_inspector_turn_projection_root
from app.services.ai_stack_evidence_service import build_session_evidence_bundle
from app.services.inspector_turn_projection_sections import build_inspector_projection_sections

_LAST_TURN_PLANNER_KEYS: tuple[str, ...] = (
    "semantic_move_record",
    "social_state_record",
    "character_mind_records",
    "scene_plan_record",
    "interpreted_move",
    "scene_assessment",
    "selected_responder_set",
    "pacing_mode",
    "silence_brevity_decision",
    "proposed_state_effects",
    "dramatic_effect_outcome",
    "continuity_impacts",
    "visibility_class_markers",
    "failure_markers",
    "fallback_markers",
    "transition_pattern",
    "turn_id",
    "turn_timestamp_iso",
    "turn_initiator_type",
    "turn_input_class",
    "turn_execution_mode",
)


def _planner_fields_from_last_turn(last_turn: dict[str, Any]) -> dict[str, Any]:
    """Lift planner-shaped fields from a diagnostics row (top-level and graph.planner_state_projection)."""
    out: dict[str, Any] = {}
    for key in _LAST_TURN_PLANNER_KEYS:
        if key in last_turn and last_turn[key] is not None:
            out[key] = last_turn[key]
    graph = last_turn.get("graph")
    if isinstance(graph, dict):
        psp = graph.get("planner_state_projection")
        if isinstance(psp, dict):
            for key in (
                "semantic_move_record",
                "social_state_record",
                "character_mind_records",
                "scene_plan_record",
            ):
                if key not in out and psp.get(key) is not None:
                    out[key] = psp[key]
    if "interpreted_move" not in out and isinstance(last_turn.get("interpreted_input"), dict):
        out["interpreted_move"] = last_turn["interpreted_input"]
    return out


def _last_turn_from_bundle(bundle: dict[str, Any]) -> dict[str, Any] | None:
    diagnostics = bundle.get("world_engine_diagnostics")
    if not isinstance(diagnostics, dict):
        return None
    rows = diagnostics.get("diagnostics")
    if not isinstance(rows, list) or not rows:
        return None
    tail = rows[-1]
    return tail if isinstance(tail, dict) else None


def _projectable_state(
    *,
    bundle: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, Any]:
    model_route = last_turn.get("model_route")
    routing = {}
    generation = {}
    if isinstance(model_route, dict):
        generation = model_route.get("generation") if isinstance(model_route.get("generation"), dict) else {}
        routing = {k: v for k, v in model_route.items() if k != "generation"}
    module_id = bundle.get("module_id")
    current_scene_id = bundle.get("current_scene_id")
    world_engine_story_session_id = bundle.get("world_engine_story_session_id")
    turn_number = last_turn.get("turn_number")
    state: dict[str, Any] = {
        "session_id": world_engine_story_session_id,
        "trace_id": last_turn.get("trace_id"),
        "module_id": module_id,
        "current_scene_id": current_scene_id,
        "turn_number": turn_number if isinstance(turn_number, int) else None,
        "retrieval": last_turn.get("retrieval") if isinstance(last_turn.get("retrieval"), dict) else {},
        "routing": routing,
        "generation": generation,
        "graph_diagnostics": last_turn.get("graph") if isinstance(last_turn.get("graph"), dict) else {},
        "visible_output_bundle": last_turn.get("visible_output_bundle"),
        "diagnostics_refs": last_turn.get("diagnostics_refs"),
        "experiment_preview": last_turn.get("experiment_preview"),
        "validation_outcome": (
            last_turn.get("validation_outcome")
            if isinstance(last_turn.get("validation_outcome"), dict)
            else {}
        ),
        "committed_result": (
            last_turn.get("committed_result") if isinstance(last_turn.get("committed_result"), dict) else {}
        ),
        "selected_scene_function": last_turn.get("selected_scene_function"),
    }
    state.update(_planner_fields_from_last_turn(last_turn))
    return state


def build_inspector_turn_projection(
    *,
    session_id: str,
    trace_id: str,
    mode: str = "canonical",
) -> dict[str, Any]:
    """Return canonical single-turn projection and optional raw evidence envelope."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle

    last_turn = _last_turn_from_bundle(bundle)
    canonical_record: dict[str, Any] | None = None
    if isinstance(last_turn, dict):
        canonical_record = build_operator_canonical_turn_record(
            _projectable_state(bundle=bundle, last_turn=last_turn)
        )

    sections = build_inspector_projection_sections(
        bundle=bundle, canonical_record=canonical_record, last_turn=last_turn
    )
    projection_status = "ok" if last_turn is not None else "partial"
    if bundle.get("world_engine_story_session_id") in (None, ""):
        projection_status = "partial"

    payload = build_inspector_turn_projection_root(
        trace_id=bundle.get("trace_id"),
        backend_session_id=str(bundle.get("backend_session_id") or session_id),
        world_engine_story_session_id=bundle.get("world_engine_story_session_id"),
        projection_status=projection_status,
        sections=sections,
        warnings=list(bundle.get("degraded_path_signals") or []),
        raw_evidence_refs={
            "source": "world_engine_diagnostics_session_bridge",
            "mode": mode,
        },
    )
    if mode == "raw":
        payload["raw_evidence"] = {
            "world_engine_state": bundle.get("world_engine_state"),
            "world_engine_diagnostics": bundle.get("world_engine_diagnostics"),
            "execution_truth": bundle.get("execution_truth"),
            "cross_layer_classifiers": bundle.get("cross_layer_classifiers"),
            "bridge_errors": bundle.get("bridge_errors"),
        }
    return payload
