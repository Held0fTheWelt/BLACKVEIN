"""Governance runtime source segment: resolved_runtime_serializers.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
            return False, "model_reference_not_found"
        if not model.is_enabled:
            return False, "model_disabled"
        if route_field in {"preferred_model_id", "fallback_model_id"}:
            if _route_expects_embedding_model(task_kind=task_kind, route_id=route_id):
                if not _is_embedding_model(model):
                    return False, "model_role_not_embedding"
            elif not _is_generation_model(model):
                return False, "model_role_not_generation"
        if route_field == "mock_model_id" and (model.model_role or "").strip().lower() != "mock":
            return False, "model_role_not_mock"
        provider = provider_rows.get(model.provider_id)
        if provider is None:
            return False, "provider_not_found"
        if not provider.is_enabled:
            return False, "provider_disabled"
        if provider.health_status in {"failing", "disabled"}:
            return False, f"provider_health_{provider.health_status}"
        contract = _provider_contract(provider.provider_type)
        if bool(contract.get("requires_credential")) and not provider.credential_configured:
            return False, "provider_credential_missing"
        if route_field in {"preferred_model_id", "fallback_model_id"} and provider.provider_type == "mock":
            return False, "provider_is_mock"
        return True, None

    out: list[dict] = []
    for row in rows:
        blockers: list[str] = []
        route_model_role = _route_model_role_kind(task_kind=row.task_kind, route_id=row.route_id)
        pref_ok, pref_blocker = _model_runtime_eligible(
            row.preferred_model_id,
            route_field="preferred_model_id",
            task_kind=row.task_kind,
            route_id=row.route_id,
        )
        fb_ok, fb_blocker = _model_runtime_eligible(
            row.fallback_model_id,
            route_field="fallback_model_id",
            task_kind=row.task_kind,
            route_id=row.route_id,
        )
        mock_ok, mock_blocker = _model_runtime_eligible(
            row.mock_model_id,
            route_field="mock_model_id",
            task_kind=row.task_kind,
            route_id=row.route_id,
        )
        if pref_blocker and row.preferred_model_id:
            blockers.append(f"preferred_{pref_blocker}")
        if fb_blocker and row.fallback_model_id:
            blockers.append(f"fallback_{fb_blocker}")
        if mock_blocker and row.mock_model_id:
            blockers.append(f"mock_{mock_blocker}")
        if not row.is_enabled:
            blockers.append("route_disabled")
        if not (pref_ok or fb_ok):
            blockers.append("no_eligible_embedding_model_reference" if route_model_role == _EMBEDDING_MODEL_ROLE else "no_eligible_ai_model_reference")
        if row.use_mock_when_provider_unavailable and not mock_ok:
            blockers.append("mock_fallback_missing_or_invalid")
        out.append(
            {
                "route_id": row.route_id,
                "task_kind": row.task_kind,
                "workflow_scope": row.workflow_scope,
                "preferred_model_id": row.preferred_model_id,
                "fallback_model_id": row.fallback_model_id,
                "mock_model_id": row.mock_model_id,
                "route_model_role": route_model_role,
                "is_enabled": row.is_enabled,
                "use_mock_when_provider_unavailable": row.use_mock_when_provider_unavailable,
                "ai_path_ready": row.is_enabled and (pref_ok or fb_ok),
                "mock_path_ready": mock_ok,
'''
