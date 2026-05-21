"""Governance runtime source segment: model_listing_and_create.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                "base_url": row.base_url,
                "is_enabled": row.is_enabled,
                "is_local": row.is_local,
                "supports_structured_output": row.supports_structured_output,
                "credential_configured": row.credential_configured,
                "credential_fingerprint": row.credential_fingerprint,
                "health_status": row.health_status,
                "last_tested_at": row.last_tested_at.isoformat() if row.last_tested_at else None,
                "allow_live_runtime": row.allow_live_runtime,
                "allow_preview_runtime": row.allow_preview_runtime,
                "allow_writers_room": row.allow_writers_room,
                "allow_research_suite": row.allow_research_suite,
                "auth_mode": contract.get("auth_mode"),
                "required_headers": contract.get("required_headers", []),
                "static_headers": contract.get("static_headers", {}),
                "supports_model_discovery": bool(contract.get("supports_model_discovery")),
                "openai_compatible": bool(contract.get("openai_compatible")),
                "health_check_strategy": contract.get("health_check_strategy"),
                "health_check_path": contract.get("health_check_path"),
                "capabilities": contract.get("capabilities", {}),
                "stage_support": contract.get("stage_support", "template"),
                "operator_notes": contract.get("operator_notes", ""),
                "model_count": models_by_provider[row.provider_id],
                "enabled_model_count": enabled_models_by_provider[row.provider_id],
                "enabled_route_reference_count": routes_by_provider[row.provider_id],
                "eligible_for_runtime_assignment": eligible_runtime,
                "limitations": limitations,
            }
        )
    return out


def create_provider(payload: dict, actor: str) -> AIProviderConfig:
    """Create provider configuration."""
    provider_type = (payload.get("provider_type") or "").strip().lower()
    display_name = (payload.get("display_name") or "").strip()
    if not provider_type or not display_name:
        raise governance_error("setting_value_invalid", "provider_type and display_name are required.", 400, {})
    contract = _provider_contract(provider_type)
    if provider_type != contract.get("provider_type"):
        raise governance_error(
            "provider_type_invalid",
            "Unsupported provider_type. Use openai, ollama, openrouter, anthropic, mock, or custom_http.",
            400,
            {"provider_type": provider_type},
        )
    provider_id = _slug(payload.get("provider_id") or f"{provider_type}_{display_name}")
    existing = db.session.get(AIProviderConfig, provider_id)
    if existing:
        return existing
    provider = AIProviderConfig(
        provider_id=provider_id,
        provider_type=provider_type,
        display_name=display_name,
        base_url=_normalize_provider_url((payload.get("base_url") or "").strip() or None, contract) or None,
        is_enabled=bool(payload.get("is_enabled", True)),
        is_local=bool(payload.get("is_local", contract.get("is_local_default", provider_type in {"mock", "ollama"}))),
        supports_structured_output=bool(payload.get("supports_structured_output", contract.get("capabilities", {}).get("structured_json_output", False))),
        allow_live_runtime=bool(payload.get("allow_live_runtime", True)),
        allow_preview_runtime=bool(payload.get("allow_preview_runtime", True)),
        allow_writers_room=bool(payload.get("allow_writers_room", True)),
        allow_research_suite=bool(payload.get("allow_research_suite", True)),
    )
    db.session.add(provider)
    _audit("provider_created", "ai_runtime", provider.provider_id, actor, "Provider created.", {"provider_type": provider.provider_type})
    return provider


def update_provider(provider_id: str, payload: dict, actor: str) -> AIProviderConfig:
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
'''
