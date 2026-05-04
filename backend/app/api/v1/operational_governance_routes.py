"""Admin APIs for operational settings and AI runtime governance MVP."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE
from app.auth.permissions import get_current_user, require_feature
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
    get_provider_credential_for_runtime,
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
from app.services.diagnosis_gates_mapping_service import (
    get_check_id_for_gate,
    get_gate_id_for_check,
)
from app.services.readiness_gates_service import (
    create_or_update_gate,
    delete_gate,
    get_all_gates,
    get_gate,
    get_gates_by_service,
    get_gates_by_status,
    get_summary,
    update_gate_status,
)
from app.services.runtime_config_truth_service import (
    get_runtime_config_truth,
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
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
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
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_presets():
    return _handle("bootstrap_presets", lambda: {"presets": list_bootstrap_presets()})


@api_v1_bp.route("/admin/bootstrap/initialize", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_initialize():
    return _handle("bootstrap_initialize", lambda: initialize_bootstrap(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/bootstrap/reopen", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_reopen():
    return _handle("bootstrap_reopen", lambda: reopen_bootstrap(_body(), _actor_identifier()))


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


@api_v1_bp.route("/admin/ai/models", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_models_list():
    return _handle("model_list", lambda: {"models": list_models()})


@api_v1_bp.route("/admin/ai/models", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_create():
    return _handle("model_create", lambda: {"model_id": create_model(_body(), _actor_identifier()).model_id, "created": True})


@api_v1_bp.route("/admin/ai/models/<model_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_update(model_id: str):
    return _handle("model_update", lambda: {"model_id": update_model(model_id, _body(), _actor_identifier()).model_id, "updated": True})


@api_v1_bp.route("/admin/ai/routes", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_routes_list():
    return _handle("route_list", lambda: {"routes": list_routes()})


@api_v1_bp.route("/admin/ai/routes", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_route_create():
    return _handle("route_create", lambda: {"route_id": create_route(_body(), _actor_identifier()).route_id, "created": True})


@api_v1_bp.route("/admin/ai/routes/<route_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_route_update(route_id: str):
    return _handle("route_update", lambda: {"route_id": update_route(route_id, _body(), _actor_identifier()).route_id, "updated": True})


@api_v1_bp.route("/admin/ai/runtime-readiness", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_runtime_readiness():
    return _handle("runtime_readiness", evaluate_runtime_readiness)


@api_v1_bp.route("/admin/runtime/modes", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_modes_get():
    return _handle("runtime_modes_get", get_runtime_modes)


@api_v1_bp.route("/admin/runtime/modes", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_modes_patch():
    return _handle("runtime_modes_patch", lambda: update_runtime_modes(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/runtime/resolved-config", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_resolved_config_get():
    return _handle("runtime_resolved_config_get", lambda: build_resolved_runtime_config(persist_snapshot=False, actor=_actor_identifier()))


@api_v1_bp.route("/admin/runtime/reload-resolved-config", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
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
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_backend_get():
    return _settings_get("backend")


@api_v1_bp.route("/admin/settings/backend", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_backend_patch():
    return _settings_patch("backend")


@api_v1_bp.route("/admin/settings/world-engine", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_world_engine_get():
    return _settings_get("world_engine")


@api_v1_bp.route("/admin/settings/world-engine", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_world_engine_patch():
    return _settings_patch("world_engine")


@api_v1_bp.route("/admin/settings/retrieval", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_retrieval_get():
    return _settings_get("retrieval")


@api_v1_bp.route("/admin/settings/retrieval", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_retrieval_patch():
    return _settings_patch("retrieval")


@api_v1_bp.route("/admin/settings/notifications", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_notifications_get():
    return _settings_get("notifications")


@api_v1_bp.route("/admin/settings/notifications", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_notifications_patch():
    return _settings_patch("notifications")


@api_v1_bp.route("/admin/settings/costs", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_costs_get():
    return _settings_get("costs")


@api_v1_bp.route("/admin/settings/costs", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_costs_patch():
    return _settings_patch("costs")


@api_v1_bp.route("/admin/costs/usage-events", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_usage_events():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_usage_events", lambda: {"items": list_usage_events(limit=limit)})


@api_v1_bp.route("/admin/costs/usage-events", methods=["POST"])
@limiter.limit("120 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_usage_events_ingest():
    def _do():
        body = _body()
        enforce_budget_guard(body.get("provider_id"), body.get("workflow_scope"))
        return ingest_usage_event(body, _actor_identifier())

    return _handle("costs_usage_events_ingest", _do)


@api_v1_bp.route("/admin/costs/rollups", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_rollups():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_rollups", lambda: {"items": list_rollups(limit=limit)})


@api_v1_bp.route("/admin/costs/rollups/rebuild", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_rollups_rebuild():
    return _handle("costs_rollups_rebuild", lambda: {"items": rebuild_rollups(_actor_identifier())})


@api_v1_bp.route("/admin/costs/budgets", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets():
    return _handle("costs_budgets", lambda: {"items": list_budgets()})


@api_v1_bp.route("/admin/costs/budgets", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets_create():
    return _handle(
        "costs_budget_create",
        lambda: {"budget_policy_id": upsert_budget(None, _body(), _actor_identifier()).budget_policy_id, "created": True},
    )


@api_v1_bp.route("/admin/costs/budgets/<budget_policy_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets_patch(budget_policy_id: str):
    return _handle(
        "costs_budget_patch",
        lambda: {"budget_policy_id": upsert_budget(budget_policy_id, _body(), _actor_identifier()).budget_policy_id, "updated": True},
    )


@api_v1_bp.route("/admin/audit/governance", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_governance_audit():
    limit = min(int(request.args.get("limit", "300")), 1000)
    return _handle("governance_audit", lambda: {"items": list_audit_events(limit=limit)})


@api_v1_bp.route("/admin/story-runtime-experience", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_story_runtime_experience_get():
    from app.services.story_runtime_experience_service import (
        build_story_runtime_experience_truth_surface,
    )

    return _handle(
        "story_runtime_experience_get",
        lambda: build_story_runtime_experience_truth_surface(),
    )


@api_v1_bp.route("/admin/story-runtime-experience", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_story_runtime_experience_update():
    from app.services.story_runtime_experience_service import (
        build_story_runtime_experience_truth_surface,
        update_story_runtime_experience_settings,
    )

    def _do():
        result = update_story_runtime_experience_settings(_body(), _actor_identifier())
        # Rebuild resolved runtime config so world-engine fetches the new
        # Story Runtime Experience section on its next reload call.
        try:
            build_resolved_runtime_config(persist_snapshot=True, actor=_actor_identifier())
        except GovernanceError:
            # Settings are persisted even if full resolve fails; the admin
            # truth surface will reflect the new values on next GET.
            pass
        truth = build_story_runtime_experience_truth_surface()
        truth["update_warnings"] = result.get("warnings") or []
        return truth

    return _handle("story_runtime_experience_update", _do)


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


@api_v1_bp.route("/internal/provider-credential/<provider_id>", methods=["GET"])
@limiter.limit("300 per minute")
def internal_provider_credential_get(provider_id: str):
    """Internal endpoint for world-engine to fetch decrypted provider credentials.

    Requires X-Internal-Config-Token header (same as runtime-config endpoint).
    Returns the decrypted API key for the specified provider.
    """
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        print(f"DEBUG: Invalid token for provider credential request: {provider_id}", flush=True)
        return fail("credential_access_forbidden", "Internal credential token is invalid.", 403, {"provider_id": provider_id})

    print(f"DEBUG: Fetching credential for provider {provider_id} via internal API", flush=True)
    api_key = get_provider_credential_for_runtime(provider_id)

    if api_key is None:
        print(f"DEBUG: No credential available for provider {provider_id}", flush=True)
        return ok({"provider_id": provider_id, "api_key": None})

    print(f"DEBUG: Successfully returned credential for provider {provider_id}", flush=True)
    return ok({"provider_id": provider_id, "api_key": api_key})


# ============================================================================
# Release Readiness Gates — Canonical Schema (Phase 1)
# ============================================================================


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gates_list():
    """Get all release readiness gates in canonical schema."""
    try:
        status_filter = request.args.get("status", None)
        service_filter = request.args.get("service", None)

        if status_filter:
            gates = get_gates_by_status(status_filter)
        elif service_filter:
            gates = get_gates_by_service(service_filter)
        else:
            gates = get_all_gates()

        summary = get_summary()
        return ok({"gates": gates, "summary": summary})
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gates.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_detail(gate_id: str):
    """Get details for a specific readiness gate."""
    try:
        gate = get_gate(gate_id)
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_create_or_update():
    """Create or update a readiness gate."""
    try:
        body = _body()
        gate_id = body.get("gate_id")
        if not gate_id:
            raise governance_error("gate_id_required", "gate_id is required", 400, {})

        gate = create_or_update_gate(
            gate_id=gate_id,
            gate_name=body.get("gate_name", ""),
            owner_service=body.get("owner_service", ""),
            status=body.get("status", "open"),
            reason=body.get("reason", ""),
            expected_evidence=body.get("expected_evidence", ""),
            actual_evidence=body.get("actual_evidence"),
            evidence_path=body.get("evidence_path"),
            truth_source=body.get("truth_source", "live_endpoint"),
            remediation=body.get("remediation", ""),
            remediation_steps=body.get("remediation_steps"),
            checked_by=_actor_identifier(),
        )
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to create/update gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>/status", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_update_status(gate_id: str):
    """Update a gate's status and evidence."""
    try:
        body = _body()
        status = body.get("status")
        if not status:
            raise governance_error("status_required", "status is required", 400, {})

        gate = update_gate_status(
            gate_id=gate_id,
            status=status,
            reason=body.get("reason", ""),
            actual_evidence=body.get("actual_evidence"),
            evidence_path=body.get("evidence_path"),
            checked_by=_actor_identifier(),
        )
        return ok(gate)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to update gate status.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/gates/<gate_id>", methods=["DELETE"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_gate_delete(gate_id: str):
    """Delete a readiness gate (cleanup only)."""
    try:
        result = delete_gate(gate_id, checked_by=_actor_identifier())
        return ok(result)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to delete gate.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/ai-stack/release-readiness/summary", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_readiness_summary():
    """Get readiness gates summary (closure percentage, gate counts)."""
    try:
        summary = get_summary()
        return ok(summary)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve summary.", 500, {"error": str(exc)})


