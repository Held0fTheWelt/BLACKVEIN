from __future__ import annotations

from pathlib import Path

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.observability.audit_log import log_workflow_audit
from app.observability.trace import get_trace_id
from app.services.improvement_service import (
    build_recommendation_package,
    create_variant,
    list_recommendation_packages,
    run_sandbox_experiment,
)
from wos_ai_stack import (
    CapabilityAccessDeniedError,
    CapabilityInvocationError,
    build_retrieval_trace,
    build_runtime_retriever,
    create_default_capability_registry,
)


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
    variant = create_variant(
        baseline_id=baseline_id,
        candidate_summary=candidate_summary,
        actor_id=actor_id,
        metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
    )
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
    experiment = run_sandbox_experiment(
        variant_id=variant_id,
        actor_id=actor_id,
        test_inputs=[str(item) for item in test_inputs] if isinstance(test_inputs, list) else None,
    )
    package = build_recommendation_package(experiment_id=experiment["experiment_id"], actor_id=actor_id)

    repo_root = Path(__file__).resolve().parents[3]
    retriever, assembler, _ = build_runtime_retriever(repo_root)
    capability_registry = create_default_capability_registry(
        retriever=retriever,
        assembler=assembler,
        repo_root=repo_root,
    )
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
        retrieval_inner = context_payload.get("retrieval")
        retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
        evidence_tag = retrieval_trace["evidence_strength"]
        evidence_sources = [
            source.get("source_path", "")
            for source in context_payload.get("retrieval", {}).get("sources", [])
            if isinstance(source, dict)
        ]
        review_bundle = capability_registry.invoke(
            name="wos.review_bundle.build",
            mode="improvement",
            actor=f"improvement:{actor_id}",
            trace_id=trace_id,
            payload={
                "module_id": experiment["baseline_id"],
                "summary": (
                    f"[evidence:{evidence_tag}] Improvement recommendation for variant "
                    f"{experiment['variant_id']}."
                ),
                "recommendations": [package["recommendation_summary"]],
                "evidence_sources": evidence_sources,
            },
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
            "recommendation_package": package,
            "retrieval": context_payload.get("retrieval", {}),
            "retrieval_trace": retrieval_trace,
            "review_bundle": review_bundle,
            "capability_audit": capability_registry.recent_audit(limit=20),
        }
    ), 200


@api_v1_bp.route("/improvement/recommendations", methods=["GET"])
@jwt_required()
def list_improvement_recommendations():
    return jsonify({"packages": list_recommendation_packages()}), 200
