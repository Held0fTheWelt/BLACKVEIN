"""Admin APIs for observability service configuration (Langfuse)."""

from __future__ import annotations

from flask import current_app, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import get_current_user, require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, fail_from_error, ok
from app.governance.errors import GovernanceError, governance_error
from app.services.observability_governance_service import (
    disable_observability,
    get_observability_config,
    get_observability_credential_for_runtime,
    test_observability_connection,
    update_observability_config,
    write_observability_credential,
)


def _actor_identifier() -> str:
    user = get_current_user()
    if user is None:
        return "system"
    return user.username or str(user.id)


def _body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise governance_error("setting_value_invalid", "JSON object body required.", 400, {})
    return body


def _handle(action: str, callback):
    try:
        data = callback()
        actor = get_current_user()
        if actor is not None:
            from app.services.governance_runtime_service import record_operational_activity
            record_operational_activity(actor, action, f"Observability action: {action}", {})
        return ok(data)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("configuration_error", "Unexpected observability failure.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/observability/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_observability_status():
    """Get current Langfuse observability configuration status."""
    return _handle("observability_status", lambda: get_observability_config())


@api_v1_bp.route("/admin/observability/update", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_observability_update():
    """Update Langfuse observability public configuration."""
    return _handle(
        "observability_update",
        lambda: update_observability_config(_body(), _actor_identifier()),
    )


@api_v1_bp.route("/admin/observability/credential", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_observability_credential():
    """Write/rotate Langfuse credentials (write-only, returns fingerprints only)."""
    body = _body()
    public_key = body.get("public_key")
    secret_key = body.get("secret_key")

    if not public_key and not secret_key:
        raise governance_error(
            "credential_invalid",
            "At least one of public_key or secret_key is required.",
            400,
            {},
        )

    return _handle(
        "observability_credential",
        lambda: write_observability_credential(
            public_key=public_key,
            secret_key=secret_key,
            actor=_actor_identifier(),
        ),
    )


@api_v1_bp.route("/admin/observability/test-connection", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_observability_test_connection():
    """Test Langfuse connection health."""
    return _handle(
        "observability_test",
        lambda: test_observability_connection(_actor_identifier()),
    )


@api_v1_bp.route("/admin/observability/disable", methods=["DELETE"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_observability_disable():
    """Disable Langfuse observability and clear configuration."""
    return _handle(
        "observability_disable",
        lambda: disable_observability(_actor_identifier()),
    )


@api_v1_bp.route("/internal/observability/initialize", methods=["POST"])
@limiter.limit("5 per minute")
def internal_observability_initialize():
    """
    Internal endpoint for docker-up.py to initialize Langfuse configuration from environment variables.
    Called once during bootstrap setup; subsequent changes via admin endpoints.
    No JWT required (internal only, restricted by network access).
    """
    try:
        from app.models.governance_core import ObservabilityConfig, ObservabilityCredential
        from app.extensions import db

        body = _body()

        # Get or create config
        config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
        if not config:
            config = ObservabilityConfig(
                service_id="langfuse",
                service_type="langfuse",
                display_name="Langfuse",
            )
            db.session.add(config)

        # Update configuration from payload
        config.is_enabled = body.get("enabled", False)
        config.base_url = body.get("base_url", "https://cloud.langfuse.com")
        config.environment = body.get("environment", "development")
        config.release = body.get("release", "unknown")
        config.sample_rate = float(body.get("sample_rate", 1.0))
        config.capture_prompts = body.get("capture_prompts", True)
        config.capture_outputs = body.get("capture_outputs", True)
        config.capture_retrieval = body.get("capture_retrieval", False)
        config.redaction_mode = body.get("redaction_mode", "strict")

        # Write credentials if provided
        public_key = body.get("public_key", "").strip()
        secret_key = body.get("secret_key", "").strip()

        if secret_key or public_key:
            write_observability_credential(
                public_key=public_key if public_key else None,
                secret_key=secret_key if secret_key else None,
                actor="system_bootstrap",
            )

        db.session.commit()

        return ok({
            "initialized": True,
            "service_id": "langfuse",
            "is_enabled": config.is_enabled,
            "credential_configured": config.credential_configured,
        })

    except Exception as e:
        return fail(
            "initialization_error",
            f"Failed to initialize Langfuse: {str(e)}",
            500,
            {},
        )