# ============================================================================
# Diagnosis ↔ Gates Integration (Phase 2)
# ============================================================================


@api_v1_bp.route("/admin/system-diagnosis/gates", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_diagnosis_gates_mapping():
    """
    Get gates mapped to diagnosis checks.

    Returns all gates with their associated diagnosis check_id and check status.
    Useful for understanding which diagnosis checks drive gate status.
    """
    try:
        gates = get_all_gates()
        gates_with_checks = []

        for gate in gates:
            gate_id = gate.get("gate_id")
            check_id = get_check_id_for_gate(gate_id)
            gate_with_check = dict(gate)
            gate_with_check["diagnosis_check_id"] = check_id
            gates_with_checks.append(gate_with_check)

        return ok({
            "gates": gates_with_checks,
            "total_gates": len(gates_with_checks),
            "gates_with_diagnosis_mapping": sum(1 for g in gates_with_checks if g.get("diagnosis_check_id")),
        })
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve diagnosis-gates mapping.", 500, {"error": str(exc)})


@api_v1_bp.route("/admin/system-diagnosis/gates/<gate_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_diagnosis_gate_detail(gate_id: str):
    """
    Get gate detail with associated diagnosis check information.

    Shows which diagnosis check (if any) is linked to this gate.
    """
    try:
        gate = get_gate(gate_id)
        check_id = get_check_id_for_gate(gate_id)

        result = dict(gate)
        result["diagnosis_check_id"] = check_id
        if check_id:
            result["diagnosis_link"] = f"/api/v1/admin/system-diagnosis?refresh=1#{check_id}"

        return ok(result)
    except GovernanceError as err:
        return fail_from_error(err)
    except Exception as exc:
        return fail("readiness_error", "Failed to retrieve gate detail.", 500, {"error": str(exc)})


# ============================================================================
# Runtime Config Truth (Phase 5)
# ============================================================================


@api_v1_bp.route("/admin/runtime/config-truth", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_config_truth():
    """
    Get runtime configuration truth snapshot.

    Shows what's actually configured vs. effective vs. loaded:
    - Backend configured state (from database)
    - Backend effective config (currently in use)
    - World-Engine loaded state (from HTTP probe)
    - Play-Service connectivity (reachable?)
    - Story Runtime active state (from HTTP probe)

    Helps operators understand whether configured != effective != loaded.
    """
    try:
        truth = get_runtime_config_truth()
        return ok(truth)
    except Exception as exc:
        return fail("config_truth_error", "Failed to retrieve runtime config truth.", 500, {"error": str(exc)})


# ============================================================================
# MVP4 Phase C: Governance, Evaluation & Operator Surfaces
# ============================================================================

# Token Budget Management


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/token-budget", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_token_budget(session_id: str):
    """Get current token budget and usage for session."""
    def _do():
        from app.services.observability_governance_service import TokenBudgetService, DegradationLevel
        from app.extensions import redis_client

        service = TokenBudgetService(redis_client)
        budget = service.get_budget(session_id)
        usage_percent = (budget.used_tokens / budget.total_budget * 100) if budget.total_budget > 0 else 0

        return {
            "session_id": session_id,
            "total_budget": budget.total_budget,
            "used_tokens": budget.used_tokens,
            "remaining_tokens": max(0, budget.total_budget - budget.used_tokens),
            "usage_percent": usage_percent,
            "warning_threshold": int(budget.warning_threshold * 100),
            "ceiling_threshold": int(budget.ceiling_threshold * 100),
            "degradation_strategy": budget.degradation_strategy,
            "degradation_level": "warning" if usage_percent >= budget.warning_threshold * 100 else (
                "critical" if usage_percent >= budget.ceiling_threshold * 100 else "none"
            ),
        }

    return _handle("token_budget_get", _do)


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/token-budget/override", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_override_token_budget(session_id: str):
    """Admin override: add tokens to session budget."""
    def _do():
        from app.services.observability_governance_service import TokenBudgetService
        from app.extensions import redis_client

        body = _body()
        tokens_to_add = int(body.get("tokens_to_add", 0))
        reason = body.get("reason", "")

        service = TokenBudgetService(redis_client)
        service.override_budget(
            session_id=session_id,
            tokens_to_add=tokens_to_add,
            admin_user=_actor_identifier(),
            reason=reason,
        )

        budget = service.get_budget(session_id)
        return {
            "session_id": session_id,
            "new_total": budget.total_budget,
            "new_used": budget.used_tokens,
            "override_applied": True,
        }

    return _handle("token_budget_override", _do)


# Override Audit Configuration


@api_v1_bp.route("/admin/mvp4/overrides/audit-config", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_audit_config():
    """Get audit granularity configuration for all override types."""
    def _do():
        from app.auth.admin_security import OverrideAuditConfigManager
        from app.extensions import redis_client

        manager = OverrideAuditConfigManager(redis_client)
        configs = manager.get_all_configs()
        return {
            "override_types": {
                ot: config.to_dict() for ot, config in configs.items()
            },
            "description": "Control which override events are logged per override type",
        }

    return _handle("override_audit_config_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/audit-config/<override_type>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_update_audit_config(override_type: str):
    """Update audit granularity configuration for override type."""
    def _do():
        from app.auth.admin_security import OverrideAuditConfig, OverrideAuditConfigManager
        from app.extensions import redis_client

        body = _body()
        config = OverrideAuditConfig(
            override_type=override_type,
            log_created=body.get("log_created", True),
            log_apply_attempt=body.get("log_apply_attempt", True),
            log_applied=body.get("log_applied", True),
            log_apply_failed=body.get("log_apply_failed", True),
            log_revoked=body.get("log_revoked", True),
            log_revoke_failed=body.get("log_revoke_failed", True),
            log_accessed=body.get("log_accessed", True),
        )

        manager = OverrideAuditConfigManager(redis_client)
        manager.set_config(config)

        return {
            "override_type": override_type,
            "config": config.to_dict(),
            "updated": True,
        }

    return _handle("override_audit_config_update", _do)


# Evaluation Configuration


@api_v1_bp.route("/admin/mvp4/evaluation/rubric", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_evaluation_rubric():
    """Get quality evaluation rubric."""
    def _do():
        from ai_stack.evaluation_pipeline import EvaluationPipeline
        from app.extensions import redis_client

        pipeline = EvaluationPipeline(redis_client)
        rubric = pipeline.get_rubric("goc_quality_v1")
        return rubric.to_dict()

    return _handle("evaluation_rubric_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/baseline", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_evaluation_baseline():
    """Get offline baseline test set."""
    def _do():
        from ai_stack.evaluation_pipeline import EvaluationPipeline
        from app.extensions import redis_client

        pipeline = EvaluationPipeline(redis_client)
        baseline = pipeline.get_baseline("goc_evaluation_baseline")
        return {
            "baseline_id": baseline.baseline_id,
            "version": baseline.version,
            "canonical_turn_count": len(baseline.canonical_turns),
            "metrics": {
                dim: metric.to_dict() for dim, metric in baseline.metrics_per_dimension.items()
            },
            "created_at": baseline.created_at,
        }

    return _handle("evaluation_baseline_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/weights/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_rubric_weights(session_id: str):
    """Get current rubric weights (auto-tuning state) for session."""
    def _do():
        from ai_stack.evaluation_pipeline import EvaluationPipeline
        from app.extensions import redis_client

        pipeline = EvaluationPipeline(redis_client)
        weights = pipeline.get_rubric_weights(session_id)
        return {
            "session_id": session_id,
            "weights": weights.to_dict(),
        }

    return _handle("evaluation_weights_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/weights/<session_id>/manual-tune", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_manual_tune_weights(session_id: str):
    """Manually trigger rubric weight tuning from recent turns."""
    def _do():
        from ai_stack.evaluation_pipeline import EvaluationPipeline
        from app.extensions import redis_client

        body = _body()
        turn_count = int(body.get("turn_count", 10))

        pipeline = EvaluationPipeline(redis_client)
        weights = pipeline.manual_tune_weights(
            session_id=session_id,
            turn_count=turn_count,
            admin_user=_actor_identifier(),
        )

        return {
            "session_id": session_id,
            "weights": weights.to_dict(),
            "tuned_at": weights.last_updated,
        }

    return _handle("evaluation_manual_tune", _do)


# Langfuse Configuration


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/langfuse-toggle", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_toggle_langfuse(session_id: str):
    """Enable/disable Langfuse tracing for session."""
    def _do():
        from app.services import log_activity

        body = _body()
        enabled = body.get("enabled", False)
        reason = body.get("reason", "")

        # In Phase B, would update session_config in database
        # Phase A: Just log and return success

        log_activity(
            actor=_actor_identifier(),
            category="mvp4_governance",
            action="langfuse_toggle",
            status="success",
            message=f"Langfuse {'enabled' if enabled else 'disabled'} for session {session_id}",
            metadata={"session_id": session_id, "enabled": enabled, "reason": reason},
            tags=["mvp4", "langfuse"],
        )

        return {
            "session_id": session_id,
            "langfuse_enabled": enabled,
            "toggled_at": datetime.now(timezone.utc).isoformat(),
        }

    return _handle("langfuse_toggle", _do)


# Object Admission Overrides


@api_v1_bp.route("/admin/mvp4/overrides/object-admission", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_object_admission_overrides():
    """Get active object admission overrides."""
    def _do():
        from app.extensions import redis_client

        # Fetch all object admission overrides from session storage
        storage_key = "object_admission_overrides:all"
        overrides = redis_client.get(storage_key) or []

        return {
            "overrides": overrides if isinstance(overrides, list) else [],
            "total_count": len(overrides) if isinstance(overrides, list) else 0,
        }

    return _handle("object_admission_overrides_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/object-admission", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_create_object_admission_override():
    """Create object admission tier override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.extensions import redis_client
        import uuid

        body = _body()
        object_id = body.get("object_id", "")
        session_id = body.get("session_id", "")
        tier_change = body.get("tier_change", "")
        reason = body.get("reason", "")

        if not object_id or not session_id:
            raise governance_error("invalid_override", "object_id and session_id required", 400, {})

        override_id = f"ov_obj_admission_{uuid.uuid4().hex[:8]}"

        # Create audit event and log it
        event = OverrideAuditEvent(
            event_type=OverrideEventType.CREATED,
            override_id=override_id,
            admin_user=_actor_identifier(),
            session_id=session_id,
            reason=reason,
            metadata={
                "object_id": object_id,
                "tier_change": tier_change,
                "override_type": "object_admission",
            },
        )

        config_manager = OverrideAuditConfigManager(redis_client)
        config = config_manager.get_config("object_admission")
        _log_override_event(event, config, _actor_identifier())

        # Store override
        storage_key = f"object_admission_override:{override_id}"
        override_data = {
            "override_id": override_id,
            "type": "object_admission_override",
            "scope": "session",
            "target": object_id,
            "tier_change": tier_change,
            "created": {
                "admin_user": _actor_identifier(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            },
            "applied_events": [],
            "active": True,
        }
        redis_client.set(storage_key, override_data)

        return {
            "override_id": override_id,
            "type": "object_admission_override",
            "object_id": object_id,
            "tier_change": tier_change,
            "created": True,
        }

    return _handle("object_admission_override_create", _do)


@api_v1_bp.route("/admin/mvp4/overrides/object-admission/<override_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_revoke_object_admission_override(override_id: str):
    """Revoke object admission override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.extensions import redis_client

        body = _body() if request.get_json(silent=True) else {}
        reason = body.get("reason", "Override revoked")

        storage_key = f"object_admission_override:{override_id}"
        override = redis_client.get(storage_key)

        if not override:
            raise governance_error("not_found", f"Override {override_id} not found", 404, {})

        # Log revocation event
        event = OverrideAuditEvent(
            event_type=OverrideEventType.REVOKED,
            override_id=override_id,
            admin_user=_actor_identifier(),
            reason=reason,
            metadata={"override_type": "object_admission"},
        )

        config_manager = OverrideAuditConfigManager(redis_client)
        config = config_manager.get_config("object_admission")
        _log_override_event(event, config, _actor_identifier())

        # Update override as revoked
        if isinstance(override, dict):
            override["active"] = False
            override["revoked"] = {
                "admin_user": _actor_identifier(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            }
            redis_client.set(storage_key, override)

        return {"override_id": override_id, "revoked": True}

    return _handle("object_admission_override_revoke", _do)


# State Delta Boundary Overrides


@api_v1_bp.route("/admin/mvp4/overrides/state-delta-boundary", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_get_state_delta_overrides():
    """Get active state delta boundary overrides."""
    def _do():
        from app.extensions import redis_client

        storage_key = "state_delta_overrides:all"
        overrides = redis_client.get(storage_key) or []

        return {
            "overrides": overrides if isinstance(overrides, list) else [],
            "total_count": len(overrides) if isinstance(overrides, list) else 0,
        }

    return _handle("state_delta_overrides_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/state-delta-boundary", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_create_state_delta_override():
    """Create state delta boundary protection override (breakglass)."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.extensions import redis_client
        import uuid

        body = _body()
        session_id = body.get("session_id", "")
        protected_path = body.get("protected_path", "")
        reason = body.get("reason", "")

        if not session_id or not protected_path:
            raise governance_error("invalid_override", "session_id and protected_path required", 400, {})

        override_id = f"ov_state_delta_{uuid.uuid4().hex[:8]}"

        # Create audit event and log it
        event = OverrideAuditEvent(
            event_type=OverrideEventType.CREATED,
            override_id=override_id,
            admin_user=_actor_identifier(),
            session_id=session_id,
            reason=reason,
            metadata={
                "protected_path": protected_path,
                "override_type": "state_delta_boundary",
            },
        )

        config_manager = OverrideAuditConfigManager(redis_client)
        config = config_manager.get_config("state_delta_boundary")
        _log_override_event(event, config, _actor_identifier())

        # Store override
        storage_key = f"state_delta_override:{override_id}"
        override_data = {
            "override_id": override_id,
            "type": "state_delta_boundary_override",
            "scope": "session",
            "target": protected_path,
            "protected_path": protected_path,
            "created": {
                "admin_user": _actor_identifier(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            },
            "applied_events": [],
            "active": True,
            "breakglass_activated": True,
        }
        redis_client.set(storage_key, override_data)

        return {
            "override_id": override_id,
            "type": "state_delta_boundary_override",
            "protected_path": protected_path,
            "created": True,
            "breakglass": True,
        }

    return _handle("state_delta_override_create", _do)


@api_v1_bp.route("/admin/mvp4/overrides/state-delta-boundary/<override_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def mvp4_revoke_state_delta_override(override_id: str):
    """Revoke state delta boundary override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.extensions import redis_client

        body = _body() if request.get_json(silent=True) else {}
        reason = body.get("reason", "Override revoked")

        storage_key = f"state_delta_override:{override_id}"
        override = redis_client.get(storage_key)

        if not override:
            raise governance_error("not_found", f"Override {override_id} not found", 404, {})

        # Log revocation event
        event = OverrideAuditEvent(
            event_type=OverrideEventType.REVOKED,
            override_id=override_id,
            admin_user=_actor_identifier(),
            reason=reason,
            metadata={"override_type": "state_delta_boundary"},
        )

        config_manager = OverrideAuditConfigManager(redis_client)
        config = config_manager.get_config("state_delta_boundary")
        _log_override_event(event, config, _actor_identifier())

        # Update override as revoked
        if isinstance(override, dict):
            override["active"] = False
            override["breakglass_activated"] = False
            override["revoked"] = {
                "admin_user": _actor_identifier(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            }
            redis_client.set(storage_key, override)

        return {"override_id": override_id, "revoked": True}

    return _handle("state_delta_override_revoke", _do)


@api_v1_bp.route("/internal/bootstrap/admin-user", methods=["POST"])
def internal_bootstrap_admin_user():
    """Internal endpoint for docker-up.py to create default admin user if missing."""
    try:
        from app.models.user import User
        from app.models.role import Role
        from app.extensions import db
        from werkzeug.security import generate_password_hash

        body = request.get_json(silent=True) or {}
        username = body.get("username", "admin")
        password = body.get("password", "Admin123")
        create_if_missing = body.get("create_if_missing", True)

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return ok({"created": False, "message": "User already exists"})

        if not create_if_missing:
            return ok({"created": False, "message": "User does not exist and create_if_missing=False"})

        # Get or create admin role (per ROLE_HIERARCHY.md: roles are user, qa, moderator, admin)
        admin_role = Role.query.filter_by(name="admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db.session.add(admin_role)
            db.session.commit()

        # Create new admin user
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role_id=admin_role.id,
            role_level=100,  # Super admin level
        )
        db.session.add(new_user)
        db.session.commit()

        return ok({"created": True, "username": username, "message": f"Admin user '{username}' created successfully"})

    except Exception as e:
        return fail(
            "admin_user_creation_error",
            f"Failed to create admin user: {str(e)}",
            500,
            {}
        )
