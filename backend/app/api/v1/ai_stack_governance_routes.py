"""Governance-facing AI stack evidence APIs (moderator/admin, feature-gated)."""

from __future__ import annotations

from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_GAME_OPERATIONS
from app.auth.permissions import get_current_user, require_feature, require_jwt_moderator_or_admin
from app.extensions import limiter
from app.observability.trace import get_trace_id
from app.services.activity_log_service import log_activity
from app.services.ai_stack_evidence_service import build_release_readiness_report, build_session_evidence_bundle
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
