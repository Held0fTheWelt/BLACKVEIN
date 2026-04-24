"""Admin APIs for operational settings and AI runtime governance MVP."""

from __future__ import annotations

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
