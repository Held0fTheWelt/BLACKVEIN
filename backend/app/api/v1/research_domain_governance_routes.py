"""Admin APIs for strategic research-domain visibility (layered governance, not a full lab)."""

from __future__ import annotations

from flask import g
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_RESEARCH_GOVERNANCE
from app.auth.permissions import get_current_user, require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, ok
from app.services.governance_runtime_service import record_operational_activity
from app.services.research_domain_governance_service import (
    LAYER_IDS,
    build_research_domain_overview,
    build_research_layer_payload,
)


def _trace_id() -> str | None:
    trace = g.get("trace_id")
    if isinstance(trace, str):
        return trace
    return None


@api_v1_bp.route("/admin/research-domain/overview", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_RESEARCH_GOVERNANCE)
def admin_research_domain_overview():
    data = build_research_domain_overview()
    actor = get_current_user()
    if actor is not None:
        record_operational_activity(
            actor,
            "research_domain_overview",
            "Research domain strategic overview",
            {"trace_id": _trace_id()},
        )
    return ok(data)


@api_v1_bp.route("/admin/research-domain/layer/<layer_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_RESEARCH_GOVERNANCE)
def admin_research_domain_layer(layer_id: str):
    if layer_id not in LAYER_IDS:
        return fail(
            "unknown_layer",
            "Unknown research governance layer.",
            400,
            {"layer_id": layer_id, "allowed": list(LAYER_IDS)},
        )
    data = build_research_layer_payload(layer_id)
    actor = get_current_user()
    if actor is not None:
        record_operational_activity(
            actor,
            "research_domain_layer",
            f"Research domain layer: {layer_id}",
            {"layer_id": layer_id, "trace_id": _trace_id()},
        )
    return ok(data)
