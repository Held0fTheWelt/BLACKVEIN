"""Governance runtime source segment: provider_update_and_credentials.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    return out


def initialize_bootstrap(payload: dict, actor: str) -> dict:
    """Initialize bootstrap config and optional initial provider/credential."""
    _seed_default_presets()
    db.session.flush()
    existing = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if existing and existing.bootstrap_locked:
        raise governance_error("bootstrap_already_initialized", "Bootstrap is already initialized and locked.", 409, {})

    preset_id = (payload.get("selected_preset") or "").strip()
    preset = db.session.get(BootstrapPreset, preset_id)
    if preset is None:
        raise governance_error(
            "preset_not_found",
            f"Preset '{preset_id}' does not exist.",
            404,
            {"available_presets": [p.preset_id for p in BootstrapPreset.query.all()]},
        )

    admin_email = (payload.get("admin_email") or "").strip()
    if not admin_email:
        raise governance_error("bootstrap_missing_admin_identity", "admin_email is required.", 400, {})

    secret_storage_mode = (payload.get("secret_storage_mode") or "").strip() or preset.default_budget_policy_json.get(
        "secret_storage_mode", "same_db_encrypted"
    )
    if secret_storage_mode not in {"same_db_encrypted", "separate_secret_db_encrypted", "external_secret_manager"}:
        raise governance_error("bootstrap_secret_storage_invalid", "Unsupported secret storage mode.", 400, {"mode": secret_storage_mode})

    bootstrap = existing or BootstrapConfig(
        bootstrap_state="initializing",
        bootstrap_locked=False,
        selected_preset=preset_id,
        secret_storage_mode=secret_storage_mode,
        runtime_profile=payload.get("runtime_profile") or preset.default_runtime_profile,
        generation_execution_mode=payload.get("generation_execution_mode") or preset.generation_execution_mode,
        retrieval_execution_mode=payload.get("retrieval_execution_mode") or preset.retrieval_execution_mode,
        validation_execution_mode=payload.get("validation_execution_mode") or preset.validation_execution_mode,
        provider_selection_mode=payload.get("provider_selection_mode") or preset.provider_selection_mode,
        reopen_requires_elevated_auth=bool(payload.get("trust_anchor", {}).get("allow_reopen_with_recovery_token", True)),
    )
    bootstrap.bootstrap_state = "initialized"
    bootstrap.bootstrap_locked = True
    bootstrap.selected_preset = preset_id
    bootstrap.secret_storage_mode = secret_storage_mode
    bootstrap.runtime_profile = payload.get("runtime_profile") or preset.default_runtime_profile
    bootstrap.generation_execution_mode = payload.get("generation_execution_mode") or preset.generation_execution_mode
    bootstrap.retrieval_execution_mode = payload.get("retrieval_execution_mode") or preset.retrieval_execution_mode
    bootstrap.validation_execution_mode = payload.get("validation_execution_mode") or preset.validation_execution_mode
    bootstrap.provider_selection_mode = payload.get("provider_selection_mode") or preset.provider_selection_mode
    bootstrap.bootstrap_completed_at = datetime.now(timezone.utc)
    bootstrap.bootstrap_completed_by = admin_email
    bootstrap.trust_anchor_fingerprint = f"sha256:{uuid4().hex[:16]}"
    bootstrap.trust_anchor_metadata_json = payload.get("trust_anchor") or {}

    db.session.add(bootstrap)
    _audit("bootstrap_initialized", "bootstrap", "bootstrap_config", actor, "Bootstrap initialized.", {"preset_id": preset_id})

    initial_provider = payload.get("initial_provider") or {}
    provider: AIProviderConfig | None = None
    if initial_provider:
        provider = create_provider(initial_provider, actor)
        initial_credential = payload.get("initial_credential") or {}
        if initial_credential and initial_credential.get("api_key"):
            write_provider_credential(provider.provider_id, {"api_key": initial_credential["api_key"]}, actor)

    if provider is None:
        _ensure_default_mock_path(actor)
    db.session.commit()
    return {
'''
