"""Admin APIs for operational settings and AI runtime governance MVP."""

from __future__ import annotations

from flask import current_app, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import get_current_user, require_jwt_admin
from app.extensions import limiter
from app.governance.envelopes import fail, fail_from_error, ok
from app.governance.errors import GovernanceError, governance_error
from app.services.governance_runtime_service import (
    build_resolved_runtime_config,
    create_model,
    create_provider,
    create_route,
    evaluate_runtime_readiness,
    enforce_budget_guard,
    get_bootstrap_status,
    get_runtime_modes,
    ingest_usage_event,
    initialize_bootstrap,
    list_audit_events,
    list_bootstrap_presets,
    list_budgets,
    list_models,
    list_providers,
    list_rollups,
    list_routes,
    list_usage_events,
    record_operational_activity,
    rebuild_rollups,
    reopen_bootstrap,
    test_provider_connection,
    update_model,
    update_provider,
    update_route,
    update_runtime_modes,
    update_scope_settings,
    upsert_budget,
    write_provider_credential,
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
            record_operational_activity(actor, action, f"Operational governance action: {action}", {})
        return ok(data)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:  # pragma: no cover - defensive fallback
        return fail("configuration_error", "Unexpected governance failure.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/bootstrap/status", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_bootstrap_status():
    return _handle("bootstrap_status", lambda: get_bootstrap_status())


@api_v1_bp.route("/bootstrap/public-status", methods=["GET"])
@limiter.limit("120 per minute")
def bootstrap_public_status():
    """Public, non-sensitive bootstrap readiness signal for docker-up guidance."""
    try:
        status = get_bootstrap_status()
        return ok(
            {
                "bootstrap_required": status["bootstrap_required"],
                "bootstrap_locked": status["bootstrap_locked"],
                "available_presets": status["available_presets"],
            }
        )
    except GovernanceError as err:
        return fail_from_error(err)


@api_v1_bp.route("/admin/bootstrap/presets", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_bootstrap_presets():
    return _handle("bootstrap_presets", lambda: {"presets": list_bootstrap_presets()})


@api_v1_bp.route("/admin/bootstrap/initialize", methods=["POST"])
@limiter.limit("10 per minute")
@require_jwt_admin
def admin_bootstrap_initialize():
    return _handle("bootstrap_initialize", lambda: initialize_bootstrap(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/bootstrap/reopen", methods=["POST"])
@limiter.limit("10 per minute")
@require_jwt_admin
def admin_bootstrap_reopen():
    return _handle("bootstrap_reopen", lambda: reopen_bootstrap(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/providers", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_ai_providers_list():
    return _handle("provider_list", lambda: {"providers": list_providers()})


@api_v1_bp.route("/admin/ai/providers", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_ai_provider_create():
    def _do():
        row = create_provider(_body(), _actor_identifier())
        db_commit = row.provider_id  # force identity access before envelope
        return {"provider_id": db_commit, "created": True}

    return _handle("provider_create", _do)


@api_v1_bp.route("/admin/ai/providers/<provider_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
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
@require_jwt_admin
def admin_ai_provider_credential_write(provider_id: str):
    return _handle("provider_credential_write", lambda: write_provider_credential(provider_id, _body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/providers/<provider_id>/rotate-credential", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
def admin_ai_provider_credential_rotate(provider_id: str):
    return _handle("provider_credential_rotate", lambda: write_provider_credential(provider_id, _body(), _actor_identifier()))


@api_v1_bp.route("/admin/ai/providers/<provider_id>/test-connection", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
def admin_ai_provider_test_connection(provider_id: str):
    return _handle("provider_test_connection", lambda: test_provider_connection(provider_id, _actor_identifier()))


@api_v1_bp.route("/admin/ai/models", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_ai_models_list():
    return _handle("model_list", lambda: {"models": list_models()})


@api_v1_bp.route("/admin/ai/models", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_ai_model_create():
    return _handle("model_create", lambda: {"model_id": create_model(_body(), _actor_identifier()).model_id, "created": True})


@api_v1_bp.route("/admin/ai/models/<model_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_ai_model_update(model_id: str):
    return _handle("model_update", lambda: {"model_id": update_model(model_id, _body(), _actor_identifier()).model_id, "updated": True})


@api_v1_bp.route("/admin/ai/routes", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_ai_routes_list():
    return _handle("route_list", lambda: {"routes": list_routes()})


@api_v1_bp.route("/admin/ai/routes", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_ai_route_create():
    return _handle("route_create", lambda: {"route_id": create_route(_body(), _actor_identifier()).route_id, "created": True})


@api_v1_bp.route("/admin/ai/routes/<route_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_ai_route_update(route_id: str):
    return _handle("route_update", lambda: {"route_id": update_route(route_id, _body(), _actor_identifier()).route_id, "updated": True})


@api_v1_bp.route("/admin/ai/runtime-readiness", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_ai_runtime_readiness():
    return _handle("runtime_readiness", evaluate_runtime_readiness)


@api_v1_bp.route("/admin/runtime/modes", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_runtime_modes_get():
    return _handle("runtime_modes_get", get_runtime_modes)


@api_v1_bp.route("/admin/runtime/modes", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_runtime_modes_patch():
    return _handle("runtime_modes_patch", lambda: update_runtime_modes(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/runtime/resolved-config", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_runtime_resolved_config_get():
    return _handle("runtime_resolved_config_get", lambda: build_resolved_runtime_config(persist_snapshot=False, actor=_actor_identifier()))


@api_v1_bp.route("/admin/runtime/reload-resolved-config", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
def admin_runtime_resolved_config_reload():
    return _handle("runtime_resolved_config_reload", lambda: build_resolved_runtime_config(persist_snapshot=True, actor=_actor_identifier()))


def _settings_get(scope: str):
    from app.services.governance_runtime_service import read_scope_settings

    return _handle(f"settings_get_{scope}", lambda: {"scope": scope, "values": read_scope_settings(scope)})


def _settings_patch(scope: str):
    return _handle(
        f"settings_patch_{scope}",
        lambda: {"scope": scope, "values": update_scope_settings(scope, _body(), _actor_identifier())},
    )


@api_v1_bp.route("/admin/settings/backend", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_settings_backend_get():
    return _settings_get("backend")


@api_v1_bp.route("/admin/settings/backend", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_settings_backend_patch():
    return _settings_patch("backend")


@api_v1_bp.route("/admin/settings/world-engine", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_settings_world_engine_get():
    return _settings_get("world_engine")


@api_v1_bp.route("/admin/settings/world-engine", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_settings_world_engine_patch():
    return _settings_patch("world_engine")


@api_v1_bp.route("/admin/settings/retrieval", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_settings_retrieval_get():
    return _settings_get("retrieval")


@api_v1_bp.route("/admin/settings/retrieval", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_settings_retrieval_patch():
    return _settings_patch("retrieval")


@api_v1_bp.route("/admin/settings/notifications", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_settings_notifications_get():
    return _settings_get("notifications")


@api_v1_bp.route("/admin/settings/notifications", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_settings_notifications_patch():
    return _settings_patch("notifications")


@api_v1_bp.route("/admin/settings/costs", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_settings_costs_get():
    return _settings_get("costs")


@api_v1_bp.route("/admin/settings/costs", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_settings_costs_patch():
    return _settings_patch("costs")


@api_v1_bp.route("/admin/costs/usage-events", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_costs_usage_events():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_usage_events", lambda: {"items": list_usage_events(limit=limit)})


@api_v1_bp.route("/admin/costs/usage-events", methods=["POST"])
@limiter.limit("120 per minute")
@require_jwt_admin
def admin_costs_usage_events_ingest():
    def _do():
        body = _body()
        enforce_budget_guard(body.get("provider_id"), body.get("workflow_scope"))
        return ingest_usage_event(body, _actor_identifier())

    return _handle("costs_usage_events_ingest", _do)


@api_v1_bp.route("/admin/costs/rollups", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_costs_rollups():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_rollups", lambda: {"items": list_rollups(limit=limit)})


@api_v1_bp.route("/admin/costs/rollups/rebuild", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_admin
def admin_costs_rollups_rebuild():
    return _handle("costs_rollups_rebuild", lambda: {"items": rebuild_rollups(_actor_identifier())})


@api_v1_bp.route("/admin/costs/budgets", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_costs_budgets():
    return _handle("costs_budgets", lambda: {"items": list_budgets()})


@api_v1_bp.route("/admin/costs/budgets", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_costs_budgets_create():
    return _handle(
        "costs_budget_create",
        lambda: {"budget_policy_id": upsert_budget(None, _body(), _actor_identifier()).budget_policy_id, "created": True},
    )


@api_v1_bp.route("/admin/costs/budgets/<budget_policy_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def admin_costs_budgets_patch(budget_policy_id: str):
    return _handle(
        "costs_budget_patch",
        lambda: {"budget_policy_id": upsert_budget(budget_policy_id, _body(), _actor_identifier()).budget_policy_id, "updated": True},
    )


@api_v1_bp.route("/admin/audit/governance", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
def admin_governance_audit():
    limit = min(int(request.args.get("limit", "300")), 1000)
    return _handle("governance_audit", lambda: {"items": list_audit_events(limit=limit)})


@api_v1_bp.route("/internal/runtime-config", methods=["GET"])
@limiter.limit("120 per minute")
def internal_runtime_config_get():
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        return fail("setting_update_forbidden", "Internal runtime config token is invalid.", 403, {})
    try:
        return ok(build_resolved_runtime_config(persist_snapshot=False, actor="internal"))
    except GovernanceError as err:
        return fail_from_error(err)


@api_v1_bp.route("/internal/runtime-config/reload", methods=["POST"])
@limiter.limit("30 per minute")
def internal_runtime_config_reload():
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        return fail("setting_update_forbidden", "Internal runtime config token is invalid.", 403, {})
    try:
        return ok(build_resolved_runtime_config(persist_snapshot=True, actor="internal"))
    except GovernanceError as err:
        return fail_from_error(err)
