"""Section builders for governance session evidence bundle (DS-004).

Mutates the bundle dict in place for nested structures; public contract unchanged.
"""

from __future__ import annotations

from typing import Any

from ai_stack import build_retrieval_trace

from app.services.game_service import GameServiceError, get_story_diagnostics, get_story_state
from app.services.improvement_service import list_recommendation_packages


def session_bundle_not_found(*, trace_id: str, session_id: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "error": "backend_session_not_found",
        "session_id": session_id,
    }


def session_bundle_base_scaffold(
    *,
    trace_id: str,
    session_id: str,
    state: Any,
    engine_id: Any,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "canonical_flow": "governance_session_evidence_bundle",
        "backend_session_id": session_id,
        "module_id": state.module_id,
        "current_scene_id": state.current_scene_id,
        "turn_counter_backend": state.turn_counter,
        "world_engine_story_session_id": engine_id,
        "world_engine_state": None,
        "world_engine_diagnostics": None,
        "bridge_errors": [],
        "improvement_recommendation_count": len(list_recommendation_packages()),
        "repaired_layer_signals": {},
        "degraded_signals": [],
        "degraded_path_signals": [],
        "execution_truth": None,
        "reproducibility_metadata": {},
    }


def apply_world_engine_bridge(bundle: dict[str, Any], *, engine_id: Any, trace_id: str) -> None:
    if not (isinstance(engine_id, str) and engine_id.strip()):
        return
    try:
        bundle["world_engine_state"] = get_story_state(engine_id, trace_id=trace_id)
        bundle["world_engine_diagnostics"] = get_story_diagnostics(engine_id, trace_id=trace_id)
    except GameServiceError as exc:
        bundle["bridge_errors"].append(
            {
                "failure_class": "world_engine_unreachable",
                "message": str(exc),
                "status_code": exc.status_code,
            }
        )


def apply_diagnostics_execution_truth_and_retrieval(
    bundle: dict[str, Any],
    ev: Any,
) -> None:
    last_diag = bundle.get("world_engine_diagnostics") or {}
    execution_truth: dict[str, Any] | None = None
    diag_list_for_classifiers: list[Any] | None = None
    if isinstance(last_diag, dict):
        execution_truth = {
            "committed_narrative_surface": ev._committed_narrative_surface(last_diag),
            "last_turn_graph_mode": None,
            "retrieval_influence": None,
            "tool_influence": None,
        }
        diag_list = last_diag.get("diagnostics") if isinstance(last_diag.get("diagnostics"), list) else None
        diag_list_for_classifiers = diag_list
        last_turn: dict[str, Any] | None = None
        if isinstance(diag_list, list) and diag_list:
            tail = diag_list[-1]
            last_turn = tail if isinstance(tail, dict) else None
        if last_turn is not None:
            execution_truth["retrieval_influence"] = ev._retrieval_influence_from_turn(last_turn)
            graph = last_turn.get("graph")
            if isinstance(graph, dict):
                execution_truth["last_turn_graph_mode"] = ev._last_turn_graph_mode(graph)
                execution_truth["tool_influence"] = ev._summarize_tool_influence(
                    graph.get("capability_audit", [])
                )
                bundle["last_turn_repro_metadata"] = graph.get("repro_metadata")
                bundle["last_turn_graph_errors"] = graph.get("errors", [])
                bundle["degraded_path_signals"] = ev._degraded_path_signal_list(graph)
                bundle["degraded_signals"] = list(bundle["degraded_path_signals"])
                repro = graph.get("repro_metadata", {})
                if isinstance(repro, dict):
                    bundle["repaired_layer_signals"] = {
                        "runtime": {
                            "trace_id": repro.get("trace_id"),
                            "graph_name": repro.get("graph_name"),
                            "graph_version": repro.get("runtime_turn_graph_version"),
                            "execution_health": graph.get("execution_health"),
                            "graph_path_summary": repro.get("graph_path_summary"),
                            "model": {
                                "selected_model": repro.get("selected_model"),
                                "selected_provider": repro.get("selected_provider"),
                                "model_success": repro.get("model_success"),
                                "model_fallback_used": repro.get("model_fallback_used"),
                            },
                            "retrieval": {
                                "domain": repro.get("retrieval_domain"),
                                "profile": repro.get("retrieval_profile"),
                                "status": repro.get("retrieval_status"),
                                "hit_count": repro.get("retrieval_hit_count"),
                            },
                            "module_id": repro.get("module_id"),
                            "session_id": repro.get("session_id"),
                        },
                        "tools": {
                            "capability_audit_count": len(graph.get("capability_audit", []))
                            if isinstance(graph.get("capability_audit"), list)
                            else 0,
                            "material_influence": (
                                execution_truth["tool_influence"] or {}
                            ).get("material_influence"),
                        },
                    }
                    bundle["reproducibility_metadata"] = {
                        "ai_stack_semantic_version": repro.get("ai_stack_semantic_version"),
                        "runtime_turn_graph_version": repro.get("runtime_turn_graph_version"),
                        "routing_policy_version": repro.get("routing_policy_version"),
                        "host_versions": repro.get("host_versions"),
                    }
            ret_payload = last_turn.get("retrieval")
            if isinstance(ret_payload, dict):
                rtrace = build_retrieval_trace(ret_payload)
                rm = bundle.get("reproducibility_metadata")
                base_rm = rm if isinstance(rm, dict) else {}
                bundle["reproducibility_metadata"] = {
                    **base_rm,
                    "retrieval_index_version": rtrace.get("index_version"),
                    "retrieval_corpus_fingerprint": rtrace.get("corpus_fingerprint"),
                    "retrieval_route": rtrace.get("retrieval_route"),
                }
    bundle["execution_truth"] = execution_truth
    bundle["cross_layer_classifiers"] = ev._build_cross_layer_classifiers(
        execution_truth=execution_truth,
        degraded_path_signals=bundle.get("degraded_path_signals") or [],
        bridge_errors=bundle.get("bridge_errors") or [],
        diag_list=diag_list_for_classifiers,
    )


def apply_writers_room_and_improvement_signals(bundle: dict[str, Any], ev: Any) -> None:
    writers_room_review = ev._latest_writers_room_review()
    if writers_room_review:
        bundle["repaired_layer_signals"]["writers_room"] = ev._writers_room_governance_signals(
            writers_room_review
        )

    improvement_package = ev._latest_improvement_package()
    if improvement_package:
        evaluation = improvement_package.get("evaluation", {})
        grs = improvement_package.get("governance_review_state")
        grs_status = grs.get("status") if isinstance(grs, dict) else None
        bundle["repaired_layer_signals"]["improvement"] = {
            "package_id": improvement_package.get("package_id"),
            "review_status": improvement_package.get("review_status"),
            "governance_review_state_status": grs_status,
            "recommendation": improvement_package.get("recommendation_summary"),
            "comparison": evaluation.get("comparison", {}),
            "evidence_influence": ev._improvement_evidence_influence(improvement_package),
        }
