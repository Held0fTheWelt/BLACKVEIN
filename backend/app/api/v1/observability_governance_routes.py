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
from app.services.governance.observability_governance_service import (
    disable_observability,
    get_observability_config,
    get_observability_credential_for_runtime,
    test_observability_connection,
    update_observability_config,
    write_observability_credential,
)
from story_runtime_core.langfuse_tracing_environment import resolve_runtime_langfuse_base_url
from story_runtime_core.observability_tree_policy import normalize_enabled_observation_trees

# Same handler set as ``tools.mcp_server`` Langfuse verify tools (explicit allow-list).
_LANGFUSE_VERIFY_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "run_projection_tests",
        "fetch_langfuse_trace",
        "query_langfuse_traces",
        "assert_langfuse_opening_contract",
        "summarize_live_opening_matrix",
        "fetch_langfuse_trace_scores",
        "summarize_opening_judge_scores",
        "build_opening_quality_context",
        "wos.evaluators.catalog",
        "wos.evaluators.get",
        "wos.evaluators.langfuse_sync_preview",
    }
)


def _langfuse_verify_handlers():
    """Load MCP-parity Langfuse verify handlers (repo root must be on sys.path)."""
    from tools.mcp_server.handlers.tools_registry_handlers_evaluators import build_evaluators_mcp_handlers
    from tools.mcp_server.handlers.tools_registry_handlers_langfuse_verify import (
        build_langfuse_verify_mcp_handlers,
    )

    out = build_langfuse_verify_mcp_handlers()
    out.update(build_evaluators_mcp_handlers())
    return out


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
            from app.services.governance.governance_runtime_service import record_operational_activity
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

    def write_cred():
        if not public_key and not secret_key:
            raise governance_error(
                "credential_invalid",
                "At least one of public_key or secret_key is required.",
                400,
                {},
            )
        return write_observability_credential(
            public_key=public_key,
            secret_key=secret_key,
            actor=_actor_identifier(),
        )

    return _handle("observability_credential", write_cred)


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
        from app.models.backend.governance_core import ObservabilityConfig, ObservabilityCredential
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
        elif config.credential_configured and not bool(body.get("overwrite_existing", False)):
            return ok({
                "initialized": False,
                "skipped_existing": True,
                "service_id": "langfuse",
                "is_enabled": config.is_enabled,
                "credential_configured": config.credential_configured,
            })

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
        config.enabled_observation_trees = normalize_enabled_observation_trees(
            body.get("enabled_observation_trees")
        )

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


@api_v1_bp.route("/internal/observability/langfuse-credentials", methods=["GET"])
@limiter.limit("300 per minute")
@jwt_required(optional=True)
def internal_langfuse_credentials():
    """
    Internal endpoint for world-engine / MCP to fetch Langfuse credentials.

    Two accepted auth paths (first match wins):
    1. X-Internal-Config-Token header — world-engine, play-service, MCP service (raw runtime credentials)
    2. Authorization: Bearer <admin-JWT> — operator diagnostics only (no raw secret material)
    """
    # Path 1: internal config token
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    via_internal_token = bool(token and expected and token == expected)

    # Path 2: admin JWT bearer (operator diagnostics only; never raw secrets)
    via_jwt = False
    if not via_internal_token:
        user = get_current_user()
        via_jwt = user is not None and user.is_admin

    if not (via_internal_token or via_jwt):
        return fail("credentials_forbidden", "Valid internal token or admin JWT required.", 403, {})

    try:
        from app.models.backend.governance_core import ObservabilityConfig

        config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
        if not config or not config.is_enabled:
            return ok({
                "enabled": False,
                "public_key": None,
                "secret_key": None,
                "base_url": "https://cloud.langfuse.com",
                "enabled_observation_trees": normalize_enabled_observation_trees(None),
            })

        # Get credentials
        public_key = get_observability_credential_for_runtime("public_key")
        secret_key = get_observability_credential_for_runtime("secret_key")

        runtime_base_url, base_url_source = resolve_runtime_langfuse_base_url(config.base_url)

        raw_secret_allowed = via_internal_token
        enabled_for_caller = config.is_enabled and bool(secret_key) and raw_secret_allowed

        return ok({
            "enabled": enabled_for_caller,
            "public_key": public_key,
            "secret_key": secret_key if raw_secret_allowed else None,
            "secret_key_configured": bool(secret_key),
            "secret_key_redacted": bool(secret_key and not raw_secret_allowed),
            "credential_fingerprint": getattr(config, "credential_fingerprint", None),
            "base_url": runtime_base_url,
            "configured_base_url": config.base_url,
            "base_url_source": base_url_source,
            "environment": config.environment,
            "release": config.release,
            "sample_rate": config.sample_rate,
            "capture_prompts": config.capture_prompts,
            "capture_outputs": config.capture_outputs,
            "capture_retrieval": config.capture_retrieval,
            "redaction_mode": config.redaction_mode,
            "enabled_observation_trees": normalize_enabled_observation_trees(
                getattr(config, "enabled_observation_trees", None)
            ),
        })

    except Exception as e:
        return fail(
            "credentials_error",
            f"Failed to retrieve Langfuse credentials: {str(e)}",
            500,
            {},
        )


@api_v1_bp.route("/internal/observability/langfuse-verify-tool", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required(optional=True)
def internal_langfuse_verify_tool():
    """
    Invoke Langfuse verification helpers using the same Python handlers as MCP ``tools/call``.

    Auth (same as ``langfuse-credentials``):
    1. ``X-Internal-Config-Token`` — automation / MCP host
    2. ``Authorization: Bearer`` admin JWT

    Body JSON::
        { "tool": "fetch_langfuse_trace_scores", "arguments": { "trace_id": "..." } }

    Response envelope:: ``data``: ``{ "tool": "<name>", "result": <handler dict> }``
    """
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    via_internal_token = bool(token and expected and token == expected)

    via_jwt = False
    if not via_internal_token:
        user = get_current_user()
        via_jwt = user is not None and user.is_admin

    if not (via_internal_token or via_jwt):
        return fail("verify_tool_forbidden", "Valid internal token or admin JWT required.", 403, {})

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("verify_tool_body_invalid", "JSON object body required.", 400, {})

    tool_name = str(body.get("tool") or "").strip()
    arguments = body.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}

    if tool_name not in _LANGFUSE_VERIFY_TOOL_NAMES:
        return fail(
            "verify_tool_unknown",
            "Unknown or disallowed tool name.",
            400,
            {"allowed": sorted(_LANGFUSE_VERIFY_TOOL_NAMES)},
        )

    try:
        handlers = _langfuse_verify_handlers()
        handler = handlers.get(tool_name)
        if handler is None:
            return fail(
                "verify_tool_not_registered",
                "Handler missing from Langfuse verify registry.",
                500,
                {"tool": tool_name},
            )
        result = handler(arguments)
        return ok({"tool": tool_name, "result": result})
    except Exception as exc:
        return fail(
            "verify_tool_execution_error",
            f"Langfuse verify tool failed: {exc!s}",
            500,
            {"tool": tool_name},
        )
