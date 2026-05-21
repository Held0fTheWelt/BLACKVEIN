"""State delta boundary override routes."""

from __future__ import annotations

from .common import *

# State Delta Boundary Overrides


@api_v1_bp.route("/admin/mvp4/overrides/state-delta-boundary", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def list_state_delta_boundary_overrides():
    """Get active state delta boundary overrides."""
    def _do():
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        storage_key = "state_delta_overrides:all"
        storage = get_runtime_governance_storage()
        overrides = [item for item in _list_storage_dicts(storage, storage_key) if item.get("active") is True]

        return {
            "overrides": overrides,
            "total_count": len(overrides),
        }

    return _handle("state_delta_overrides_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/state-delta-boundary", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def create_state_delta_boundary_override():
    """Create state delta boundary protection override (breakglass)."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.services.governance.observability_governance_service import get_runtime_governance_storage
        import uuid

        redis_client = get_runtime_governance_storage()
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
        _log_override_event(event, config, get_current_user())

        # Store override
        storage_key = f"state_delta_override:{override_id}"
        override_data = {
            "override_id": override_id,
            "type": "state_delta_boundary_override",
            "scope": "session",
            "session_id": session_id,
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
        _upsert_storage_dict(redis_client, "state_delta_overrides:all", override_data)

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
def revoke_state_delta_boundary_override(override_id: str):
    """Revoke state delta boundary override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        redis_client = get_runtime_governance_storage()
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
        _log_override_event(event, config, get_current_user())

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
            _upsert_storage_dict(redis_client, "state_delta_overrides:all", override)

        return {"override_id": override_id, "revoked": True}

    return _handle("state_delta_override_revoke", _do)

__all__ = (
    'list_state_delta_boundary_overrides',
    'create_state_delta_boundary_override',
    'revoke_state_delta_boundary_override',
)
