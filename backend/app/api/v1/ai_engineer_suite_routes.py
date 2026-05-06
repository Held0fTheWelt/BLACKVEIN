"""Admin APIs for Phase 2 AI Engineer Suite."""

from __future__ import annotations

from flask import g, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import get_current_user, require_feature
from app.extensions import limiter
from app.governance.envelopes import fail, fail_from_error, ok
from app.governance.errors import GovernanceError
from app.services.ai_engineer_suite_service import (
    apply_runtime_preset,
    get_advanced_settings,
    get_effective_runtime_config,
    get_orchestration_settings,
    get_orchestration_status,
    get_rag_operations_status,
    get_rag_settings,
    get_runtime_dashboard,
    list_runtime_presets,
    list_settings_changes,
    reset_advanced_overrides,
    run_rag_query_probe,
    run_rag_safe_action,
    update_advanced_settings,
    update_orchestration_settings,
    update_rag_settings,
)
from app.services.governance_runtime_service import record_operational_activity
from app.services.hf_hub_governance_service import (
    clear_hf_hub_token,
    get_hf_hub_status,
    test_hf_hub_connection,
    write_hf_hub_token,
)


def _actor_identifier() -> str:
    user = get_current_user()
    if user is None:
        return "system"
    return user.username or str(user.id)


def _body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise GovernanceError("setting_value_invalid", "JSON object body required.", 400, {})
    return body


def _trace_id() -> str | None:
    trace = g.get("trace_id")
    if isinstance(trace, str):
        return trace
    return None


def _handle(action: str, callback):
    try:
        data = callback()
        actor = get_current_user()
        if actor is not None:
            record_operational_activity(actor, action, f"AI engineer suite action: {action}", {})
        return ok(data)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:  # pragma: no cover - defensive fallback
        return fail("configuration_error", "Unexpected AI engineer suite failure.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai/rag/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_rag_status():
    return _handle("ai_rag_status", get_rag_operations_status)


@api_v1_bp.route("/admin/ai/rag/probe", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_rag_probe():
    return _handle("ai_rag_probe", lambda: run_rag_query_probe(_body()))


@api_v1_bp.route("/admin/ai/rag/actions/<action_id>", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_rag_action(action_id: str):
    return _handle("ai_rag_action", lambda: run_rag_safe_action(action_id))


@api_v1_bp.route("/admin/ai/rag/settings", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_rag_settings_get():
    return _handle("ai_rag_settings_get", get_rag_settings)


@api_v1_bp.route("/admin/ai/rag/settings", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_rag_settings_patch():
    return _handle("ai_rag_settings_patch", lambda: update_rag_settings(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/hf-hub/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_hf_hub_status():
    return _handle("ai_hf_hub_status", get_hf_hub_status)


@api_v1_bp.route("/admin/ai/hf-hub/credential", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_hf_hub_credential_write():
    body = _body()
    token = str(body.get("token") or "").strip()
    if not token:
        raise GovernanceError("credential_invalid", "token is required.", 400, {})
    return _handle("ai_hf_hub_credential_write", lambda: write_hf_hub_token(token, _actor_identifier()))


@api_v1_bp.route("/admin/ai/hf-hub/credential", methods=["DELETE"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_hf_hub_credential_delete():
    return _handle("ai_hf_hub_credential_clear", lambda: clear_hf_hub_token(_actor_identifier()))


@api_v1_bp.route("/admin/ai/hf-hub/test-connection", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_hf_hub_test_connection():
    return _handle("ai_hf_hub_test_connection", lambda: test_hf_hub_connection(_actor_identifier()))


@api_v1_bp.route("/admin/ai/orchestration/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_orchestration_status():
    return _handle("ai_orchestration_status", lambda: get_orchestration_status(trace_id=_trace_id()))


@api_v1_bp.route("/admin/ai/orchestration/settings", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_orchestration_settings_get():
    return _handle("ai_orchestration_settings_get", get_orchestration_settings)


@api_v1_bp.route("/admin/ai/orchestration/settings", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_orchestration_settings_patch():
    return _handle(
        "ai_orchestration_settings_patch",
        lambda: update_orchestration_settings(_body(), _actor_identifier()),
    )


@api_v1_bp.route("/admin/ai/runtime-dashboard", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_runtime_dashboard():
    return _handle("ai_runtime_dashboard", lambda: get_runtime_dashboard(trace_id=_trace_id()))


@api_v1_bp.route("/admin/ai/presets", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_presets_list():
    return _handle("ai_presets_list", list_runtime_presets)


@api_v1_bp.route("/admin/ai/presets/apply", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_presets_apply():
    return _handle(
        "ai_presets_apply",
        lambda: apply_runtime_preset(
            str(_body().get("preset_id") or ""),
            _actor_identifier(),
            keep_overrides=bool(_body().get("keep_overrides", False)),
        ),
    )


@api_v1_bp.route("/admin/ai/advanced-settings", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_advanced_settings_get():
    return _handle("ai_advanced_settings_get", get_advanced_settings)


@api_v1_bp.route("/admin/ai/advanced-settings", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_advanced_settings_patch():
    return _handle("ai_advanced_settings_patch", lambda: update_advanced_settings(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/effective-config", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_effective_config_get():
    return _handle("ai_effective_config_get", get_effective_runtime_config)


@api_v1_bp.route("/admin/ai/settings-changes", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_settings_changes_get():
    limit_raw = request.args.get("limit")
    try:
        limit = int(limit_raw) if limit_raw is not None else 25
    except ValueError:
        limit = 25
    limit = max(1, min(limit, 100))
    return _handle("ai_settings_changes_get", lambda: list_settings_changes(limit=limit))


@api_v1_bp.route("/admin/ai/advanced-settings/reset-overrides", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_advanced_settings_reset():
    return _handle("ai_advanced_settings_reset", lambda: reset_advanced_overrides(_actor_identifier()))
