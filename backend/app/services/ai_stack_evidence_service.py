"""Aggregate AI-stack evidence for governance (World-Engine diagnostics + backend session truth)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_stack import build_retrieval_trace

from app.runtime.session_store import get_session as get_runtime_session
from app.services.improvement_service import list_recommendation_packages
from app.services.ai_stack_evidence_internals import (  # noqa: F401
    _improvement_evidence_strength_map,
    _retrieval_tier_strong_enough_for_governance,
    _writers_room_retrieval_trace_tier,
)

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
    """Build retrieval diagnostics for session evidence bundles.

    Values are control-plane and diagnostic aggregates from the retrieval trace only.
    They are not semantic authority and must not be treated as canonical authored truth.
    """
    if not isinstance(last_turn, dict):
        return None
    retrieval = last_turn.get("retrieval")
    if not isinstance(retrieval, dict):
        retrieval = {}
    trace = build_retrieval_trace(retrieval)
    out: dict[str, Any] = {
        "domain": trace.get("domain"),
        "profile": trace.get("profile"),
        "hit_count": trace.get("hit_count"),
        "status": trace.get("status"),
        "evidence_strength": trace.get("evidence_strength"),
        "evidence_tier": trace.get("evidence_tier"),
        "evidence_rationale": trace.get("evidence_rationale"),
        "evidence_lane_mix": trace.get("evidence_lane_mix"),
        "lane_anchor_counts": trace.get("lane_anchor_counts"),
        "confidence_posture": trace.get("confidence_posture"),
        "retrieval_posture_summary": trace.get("retrieval_posture_summary"),
        "governance_influence_compact": trace.get("governance_influence_compact"),
        "readiness_label": trace.get("readiness_label"),
        "retrieval_quality_hint": trace.get("retrieval_quality_hint"),
        "policy_outcome_hint": trace.get("policy_outcome_hint"),
        "dedup_shaped_selection": trace.get("dedup_shaped_selection"),
        "retrieval_trace_schema_version": trace.get("retrieval_trace_schema_version"),
    }
    rgs = trace.get("retrieval_governance_summary")
    if isinstance(rgs, dict):
        out["retrieval_governance_summary"] = rgs
    return out


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
    loop_stages: list[str] = []
    if isinstance(stages, list):
        for s in stages:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                stage_ids.append(s["id"])
            if isinstance(s, dict) and isinstance(s.get("loop_stage"), str):
                loop_stages.append(s["loop_stage"])
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
    sc = package.get("semantic_compliance_validation")
    sc_status = sc.get("status") if isinstance(sc, dict) else None
    ilp = package.get("improvement_loop_progress")
    ilp_len = len(ilp) if isinstance(ilp, list) else 0
    return {
        "workflow_stage_ids": stage_ids,
        "improvement_loop_stages": loop_stages,
        "semantic_compliance_status": sc_status,
        "improvement_loop_progress_len": ilp_len,
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
            "retrieval_confidence_posture": rt.get("confidence_posture"),
            "retrieval_posture_summary": rt.get("retrieval_posture_summary"),
            "retrieval_lane_anchor_counts": rt.get("lane_anchor_counts"),
            "langgraph_orchestration": "seed_stub_not_runtime_turn_parity",
        },
        "artifact_counts": {
            "issues": len(review.get("issues", [])),
            "patch_candidates": len(review.get("patch_candidates", [])),
            "variant_candidates": len(review.get("variant_candidates", [])),
        },
    }


def assemble_session_evidence_bundle(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Build governance session evidence bundle (same contract as historical ``session_bundle`` module)."""
    from app.services.ai_stack_evidence_session_bundle_sections import (
        apply_diagnostics_execution_truth_and_retrieval,
        apply_world_engine_bridge,
        apply_writers_room_and_improvement_signals,
        session_bundle_base_scaffold,
        session_bundle_not_found,
    )

    import sys

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return session_bundle_not_found(trace_id=trace_id, session_id=session_id)

    state = runtime_session.current_runtime_state
    metadata = state.metadata if isinstance(state.metadata, dict) else {}
    engine_id = metadata.get("world_engine_story_session_id")

    bundle = session_bundle_base_scaffold(
        trace_id=trace_id,
        session_id=session_id,
        state=state,
        engine_id=engine_id,
    )

    apply_world_engine_bridge(bundle, engine_id=engine_id, trace_id=trace_id)
    ev_mod = sys.modules[__name__]
    apply_diagnostics_execution_truth_and_retrieval(bundle, ev_mod)
    apply_writers_room_and_improvement_signals(bundle, ev_mod)

    return bundle


def build_session_evidence_bundle(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return inspectable evidence for a backend runtime session (may include World-Engine story host data)."""
    return assemble_session_evidence_bundle(session_id=session_id, trace_id=trace_id)


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




def build_release_readiness_report(*, trace_id: str) -> dict[str, Any]:
    """Honest multi-area readiness: no proxying story-runtime signals from Writers-Room artifacts."""
    from app.services.ai_stack_release_readiness_report import build_release_readiness_report_payload

    writers_room_review = _latest_writers_room_review()
    improvement_package = _latest_improvement_package()
    return build_release_readiness_report_payload(
        trace_id=trace_id,
        writers_room_review=writers_room_review,
        improvement_package=improvement_package,
    )
