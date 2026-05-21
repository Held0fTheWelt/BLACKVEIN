"""AI provider governance routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/ai/providers", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_providers_list():
    return _handle("provider_list", lambda: {"providers": list_providers()})


@api_v1_bp.route("/admin/ai/providers", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_provider_create():
    def _do():
        row = create_provider(_body(), _actor_identifier())
        db_commit = row.provider_id  # force identity access before envelope
        return {"provider_id": db_commit, "created": True}

    return _handle("provider_create", _do)


@api_v1_bp.route("/admin/ai/providers/<provider_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_provider_update(provider_id: str):
    return _handle(
        "provider_update",
        lambda: {
            "provider_id": update_provider(provider_id, _body(), _actor_identifier()).provider_id,
            "updated": True,
        },
    )


@api_v1_bp.route("/admin/ai/providers/<provider_id>/credential", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_provider_credential_write(provider_id: str):
    return _handle("provider_credential_write", lambda: write_provider_credential(provider_id, _body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/providers/<provider_id>/rotate-credential", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_provider_credential_rotate(provider_id: str):
    return _handle("provider_credential_rotate", lambda: write_provider_credential(provider_id, _body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/providers/<provider_id>/test-connection", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_provider_test_connection(provider_id: str):
    return _handle("provider_test_connection", lambda: test_provider_connection(provider_id, _actor_identifier()))

__all__ = (
    'admin_ai_providers_list',
    'admin_ai_provider_create',
    'admin_ai_provider_update',
    'admin_ai_provider_credential_write',
    'admin_ai_provider_credential_rotate',
    'admin_ai_provider_test_connection',
)
