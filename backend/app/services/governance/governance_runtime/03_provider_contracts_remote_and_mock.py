"""Governance runtime source segment: provider_contracts_remote_and_mock.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        "ollama": {
            "provider_type": "ollama",
            "default_base_url": (current_app.config.get("OLLAMA_BASE_URL") or "http://localhost:11434/api").strip(),
            "auth_mode": "none",
            "required_headers": [],
            "static_headers": {},
            "requires_credential": False,
            "is_local_default": True,
            "openai_compatible": False,
            "health_check_strategy": "ollama_tags",
            "health_check_path": "/api/tags",
            "supports_model_discovery": True,
            "capabilities": {
                "text_generation": True,
                "structured_json_output": True,
                "streaming": True,
                "tool_calling": False,
                "model_discovery": True,
                "local_provider": True,
                "cloud_provider": False,
                "openai_compatible": False,
            },
            "stage_support": "full",
            "operator_notes": "Requires local Ollama daemon and pulled models.",
        },
        "openrouter": {
            "provider_type": "openrouter",
            "default_base_url": (current_app.config.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").strip(),
            "auth_mode": "bearer_api_key",
            "required_headers": ["Authorization"],
            "static_headers": {"HTTP-Referer": app_base, "X-Title": "World of Shadows"},
            "requires_credential": True,
            "is_local_default": False,
            "openai_compatible": True,
            "health_check_strategy": "models_get",
            "health_check_path": "/models",
            "supports_model_discovery": True,
            "capabilities": {
                "text_generation": True,
                "structured_json_output": True,
                "streaming": True,
                "tool_calling": True,
                "model_discovery": True,
                "embeddings": False,
                "local_provider": False,
                "cloud_provider": True,
                "openai_compatible": True,
            },
            "stage_support": "template",
            "operator_notes": "Full runtime use depends on model/route policy and key provisioning.",
        },
        "anthropic": {
            "provider_type": "anthropic",
            "default_base_url": (current_app.config.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").strip(),
            "auth_mode": "x_api_key",
            "required_headers": ["x-api-key", "anthropic-version"],
            "static_headers": {
                "anthropic-version": (current_app.config.get("ANTHROPIC_VERSION") or "2023-06-01").strip()
            },
            "requires_credential": True,
            "is_local_default": False,
            "openai_compatible": False,
            "health_check_strategy": "anthropic_models_get",
            "health_check_path": "/v1/models",
            "supports_model_discovery": True,
            "capabilities": {
                "text_generation": True,
                "structured_json_output": True,
                "streaming": True,
                "tool_calling": True,
                "model_discovery": True,
                "embeddings": False,
'''
