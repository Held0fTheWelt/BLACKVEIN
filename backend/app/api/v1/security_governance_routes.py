"""Admin security governance API routes."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import require_feature
from app.services.governance.security_governance_service import (
    get_security_governance,
    update_security_governance,
)


def _ok(data: dict):
    return jsonify({"ok": True, "data": data})


def _bad_request(message: str):
    return jsonify({"ok": False, "error": {"code": "invalid_security_governance", "message": message}}), 400


@api_v1_bp.route("/admin/security/governance", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def security_governance_get():
    return _ok(get_security_governance())


@api_v1_bp.route("/admin/security/governance", methods=["PATCH"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def security_governance_patch():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _bad_request("Expected JSON object")
    try:
        return _ok(update_security_governance(body))
    except ValueError as exc:
        return _bad_request(str(exc))

