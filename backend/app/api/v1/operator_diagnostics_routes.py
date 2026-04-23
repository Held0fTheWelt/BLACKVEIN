"""Operator diagnostics routes for agency and turn-history visibility.

Surfaces actor-survival telemetry and turn-history dashboards so operators
can diagnose where actor behavior survived or degraded through generation →
validation → commit → render.
"""

from __future__ import annotations

from flask import request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_SYSTEM_DIAGNOSIS
from app.auth.permissions import require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, ok
from app.services.operator_turn_history_service import (
    build_turn_history_summary_for_session,
    operator_diagnostics_surface,
)


@api_v1_bp.route("/operator/diagnostics/session/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_SYSTEM_DIAGNOSIS)
def operator_session_diagnostics(session_id: str):
    """Operator diagnostics surface for a session: actor-survival telemetry,
    degradation patterns, and hints for troubleshooting where actor behavior
    survived or failed through the turn pipeline.
    """
    try:
        from app.services import session_service as _session_service

        getter = getattr(_session_service, "get_session_by_id", None)
        if not callable(getter):
            getter = getattr(_session_service, "get_session", None)
        session = getter(session_id) if callable(getter) else None
        if session is None:
            return fail("session_not_found", f"Session {session_id} not found.", 404, {})

        diagnostics = (
            session.diagnostics
            if hasattr(session, "diagnostics")
            else session.get("diagnostics")
            if isinstance(session, dict)
            else []
        )
        diagnostics_list = list(diagnostics) if isinstance(diagnostics, list) else []

        surface = operator_diagnostics_surface(diagnostics_list)
        return ok(surface)
    except Exception as exc:
        return fail("diagnostics_error", f"Failed to build diagnostics: {str(exc)[:200]}", 500, {})


@api_v1_bp.route("/operator/diagnostics/session/<session_id>/turn-history", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_SYSTEM_DIAGNOSIS)
def operator_turn_history(session_id: str):
    """Turn-history dashboard: formatted turn-by-turn telemetry showing
    responder, validation result, render summary, fallback truth, and
    agency level.
    """
    try:
        from app.services import session_service as _session_service

        limit = min(int(request.args.get("limit", "100")), 500)
        getter = getattr(_session_service, "get_session_by_id", None)
        if not callable(getter):
            getter = getattr(_session_service, "get_session", None)
        session = getter(session_id) if callable(getter) else None
        if session is None:
            return fail("session_not_found", f"Session {session_id} not found.", 404, {})

        diagnostics = (
            session.diagnostics
            if hasattr(session, "diagnostics")
            else session.get("diagnostics")
            if isinstance(session, dict)
            else []
        )
        diagnostics_list = list(diagnostics) if isinstance(diagnostics, list) else []

        summary = build_turn_history_summary_for_session(diagnostics_list, limit=limit)
        return ok(summary)
    except Exception as exc:
        return fail("turn_history_error", f"Failed to build turn history: {str(exc)[:200]}", 500, {})


__all__ = []
