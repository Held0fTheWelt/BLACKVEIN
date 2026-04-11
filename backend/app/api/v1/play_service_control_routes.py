"""Admin API: persisted desired Play-Service posture and application-level apply (no host orchestration)."""

from __future__ import annotations

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_PLAY_SERVICE_CONTROL
from app.auth.permissions import require_feature, require_jwt_admin
from app.extensions import limiter
from app.services.play_service_control_service import (
    apply_desired,
    get_control_payload,
    run_test_persist,
    save_desired,
)


def _operator_user_id() -> int | None:
    raw = get_jwt_identity()
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@api_v1_bp.route("/admin/play-service-control", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_PLAY_SERVICE_CONTROL)
def admin_play_service_control_get():
    app = current_app._get_current_object()
    return jsonify(get_control_payload(app)), 200


@api_v1_bp.route("/admin/play-service-control", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_PLAY_SERVICE_CONTROL)
def admin_play_service_control_post():
    app = current_app._get_current_object()
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return (
            jsonify(
                {
                    "saved": False,
                    "desired_state": None,
                    "validation_errors": ["JSON object body required"],
                }
            ),
            400,
        )
    out = save_desired(app, body, user_id=_operator_user_id())
    status = 200 if out["saved"] else 400
    return jsonify(out), status


@api_v1_bp.route("/admin/play-service-control/test", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_PLAY_SERVICE_CONTROL)
def admin_play_service_control_test():
    app = current_app._get_current_object()
    out = run_test_persist(app, user_id=_operator_user_id())
    return jsonify(out), 200


@api_v1_bp.route("/admin/play-service-control/apply", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_PLAY_SERVICE_CONTROL)
def admin_play_service_control_apply():
    app = current_app._get_current_object()
    out = apply_desired(app, user_id=_operator_user_id())
    return jsonify(out), 200
