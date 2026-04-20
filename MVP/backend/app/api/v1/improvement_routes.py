from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.contracts.improvement_operating_loop import ImprovementLoopStage
from app.observability.audit_log import log_workflow_audit
from app.observability.trace import get_trace_id
from app.services.improvement_service import (
    ImprovementStore,
    apply_improvement_recommendation_decision,
    build_evidence_strength_map,
    build_recommendation_package,
    build_recommendation_rationale,
    create_variant,
    finalize_recommendation_rationale_with_retrieval_digest,
    list_recommendation_packages,
    recompute_semantic_compliance_validation,
    run_sandbox_experiment,
)
from app.services.improvement_task2a_routing import enrich_improvement_package_with_task2a_routing
from ai_stack import (
    CapabilityAccessDeniedError,
    CapabilityInvocationError,
    build_retrieval_trace,
    build_runtime_retriever,
    create_default_capability_registry,
)
from ai_stack.operational_profile import build_operational_cost_hints_from_retrieval

_improvement_rag_lock = threading.Lock()
# Process-lifetime cache: (repo_root, retriever, assembler, capability_registry)
_improvement_rag_stack: tuple[Path, Any, Any, Any] | None = None


def _get_improvement_rag_stack(repo_root: Path) -> tuple[Any, Any, Any]:
    """Return shared retriever, assembler, and capability registry for improvement workflows.

    Caching avoids rebuilding the on-disk corpus handle and capability registry on every
    experiment POST. Cache is keyed by ``repo_root`` and lasts for the process lifetime;
    if corpus files change on disk, restart the process to pick up a fresh index.
    """
    global _improvement_rag_stack
    with _improvement_rag_lock:
        if _improvement_rag_stack is not None:
            cached_root, retriever, assembler, registry = _improvement_rag_stack
            if cached_root == repo_root:
                return retriever, assembler, registry
        retriever, assembler, _corpus = build_runtime_retriever(repo_root)
        capability_registry = create_default_capability_registry(
            retriever=retriever,
            assembler=assembler,
            repo_root=repo_root,
        )
        _improvement_rag_stack = (repo_root, retriever, assembler, capability_registry)
        return retriever, assembler, capability_registry


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _transcript_tool_evidence_for_improvement(
    *,
    repo_root: Path,
    experiment: dict[str, Any],
    capability_registry: Any,
    actor_id: str,
    trace_id: str | None,
) -> tuple[str, dict[str, Any]]:
    """Persist sandbox transcript, read via capability tool, return (summary_suffix, meta).

    The suffix is derived only from ``wos.transcript.read`` output so workflows visibly depend
    on tool content rather than optional decoration.
    """
    runs_dir = repo_root / "world-engine" / "app" / "var" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"improvement_{experiment['experiment_id']}"
    payload = {
        "experiment_id": experiment["experiment_id"],
        "variant_id": experiment["variant_id"],
        "transcript": experiment.get("transcript", []),
    }
    run_path = runs_dir / f"{run_id}.json"
    run_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    try:
        t_result = capability_registry.invoke(
            name="wos.transcript.read",
            mode="improvement",
            actor=f"improvement:{actor_id}",
            trace_id=trace_id,
            payload={"run_id": run_id},
        )
    except CapabilityInvocationError:
        return "|transcript_tool_error", {"run_id": run_id, "tool_error": True}
    content = t_result.get("content", "")
    meta: dict[str, Any] = {"run_id": run_id, "content_length": len(str(content))}
    if not str(content).strip():
        return "|transcript_tool_empty", meta
    try:
        parsed = json.loads(str(content))
    except json.JSONDecodeError:
        return "|transcript_json_invalid", meta
    turns = parsed.get("transcript")
    if not isinstance(turns, list):
        return "|transcript_shape_invalid", meta
    rep = sum(1 for row in turns if isinstance(row, dict) and row.get("repetition_flag"))
    meta["turn_count"] = len(turns)
    meta["repetition_turn_count"] = rep
    suffix = f"|tr_turns={len(turns)}|tr_rep={rep}"
    return suffix, meta


