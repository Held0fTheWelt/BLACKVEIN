"""Governance runtime source segment: activity_and_provider_credentials.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        metadata=metadata or {},
        target_type="operational_settings",
        target_id="runtime",
    )


def get_provider_credential_for_runtime(provider_id: str) -> str | None:
    """Fetch and decrypt provider credential for world-engine runtime use.

    This is called by world-engine via internal API to get live credentials
    without storing them in config. Logs all steps for debugging.
    """
    print(f"DEBUG: get_provider_credential_for_runtime called for {provider_id}", flush=True)

    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        print(f"DEBUG: Provider {provider_id} not found", flush=True)
        return None

    if not provider.credential_configured:
        print(f"DEBUG: Provider {provider_id} has no credential configured", flush=True)
        return None

    from app.models.backend.governance_core import AIProviderCredential

    active_cred = AIProviderCredential.query.filter_by(
        provider_id=provider_id,
        is_active=True
    ).first()

    if not active_cred:
        print(f"DEBUG: No active credential found for {provider_id}", flush=True)
        return None

    try:
        decrypted = decrypt_secret(
            encrypted_secret=active_cred.encrypted_secret,
            encrypted_dek=active_cred.encrypted_dek,
            secret_nonce=active_cred.secret_nonce,
            dek_nonce=active_cred.dek_nonce,
        )
        api_key = decrypted.get("api_key") if isinstance(decrypted, dict) else str(decrypted)
        print(f"DEBUG: Successfully decrypted credential for {provider_id}: present={bool(api_key)}", flush=True)
        return api_key
    except Exception as e:
        print(f"DEBUG: Failed to decrypt credential for {provider_id}: {type(e).__name__}", flush=True)
        return None
'''
