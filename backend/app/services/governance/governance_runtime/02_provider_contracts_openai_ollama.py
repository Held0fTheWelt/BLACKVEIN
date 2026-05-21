"""Governance runtime source segment: provider_contracts_openai_ollama.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        "provider_selection_mode": "restricted_by_route",
        "default_runtime_profile": "balanced",
        "default_provider_templates_json": [
            {"provider_type": "mock", "display_name": "Mock Provider", "enabled_by_default": True, "requires_secret": False},
            {"provider_type": "ollama", "display_name": "Local Ollama", "enabled_by_default": True, "base_url": "http://ollama:11434", "requires_secret": False},
            {"provider_type": "openrouter", "display_name": "OpenRouter", "enabled_by_default": False, "base_url": "https://openrouter.ai/api/v1", "requires_secret": True},
            {"provider_type": "anthropic", "display_name": "Anthropic", "enabled_by_default": False, "base_url": "https://api.anthropic.com", "requires_secret": True},
        ],
        "default_budget_policy_json": {"daily_limit": "50.00", "monthly_limit": "1000.00", "warning_threshold_percent": 80, "hard_stop_enabled": False},
    },
    {
        "preset_id": "quality_first",
        "display_name": "Cloud Narrative",
        "description": "Cloud-first quality path with routed LLM/SLM and full costs tracking.",
        "generation_execution_mode": "routed_llm_slm",
        "retrieval_execution_mode": "hybrid_dense_sparse",
        "validation_execution_mode": "schema_plus_semantic",
        "provider_selection_mode": "remote_preferred",
        "default_runtime_profile": "quality_first",
        "default_provider_templates_json": [
            {"provider_type": "openai", "display_name": "OpenAI Primary", "enabled_by_default": True, "base_url": "https://api.openai.com/v1", "requires_secret": True},
            {"provider_type": "openrouter", "display_name": "OpenRouter", "enabled_by_default": False, "base_url": "https://openrouter.ai/api/v1", "requires_secret": True},
            {"provider_type": "anthropic", "display_name": "Anthropic", "enabled_by_default": False, "base_url": "https://api.anthropic.com", "requires_secret": True},
        ],
        "default_budget_policy_json": {"daily_limit": "100.00", "monthly_limit": "2500.00", "warning_threshold_percent": 80, "hard_stop_enabled": False},
    },
    {
        "preset_id": "cost_aware",
        "display_name": "Research / Evaluation",
        "description": "Hybrid or AI-focused profile for research and evaluation workflows.",
        "generation_execution_mode": "hybrid_routed_with_mock_fallback",
        "retrieval_execution_mode": "hybrid_dense_sparse",
        "validation_execution_mode": "schema_plus_semantic",
        "provider_selection_mode": "remote_allowed",
        "default_runtime_profile": "cost_aware",
        "default_provider_templates_json": [{"provider_type": "mock", "display_name": "Mock Provider", "enabled_by_default": True, "requires_secret": False}],
        "default_budget_policy_json": {"daily_limit": "25.00", "monthly_limit": "500.00", "warning_threshold_percent": 75, "hard_stop_enabled": False},
    },
)


def _provider_contract(provider_type: str) -> dict:
    """Return canonical provider contract metadata for known provider types."""
    normalized = (provider_type or "").strip().lower()
    app_base = (current_app.config.get("APP_PUBLIC_BASE_URL") or "http://localhost:5002").strip()
    contracts: dict[str, dict] = {
        "openai": {
            "provider_type": "openai",
            "default_base_url": (current_app.config.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip(),
            "auth_mode": "bearer_api_key",
            "required_headers": ["Authorization"],
            "static_headers": {},
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
                "embeddings": True,
                "local_provider": False,
                "cloud_provider": True,
                "openai_compatible": True,
            },
            "stage_support": "full",
            "operator_notes": "",
        },
'''
