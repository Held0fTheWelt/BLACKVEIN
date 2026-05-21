"""Object admission override routes."""

from __future__ import annotations

from .common import *

# Object Admission Overrides


@api_v1_bp.route("/admin/mvp4/overrides/object-admission", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def list_object_admission_overrides():
    """Get active object admission overrides."""
    def _do():
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        # Fetch all object admission overrides from session storage
        storage_key = "object_admission_overrides:all"
        storage = get_runtime_governance_storage()
        overrides = [item for item in _list_storage_dicts(storage, storage_key) if item.get("active") is True]

        return {
            "overrides": overrides,
            "total_count": len(overrides),
        }

    return _handle("object_admission_overrides_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/object-admission", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def create_object_admission_override():
    """Create object admission tier override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.services.governance.observability_governance_service import get_runtime_governance_storage
        import uuid

        redis_client = get_runtime_governance_storage()
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
        _log_override_event(event, config, get_current_user())

        # Store override
        storage_key = f"object_admission_override:{override_id}"
        override_data = {
            "override_id": override_id,
            "type": "object_admission_override",
            "scope": "session",
            "session_id": session_id,
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
        _upsert_storage_dict(redis_client, "object_admission_overrides:all", override_data)

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
def revoke_object_admission_override(override_id: str):
    """Revoke object admission override."""
    def _do():
        from app.auth.admin_security import OverrideAuditEvent, OverrideEventType, OverrideAuditConfig, OverrideAuditConfigManager, _log_override_event
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        redis_client = get_runtime_governance_storage()
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
        _log_override_event(event, config, get_current_user())

        # Update override as revoked
        if isinstance(override, dict):
            override["active"] = False
            override["revoked"] = {
                "admin_user": _actor_identifier(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            }
            redis_client.set(storage_key, override)
            _upsert_storage_dict(redis_client, "object_admission_overrides:all", override)

        return {"override_id": override_id, "revoked": True}

    return _handle("object_admission_override_revoke", _do)

__all__ = (
    'list_object_admission_overrides',
    'create_object_admission_override',
    'revoke_object_admission_override',
)
