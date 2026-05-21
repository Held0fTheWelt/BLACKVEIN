"""Governance runtime source segment: provider_secret_and_model_helpers.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                "local_provider": False,
                "cloud_provider": True,
                "openai_compatible": False,
            },
            "stage_support": "template",
            "operator_notes": "Uses Anthropic-native headers and version semantics.",
        },
        "mock": {
            "provider_type": "mock",
            "default_base_url": "",
            "auth_mode": "none",
            "required_headers": [],
            "static_headers": {},
            "requires_credential": False,
            "is_local_default": True,
            "openai_compatible": False,
            "health_check_strategy": "internal",
            "health_check_path": "",
            "supports_model_discovery": False,
            "capabilities": {
                "text_generation": True,
                "structured_json_output": True,
                "streaming": False,
                "tool_calling": False,
                "model_discovery": False,
                "embeddings": False,
                "local_provider": True,
                "cloud_provider": False,
                "openai_compatible": False,
            },
            "stage_support": "full",
            "operator_notes": "Deterministic local fallback provider.",
        },
        "custom_http": {
            "provider_type": "custom_http",
            "default_base_url": "",
            "auth_mode": "custom",
            "required_headers": [],
            "static_headers": {},
            "requires_credential": False,
            "is_local_default": False,
            "openai_compatible": False,
            "health_check_strategy": "generic_health",
            "health_check_path": "/health",
            "supports_model_discovery": False,
            "capabilities": {
                "text_generation": False,
                "structured_json_output": False,
                "streaming": False,
                "tool_calling": False,
                "model_discovery": False,
                "embeddings": False,
                "local_provider": False,
                "cloud_provider": True,
                "openai_compatible": False,
            },
            "stage_support": "template",
            "operator_notes": "Custom provider support is limited and operator-validated only.",
        },
    }
    return contracts.get(normalized, contracts["custom_http"])


def _active_provider_secret(provider_id: str) -> str | None:
    """Return decrypted active provider API key for internal health checks."""
    row = AIProviderCredential.query.filter_by(provider_id=provider_id, is_active=True).order_by(AIProviderCredential.created_at.desc()).first()
    if row is None:
        return None
    return decrypt_secret(
        encrypted_secret=row.encrypted_secret,
        encrypted_dek=row.encrypted_dek,
        secret_nonce=row.secret_nonce,
'''
