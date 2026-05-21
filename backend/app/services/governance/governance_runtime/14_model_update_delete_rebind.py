"""Governance runtime source segment: model_update_delete_rebind.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    if "provider_type" in payload:
        requested_type = (payload.get("provider_type") or "").strip().lower()
        contract = _provider_contract(requested_type)
        if requested_type != contract.get("provider_type"):
            raise governance_error(
                "provider_type_invalid",
                "Unsupported provider_type. Use openai, ollama, openrouter, anthropic, mock, or custom_http.",
                400,
                {"provider_type": requested_type},
            )
        provider.provider_type = requested_type
    for key in (
        "display_name",
        "base_url",
        "is_enabled",
        "is_local",
        "supports_structured_output",
        "allow_live_runtime",
        "allow_preview_runtime",
        "allow_writers_room",
        "allow_research_suite",
    ):
        if key in payload:
            setattr(provider, key, payload[key])
    contract = _provider_contract(provider.provider_type)
    if not provider.base_url:
        provider.base_url = _normalize_provider_url(provider.base_url, contract) or None
    provider.updated_at = datetime.now(timezone.utc)
    _audit("provider_updated", "ai_runtime", provider.provider_id, actor, "Provider updated.", {})
    db.session.commit()

    # After provider update, trigger world-engine rebind to pick up the change
    try:
        from app.services.game.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config
        if has_complete_play_service_config():
            reload_play_story_runtime_governed_config()
    except Exception as exc:  # noqa: BLE001 — best-effort rebind must not fail the provider update
        import logging
        logging.getLogger(__name__).warning("Provider update succeeded but world-engine rebind failed: %s", exc)

    return provider


def write_provider_credential(provider_id: str, payload: dict, actor: str) -> dict:
    """Write/replace provider credential in write-only mode."""
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
    api_key = (payload.get("api_key") or payload.get("new_api_key") or "").strip()
    if not api_key:
        raise governance_error("provider_secret_rejected", "api_key is required.", 400, {})
    record = encrypt_secret(api_key)
    active = AIProviderCredential.query.filter_by(provider_id=provider_id, is_active=True).first()
    if active is not None:
        if active.rotation_in_progress:
            raise governance_error("credential_rotation_in_progress", "Credential rotation already in progress.", 409, {"provider_id": provider_id})
        active.is_active = False
    credential = AIProviderCredential(
        credential_id=f"cred_{uuid4().hex}",
        provider_id=provider_id,
        secret_name="api_key",
        encrypted_secret=record.encrypted_secret,
        encrypted_dek=record.encrypted_dek,
        secret_nonce=record.secret_nonce,
        dek_nonce=record.dek_nonce,
        dek_algorithm=record.dek_algorithm,
        secret_fingerprint=record.secret_fingerprint,
        is_active=True,
        rotated_at=datetime.now(timezone.utc),
    )
    provider.credential_configured = True
    provider.credential_fingerprint = record.secret_fingerprint
'''
