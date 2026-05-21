"""Governance runtime source segment: provider_connection_health.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        "bootstrap_status": "initialized",
        "bootstrap_locked": True,
        "secret_storage_mode": bootstrap.secret_storage_mode,
        "trust_anchor_fingerprint": bootstrap.trust_anchor_fingerprint,
        "next_actions": ["launch_stack", "open_administration_tool", "configure_models_and_routes"],
        "stack_start_ready": True,
    }


def reopen_bootstrap(payload: dict, actor: str) -> dict:
    """Reopen bootstrap in explicit recovery mode."""
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        raise governance_error("bootstrap_recovery_token_invalid", "Bootstrap has not been initialized yet.", 403, {})
    recovery_token = (payload.get("recovery_token") or "").strip()
    configured_token = (current_app.config.get("BOOTSTRAP_RECOVERY_TOKEN") or "").strip()
    if not recovery_token or not configured_token or recovery_token != configured_token:
        raise governance_error("bootstrap_recovery_token_invalid", "Recovery token is invalid.", 403, {})
    bootstrap.bootstrap_state = "bootstrap_recovery_required"
    bootstrap.bootstrap_locked = False
    _audit("bootstrap_reopened", "bootstrap", "bootstrap_config", actor, "Bootstrap reopened in recovery mode.", {})
    db.session.commit()
    return {
        "bootstrap_reopen_status": "accepted",
        "recovery_mode": True,
        "allowed_sections": ["secret_storage", "provider_credentials", "runtime_modes"],
    }


def list_providers() -> list[dict]:
    rows = AIProviderConfig.query.order_by(AIProviderConfig.provider_id.asc()).all()
    model_rows = AIModelConfig.query.all()
    route_rows = AITaskRoute.query.filter_by(is_enabled=True).all()
    models_by_provider: dict[str, int] = defaultdict(int)
    enabled_models_by_provider: dict[str, int] = defaultdict(int)
    for m in model_rows:
        models_by_provider[m.provider_id] += 1
        if m.is_enabled:
            enabled_models_by_provider[m.provider_id] += 1
    routes_by_provider: dict[str, int] = defaultdict(int)
    for route in route_rows:
        refs = [route.preferred_model_id, route.fallback_model_id, route.mock_model_id]
        touched: set[str] = set()
        for rid in refs:
            if not rid:
                continue
            model = next((m for m in model_rows if m.model_id == rid), None)
            if model:
                touched.add(model.provider_id)
        for pid in touched:
            routes_by_provider[pid] += 1
    out: list[dict] = []
    for row in rows:
        contract = _provider_contract(row.provider_type)
        requires_credential = bool(contract.get("requires_credential"))
        eligible_runtime = bool(
            row.is_enabled
            and (not requires_credential or row.credential_configured)
            and row.health_status not in {"failing", "disabled"}
        )
        limitations: list[str] = []
        if requires_credential and not row.credential_configured:
            limitations.append("credential_missing")
        if row.health_status in {"failing", "degraded"}:
            limitations.append(f"health_{row.health_status}")
        if enabled_models_by_provider[row.provider_id] == 0:
            limitations.append("no_enabled_models")
        out.append(
            {
                "provider_id": row.provider_id,
                "provider_type": row.provider_type,
                "display_name": row.display_name,
'''
