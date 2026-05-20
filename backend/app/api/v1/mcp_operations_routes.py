"""MCP operations cockpit: telemetry ingest (service token) and admin read/actions."""

from __future__ import annotations

import json

from flask import current_app, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.auth import require_mcp_service_token
from app.auth.feature_registry import FEATURE_MANAGE_MCP_OPERATIONS
from app.auth.permissions import require_feature, require_jwt_moderator_or_admin
from app.extensions import db, limiter
from app.services.mcp.mcp_operations_service import (
    INGEST_MAX_BODY_BYTES,
    action_audit_bundle,
    action_refresh_catalog,
    case_to_dict,
    create_manual_case,
    get_overview,
    get_suites_detail,
    ingest_telemetry_batch,
    query_activity,
    query_diagnostics,
    query_logs,
    rebuild_automatic_cases,
    reclassify_case,
)
from app.config.route_constants import route_status_codes, route_pagination_config


def _parse_int_q(q: str | None, default: int, *, min_v: int = 1, max_v: int = 500) -> int:
    if q is None or q == "":
        return default
    try:
        n = int(q)
        return max(min_v, min(n, max_v))
    except (TypeError, ValueError):
        return default


@api_v1_bp.route("/operator/mcp-telemetry/ingest", methods=["POST"])
@limiter.limit("120 per minute")
@require_mcp_service_token
def mcp_telemetry_ingest():
    """Append-only ingest for MCP process JSON log lines (Bearer MCP_SERVICE_TOKEN)."""
    raw = request.get_data(cache=False, as_text=False) or b""
    if len(raw) > INGEST_MAX_BODY_BYTES:
        return jsonify({"error": {"code": "PAYLOAD_TOO_LARGE", "message": "Body exceeds limit"}}), route_status_codes.bad_request
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return jsonify({"error": {"code": "INVALID_JSON", "message": "Invalid JSON"}}), route_status_codes.bad_request
    if not isinstance(body, dict):
        return jsonify({"error": {"code": "INVALID_BODY", "message": "JSON object required"}}), route_status_codes.bad_request
    records = body.get("records")
    if not isinstance(records, list):
        return jsonify({"error": {"code": "INVALID_RECORDS", "message": "records array required"}}), route_status_codes.bad_request
    if len(records) > 200:
        return jsonify({"error": {"code": "TOO_MANY_RECORDS", "message": "Max 200 records per request"}}), route_status_codes.bad_request
    try:
        out = ingest_telemetry_batch(records)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": {"code": "INGEST_FAILED", "message": str(exc)}}), route_status_codes.internal_error
    return jsonify(out), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/overview", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_overview():
    return jsonify(get_overview(current_app._get_current_object())), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/suites", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_suites():
    return jsonify(get_suites_detail()), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/activity", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_activity():
    page = _parse_int_q(request.args.get("page"), 1, min_v=1, max_v=10_000)
    limit = _parse_int_q(request.args.get("limit"), 50, min_v=1, max_v=200)
    suite = (request.args.get("suite") or "").strip() or None
    trace_id = (request.args.get("trace_id") or "").strip() or None
    errors_only = (request.args.get("errors_only") or "").strip().lower() in ("1", "true", "yes")
    items, total = query_activity(page=page, limit=limit, suite=suite, trace_id=trace_id, errors_only=errors_only)
    return jsonify({"items": items, "total": total, "page": page, "limit": limit}), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/logs", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_logs():
    page = _parse_int_q(request.args.get("page"), 1, min_v=1, max_v=10_000)
    limit = _parse_int_q(request.args.get("limit"), 50, min_v=1, max_v=200)
    log_level = (request.args.get("log_level") or "").strip().lower() or None
    if log_level not in (None, "", "info", "error", "warning"):
        log_level = None
    suite = (request.args.get("suite") or "").strip() or None
    trace_id = (request.args.get("trace_id") or "").strip() or None
    session_id = (request.args.get("session_id") or "").strip() or None
    errors_only = (request.args.get("errors_only") or "").strip().lower() in ("1", "true", "yes")
    date_from = (request.args.get("date_from") or "").strip() or None
    date_to = (request.args.get("date_to") or "").strip() or None
    items, total = query_logs(
        page=page,
        limit=limit,
        log_level=log_level,
        suite=suite,
        trace_id=trace_id,
        session_id=session_id,
        errors_only=errors_only,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify({"items": items, "total": total, "page": page, "limit": limit}), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/diagnostics", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_diagnostics_list():
    page = _parse_int_q(request.args.get("page"), 1, min_v=1, max_v=10_000)
    limit = _parse_int_q(request.args.get("limit"), 50, min_v=1, max_v=200)
    status = (request.args.get("status") or "").strip() or None
    items, total = query_diagnostics(page=page, limit=limit, status=status)
    return jsonify({"items": items, "total": total, "page": page, "limit": limit}), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/diagnostics/manual", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_diagnostics_manual():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object required"}), route_status_codes.bad_request
    case_type = (body.get("case_type") or "").strip()
    summary = (body.get("summary") or "").strip()
    if not case_type or not summary:
        return jsonify({"error": "case_type and summary required"}), route_status_codes.bad_request
    suite_name = (body.get("suite_name") or "unknown").strip()[:40] or "unknown"
    severity = (body.get("severity") or "medium").strip()[:16]
    rec = body.get("recommended_next_action")
    rec_s = str(rec).strip()[:512] if rec is not None else None
    try:
        c = create_manual_case(
            case_type=case_type,
            summary=summary,
            suite_name=suite_name,
            severity=severity,
            recommended_next_action=rec_s,
        )
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), route_status_codes.internal_error
    return jsonify(case_to_dict(c)), route_status_codes.created


@api_v1_bp.route("/admin/mcp/actions/refresh-catalog", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_action_refresh_catalog():
    return jsonify(action_refresh_catalog(current_app._get_current_object())), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/actions/retry-job", methods=["POST"])
@limiter.limit("10 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_action_retry_job():
    """Idempotent rebuild of auto_rule diagnostic cases from telemetry (MVP 'retry job')."""
    body = request.get_json(silent=True) or {}
    since_days = 30
    if isinstance(body, dict) and body.get("since_days") is not None:
        try:
            since_days = int(body["since_days"])
        except (TypeError, ValueError):
            pass
    try:
        out = rebuild_automatic_cases(since_days=since_days)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), route_status_codes.internal_error
    return jsonify(out), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/actions/generate-audit-bundle", methods=["POST"])
@limiter.limit("10 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_action_audit_bundle():
    body = request.get_json(silent=True) or {}
    lim = 500
    if isinstance(body, dict) and body.get("limit_events") is not None:
        try:
            lim = int(body["limit_events"])
        except (TypeError, ValueError):
            pass
    lim = max(1, min(lim, 2000))
    return jsonify(action_audit_bundle(limit_events=lim)), route_status_codes.ok


@api_v1_bp.route("/admin/mcp/actions/reclassify-diagnostic", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_MCP_OPERATIONS)
def admin_mcp_action_reclassify():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object required"}), route_status_codes.bad_request
    case_id = (body.get("case_id") or "").strip()
    if not case_id:
        return jsonify({"error": "case_id required"}), route_status_codes.bad_request
    try:
        c = reclassify_case(
            public_id=case_id,
            case_type=body.get("case_type"),
            status=body.get("status"),
            suite_display_override=body.get("suite_display_override"),
        )
        if not c:
            return jsonify({"error": "case not found"}), route_status_codes.not_found
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), route_status_codes.internal_error
    return jsonify(case_to_dict(c)), route_status_codes.ok
