"""Shared dependencies and helpers for operational governance API modules."""

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
from app.services.governance.governance_runtime_service import (
    build_resolved_runtime_config,
    create_model,
    create_provider,
    create_route,
    delete_model,
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
    test_model_connection,
    update_model,
    update_provider,
    update_route,
    update_runtime_modes,
    update_scope_settings,
    upsert_budget,
    write_provider_credential,
)
from app.services.governance.diagnosis_gates_mapping_service import (
    ensure_all_gates_exist,
    get_check_id_for_gate,
    get_gate_id_for_check,
)
from app.services.governance.readiness_gates_service import (
    create_or_update_gate,
    delete_gate,
    get_all_gates,
    get_gate,
    get_gates_by_service,
    get_gates_by_status,
    get_summary,
    update_gate_status,
)
from app.services.governance.runtime_config_truth_service import (
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


def _list_storage_dicts(storage, key: str) -> list[dict]:
    stored = storage.get(key)
    if isinstance(stored, list):
        return [item for item in stored if isinstance(item, dict)]
    return []


def _upsert_storage_dict(storage, key: str, item: dict, *, identity_key: str = "override_id") -> None:
    items = _list_storage_dicts(storage, key)
    identity = item.get(identity_key)
    replaced = False
    for index, existing in enumerate(items):
        if existing.get(identity_key) == identity:
            items[index] = item
            replaced = True
            break
    if not replaced:
        items.append(item)
    storage.set(key, items)


def _active_session_overrides(storage, session_id: str) -> dict[str, list[dict]]:
    object_overrides = [
        item
        for item in _list_storage_dicts(storage, "object_admission_overrides:all")
        if item.get("session_id") == session_id and item.get("active") is True
    ]
    state_delta_overrides = [
        item
        for item in _list_storage_dicts(storage, "state_delta_overrides:all")
        if item.get("session_id") == session_id and item.get("active") is True
    ]
    return {
        "object_admission": object_overrides,
        "state_delta_boundary": state_delta_overrides,
    }

__all__ = [name for name in globals() if not name.startswith("__")]