@api_v1_bp.route("/improvement/variants", methods=["POST"])
@jwt_required()
def create_improvement_variant():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    baseline_id = (data.get("baseline_id") or "").strip()
    candidate_summary = (data.get("candidate_summary") or "").strip()
    if not baseline_id:
        return jsonify({"error": "baseline_id is required"}), 400
    if not candidate_summary:
        return jsonify({"error": "candidate_summary is required"}), 400
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    raw_iec = data.get("improvement_entry_class")
    top_iec = raw_iec.strip() if isinstance(raw_iec, str) and raw_iec.strip() else None
    try:
        variant = create_variant(
            baseline_id=baseline_id,
            candidate_summary=candidate_summary,
            actor_id=actor_id,
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
            improvement_entry_class=top_iec,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    log_workflow_audit(
        trace_id,
        workflow="improvement_variant_create",
        actor_id=actor_id,
        outcome="ok",
        resource_id=variant.get("variant_id"),
    )
    return jsonify(variant), 201


@api_v1_bp.route("/improvement/experiments/run", methods=["POST"])
@jwt_required()
def run_improvement_experiment():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    variant_id = (data.get("variant_id") or "").strip()
    if not variant_id:
        return jsonify({"error": "variant_id is required"}), 400
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    test_inputs = data.get("test_inputs")
    if test_inputs is not None and not isinstance(test_inputs, list):
        return jsonify({"error": "test_inputs must be a list when provided"}), 400

    workflow_stages: list[dict[str, Any]] = [
        {
            "id": "variant_resolution",
            "loop_stage": ImprovementLoopStage.issue_selection.value,
            "completed_at": _utc_iso(),
            "artifact_key": "variant_id",
            "resource_id": variant_id,
        }
    ]
    experiment = run_sandbox_experiment(
        variant_id=variant_id,
        actor_id=actor_id,
        test_inputs=[str(item) for item in test_inputs] if isinstance(test_inputs, list) else None,
    )
    workflow_stages.append(
        {
            "id": "baseline_context",
            "loop_stage": ImprovementLoopStage.evidence_collection.value,
            "completed_at": _utc_iso(),
            "artifact_key": "baseline_id",
            "resource_id": experiment.get("baseline_id"),
        }
    )
    workflow_stages.append(
        {
            "id": "sandbox_execution",
            "loop_stage": ImprovementLoopStage.evidence_collection.value,
            "completed_at": _utc_iso(),
            "artifact_key": "experiment",
            "resource_id": experiment.get("experiment_id"),
        }
    )
    package = build_recommendation_package(experiment_id=experiment["experiment_id"], actor_id=actor_id)
    workflow_stages.append(
        {
            "id": "evaluation_and_recommendation_draft",
            "loop_stage": ImprovementLoopStage.bounded_proposal_generation.value,
            "completed_at": _utc_iso(),
            "artifact_key": "recommendation_package",
            "resource_id": package.get("package_id"),
        }
    )

    repo_root = Path(__file__).resolve().parents[4]
    _retriever, _assembler, capability_registry = _get_improvement_rag_stack(repo_root)
    try:
        context_payload = capability_registry.invoke(
            name="wos.context_pack.build",
            mode="improvement",
            actor=f"improvement:{actor_id}",
            trace_id=trace_id,
            payload={
                "domain": "improvement",
                "profile": "improvement_eval",
                "query": f"{experiment['baseline_id']} {package['candidate']['candidate_summary']} "
                "variant evaluation recommendation",
                "module_id": experiment["baseline_id"],
                "max_chunks": 5,
            },
        )
        workflow_stages.append(
            {
                "id": "retrieval_improvement_context",
                "loop_stage": ImprovementLoopStage.evidence_collection.value,
                "completed_at": _utc_iso(),
                "artifact_key": "wos.context_pack.build",
            }
        )
        retrieval_inner = context_payload.get("retrieval")
        retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
        evidence_tag = retrieval_trace["evidence_tier"]
        transcript_suffix, transcript_meta = _transcript_tool_evidence_for_improvement(
            repo_root=repo_root,
            experiment=experiment,
            capability_registry=capability_registry,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        workflow_stages.append(
            {
                "id": "transcript_tool_evidence",
                "loop_stage": ImprovementLoopStage.evidence_collection.value,
                "completed_at": _utc_iso(),
                "artifact_key": "wos.transcript.read",
                "resource_id": transcript_meta.get("run_id"),
            }
        )
        evidence_sources = [
            source.get("source_path", "")
            for source in context_payload.get("retrieval", {}).get("sources", [])
            if isinstance(source, dict)
        ]
        package_response = dict(package)
        base_summary = str(package_response["recommendation_summary"])
        if transcript_meta.get("repetition_turn_count", 0) >= 2:
            package_response["deterministic_recommendation_base"] = "revise_before_review"
            package_response["recommendation_summary"] = "revise_before_review" + transcript_suffix
        else:
            package_response["deterministic_recommendation_base"] = base_summary
            package_response["recommendation_summary"] = base_summary + transcript_suffix
        package_response["transcript_evidence"] = transcript_meta

        evaluation_block = package_response.get("evaluation") if isinstance(package_response.get("evaluation"), dict) else {}
        evidence_bundle = dict(package_response.get("evidence_bundle") or {})
        evidence_bundle["retrieval_source_paths"] = list(evidence_sources)
        evidence_bundle["transcript_evidence"] = {
            "run_id": transcript_meta.get("run_id"),
            "turn_count": transcript_meta.get("turn_count"),
            "repetition_turn_count": transcript_meta.get("repetition_turn_count"),
            "content_length": transcript_meta.get("content_length"),
        }
        evidence_bundle["metrics_snapshot"] = evaluation_block.get("metrics")
        evidence_bundle["baseline_metrics_snapshot"] = evaluation_block.get("baseline_metrics")
        evidence_bundle["comparison_snapshot"] = evaluation_block.get("comparison")
        package_response["evidence_bundle"] = evidence_bundle

        review_bundle = capability_registry.invoke(
            name="wos.review_bundle.build",
            mode="improvement",
            actor=f"improvement:{actor_id}",
            trace_id=trace_id,
            payload={
                "module_id": experiment["baseline_id"],
                "summary": (
                    f"[evidence_tier:{evidence_tag}] [transcript:{transcript_meta.get('run_id', '')}] "
                    f"Improvement recommendation for variant {experiment['variant_id']}."
                ),
                "recommendations": [package_response["recommendation_summary"]],
                "evidence_sources": evidence_sources,
            },
        )
        workflow_stages.append(
            {
                "id": "governance_review_bundle",
                "loop_stage": ImprovementLoopStage.bounded_proposal_generation.value,
                "completed_at": _utc_iso(),
                "artifact_key": "wos.review_bundle.build",
                "resource_id": (review_bundle.get("bundle_id") if isinstance(review_bundle, dict) else None),
            }
        )
        evidence_bundle_final = dict(package_response["evidence_bundle"])
        if isinstance(review_bundle, dict):
            evidence_bundle_final["governance_review_bundle_id"] = review_bundle.get("bundle_id")
            evidence_bundle_final["governance_review_bundle_status"] = review_bundle.get("status")

        hit_count = len(evidence_sources)
        if isinstance(retrieval_inner, dict) and retrieval_inner.get("hit_count") is not None:
            try:
                hit_count = int(retrieval_inner["hit_count"])
            except (TypeError, ValueError):
                hit_count = len(evidence_sources)

        rationale_fresh = build_recommendation_rationale(
            evaluation=package_response["evaluation"],
            recommendation_summary=package_response["recommendation_summary"],
            retrieval_hit_count=hit_count,
            retrieval_source_paths=evidence_sources,
            transcript_meta=transcript_meta,
        )
        rationale_final = finalize_recommendation_rationale_with_retrieval_digest(
            rationale_fresh,
            context_text=str(context_payload.get("context_text") or ""),
            retrieval_source_paths=evidence_sources,
            hit_count=hit_count,
        )
        package_response["recommendation_rationale"] = rationale_final
        package_response["evidence_strength_map"] = build_evidence_strength_map(
            evaluation=package_response["evaluation"],
            retrieval_hit_count=hit_count,
            transcript_tool_ok=bool(
                transcript_meta.get("turn_count") is not None and not transcript_meta.get("tool_error")
            ),
            governance_bundle_attached=isinstance(review_bundle, dict) and bool(review_bundle.get("bundle_id")),
        )
        evidence_bundle_final["retrieval_context_fingerprint_sha256_16"] = rationale_final.get(
            "retrieval_context_fingerprint_sha256_16"
        )
        evidence_bundle_final["recommendation_driver_categories"] = [
            d.get("category")
            for d in (rationale_final.get("drivers") or [])
            if isinstance(d, dict) and d.get("category")
        ]
        evidence_bundle_final["retrieval_readiness"] = {
            "evidence_tier": retrieval_trace.get("evidence_tier"),
            "confidence_posture": retrieval_trace.get("confidence_posture"),
            "evidence_lane_mix": retrieval_trace.get("evidence_lane_mix"),
            "lane_anchor_counts": retrieval_trace.get("lane_anchor_counts"),
            "retrieval_posture_summary": retrieval_trace.get("retrieval_posture_summary"),
            "governance_influence_compact": retrieval_trace.get("governance_influence_compact"),
            "readiness_label": retrieval_trace.get("readiness_label"),
            "policy_outcome_hint": retrieval_trace.get("policy_outcome_hint"),
            "retrieval_quality_hint": retrieval_trace.get("retrieval_quality_hint"),
            "retrieval_trace_schema_version": retrieval_trace.get("retrieval_trace_schema_version"),
        }

        package_response["evidence_bundle"] = evidence_bundle_final
        enrich_improvement_package_with_task2a_routing(
            package_response,
            context_text=str(context_payload.get("context_text") or ""),
            baseline_id=experiment["baseline_id"],
            variant_id=experiment["variant_id"],
        )
        workflow_stages.append(
            {
                "id": "semantic_compliance_validation",
                "loop_stage": ImprovementLoopStage.semantic_compliance_validation.value,
                "completed_at": _utc_iso(),
                "artifact_key": "semantic_compliance_validation",
                "resource_id": package_response.get("package_id"),
            }
        )
        package_response["workflow_stages"] = workflow_stages
        recompute_semantic_compliance_validation(package_response)
        ImprovementStore.default().write_json(
            "recommendations",
            str(package_response["package_id"]),
            package_response,
        )
    except (CapabilityAccessDeniedError, CapabilityInvocationError) as exc:
        return (
            jsonify(
                {
                    "error": "capability_workflow_failed",
                    "detail": str(exc),
                    "trace_id": trace_id,
                    "capability_audit": capability_registry.recent_audit(limit=20),
                }
            ),
            502,
        )
    log_workflow_audit(
        trace_id,
        workflow="improvement_experiment_run",
        actor_id=actor_id,
        outcome="ok",
        resource_id=experiment.get("experiment_id"),
    )
    return jsonify(
        {
            "trace_id": trace_id,
            "experiment": experiment,
            "recommendation_package": package_response,
            "workflow_stages": workflow_stages,
            "retrieval": context_payload.get("retrieval", {}),
            "retrieval_trace": retrieval_trace,
            "transcript_evidence": transcript_meta,
            "review_bundle": review_bundle,
            "capability_audit": capability_registry.recent_audit(limit=20),
            "operational_cost_hints": build_operational_cost_hints_from_retrieval(
                context_payload.get("retrieval") if isinstance(context_payload.get("retrieval"), dict) else {}
            ),
        }
    ), 200


@api_v1_bp.route("/improvement/recommendations", methods=["GET"])
@jwt_required()
def list_improvement_recommendations():
    return jsonify({"packages": list_recommendation_packages()}), 200


@api_v1_bp.route("/improvement/recommendations/<package_id>/decision", methods=["POST"])
@jwt_required()
def improvement_recommendation_decision(package_id: str):
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    decision = data.get("decision")
    if not isinstance(decision, str) or not decision.strip():
        return jsonify({"error": "decision is required"}), 400
    note = data.get("note") if isinstance(data.get("note"), str) else None
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    try:
        package = apply_improvement_recommendation_decision(
            package_id=package_id.strip(),
            actor_id=actor_id,
            decision=decision.strip(),
            note=note,
        )
    except FileNotFoundError:
        return jsonify({"error": "recommendation package not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    log_workflow_audit(
        trace_id,
        workflow="improvement_recommendation_decision",
        actor_id=actor_id,
        outcome="ok",
        resource_id=package_id,
    )
    return jsonify(package), 200
