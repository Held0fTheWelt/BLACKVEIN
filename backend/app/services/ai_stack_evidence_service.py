"""Aggregate AI-stack evidence for governance (World-Engine diagnostics + backend session truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.runtime.session_store import get_session as get_runtime_session
from app.services.game_service import GameServiceError, get_story_diagnostics, get_story_state
from app.services.improvement_service import list_recommendation_packages


def build_session_evidence_bundle(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return inspectable evidence for a backend runtime session (may include World-Engine story host data)."""
    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return {
            "trace_id": trace_id,
            "error": "backend_session_not_found",
            "session_id": session_id,
        }

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_id = metadata.get("world_engine_story_session_id")

    bundle: dict[str, Any] = {
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
        "reproducibility_metadata": {},
    }

    if isinstance(engine_id, str) and engine_id.strip():
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

    last_diag = bundle.get("world_engine_diagnostics") or {}
    diag_list = last_diag.get("diagnostics") if isinstance(last_diag, dict) else None
    if isinstance(diag_list, list) and diag_list:
        last_turn = diag_list[-1]
        graph = last_turn.get("graph") if isinstance(last_turn, dict) else None
        if isinstance(graph, dict):
            bundle["last_turn_repro_metadata"] = graph.get("repro_metadata")
            bundle["last_turn_graph_errors"] = graph.get("errors", [])
            bundle["degraded_signals"] = [
                "graph_errors_present" if graph.get("errors") else "none",
                "fallback_path_taken" if graph.get("fallback_path_taken") else "none",
            ]
            repro = graph.get("repro_metadata", {})
            if isinstance(repro, dict):
                bundle["repaired_layer_signals"] = {
                    "runtime": {
                        "trace_id": repro.get("trace_id"),
                        "graph_name": repro.get("graph_name"),
                        "graph_version": repro.get("runtime_turn_graph_version"),
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
                    },
                }
                bundle["reproducibility_metadata"] = {
                    "ai_stack_semantic_version": repro.get("ai_stack_semantic_version"),
                    "runtime_turn_graph_version": repro.get("runtime_turn_graph_version"),
                    "routing_policy_version": repro.get("routing_policy_version"),
                    "host_versions": repro.get("host_versions"),
                }

    writers_room_review = _latest_writers_room_review()
    if writers_room_review:
        bundle["repaired_layer_signals"]["writers_room"] = {
            "review_id": writers_room_review.get("review_id"),
            "review_status": (writers_room_review.get("review_state") or {}).get("status"),
            "artifact_counts": {
                "issues": len(writers_room_review.get("issues", [])),
                "patch_candidates": len(writers_room_review.get("patch_candidates", [])),
                "variant_candidates": len(writers_room_review.get("variant_candidates", [])),
            },
        }

    improvement_package = _latest_improvement_package()
    if improvement_package:
        evaluation = improvement_package.get("evaluation", {})
        bundle["repaired_layer_signals"]["improvement"] = {
            "package_id": improvement_package.get("package_id"),
            "review_status": improvement_package.get("review_status"),
            "recommendation": improvement_package.get("recommendation_summary"),
            "comparison": evaluation.get("comparison", {}),
            "evidence_bundle": improvement_package.get("evidence_bundle", {}),
        }

    return bundle


def _latest_writers_room_review() -> dict[str, Any] | None:
    root = Path(__file__).resolve().parents[2] / "var" / "writers_room" / "reviews"
    if not root.exists():
        return None
    files = sorted(root.glob("*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def _latest_improvement_package() -> dict[str, Any] | None:
    packages = list_recommendation_packages()
    if not packages:
        return None
    return packages[-1]


def build_release_readiness_report(*, trace_id: str) -> dict[str, Any]:
    writers_room_review = _latest_writers_room_review()
    improvement_package = _latest_improvement_package()
    runtime_repro_present = False
    if writers_room_review:
        runtime_signals = writers_room_review.get("stack_components", {})
        runtime_repro_present = bool(runtime_signals)
    areas = [
        {
            "area": "runtime_observability",
            "status": "ready" if runtime_repro_present else "partial",
            "reason": "runtime graph/retrieval/model fields available in active workflow responses"
            if runtime_repro_present
            else "runtime repro evidence not observed in latest review artifact",
        },
        {
            "area": "writers_room_hil",
            "status": "ready"
            if writers_room_review and (writers_room_review.get("review_state") or {}).get("status")
            else "partial",
            "reason": "writers-room review artifacts with persisted review state available"
            if writers_room_review
            else "no persisted writers-room review artifacts found",
        },
        {
            "area": "improvement_evidence",
            "status": "ready"
            if improvement_package and (improvement_package.get("evidence_bundle") or {}).get("comparison")
            else "partial",
            "reason": "improvement recommendations include comparison evidence bundle"
            if improvement_package
            else "no improvement recommendation package with evidence bundle found",
        },
    ]
    overall = "ready" if all(area["status"] == "ready" for area in areas) else "partial"
    return {
        "trace_id": trace_id,
        "overall_status": overall,
        "areas": areas,
        "known_partiality": [
            "local_json_persistence_not_distributed",
            "no_signed_immutable_audit_store",
        ],
    }
