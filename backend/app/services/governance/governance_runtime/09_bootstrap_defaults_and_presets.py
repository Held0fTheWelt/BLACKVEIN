"""Governance runtime source segment: bootstrap_defaults_and_presets.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")


def get_bootstrap_status() -> dict:
    """Return current bootstrap state and available presets."""
    _seed_default_presets()
    db.session.flush()
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    presets = BootstrapPreset.query.order_by(BootstrapPreset.display_name.asc()).all()
    if bootstrap is None:
        return {
            "bootstrap_required": True,
            "bootstrap_locked": False,
            "available_presets": [p.preset_id for p in presets],
            "configured": {
                "trust_anchor": False,
                "initial_admin": False,
                "secret_storage": False,
                "initial_provider": False,
            },
        }
    return {
        "bootstrap_required": bootstrap.bootstrap_state in {"uninitialized", "initializing", "bootstrap_recovery_required"},
        "bootstrap_locked": bool(bootstrap.bootstrap_locked),
        "available_presets": [p.preset_id for p in presets],
        "configured": {
            "trust_anchor": bool(bootstrap.trust_anchor_fingerprint),
            "initial_admin": bool(bootstrap.bootstrap_completed_by),
            "secret_storage": bool(bootstrap.secret_storage_mode),
            "initial_provider": bool(AIProviderConfig.query.count()),
        },
    }


def ensure_governance_baseline() -> None:
    """Ensure baseline bootstrap and operational setting rows exist."""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table("bootstrap_configs") or not inspector.has_table("system_setting_records"):
            return
    except OperationalError:
        return

    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        bootstrap = BootstrapConfig(
            bootstrap_state="uninitialized",
            bootstrap_locked=False,
            selected_preset=None,
            secret_storage_mode="same_db_encrypted",
            runtime_profile="safe_local",
            generation_execution_mode="mock_only",
            retrieval_execution_mode="disabled",
            validation_execution_mode="schema_only",
            provider_selection_mode="local_only",
            reopen_requires_elevated_auth=True,
            trust_anchor_metadata_json={},
        )
        db.session.add(bootstrap)

    defaults: dict[str, dict[str, object]] = {
        "backend": {
            "play_service_internal_url": current_app.config.get("PLAY_SERVICE_INTERNAL_URL"),
            "play_service_public_url": current_app.config.get("PLAY_SERVICE_PUBLIC_URL"),
            "play_service_request_timeout_seconds": int(current_app.config.get("PLAY_SERVICE_REQUEST_TIMEOUT", 30)),
            "game_ticket_ttl_seconds": int(current_app.config.get("PLAY_SERVICE_TICKET_TTL_SECONDS", 900)),
        },
        "notifications": {
            "mail_enabled": bool(current_app.config.get("MAIL_ENABLED", False)),
'''
