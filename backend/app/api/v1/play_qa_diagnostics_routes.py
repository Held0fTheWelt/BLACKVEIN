"""QA canonical turn diagnostics routes (Phase D).

Exposes the canonical dramatic turn record for QA debugging via:
- /api/v1/play/<session_id>/qa-diagnostics-canonical-turn

Gated by JWT + feature flag FEATURE_VIEW_QA_CANONICAL_TURN.
"""

from __future__ import annotations

from flask import request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_VIEW_QA_CANONICAL_TURN
from app.auth.permissions import require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, ok


@api_v1_bp.route("/play/<session_id>/qa-diagnostics-canonical-turn", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_VIEW_QA_CANONICAL_TURN)
def get_qa_canonical_turn_diagnostics(session_id: str):
    """QA-facing canonical dramatic turn record for this session's current turn.

    Returns the operator canonical turn record (Phase D) in QA projection form,
    with three-tier field classification:
    - Tier A (primary): responder selection, validation, quality, vitality
    - Tier B (detailed): summarized continuity, social state, scene assessment
    - Tier C (raw JSON): full canonical record available via raw_canonical_record_available flag

    Access: JWT + FEATURE_VIEW_QA_CANONICAL_TURN
    """
    try:
        from ai_stack.goc_turn_seams import build_operator_canonical_turn_record
        from ai_stack.qa_canonical_turn_projection import build_qa_canonical_turn_projection
        from app.services import session_service as _session_service

        # Fetch session
        getter = getattr(_session_service, "get_session_by_id", None)
        if not callable(getter):
            getter = getattr(_session_service, "get_session", None)
        session = getter(session_id) if callable(getter) else None

        if session is None:
            return fail("session_not_found", f"Session {session_id} not found.", 404, {})

        # Get the last turn's runtime state from session payload
        session_payload = session.get("payload") if isinstance(session, dict) else getattr(session, "payload", None)
        if not isinstance(session_payload, dict):
            return fail("invalid_session_state", "Session payload is not available or invalid.", 400, {})

        runtime_state = session_payload.get("runtime_state") if isinstance(session_payload, dict) else {}
        if not isinstance(runtime_state, dict):
            return fail("no_runtime_state", "No runtime state available for this session.", 404, {})

        # Build canonical record from current runtime state
        canonical_record = build_operator_canonical_turn_record(runtime_state)

        # Build QA projection (three-tier view)
        qa_projection = build_qa_canonical_turn_projection(canonical_record)

        # Include raw canonical record if requested
        include_raw = str(request.args.get("include_raw", "0")).lower() in {"1", "true", "yes"}
        if include_raw:
            qa_projection["raw_canonical_record"] = canonical_record
        else:
            qa_projection["raw_canonical_record"] = None

        return ok(qa_projection)

    except ImportError as e:
        return fail(
            "import_error",
            f"Missing dependency (ai_stack or projection module): {str(e)[:100]}",
            500,
            {},
        )
    except Exception as exc:
        return fail(
            "qa_diagnostics_error",
            f"Failed to build QA diagnostics: {str(exc)[:200]}",
            500,
            {},
        )


__all__ = []
