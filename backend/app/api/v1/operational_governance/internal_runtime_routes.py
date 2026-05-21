"""Internal runtime configuration and credential routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/internal/runtime-config", methods=["GET"])
@limiter.limit("120 per minute")
def internal_runtime_config_get():
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        return fail("setting_update_forbidden", "Internal runtime config token is invalid.", 403, {})
    try:
        return ok(build_resolved_runtime_config(persist_snapshot=False, actor="internal"))
    except GovernanceError as err:
        return fail_from_error(err)


@api_v1_bp.route("/internal/runtime-config/reload", methods=["POST"])
@limiter.limit("30 per minute")
def internal_runtime_config_reload():
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        return fail("setting_update_forbidden", "Internal runtime config token is invalid.", 403, {})
    try:
        return ok(build_resolved_runtime_config(persist_snapshot=True, actor="internal"))
    except GovernanceError as err:
        return fail_from_error(err)


@api_v1_bp.route("/internal/provider-credential/<provider_id>", methods=["GET"])
@limiter.limit("300 per minute")
def internal_provider_credential_get(provider_id: str):
    """Internal endpoint for world-engine to fetch decrypted provider credentials.

    Requires X-Internal-Config-Token header (same as runtime-config endpoint).
    Returns the decrypted API key for the specified provider.
    """
    token = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token != expected:
        print(f"DEBUG: Invalid token for provider credential request: {provider_id}", flush=True)
        return fail("credential_access_forbidden", "Internal credential token is invalid.", 403, {"provider_id": provider_id})

    print(f"DEBUG: Fetching credential for provider {provider_id} via internal API", flush=True)
    api_key = get_provider_credential_for_runtime(provider_id)

    if api_key is None:
        print(f"DEBUG: No credential available for provider {provider_id}", flush=True)
        return ok({"provider_id": provider_id, "api_key": None})

    print(f"DEBUG: Successfully returned credential for provider {provider_id}", flush=True)
    return ok({"provider_id": provider_id, "api_key": api_key})


@api_v1_bp.route("/internal/hf-hub/token", methods=["GET"])
@limiter.limit("300 per minute")
def internal_hf_hub_token_get():
    """Internal: decrypted HF Hub read token for play-service / world-engine (same auth as runtime-config)."""
    token_hdr = (request.headers.get("X-Internal-Config-Token") or "").strip()
    expected = (current_app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN") or "").strip()
    if not expected or token_hdr != expected:
        return fail("credential_access_forbidden", "Internal credential token is invalid.", 403, {})

    from app.services.governance.hf_hub_governance_service import get_hf_hub_token_for_runtime

    hub_token = get_hf_hub_token_for_runtime()
    return ok({"token": hub_token})

__all__ = (
    'internal_runtime_config_get',
    'internal_runtime_config_reload',
    'internal_provider_credential_get',
    'internal_hf_hub_token_get',
)
