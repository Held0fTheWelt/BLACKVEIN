"""Governance runtime source segment: model_connection_health.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    db.session.add(credential)
    _audit("provider_credential_written", "ai_runtime", provider_id, actor, "Provider credential rotated.", {"fingerprint": record.secret_fingerprint})
    db.session.commit()
    return {
        "provider_id": provider_id,
        "credential_written": True,
        "credential_fingerprint": record.secret_fingerprint,
        "rotated_at": credential.rotated_at.isoformat() if credential.rotated_at else None,
    }


def test_provider_connection(provider_id: str, actor: str) -> dict:
    """Run provider-aware health checks and persist normalized status."""
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
    contract = _provider_contract(provider.provider_type)
    requires_credential = bool(contract.get("requires_credential"))
    secret = _active_provider_secret(provider_id) if provider.credential_configured else None
    if requires_credential and not secret:
        raise governance_error("provider_credential_required", "Provider requires credential before health test.", 400, {"provider_id": provider_id})
    tested_at = datetime.now(timezone.utc)
    if not provider.is_enabled:
        health_status = "disabled"
        reachable = False
        authenticated = False
        usable = False
        latency_ms = 0
        error_code = "provider_disabled"
        error_message = "Provider is disabled."
    elif provider.provider_type == "mock":
        health_status = "healthy"
        reachable = True
        authenticated = True
        usable = True
        latency_ms = 0
        error_code = None
        error_message = ""
    else:
        base_url = _normalize_provider_url(provider.base_url, contract)
        if not base_url:
            health_status = "degraded"
            reachable = False
            authenticated = False
            usable = False
            latency_ms = 0
            error_code = "missing_base_url"
            error_message = "Provider has no base URL configured."
        else:
            target = _probe_target(base_url, contract)
            headers = _provider_headers(contract, secret)
            started = perf_counter()
            try:
                request = Request(target, headers=headers, method="GET")
                with urlopen(request, timeout=5.0) as response:
                    status = int(getattr(response, "status", 200))
                latency_ms = int((perf_counter() - started) * 1000)
                reachable = True
                authenticated = status < 400
                usable = status < 400
                if status < 400:
                    health_status = "healthy"
                    error_code = None
                    error_message = ""
                else:
                    health_status = "degraded"
                    error_code = f"http_{status}"
                    error_message = f"Provider responded with HTTP {status}."
            except HTTPError as e:
                latency_ms = int((perf_counter() - started) * 1000)
                status = int(getattr(e, "code", 500))
                reachable = True
'''
