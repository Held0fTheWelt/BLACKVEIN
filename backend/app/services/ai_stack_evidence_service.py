"""Aggregate AI-stack evidence for governance (World-Engine diagnostics + backend session truth)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_stack import build_retrieval_trace

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
    tail = last_diag.get("authoritative_history_tail")
    last_committed = None
    if isinstance(tail, list) and tail:
        last = tail[-1]
        if isinstance(last, dict):
            last_committed = {
                "turn_number": last.get("turn_number"),
                "trace_id": last.get("trace_id"),
                "narrative_commit": last.get("narrative_commit"),
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
            "history/authoritative_history_tail entries without the graph envelope."
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


def _improvement_package_recency_timestamp(package: dict[str, Any]) -> float:
    raw = package.get("generated_at")
    if not isinstance(raw, str) or not raw.strip():
        return 0.0
    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return 0.0


def _retrieval_tier_strong_enough_for_governance(tier: Any) -> bool:
    return tier in ("moderate", "strong")


def _build_cross_layer_classifiers(
    *,
    execution_truth: dict[str, Any] | None,
    degraded_path_signals: list[str],
    bridge_errors: list[Any],
    diag_list: list[Any] | None,
) -> dict[str, Any]:
    """Explicit cross-layer labels for review (derived only from existing bundle inputs)."""
    has_last_turn = bool(diag_list) and isinstance(diag_list[-1], dict)
    graph_mode = (execution_truth or {}).get("last_turn_graph_mode") if execution_truth else None
    retrieval = (execution_truth or {}).get("retrieval_influence") if execution_truth else None
    tools = (execution_truth or {}).get("tool_influence") if execution_truth else None
    tier = retrieval.get("evidence_tier") if isinstance(retrieval, dict) else None
    if not has_last_turn:
        retrieval_class = "no_turn_diagnostics"
    elif tier is None:
        retrieval_class = "unknown"
    else:
        retrieval_class = tier

    graph_posture = "no_turn_diagnostics"
    if isinstance(graph_mode, dict):
        if graph_mode.get("fallback_path_taken"):
            graph_posture = "fallback_or_alternate_path"
        elif graph_mode.get("execution_health") not in (None, "healthy"):
            graph_posture = "degraded_execution_health"
        else:
            graph_posture = "primary_graph_path"

    return {
        "committed_vs_diagnostic": (
            "committed_truth_is_session_fields_and_history_tail_diagnostic_rows_are_orchestration_envelopes"
        ),
        "last_turn_diagnostics_available": has_last_turn,
        "graph_execution_posture": graph_posture,
        "runtime_retrieval_evidence_tier": retrieval_class,
        "tool_influenced_last_turn": bool(isinstance(tools, dict) and tools.get("material_influence")),
        "bridge_reachability": "ok" if not bridge_errors else "degraded",
        "active_degradation_markers": list(degraded_path_signals),
    }


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
    strength = package.get("evidence_strength_map")
    strength_map = strength if isinstance(strength, dict) else None
    grs = package.get("governance_review_state") if isinstance(package.get("governance_review_state"), dict) else {}
    human_status = grs.get("status") or package.get("review_status")
    terminal_accepted = human_status == "governance_accepted"
    terminal_rejected = human_status == "governance_rejected"
    revision_requested = human_status == "governance_revision_requested"
    pending_human = human_status == "pending_governance_review"
    return {
        "workflow_stage_ids": stage_ids,
        "retrieval_source_path_count": path_count,
        "has_transcript_evidence": bool(tx),
        "has_governance_review_bundle": bool(evidence.get("governance_review_bundle_id")),
        "evidence_strength_map": strength_map,
        "governance_human_status": human_status,
        "governance_terminal_accepted": terminal_accepted,
        "governance_terminal_rejected": terminal_rejected,
        "governance_revision_requested": revision_requested,
        "governance_pending_review": pending_human,
        "distinct_from_publishable_recommendation": not terminal_accepted,
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
    wr_tier = rt.get("evidence_tier")
    return {
        "review_id": review.get("review_id"),
        "review_status": (review.get("review_state") or {}).get("status"),
        "evidence_tier": wr_tier,
        "evidence_strength": rt.get("evidence_strength"),
        "retrieval_evidence_rationale": rt.get("evidence_rationale"),
        "model_adapter_invocation_mode": mg.get("adapter_invocation_mode"),
        "review_bundle_id": rs.get("bundle_id"),
        "review_bundle_status": rs.get("bundle_status"),
        "capability_audit_tail": audit_names,
        "review_readiness": {
            "governance_review_state_present": bool((review.get("review_state") or {}).get("status")),
            "retrieval_evidence_sufficient_for_review": _retrieval_tier_strong_enough_for_governance(wr_tier),
            "retrieval_evidence_tier": wr_tier,
            "langgraph_orchestration": "seed_stub_not_runtime_turn_parity",
        },
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
    diag_list_for_classifiers: list[Any] | None = None
    if isinstance(last_diag, dict):
        execution_truth = {
            "committed_narrative_surface": _committed_narrative_surface(last_diag),
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
    bundle["cross_layer_classifiers"] = _build_cross_layer_classifiers(
        execution_truth=execution_truth,
        degraded_path_signals=bundle.get("degraded_path_signals") or [],
        bridge_errors=bundle.get("bridge_errors") or [],
        diag_list=diag_list_for_classifiers,
    )

    writers_room_review = _latest_writers_room_review()
    if writers_room_review:
        bundle["repaired_layer_signals"]["writers_room"] = _writers_room_governance_signals(writers_room_review)

    improvement_package = _latest_improvement_package()
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
    return max(packages, key=_improvement_package_recency_timestamp)


def _writers_room_retrieval_trace_tier(writers_room_review: dict[str, Any] | None) -> Any:
    if not writers_room_review:
        return None
    rt = writers_room_review.get("retrieval_trace")
    if not isinstance(rt, dict):
        return None
    return rt.get("evidence_tier")


def _improvement_evidence_strength_map(package: dict[str, Any] | None) -> dict[str, Any] | None:
    if not package:
        return None
    m = package.get("evidence_strength_map")
    return m if isinstance(m, dict) else None


def build_release_readiness_report(*, trace_id: str) -> dict[str, Any]:
    """Honest multi-area readiness: no proxying story-runtime signals from Writers-Room artifacts."""
    writers_room_review = _latest_writers_room_review()
    improvement_package = _latest_improvement_package()

    wr_governance_ready = bool(
        writers_room_review and (writers_room_review.get("review_state") or {}).get("status")
    )
    wr_rt = _writers_room_retrieval_trace_tier(writers_room_review)
    wr_has_trace = bool(
        writers_room_review and isinstance(writers_room_review.get("retrieval_trace"), dict)
    )
    wr_evidence_ready = bool(wr_has_trace and _retrieval_tier_strong_enough_for_governance(wr_rt))
    wr_evidence_posture = (
        "missing_retrieval_trace"
        if not wr_has_trace
        else (
            "strong_enough_for_review"
            if _retrieval_tier_strong_enough_for_governance(wr_rt)
            else f"weak_retrieval_tier:{wr_rt}"
        )
    )

    improvement_ready = bool(
        improvement_package and (improvement_package.get("evidence_bundle") or {}).get("comparison")
    )
    improvement_governance_ready = bool(
        improvement_ready
        and (improvement_package.get("evidence_bundle") or {}).get("governance_review_bundle_id")
    )
    imp_map = _improvement_evidence_strength_map(improvement_package)
    imp_retrieval_class = imp_map.get("retrieval_context") if imp_map else None
    improvement_retrieval_backing_ready = bool(
        improvement_package
        and imp_map is not None
        and imp_retrieval_class not in (None, "none")
    )
    if not improvement_package:
        imp_backing_reason = "no improvement recommendation package found"
        imp_backing_posture = "no_package"
    elif imp_map is None:
        imp_backing_reason = "latest package has no evidence_strength_map (legacy or incomplete)"
        imp_backing_posture = "missing_strength_map"
    elif imp_retrieval_class == "none":
        imp_backing_reason = (
            "latest package has governance artifacts but retrieval_context strength is none "
            "(recommendation not materially retrieval-backed)"
        )
        imp_backing_posture = "weak_retrieval_backing"
    else:
        imp_backing_reason = "retrieval_context strength is not none on latest package"
        imp_backing_posture = "retrieval_backed"

    areas = [
        {
            "area": "story_runtime_cross_layer",
            "status": "partial",
            "evidence_posture": "aggregate_only_not_session_scoped",
            "reason": (
                "This aggregate report does not inspect a live World-Engine session; "
                "use GET /admin/ai-stack/session-evidence/<id> after turns for bridged execution_truth."
            ),
        },
        {
            "area": "runtime_turn_graph_contract",
            "status": "ready",
            "evidence_posture": "repository_contract_verified_by_tests",
            "reason": (
                "Repository implements RuntimeTurnGraphExecutor with execution_health, "
                "fallback markers, and repro_metadata (verified in ai_stack/world-engine tests)."
            ),
        },
        {
            "area": "writers_room_review_artifacts",
            "status": "ready" if wr_governance_ready else "partial",
            "evidence_posture": "governance_review_state_present" if wr_governance_ready else "missing_review_state",
            "reason": "Persisted writers-room review with review_state"
            if wr_governance_ready
            else "no persisted writers-room review artifacts with review state",
        },
        {
            "area": "writers_room_retrieval_evidence_surface",
            "status": "ready" if wr_evidence_ready else "partial",
            "evidence_posture": wr_evidence_posture,
            "reason": (
                "Latest writers-room review has retrieval_trace with moderate or strong evidence tier"
                if wr_evidence_ready
                else (
                    f"retrieval evidence tier is weak or none (tier={wr_rt!r}); "
                    "not treated as review-grade retrieval backing"
                    if wr_has_trace
                    else "no retrieval_trace on latest writers-room review"
                )
            ),
        },
        {
            "area": "writers_room_langgraph_orchestration_depth",
            "status": "partial",
            "evidence_posture": "seed_stub_intentionally_lightweight",
            "reason": (
                "Writers-Room workflow uses a LangGraph seed graph stub for workflow_seed; "
                "it is not runtime turn-graph parity (intentionally lightweight)."
            ),
        },
        {
            "area": "improvement_governance_evidence",
            "status": "ready" if improvement_governance_ready else "partial",
            "evidence_posture": (
                "comparison_and_governance_bundle_id_present"
                if improvement_governance_ready
                else "missing_comparison_or_governance_bundle_id"
            ),
            "reason": "Recommendation package includes comparison plus governance review bundle id"
            if improvement_governance_ready
            else (
                "improvement package missing governance_review_bundle_id or comparison evidence"
                if improvement_package
                else "no improvement recommendation package found"
            ),
        },
        {
            "area": "improvement_retrieval_evidence_backing",
            "status": "ready" if improvement_retrieval_backing_ready else "partial",
            "evidence_posture": imp_backing_posture,
            "reason": imp_backing_reason,
        },
    ]
    overall = "ready" if all(area["status"] == "ready" for area in areas) else "partial"
    decision_support = {
        "committed_vs_diagnostic_authority": "world_engine_session_fields_and_history_vs_diagnostics_envelopes",
        "latest_writers_room_retrieval_tier": wr_rt,
        "latest_improvement_retrieval_context_class": imp_retrieval_class,
        "latest_improvement_selected_by": "max_generated_at_timestamp",
        "writers_room_review_ready_for_retrieval_graded_review": wr_evidence_ready,
        "improvement_review_ready_for_retrieval_graded_review": improvement_retrieval_backing_ready,
    }
    return {
        "trace_id": trace_id,
        "overall_status": overall,
        "areas": areas,
        "decision_support": decision_support,
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
        "known_environment_sensitivities": [
            "writers_room_and_improvement_artifacts_depend_on_local_var_json_layout",
            "improvement_latest_package_requires_parseable_generated_at_iso_timestamps",
        ],
    }
