from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.api.v1.improvement_experiment_pipeline import apply_capability_pipeline_to_improvement_package
from app.contracts.improvement_operating_loop import ImprovementLoopStage
from app.observability.audit_log import log_workflow_audit
from app.observability.trace import get_trace_id
from app.services.improvement_service import (
    ImprovementStore,
    apply_improvement_recommendation_decision,
    build_recommendation_package,
    create_variant,
    list_recommendation_packages,
    run_sandbox_experiment,
)
from app.config.route_constants import route_status_codes, route_pagination_config
from app.utils.time_utils import _utc_iso

# Imported for stable test patch path ``app.api.v1.improvement_routes.ImprovementStore`` (pipeline calls Store.default()).
from ai_stack import (
    CapabilityAccessDeniedError,
    CapabilityInvocationError,
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
        return jsonify({"error": "Invalid JSON body"}), route_status_codes.bad_request
    baseline_id = (data.get("baseline_id") or "").strip()
    candidate_summary = (data.get("candidate_summary") or "").strip()
    if not baseline_id:
        return jsonify({"error": "baseline_id is required"}), route_status_codes.bad_request
    if not candidate_summary:
        return jsonify({"error": "candidate_summary is required"}), route_status_codes.bad_request
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
        return jsonify({"error": str(exc)}), route_status_codes.bad_request
    log_workflow_audit(
        trace_id,
        workflow="improvement_variant_create",
        actor_id=actor_id,
        outcome="ok",
        resource_id=variant.get("variant_id"),
    )
    return jsonify(variant), route_status_codes.created


@api_v1_bp.route("/improvement/experiments/run", methods=["POST"])
@jwt_required()
def run_improvement_experiment():
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), route_status_codes.bad_request
    variant_id = (data.get("variant_id") or "").strip()
    if not variant_id:
        return jsonify({"error": "variant_id is required"}), route_status_codes.bad_request
    actor_id = str(get_jwt_identity() or "unknown")
    trace_id = g.get("trace_id") or get_trace_id()
    test_inputs = data.get("test_inputs")
    if test_inputs is not None and not isinstance(test_inputs, list):
        return jsonify({"error": "test_inputs must be a list when provided"}), route_status_codes.bad_request

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
        outcome = apply_capability_pipeline_to_improvement_package(
            experiment=experiment,
            package=package,
            actor_id=actor_id,
            trace_id=trace_id,
            repo_root=repo_root,
            capability_registry=capability_registry,
            workflow_stages=workflow_stages,
            utc_iso=_utc_iso,
            transcript_tool_evidence=_transcript_tool_evidence_for_improvement,
        )
        package_response = outcome.package_response
        context_payload = outcome.context_payload
        retrieval_trace = outcome.retrieval_trace
        transcript_meta = outcome.transcript_meta
        review_bundle = outcome.review_bundle
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
    ), route_status_codes.ok


@api_v1_bp.route("/improvement/recommendations", methods=["GET"])
@jwt_required()
def list_improvement_recommendations():
    return jsonify({"packages": list_recommendation_packages()}), route_status_codes.ok


@api_v1_bp.route("/improvement/recommendations/<package_id>/decision", methods=["POST"])
@jwt_required()
def improvement_recommendation_decision(package_id: str):
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), route_status_codes.bad_request
    decision = data.get("decision")
    if not isinstance(decision, str) or not decision.strip():
        return jsonify({"error": "decision is required"}), route_status_codes.bad_request
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
        return jsonify({"error": "recommendation package not found"}), route_status_codes.not_found
    except ValueError as exc:
        return jsonify({"error": str(exc)}), route_status_codes.bad_request
    log_workflow_audit(
        trace_id,
        workflow="improvement_recommendation_decision",
        actor_id=actor_id,
        outcome="ok",
        resource_id=package_id,
    )
    return jsonify(package), route_status_codes.ok
