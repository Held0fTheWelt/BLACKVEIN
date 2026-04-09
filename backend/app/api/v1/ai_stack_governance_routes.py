"""Governance-facing AI stack evidence APIs (moderator/admin, feature-gated)."""

from __future__ import annotations

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_GAME_OPERATIONS
from app.auth.permissions import get_current_user, require_feature, require_jwt_moderator_or_admin
from app.extensions import limiter
from app.observability.trace import get_trace_id
from app.services.activity_log_service import log_activity
from app.services.ai_stack_closure_cockpit_service import build_closure_cockpit_report
from app.services.ai_stack_evidence_service import build_release_readiness_report, build_session_evidence_bundle
from app.services.inspector_projection_service import (
    build_inspector_comparison_projection,
    build_inspector_coverage_health_projection,
    build_inspector_provenance_raw_projection,
    build_inspector_timeline_projection,
)
from app.services.inspector_turn_projection_service import build_inspector_turn_projection
from app.services.improvement_service import list_recommendation_packages


@api_v1_bp.route("/admin/ai-stack/session-evidence/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_session_evidence(session_id: str):
    """Aggregate backend session + World-Engine diagnostics for human review."""
    trace_id = g.get("trace_id") or get_trace_id()
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="session_evidence_view",
        status="success" if bundle.get("error") != "backend_session_not_found" else "error",
        message=f"AI stack evidence for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id},
    )
    status = 404 if bundle.get("error") == "backend_session_not_found" else 200
    return jsonify(bundle), status


@api_v1_bp.route("/admin/ai-stack/inspector/turn/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_inspector_turn_projection(session_id: str):
    """Return canonical single-turn diagnostic projection for Inspector Suite (read-only)."""
    trace_id = g.get("trace_id") or get_trace_id()
    mode = (request.args.get("mode") or "canonical").strip().lower()
    if mode not in {"canonical", "raw"}:
        mode = "canonical"
    payload = build_inspector_turn_projection(session_id=session_id, trace_id=trace_id, mode=mode)
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="inspector_turn_projection_view",
        status="success" if payload.get("error") != "backend_session_not_found" else "error",
        message=f"Inspector turn projection for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id, "mode": mode},
    )
    status = 404 if payload.get("error") == "backend_session_not_found" else 200
    return jsonify(payload), status


@api_v1_bp.route("/admin/ai-stack/inspector/timeline/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_inspector_timeline_projection(session_id: str):
    """Return read-only multi-turn timeline projection for one session."""
    trace_id = g.get("trace_id") or get_trace_id()
    payload = build_inspector_timeline_projection(session_id=session_id, trace_id=trace_id)
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="inspector_timeline_projection_view",
        status="success" if payload.get("error") != "backend_session_not_found" else "error",
        message=f"Inspector timeline projection for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id},
    )
    status = 404 if payload.get("error") == "backend_session_not_found" else 200
    return jsonify(payload), status


@api_v1_bp.route("/admin/ai-stack/inspector/comparison/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_inspector_comparison_projection(session_id: str):
    """Return bounded read-only comparison projection for one session."""
    trace_id = g.get("trace_id") or get_trace_id()
    payload = build_inspector_comparison_projection(session_id=session_id, trace_id=trace_id)
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="inspector_comparison_projection_view",
        status="success" if payload.get("error") != "backend_session_not_found" else "error",
        message=f"Inspector comparison projection for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id},
    )
    status = 404 if payload.get("error") == "backend_session_not_found" else 200
    return jsonify(payload), status


@api_v1_bp.route("/admin/ai-stack/inspector/coverage-health/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_inspector_coverage_health_projection(session_id: str):
    """Return read-only coverage/health projection for one session."""
    trace_id = g.get("trace_id") or get_trace_id()
    payload = build_inspector_coverage_health_projection(session_id=session_id, trace_id=trace_id)
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="inspector_coverage_health_projection_view",
        status="success" if payload.get("error") != "backend_session_not_found" else "error",
        message=f"Inspector coverage/health projection for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id},
    )
    status = 404 if payload.get("error") == "backend_session_not_found" else 200
    return jsonify(payload), status


@api_v1_bp.route("/admin/ai-stack/inspector/provenance-raw/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_inspector_provenance_raw_projection(session_id: str):
    """Return provenance/read-only raw projection for one session."""
    trace_id = g.get("trace_id") or get_trace_id()
    mode = (request.args.get("mode") or "canonical").strip().lower()
    if mode not in {"canonical", "raw"}:
        mode = "canonical"
    payload = build_inspector_provenance_raw_projection(
        session_id=session_id,
        trace_id=trace_id,
        mode=mode,
    )
    user = get_current_user()
    log_activity(
        actor=user,
        category="ai_stack",
        action="inspector_provenance_raw_projection_view",
        status="success" if payload.get("error") != "backend_session_not_found" else "error",
        message=f"Inspector provenance/raw projection for session {session_id}",
        route=request.path,
        method=request.method,
        target_type="runtime_session",
        target_id=session_id,
        metadata={"trace_id": trace_id, "mode": mode},
    )
    status = 404 if payload.get("error") == "backend_session_not_found" else 200
    return jsonify(payload), status


@api_v1_bp.route("/admin/ai-stack/improvement-packages", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_improvement_packages():
    """List improvement recommendation packages (same store as authenticated improvement API)."""
    trace_id = g.get("trace_id") or get_trace_id()
    packages = list_recommendation_packages()
    return jsonify({"trace_id": trace_id, "packages": packages, "total": len(packages)}), 200


@api_v1_bp.route("/admin/ai-stack/release-readiness", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_release_readiness():
    """Return honest release-readiness state for repaired AI stack paths."""
    trace_id = g.get("trace_id") or get_trace_id()
    report = build_release_readiness_report(trace_id=trace_id)
    return jsonify(report), 200


@api_v1_bp.route("/admin/ai-stack/closure-cockpit", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_GAME_OPERATIONS)
def admin_ai_stack_closure_cockpit():
    """Return normalized closure cockpit state from canonical GoC audit artifacts."""
    trace_id = g.get("trace_id") or get_trace_id()
    report = build_closure_cockpit_report(trace_id=trace_id)
    return jsonify(report), 200
