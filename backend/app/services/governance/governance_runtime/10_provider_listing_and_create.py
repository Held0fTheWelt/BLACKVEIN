"""Governance runtime source segment: provider_listing_and_create.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
            "email_verification_enabled": bool(current_app.config.get("EMAIL_VERIFICATION_ENABLED", True)),
            "verification_ttl_minutes": int(current_app.config.get("EMAIL_VERIFICATION_TOKEN_TTL_MINUTES", 30)),
        },
        "costs": {
            "daily_global_limit": "50.00",
            "monthly_global_limit": "1000.00",
            "warning_threshold_percent": 80,
            "hard_stop_enabled": False,
        },
        "retrieval": {
            "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
            "embeddings_enabled": False,
            "embedding_cache_policy": "default",
        },
        "world_engine": {
            "validation_execution_mode": bootstrap.validation_execution_mode,
            "max_retry_attempts": 1,
            "enable_corrective_feedback": True,
            "preview_isolation_mode": "in_memory_namespace",
            "runtime_diagnostics_verbosity": "operator",
        },
    }
    for scope, values in defaults.items():
        for setting_key, setting_value in values.items():
            setting_id = _slug(f"{scope}_{setting_key}")
            if db.session.get(SystemSettingRecord, setting_id) is None:
                db.session.add(
                    SystemSettingRecord(
                        setting_id=setting_id,
                        scope=scope,
                        setting_key=setting_key,
                        setting_value_json=setting_value,
                        is_secret_backed=False,
                        is_user_visible=True,
                        updated_by="system",
                    )
                )
    _seed_default_presets()
    # Seed Story Runtime Experience defaults so fresh docker-up.py boots have
    # a working governed configuration with no manual admin step.
    try:
        from app.services.story_runtime.story_runtime_experience_service import (
            seed_default_story_runtime_experience,
        )

        seed_default_story_runtime_experience(actor="system")
    except Exception:  # noqa: BLE001 — baseline seeding must not block startup
        pass
    db.session.commit()


def list_bootstrap_presets() -> list[dict]:
    """List preset definitions."""
    _seed_default_presets()
    db.session.flush()
    presets = BootstrapPreset.query.order_by(BootstrapPreset.display_name.asc()).all()
    out: list[dict] = []
    for preset in presets:
        out.append(
            {
                "preset_id": preset.preset_id,
                "display_name": preset.display_name,
                "description": preset.description,
                "generation_execution_mode": preset.generation_execution_mode,
                "retrieval_execution_mode": preset.retrieval_execution_mode,
                "validation_execution_mode": preset.validation_execution_mode,
                "provider_selection_mode": preset.provider_selection_mode,
                "runtime_profile": preset.default_runtime_profile,
                "provider_templates": preset.default_provider_templates_json,
                "budget_policy": preset.default_budget_policy_json,
            }
        )
'''
