"""Admin API: aggregated system diagnosis for the administration tool."""

from __future__ import annotations

from flask import current_app, g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_SYSTEM_DIAGNOSIS
from app.auth.permissions import require_feature, require_jwt_moderator_or_admin
from app.extensions import limiter
from app.observability.trace import get_trace_id
from app.services.system_diagnosis_service import get_system_diagnosis


@api_v1_bp.route("/admin/system-diagnosis", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_feature(FEATURE_MANAGE_SYSTEM_DIAGNOSIS)
def admin_system_diagnosis():
    """Single aggregated operator diagnosis (timeouts, concurrency, short TTL cache)."""
    trace_id = g.get("trace_id") or get_trace_id()
    refresh = (request.args.get("refresh") or "").strip().lower() in ("1", "true", "yes")
    self_base = request.url_root.rstrip("/")
    payload = get_system_diagnosis(
        current_app._get_current_object(),
        self_base_url=self_base,
        refresh=refresh,
        trace_id=trace_id,
    )
    return jsonify(payload), 200
