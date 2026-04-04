"""Aggregate AI-stack evidence for governance (World-Engine diagnostics + backend session truth)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wos_ai_stack import build_retrieval_trace

from app.runtime.session_store import get_session as get_runtime_session
from app.services.game_service import GameServiceError, get_story_diagnostics, get_story_state
from app.services.improvement_service import list_recommendation_packages

# Capabilities whose invocation materially affects workflow outputs (context, transcript, governance bundle).
_MATERIAL_CAPABILITY_NAMES: frozenset[str] = frozenset(
    {
        "wos.context_pack.build",
        "wos.transcript.read",
        "wos.review_bundle.build",
    }
)


def _summarize_tool_influence(capability_audit: list[Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    material_hits: list[str] = []
    if not isinstance(capability_audit, list):
        return {"entries": entries, "material_capability_invocations": material_hits}
    for row in capability_audit:
        if not isinstance(row, dict):
            continue
        name = row.get("capability_name")
        outcome = row.get("outcome")
        if not isinstance(name, str):
            continue
        entries.append({"capability_name": name, "outcome": outcome})
        if name in _MATERIAL_CAPABILITY_NAMES and outcome in (None, "allowed", "success", "ok"):
            if name not in material_hits:
                material_hits.append(name)
    return {
        "entries": entries[:24],
        "material_capability_invocations": material_hits,
        "material_influence": bool(material_hits),
    }


def _retrieval_influence_from_turn(last_turn: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(last_turn, dict):
        return None
    retrieval = last_turn.get("retrieval")
    if not isinstance(retrieval, dict):
        retrieval = {}
    trace = build_retrieval_trace(retrieval)
    return {
        "domain": trace.get("domain"),
        "profile": trace.get("profile"),
        "hit_count": trace.get("hit_count"),
        "status": trace.get("status"),
        "evidence_strength": trace.get("evidence_strength"),
        "evidence_tier": trace.get("evidence_tier"),
        "evidence_rationale": trace.get("evidence_rationale"),
    }


def _committed_narrative_surface(last_diag: dict[str, Any]) -> dict[str, Any]:
    committed_state = last_diag.get("committed_state")
    tail = last_diag.get("committed_history_tail")
    last_committed = None
    if isinstance(tail, list) and tail:
        last = tail[-1]
        if isinstance(last, dict):
            last_committed = {
                "turn_number": last.get("turn_number"),
                "trace_id": last.get("trace_id"),
                "progression_commit": last.get("progression_commit"),
                "committed_state_after": last.get("committed_state_after"),
                "turn_outcome": last.get("turn_outcome"),
            }
    warnings = last_diag.get("warnings")
    return {
        "committed_state": committed_state if isinstance(committed_state, dict) else None,
        "last_committed_turn_summary": last_committed,
        "diagnostic_envelope_note": (
            "Full turn rows under world_engine_diagnostics.diagnostics include graph, retrieval, and "
            "model_route (orchestration proposals). Committed narrative truth is session fields plus "
            "history/committed_history_tail entries without the graph envelope."
        ),
        "world_engine_warnings": warnings if isinstance(warnings, list) else [],
    }


def _last_turn_graph_mode(graph: dict[str, Any]) -> dict[str, Any]:
    repro = graph.get("repro_metadata")
    if not isinstance(repro, dict):
        repro = {}
    return {
        "execution_health": graph.get("execution_health"),
        "fallback_path_taken": bool(graph.get("fallback_path_taken")),
        "graph_path_summary": repro.get("graph_path_summary"),
        "adapter_invocation_mode": repro.get("adapter_invocation_mode"),
        "graph_name": graph.get("graph_name"),
        "graph_version": graph.get("graph_version"),
    }


def _degraded_path_signal_list(graph: dict[str, Any]) -> list[str]:
    active: list[str] = []
    errors = graph.get("errors")
    if isinstance(errors, list) and errors:
        active.append("graph_errors_present")
    if graph.get("fallback_path_taken"):
        active.append("fallback_path_taken")
    eh = graph.get("execution_health")
    if eh in ("model_fallback", "degraded_generation", "graph_error"):
        active.append(f"execution_health:{eh}")
    return active


def _improvement_evidence_influence(package: dict[str, Any]) -> dict[str, Any]:
    evidence = package.get("evidence_bundle") if isinstance(package.get("evidence_bundle"), dict) else {}
    stages = package.get("workflow_stages")
    stage_ids: list[str] = []
    if isinstance(stages, list):
        for s in stages:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                stage_ids.append(s["id"])
    paths = evidence.get("retrieval_source_paths")
    path_count = len(paths) if isinstance(paths, list) else 0
    tx = evidence.get("transcript_evidence")
    return {
        "workflow_stage_ids": stage_ids,
        "retrieval_source_path_count": path_count,
        "has_transcript_evidence": bool(tx),
        "has_governance_review_bundle": bool(evidence.get("governance_review_bundle_id")),
        "tool_influence_indicators": {
            "context_pack_sources": path_count > 0,
            "transcript_tool": bool(tx),
            "review_bundle": bool(evidence.get("governance_review_bundle_id")),
        },
    }


def _writers_room_governance_signals(review: dict[str, Any]) -> dict[str, Any]:
    rt = review.get("retrieval_trace") if isinstance(review.get("retrieval_trace"), dict) else {}
    mg = review.get("model_generation") if isinstance(review.get("model_generation"), dict) else {}
    rs = review.get("review_summary") if isinstance(review.get("review_summary"), dict) else {}
    audit = review.get("capability_audit")
    audit_names: list[str] = []
    if isinstance(audit, list):
        for row in audit[-12:]:
            if isinstance(row, dict) and isinstance(row.get("capability_name"), str):
                audit_names.append(row["capability_name"])
    return {
        "review_id": review.get("review_id"),
        "review_status": (review.get("review_state") or {}).get("status"),
        "evidence_tier": rt.get("evidence_tier"),
        "evidence_strength": rt.get("evidence_strength"),
        "retrieval_evidence_rationale": rt.get("evidence_rationale"),
        "model_adapter_invocation_mode": mg.get("adapter_invocation_mode"),
        "review_bundle_id": rs.get("bundle_id"),
        "review_bundle_status": rs.get("bundle_status"),
        "capability_audit_tail": audit_names,
        "artifact_counts": {
            "issues": len(review.get("issues", [])),
            "patch_candidates": len(review.get("patch_candidates", [])),
            "variant_candidates": len(review.get("variant_candidates", [])),
        },
    }


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
        "degraded_path_signals": [],
        "execution_truth": None,
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
    execution_truth: dict[str, Any] | None = None
    if isinstance(last_diag, dict):
        execution_truth = {
            "committed_narrative_surface": _committed_narrative_surface(last_diag),
            "last_turn_graph_mode": None,
            "retrieval_influence": None,
            "tool_influence": None,
        }
        diag_list = last_diag.get("diagnostics") if isinstance(last_diag.get("diagnostics"), list) else None
        last_turn: dict[str, Any] | None = None
        if isinstance(diag_list, list) and diag_list:
            tail = diag_list[-1]
            last_turn = tail if isinstance(tail, dict) else None
        if last_turn is not None:
            execution_truth["retrieval_influence"] = _retrieval_influence_from_turn(last_turn)
            graph = last_turn.get("graph")
            if isinstance(graph, dict):
                execution_truth["last_turn_graph_mode"] = _last_turn_graph_mode(graph)
                execution_truth["tool_influence"] = _summarize_tool_influence(
                    graph.get("capability_audit", [])
                )
                bundle["last_turn_repro_metadata"] = graph.get("repro_metadata")
                bundle["last_turn_graph_errors"] = graph.get("errors", [])
                bundle["degraded_path_signals"] = _degraded_path_signal_list(graph)
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
    bundle["execution_truth"] = execution_truth

    writers_room_review = _latest_writers_room_review()
    if writers_room_review:
        bundle["repaired_layer_signals"]["writers_room"] = _writers_room_governance_signals(writers_room_review)

    improvement_package = _latest_improvement_package()
    if improvement_package:
        evaluation = improvement_package.get("evaluation", {})
        bundle["repaired_layer_signals"]["improvement"] = {
            "package_id": improvement_package.get("package_id"),
            "review_status": improvement_package.get("review_status"),
            "recommendation": improvement_package.get("recommendation_summary"),
            "comparison": evaluation.get("comparison", {}),
            "evidence_influence": _improvement_evidence_influence(improvement_package),
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
    """Honest multi-area readiness: no proxying story-runtime signals from Writers-Room artifacts."""
    writers_room_review = _latest_writers_room_review()
    improvement_package = _latest_improvement_package()

    wr_governance_ready = bool(
        writers_room_review and (writers_room_review.get("review_state") or {}).get("status")
    )
    wr_evidence_ready = bool(
        writers_room_review
        and isinstance(writers_room_review.get("retrieval_trace"), dict)
        and writers_room_review["retrieval_trace"].get("evidence_tier") is not None
    )
    improvement_ready = bool(
        improvement_package and (improvement_package.get("evidence_bundle") or {}).get("comparison")
    )
    improvement_governance_ready = bool(
        improvement_ready
        and (improvement_package.get("evidence_bundle") or {}).get("governance_review_bundle_id")
    )

    areas = [
        {
            "area": "story_runtime_cross_layer",
            "status": "partial",
            "reason": (
                "This aggregate report does not inspect a live World-Engine session; "
                "use GET /admin/ai-stack/session-evidence/<id> after turns for bridged execution_truth."
            ),
        },
        {
            "area": "runtime_turn_graph_contract",
            "status": "ready",
            "reason": (
                "Repository implements RuntimeTurnGraphExecutor with execution_health, "
                "fallback markers, and repro_metadata (verified in wos_ai_stack/world-engine tests)."
            ),
        },
        {
            "area": "writers_room_review_artifacts",
            "status": "ready" if wr_governance_ready else "partial",
            "reason": "Persisted writers-room review with review_state"
            if wr_governance_ready
            else "no persisted writers-room review artifacts with review state",
        },
        {
            "area": "writers_room_retrieval_evidence_surface",
            "status": "ready" if wr_evidence_ready else "partial",
            "reason": "Latest review includes retrieval_trace evidence tier"
            if wr_evidence_ready
            else "no retrieval_trace on latest writers-room review",
        },
        {
            "area": "writers_room_langgraph_orchestration_depth",
            "status": "partial",
            "reason": (
                "Writers-Room workflow uses a LangGraph seed graph stub for workflow_seed; "
                "it is not runtime turn-graph parity (intentionally lightweight)."
            ),
        },
        {
            "area": "improvement_governance_evidence",
            "status": "ready" if improvement_governance_ready else "partial",
            "reason": "Recommendation package includes comparison plus governance review bundle id"
            if improvement_governance_ready
            else (
                "improvement package missing governance_review_bundle_id or comparison evidence"
                if improvement_package
                else "no improvement recommendation package found"
            ),
        },
    ]
    overall = "ready" if all(area["status"] == "ready" for area in areas) else "partial"
    return {
        "trace_id": trace_id,
        "overall_status": overall,
        "areas": areas,
        "subsystem_maturity": [
            {
                "subsystem": "story_runtime_world_engine",
                "role": "authoritative_host",
                "maturity_note": "Committed state vs diagnostic envelopes are explicit in engine diagnostics API.",
            },
            {
                "subsystem": "writers_room_langgraph",
                "role": "workflow_seed",
                "maturity_note": "Seed graph only; orchestration depth is partial vs runtime turn graph.",
            },
            {
                "subsystem": "runtime_turn_langgraph",
                "role": "primary_turn_executor",
                "maturity_note": "Full node chain with explicit execution_health and fallback semantics.",
            },
        ],
        "known_partiality": [
            "local_json_persistence_not_distributed",
            "no_signed_immutable_audit_store",
            "release_readiness_aggregate_does_not_substitute_for_session_evidence",
        ],
    }
