"""Read-only governance console API routes."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import require_feature
from app.services.governance import governance_console_service as service


def _ok(data: dict):
    return jsonify({"ok": True, "data": data})


@api_v1_bp.route("/admin/governance/runtime-readiness-authority", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_runtime_readiness_authority():
    return _ok(service.get_runtime_readiness_authority(session_id=request.args.get("session_id")))


@api_v1_bp.route("/admin/governance/adr0041-authority-state", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_adr0041_authority_state():
    return _ok(service.get_adr0041_authority_state(session_id=request.args.get("session_id")))


@api_v1_bp.route("/admin/governance/capability-matrix", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_capability_matrix():
    return _ok(service.get_capability_matrix_status(session_id=request.args.get("session_id")))


@api_v1_bp.route("/admin/governance/validators/registry", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_validator_registry():
    return _ok(service.get_validator_registry_status())


@api_v1_bp.route("/admin/governance/evidence/langfuse-mcp", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_langfuse_mcp_evidence():
    return _ok(service.get_langfuse_mcp_evidence_status())


@api_v1_bp.route("/admin/governance/runtime-aspect-ledger", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_runtime_aspect_ledger():
    return _ok(
        service.get_runtime_aspect_ledger_view(
            session_id=request.args.get("session_id"),
            aspect_filter=request.args.get("aspect"),
        )
    )


@api_v1_bp.route("/admin/governance/narrative-systems", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_narrative_systems():
    return _ok(
        service.get_narrative_systems_governance(
            module_id=request.args.get("module_id"),
            session_id=request.args.get("session_id"),
        )
    )


@api_v1_bp.route("/admin/governance/feature-flags", methods=["GET"])
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def governance_feature_flags():
    return _ok(service.get_feature_flag_governance())
