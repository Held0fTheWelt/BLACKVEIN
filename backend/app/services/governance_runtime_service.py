"""Operational settings and runtime governance services."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import current_app
from sqlalchemy import and_
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.governance.errors import GovernanceError, governance_error
from app.models import (
    AITaskRoute,
    AIModelConfig,
    AIProviderConfig,
    AIProviderCredential,
    AIUsageEvent,
    BootstrapConfig,
    BootstrapPreset,
    CostBudgetPolicy,
    CostRollup,
    ProviderHealthCheck,
    ResolvedRuntimeConfigSnapshot,
    SettingAuditEvent,
    SystemSettingRecord,
)
from app.services.activity_log_service import log_activity
from app.services.governance_secret_crypto_service import decrypt_secret, encrypt_secret
from app.services.runtime_status_semantics import STATUS_SEMANTICS


_REQUIRED_TASK_KINDS: tuple[str, ...] = (
    "narrative_live_generation",
    "narrative_preview_generation",
    "narrative_validation_semantic",
    "research_synthesis",
    "research_revision_drafting",
    "writers_room_revision_assist",
    "retrieval_embedding_generation",
    "retrieval_query_expansion",
)

_DEFAULT_PRESETS: tuple[dict, ...] = (
    {
        "preset_id": "safe_local",
        "display_name": "Local Mock Safe",
        "description": "Deterministic local mock setup with conservative defaults.",
        "generation_execution_mode": "mock_only",
        "retrieval_execution_mode": "disabled",
        "validation_execution_mode": "schema_only",
        "provider_selection_mode": "local_only",
        "default_runtime_profile": "safe_local",
        "default_provider_templates_json": [{"provider_type": "mock", "display_name": "Mock Provider", "enabled_by_default": True, "requires_secret": False}],
        "default_budget_policy_json": {"daily_limit": "0", "monthly_limit": "0", "warning_threshold_percent": 80, "hard_stop_enabled": False},
    },
    {
        "preset_id": "balanced",
        "display_name": "Local Hybrid",
        "description": "Hybrid routed setup with mock fallback and optional cloud provider.",
        "generation_execution_mode": "hybrid_routed_with_mock_fallback",
        "retrieval_execution_mode": "hybrid_dense_sparse",
        "validation_execution_mode": "schema_plus_semantic",
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
                "local_provider": False,
                "cloud_provider": True,
                "openai_compatible": True,
            },
            "stage_support": "full",
            "operator_notes": "",
        },
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
        dek_nonce=row.dek_nonce,
    )


def _normalize_provider_url(base_url: str | None, contract: dict) -> str:
    base = (base_url or "").strip() or str(contract.get("default_base_url") or "").strip()
    if not base:
        return ""
    return base.rstrip("/")


def _probe_target(base_url: str, contract: dict) -> str:
    path = str(contract.get("health_check_path") or "").strip()
    if not path:
        return base_url
    if contract.get("provider_type") == "ollama" and base_url.endswith("/api") and path.startswith("/api/"):
        return base_url + path[len("/api") :]
    return base_url + path


def _provider_headers(contract: dict, secret: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    for k, v in (contract.get("static_headers") or {}).items():
        if v:
            headers[str(k)] = str(v)
    auth_mode = contract.get("auth_mode")
    if auth_mode == "bearer_api_key" and secret:
        headers["Authorization"] = f"Bearer {secret}"
    elif auth_mode == "x_api_key" and secret:
        headers["x-api-key"] = secret
    return headers


def _audit(event_type: str, scope: str, target_ref: str, changed_by: str, summary: str, metadata: dict | None = None) -> None:
    db.session.add(
        SettingAuditEvent(
            audit_event_id=f"audit_{uuid4().hex}",
            event_type=event_type,
            scope=scope,
            target_ref=target_ref,
            changed_by=changed_by,
            summary=summary,
            metadata_json=metadata or {},
        )
    )


def _seed_default_presets() -> None:
    for preset_payload in _DEFAULT_PRESETS:
        if BootstrapPreset.query.get(preset_payload["preset_id"]) is not None:
            continue
        db.session.add(BootstrapPreset(**preset_payload, is_builtin=True))


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def get_bootstrap_status() -> dict:
    """Return current bootstrap state and available presets."""
    _seed_default_presets()
    db.session.flush()
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    presets = BootstrapPreset.query.order_by(BootstrapPreset.display_name.asc()).all()
    if bootstrap is None:
        return {
            "bootstrap_required": True,
            "bootstrap_locked": False,
            "available_presets": [p.preset_id for p in presets],
            "configured": {
                "trust_anchor": False,
                "initial_admin": False,
                "secret_storage": False,
                "initial_provider": False,
            },
        }
    return {
        "bootstrap_required": bootstrap.bootstrap_state in {"uninitialized", "initializing", "bootstrap_recovery_required"},
        "bootstrap_locked": bool(bootstrap.bootstrap_locked),
        "available_presets": [p.preset_id for p in presets],
        "configured": {
            "trust_anchor": bool(bootstrap.trust_anchor_fingerprint),
            "initial_admin": bool(bootstrap.bootstrap_completed_by),
            "secret_storage": bool(bootstrap.secret_storage_mode),
            "initial_provider": bool(AIProviderConfig.query.count()),
        },
    }


def ensure_governance_baseline() -> None:
    """Ensure baseline bootstrap and operational setting rows exist."""
    try:
        inspector = inspect(db.engine)
        if not inspector.has_table("bootstrap_configs") or not inspector.has_table("system_setting_records"):
            return
    except OperationalError:
        return

    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        bootstrap = BootstrapConfig(
            bootstrap_state="uninitialized",
            bootstrap_locked=False,
            selected_preset=None,
            secret_storage_mode="same_db_encrypted",
            runtime_profile="safe_local",
            generation_execution_mode="mock_only",
            retrieval_execution_mode="disabled",
            validation_execution_mode="schema_only",
            provider_selection_mode="local_only",
            reopen_requires_elevated_auth=True,
            trust_anchor_metadata_json={},
        )
        db.session.add(bootstrap)

    defaults: dict[str, dict[str, object]] = {
        "backend": {
            "play_service_internal_url": current_app.config.get("PLAY_SERVICE_INTERNAL_URL"),
            "play_service_public_url": current_app.config.get("PLAY_SERVICE_PUBLIC_URL"),
            "play_service_request_timeout_seconds": int(current_app.config.get("PLAY_SERVICE_REQUEST_TIMEOUT", 30)),
            "game_ticket_ttl_seconds": int(current_app.config.get("PLAY_SERVICE_TICKET_TTL_SECONDS", 900)),
        },
        "notifications": {
            "mail_enabled": bool(current_app.config.get("MAIL_ENABLED", False)),
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
            if SystemSettingRecord.query.get(setting_id) is None:
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
    return out


def initialize_bootstrap(payload: dict, actor: str) -> dict:
    """Initialize bootstrap config and optional initial provider/credential."""
    _seed_default_presets()
    db.session.flush()
    existing = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if existing and existing.bootstrap_locked:
        raise governance_error("bootstrap_already_initialized", "Bootstrap is already initialized and locked.", 409, {})

    preset_id = (payload.get("selected_preset") or "").strip()
    preset = BootstrapPreset.query.get(preset_id)
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
        "bootstrap_status": "initialized",
        "bootstrap_locked": True,
        "secret_storage_mode": bootstrap.secret_storage_mode,
        "trust_anchor_fingerprint": bootstrap.trust_anchor_fingerprint,
        "next_actions": ["launch_stack", "open_administration_tool", "configure_models_and_routes"],
        "stack_start_ready": True,
    }


def reopen_bootstrap(payload: dict, actor: str) -> dict:
    """Reopen bootstrap in explicit recovery mode."""
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        raise governance_error("bootstrap_recovery_token_invalid", "Bootstrap has not been initialized yet.", 403, {})
    recovery_token = (payload.get("recovery_token") or "").strip()
    configured_token = (current_app.config.get("BOOTSTRAP_RECOVERY_TOKEN") or "").strip()
    if not recovery_token or not configured_token or recovery_token != configured_token:
        raise governance_error("bootstrap_recovery_token_invalid", "Recovery token is invalid.", 403, {})
    bootstrap.bootstrap_state = "bootstrap_recovery_required"
    bootstrap.bootstrap_locked = False
    _audit("bootstrap_reopened", "bootstrap", "bootstrap_config", actor, "Bootstrap reopened in recovery mode.", {})
    db.session.commit()
    return {
        "bootstrap_reopen_status": "accepted",
        "recovery_mode": True,
        "allowed_sections": ["secret_storage", "provider_credentials", "runtime_modes"],
    }


def list_providers() -> list[dict]:
    rows = AIProviderConfig.query.order_by(AIProviderConfig.provider_id.asc()).all()
    model_rows = AIModelConfig.query.all()
    route_rows = AITaskRoute.query.filter_by(is_enabled=True).all()
    models_by_provider: dict[str, int] = defaultdict(int)
    enabled_models_by_provider: dict[str, int] = defaultdict(int)
    for m in model_rows:
        models_by_provider[m.provider_id] += 1
        if m.is_enabled:
            enabled_models_by_provider[m.provider_id] += 1
    routes_by_provider: dict[str, int] = defaultdict(int)
    for route in route_rows:
        refs = [route.preferred_model_id, route.fallback_model_id, route.mock_model_id]
        touched: set[str] = set()
        for rid in refs:
            if not rid:
                continue
            model = next((m for m in model_rows if m.model_id == rid), None)
            if model:
                touched.add(model.provider_id)
        for pid in touched:
            routes_by_provider[pid] += 1
    out: list[dict] = []
    for row in rows:
        contract = _provider_contract(row.provider_type)
        requires_credential = bool(contract.get("requires_credential"))
        eligible_runtime = bool(
            row.is_enabled
            and (not requires_credential or row.credential_configured)
            and row.health_status not in {"failing", "disabled"}
        )
        limitations: list[str] = []
        if requires_credential and not row.credential_configured:
            limitations.append("credential_missing")
        if row.health_status in {"failing", "degraded"}:
            limitations.append(f"health_{row.health_status}")
        if enabled_models_by_provider[row.provider_id] == 0:
            limitations.append("no_enabled_models")
        out.append(
            {
                "provider_id": row.provider_id,
                "provider_type": row.provider_type,
                "display_name": row.display_name,
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
    existing = AIProviderConfig.query.get(provider_id)
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
    provider = AIProviderConfig.query.get(provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
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
        from app.services.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config
        if has_complete_play_service_config():
            reload_play_story_runtime_governed_config()
    except Exception as exc:  # noqa: BLE001 — best-effort rebind must not fail the provider update
        import logging
        logging.getLogger(__name__).warning("Provider update succeeded but world-engine rebind failed: %s", exc)

    return provider


def write_provider_credential(provider_id: str, payload: dict, actor: str) -> dict:
    """Write/replace provider credential in write-only mode."""
    provider = AIProviderConfig.query.get(provider_id)
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
    provider = AIProviderConfig.query.get(provider_id)
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
                authenticated = status not in {401, 403}
                usable = False
                health_status = "failing" if status in {401, 403} else "degraded"
                error_code = "auth_failed" if status in {401, 403} else f"http_{status}"
                error_message = f"Provider responded with HTTP {status}."
            except URLError as e:
                latency_ms = int((perf_counter() - started) * 1000)
                reachable = False
                authenticated = False
                usable = False
                health_status = "failing"
                error_code = "network_unreachable"
                error_message = str(e.reason) if getattr(e, "reason", None) else "Provider endpoint unreachable."
            except Exception as e:  # pragma: no cover - defensive
                latency_ms = int((perf_counter() - started) * 1000)
                reachable = False
                authenticated = False
                usable = False
                health_status = "failing"
                error_code = "health_check_failed"
                error_message = str(e)
    provider.health_status = health_status
    provider.last_tested_at = tested_at
    db.session.add(
        ProviderHealthCheck(
            health_check_id=f"health_{uuid4().hex}",
            provider_id=provider_id,
            health_status=health_status,
            latency_ms=latency_ms,
            error_code=error_code,
            error_message=error_message,
            tested_at=tested_at,
        )
    )
    _audit(
        "provider_health_tested",
        "ai_runtime",
        provider_id,
        actor,
        "Provider health test executed.",
        {"health_status": health_status, "error_code": error_code},
    )
    db.session.commit()
    return {
        "provider_id": provider_id,
        "provider_type": provider.provider_type,
        "health_status": health_status,
        "reachable": reachable,
        "authenticated": authenticated,
        "credential_configured": bool(provider.credential_configured),
        "usable": usable,
        "latency_ms": latency_ms,
        "error_code": error_code,
        "operator_message": error_message or "Provider is usable.",
        "health_check_strategy": contract.get("health_check_strategy"),
        "tested_at": tested_at.isoformat(),
    }


def list_models() -> list[dict]:
    rows = AIModelConfig.query.order_by(AIModelConfig.model_id.asc()).all()
    providers = {p.provider_id: p for p in AIProviderConfig.query.all()}

    def _provider_runtime_eligible(provider: AIProviderConfig | None) -> bool:
        if provider is None:
            return False
        contract = _provider_contract(provider.provider_type)
        requires_credential = bool(contract.get("requires_credential"))
        return bool(
            provider.is_enabled
            and (not requires_credential or provider.credential_configured)
            and provider.health_status not in {"failing", "disabled"}
        )

    out: list[dict] = []
    for row in rows:
        provider = providers.get(row.provider_id)
        blockers: list[str] = []
        if provider is None:
            blockers.append("provider_missing")
        else:
            if not provider.is_enabled:
                blockers.append("provider_disabled")
            if provider.health_status in {"failing", "disabled"}:
                blockers.append(f"provider_health_{provider.health_status}")
            contract = _provider_contract(provider.provider_type)
            if bool(contract.get("requires_credential")) and not provider.credential_configured:
                blockers.append("provider_credential_missing")
        if not row.is_enabled:
            blockers.append("model_disabled")
        out.append(
            {
                "model_id": row.model_id,
                "provider_id": row.provider_id,
                "model_name": row.model_name,
                "display_name": row.display_name,
                "model_role": row.model_role,
                "is_enabled": row.is_enabled,
                "structured_output_capable": row.structured_output_capable,
                "timeout_seconds": row.timeout_seconds,
                "max_context_tokens": row.max_context_tokens,
                "cost_method": row.cost_method,
                "input_price_per_1k": str(row.input_price_per_1k) if row.input_price_per_1k is not None else None,
                "output_price_per_1k": str(row.output_price_per_1k) if row.output_price_per_1k is not None else None,
                "flat_request_price": str(row.flat_request_price) if row.flat_request_price is not None else None,
                "provider_runtime_eligible": _provider_runtime_eligible(provider),
                "runtime_eligible": row.is_enabled and _provider_runtime_eligible(provider),
                "readiness_blockers": blockers,
            }
        )
    return out


def create_model(payload: dict, actor: str) -> AIModelConfig:
    provider_id = (payload.get("provider_id") or "").strip()
    provider = AIProviderConfig.query.get(provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
    if not provider.is_enabled:
        raise governance_error(
            "provider_not_eligible_for_model_assignment",
            "Cannot assign models to a disabled provider.",
            409,
            {"provider_id": provider_id},
        )
    model_name = (payload.get("model_name") or "").strip()
    if not model_name:
        raise governance_error("setting_value_invalid", "model_name is required.", 400, {})
    model_id = _slug(payload.get("model_id") or f"{provider_id}_{model_name}")
    model = AIModelConfig.query.get(model_id)
    if model:
        return model
    model = AIModelConfig(
        model_id=model_id,
        provider_id=provider_id,
        model_name=model_name,
        display_name=(payload.get("display_name") or model_name).strip(),
        model_role=(payload.get("model_role") or "llm").strip(),
        is_enabled=bool(payload.get("is_enabled", True)),
        structured_output_capable=bool(payload.get("supports_structured_output", payload.get("structured_output_capable", False))),
        timeout_seconds=int(payload.get("timeout_seconds", 30)),
        max_context_tokens=payload.get("max_context_tokens"),
        cost_method=(payload.get("cost_method") or "none").strip(),
        input_price_per_1k=Decimal(str(payload["input_price_per_1k"])) if payload.get("input_price_per_1k") is not None else None,
        output_price_per_1k=Decimal(str(payload["output_price_per_1k"])) if payload.get("output_price_per_1k") is not None else None,
        flat_request_price=Decimal(str(payload["flat_request_price"])) if payload.get("flat_request_price") is not None else None,
    )
    db.session.add(model)
    _audit("model_created", "ai_runtime", model_id, actor, "Model created.", {"provider_id": provider_id})
    db.session.commit()
    return model


def update_model(model_id: str, payload: dict, actor: str) -> AIModelConfig:
    print(f"DEBUG: update_model called: model_id={model_id} payload={payload}", flush=True)

    model = AIModelConfig.query.get(model_id)
    if model is None:
        raise governance_error("model_not_found", f"Model '{model_id}' not found.", 404, {"model_id": model_id})

    print(f"DEBUG: Before update: model_name={model.model_name} display_name={model.display_name}", flush=True)

    for key in (
        "model_name",
        "display_name",
        "model_role",
        "is_enabled",
        "structured_output_capable",
        "timeout_seconds",
        "max_context_tokens",
        "cost_method",
    ):
        if key in payload:
            old_val = getattr(model, key)
            new_val = payload[key]
            setattr(model, key, new_val)
            print(f"DEBUG: Changed {key}: {old_val} -> {new_val}", flush=True)

    for key in ("input_price_per_1k", "output_price_per_1k", "flat_request_price"):
        if key in payload:
            value = payload[key]
            setattr(model, key, Decimal(str(value)) if value is not None else None)

    model.updated_at = datetime.now(timezone.utc)
    _audit("model_updated", "ai_runtime", model_id, actor, "Model updated.", {})

    print(f"DEBUG: Before commit: model_name={model.model_name}", flush=True)
    db.session.commit()
    print(f"DEBUG: After commit: model_name={model.model_name}", flush=True)

    # After model update, trigger world-engine rebind to pick up the change
    try:
        from app.services.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config
        if has_complete_play_service_config():
            reload_play_story_runtime_governed_config()
    except Exception as exc:  # noqa: BLE001 — best-effort rebind must not fail the model update
        import logging
        logging.getLogger(__name__).warning("Model update succeeded but world-engine rebind failed: %s", exc)

    return model


def list_routes() -> list[dict]:
    rows = AITaskRoute.query.order_by(AITaskRoute.route_id.asc()).all()
    model_rows = {m.model_id: m for m in AIModelConfig.query.all()}
    provider_rows = {p.provider_id: p for p in AIProviderConfig.query.all()}

    def _model_runtime_eligible(model_id: str | None, *, require_non_mock: bool) -> tuple[bool, str | None]:
        if not model_id:
            return False, "model_reference_missing"
        model = model_rows.get(model_id)
        if model is None:
            return False, "model_reference_not_found"
        if not model.is_enabled:
            return False, "model_disabled"
        provider = provider_rows.get(model.provider_id)
        if provider is None:
            return False, "provider_not_found"
        if not provider.is_enabled:
            return False, "provider_disabled"
        if provider.health_status in {"failing", "disabled"}:
            return False, f"provider_health_{provider.health_status}"
        contract = _provider_contract(provider.provider_type)
        if bool(contract.get("requires_credential")) and not provider.credential_configured:
            return False, "provider_credential_missing"
        if require_non_mock and provider.provider_type == "mock":
            return False, "provider_is_mock"
        return True, None

    out: list[dict] = []
    for row in rows:
        blockers: list[str] = []
        pref_ok, pref_blocker = _model_runtime_eligible(row.preferred_model_id, require_non_mock=True)
        fb_ok, fb_blocker = _model_runtime_eligible(row.fallback_model_id, require_non_mock=True)
        mock_ok, mock_blocker = _model_runtime_eligible(row.mock_model_id, require_non_mock=False)
        if pref_blocker and row.preferred_model_id:
            blockers.append(f"preferred_{pref_blocker}")
        if fb_blocker and row.fallback_model_id:
            blockers.append(f"fallback_{fb_blocker}")
        if mock_blocker and row.mock_model_id:
            blockers.append(f"mock_{mock_blocker}")
        if not row.is_enabled:
            blockers.append("route_disabled")
        if not (pref_ok or fb_ok):
            blockers.append("no_eligible_ai_model_reference")
        if row.use_mock_when_provider_unavailable and not mock_ok:
            blockers.append("mock_fallback_missing_or_invalid")
        out.append(
            {
                "route_id": row.route_id,
                "task_kind": row.task_kind,
                "workflow_scope": row.workflow_scope,
                "preferred_model_id": row.preferred_model_id,
                "fallback_model_id": row.fallback_model_id,
                "mock_model_id": row.mock_model_id,
                "is_enabled": row.is_enabled,
                "use_mock_when_provider_unavailable": row.use_mock_when_provider_unavailable,
                "ai_path_ready": row.is_enabled and (pref_ok or fb_ok),
                "mock_path_ready": mock_ok,
                "runtime_eligible": row.is_enabled and ((pref_ok or fb_ok) or (row.use_mock_when_provider_unavailable and mock_ok)),
                "readiness_blockers": blockers,
            }
        )
    return out


def _readiness_suggested_action(*, code: str, entity_id: str | None, limitation: str | None = None) -> str:
    """Return a concrete operator-facing remediation line for readiness blockers."""
    if code == "enabled_non_mock_provider_missing":
        return (
            "Create or enable a non-mock provider (openai, ollama, openrouter, or anthropic), set base URL when prompted, "
            "store the API key for cloud providers, then run **Test provider health** on this page."
        )
    if code == "enabled_non_mock_model_missing":
        return (
            "Under **Model governance**, create at least one enabled model bound to an eligible non-mock provider, "
            "then attach it to a route."
        )
    if code == "enabled_ai_route_missing":
        return (
            "Under **Route governance**, enable a route whose preferred or fallback model points at a non-mock model on a healthy provider."
        )
    if code.startswith("provider_") and entity_id:
        lim = limitation or code.removeprefix("provider_")
        if lim == "credential_missing":
            return (
                f"Open provider `{entity_id}`: paste the API key in the credential field, save, then run **Test provider health**."
            )
        if lim.startswith("health_"):
            return (
                f"Fix base URL and credentials for `{entity_id}`, then run **Test provider health** until status is healthy."
            )
        if lim == "no_enabled_models":
            return f"Create or enable at least one model for provider `{entity_id}`."
        return f"Review provider `{entity_id}` in **Provider governance** and clear limitation `{lim}`."
    if code.startswith("route_") and entity_id:
        return (
            f"Edit route `{entity_id}`: ensure preferred/fallback models reference enabled models on healthy providers, "
            "or enable a valid mock fallback when **Use mock when provider unavailable** is checked."
        )
    return "Review **Runtime readiness** details and the raw inventory below."


def evaluate_runtime_readiness() -> dict:
    """Deterministic readiness and blocker report for operator runtime decisions."""
    provider_rows = list_providers()
    model_rows = list_models()
    route_rows = list_routes()

    enabled_non_mock_provider = any(
        p["eligible_for_runtime_assignment"] and p["provider_type"] != "mock" for p in provider_rows
    )
    enabled_non_mock_model = any(
        m["runtime_eligible"]
        and (next((p for p in provider_rows if p["provider_id"] == m["provider_id"]), {}).get("provider_type") != "mock")
        for m in model_rows
    )
    enabled_ai_route = any(r["ai_path_ready"] for r in route_rows)

    blockers: list[dict] = []
    if not enabled_non_mock_provider:
        blockers.append(
            {
                "code": "enabled_non_mock_provider_missing",
                "entity_type": "provider",
                "entity_id": None,
                "message": "No enabled non-mock provider is currently eligible for runtime assignment.",
                "suggested_action": _readiness_suggested_action(code="enabled_non_mock_provider_missing", entity_id=None),
            }
        )
    if not enabled_non_mock_model:
        blockers.append(
            {
                "code": "enabled_non_mock_model_missing",
                "entity_type": "model",
                "entity_id": None,
                "message": "No enabled model is attached to an eligible non-mock provider.",
                "suggested_action": _readiness_suggested_action(code="enabled_non_mock_model_missing", entity_id=None),
            }
        )
    if not enabled_ai_route:
        blockers.append(
            {
                "code": "enabled_ai_route_missing",
                "entity_type": "route",
                "entity_id": None,
                "message": "No enabled route currently resolves to an eligible preferred or fallback non-mock model.",
                "suggested_action": _readiness_suggested_action(code="enabled_ai_route_missing", entity_id=None),
            }
        )

    for provider in provider_rows:
        for limitation in provider.get("limitations") or []:
            code = f"provider_{limitation}"
            blockers.append(
                {
                    "code": code,
                    "entity_type": "provider",
                    "entity_id": provider["provider_id"],
                    "message": f"Provider '{provider['provider_id']}' is not ready for AI routes: {limitation}.",
                    "suggested_action": _readiness_suggested_action(
                        code=code, entity_id=provider["provider_id"], limitation=limitation
                    ),
                }
            )
    for route in route_rows:
        for route_blocker in route.get("readiness_blockers") or []:
            code = f"route_{route_blocker}"
            blockers.append(
                {
                    "code": code,
                    "entity_type": "route",
                    "entity_id": route["route_id"],
                    "message": f"Route '{route['route_id']}' cannot run as configured: {route_blocker}.",
                    "suggested_action": _readiness_suggested_action(code=code, entity_id=route["route_id"]),
                }
            )

    ai_only_valid = enabled_non_mock_provider and enabled_non_mock_model and enabled_ai_route
    mock_only_required = not ai_only_valid
    next_actions: list[str] = []
    if not enabled_non_mock_provider:
        next_actions.append("Create or enable a non-mock provider and configure its credential.")
    if enabled_non_mock_provider and not enabled_non_mock_model:
        next_actions.append("Create or enable a model on an eligible non-mock provider.")
    if enabled_non_mock_model and not enabled_ai_route:
        next_actions.append("Assign preferred or fallback non-mock models to at least one enabled route.")
    if ai_only_valid:
        next_actions.append("Switch generation_execution_mode to ai_only when desired.")

    if ai_only_valid:
        readiness_headline = "AI-only generation is currently valid for governed routes."
        readiness_severity = "healthy"
    elif mock_only_required:
        readiness_headline = "Stay on mock_only (or hybrid with mock fallback) until the blockers below are cleared."
        readiness_severity = "blocked" if len([b for b in blockers if b["entity_id"] is None]) else "degraded"
    else:
        readiness_headline = "Review readiness signals before enabling ai_only."
        readiness_severity = "degraded"

    readiness_legend: list[str] = [
        "mock_only_required=true means at least one governed AI precondition is still missing; keep generation_execution_mode on mock_only until blockers clear.",
        "ai_only_valid=true means an eligible non-mock provider, a runtime-eligible model on it, and at least one enabled route with a working AI model chain are all satisfied.",
        "Each blocker lists entity_type/entity_id when a specific provider or route is at fault; global rows (no entity_id) describe missing prerequisites.",
    ]

    play_story_runtime_governance: dict[str, object] = {"status": "skipped", "reason": "play_service_not_configured"}
    try:
        from flask import has_app_context

        from app.services.game_service import GameServiceError, get_play_story_runtime_config_status, has_complete_play_service_config

        if has_app_context() and has_complete_play_service_config():
            probe = get_play_story_runtime_config_status()
            st = probe.get("runtime_config_status") if isinstance(probe, dict) else {}
            play_story_runtime_governance = {"status": "ok", "runtime_config_status": st}
            if not isinstance(st, dict):
                play_story_runtime_governance = {"status": "error", "message": "unexpected_runtime_config_status_shape"}
            else:
                if not bool(st.get("governed_runtime_active")):
                    blockers.append(
                        {
                            "code": "play_story_runtime_not_governed",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime is not bound to governed resolved config (or execution is blocked).",
                            "suggested_action": "Rebuild resolved runtime config from Administration Center, verify BACKEND_RUNTIME_CONFIG_URL and INTERNAL_RUNTIME_CONFIG_TOKEN on the play service, then POST /api/internal/story/runtime/reload-config or restart the play service.",
                        }
                    )
                if bool(st.get("legacy_default_registry_path")):
                    # P1-4: This blocker can no longer occur (escape hatch removed in P0-1)
                    # Kept for backwards compatibility with older play-service versions
                    blockers.append(
                        {
                            "code": "play_story_runtime_legacy_default_registry",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime reports legacy default registry posture (should not occur in current version).",
                            "suggested_action": "Rebuild governed resolved runtime config and restart play-service.",
                        }
                    )
                if bool(st.get("live_execution_blocked")):
                    blockers.append(
                        {
                            "code": "play_story_runtime_live_execution_blocked",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime reports live_execution_blocked.",
                            "suggested_action": "Fix governed runtime configuration completeness, then reload the play-service story runtime from the backend rebuild path.",
                        }
                    )
                if not str(st.get("config_version") or "").strip():
                    blockers.append(
                        {
                            "code": "play_story_runtime_missing_config_version",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime is missing an active config_version.",
                            "suggested_action": "Rebuild resolved runtime config and rebind the play service story runtime.",
                        }
                    )
    except GameServiceError as exc:
        play_story_runtime_governance = {"status": "error", "message": str(exc)}
        blockers.append(
            {
                "code": "play_story_runtime_governance_probe_failed",
                "entity_type": "play_service",
                "entity_id": None,
                "message": f"Backend could not read play-service story runtime governance status: {exc}",
                "suggested_action": "Verify play-service health, internal URL, and X-Play-Service-Key alignment, then retry.",
            }
        )

    if play_story_runtime_governance.get("status") == "error" or any(
        b.get("code", "").startswith("play_story_runtime") for b in blockers
    ):
        if readiness_severity == "healthy":
            readiness_severity = "degraded"
        if readiness_headline.startswith("AI-only generation is currently valid"):
            readiness_headline = "Governance inventory looks eligible, but play-service story-runtime binding needs attention."

    return {
        "mock_only_required": mock_only_required,
        "ai_only_valid": ai_only_valid,
        "readiness_headline": readiness_headline,
        "readiness_severity": readiness_severity,
        "status_semantics": STATUS_SEMANTICS,
        "readiness_legend": readiness_legend,
        "enabled_non_mock_provider_present": enabled_non_mock_provider,
        "enabled_non_mock_model_present": enabled_non_mock_model,
        "enabled_ai_route_present": enabled_ai_route,
        "blockers": blockers,
        "next_actions": next_actions,
        "provider_summary": {
            "total": len(provider_rows),
            "eligible_non_mock": sum(1 for p in provider_rows if p["eligible_for_runtime_assignment"] and p["provider_type"] != "mock"),
        },
        "model_summary": {
            "total": len(model_rows),
            "runtime_eligible_non_mock": sum(
                1
                for m in model_rows
                if m["runtime_eligible"]
                and (next((p for p in provider_rows if p["provider_id"] == m["provider_id"]), {}).get("provider_type") != "mock")
            ),
        },
        "route_summary": {
            "total": len(route_rows),
            "ai_ready": sum(1 for r in route_rows if r["ai_path_ready"]),
            "runtime_eligible": sum(1 for r in route_rows if r["runtime_eligible"]),
        },
        "play_story_runtime_governance": play_story_runtime_governance,
    }


def _ensure_model_exists(model_id: str | None) -> None:
    if model_id is None:
        return
    model = AIModelConfig.query.get(model_id)
    if model is None or not model.is_enabled:
        raise governance_error("route_invalid_model_reference", "Route references missing or disabled model.", 409, {"model_id": model_id})


def create_route(payload: dict, actor: str) -> AITaskRoute:
    route_id = _slug(payload.get("route_id") or f"{payload.get('task_kind','task')}_{payload.get('workflow_scope','global')}")
    for field in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
        _ensure_model_exists(payload.get(field))
    route = AITaskRoute.query.get(route_id)
    if route:
        return route
    route = AITaskRoute(
        route_id=route_id,
        task_kind=(payload.get("task_kind") or "").strip(),
        workflow_scope=(payload.get("workflow_scope") or "global").strip(),
        preferred_model_id=payload.get("preferred_model_id"),
        fallback_model_id=payload.get("fallback_model_id"),
        mock_model_id=payload.get("mock_model_id"),
        is_enabled=bool(payload.get("is_enabled", True)),
        use_mock_when_provider_unavailable=bool(payload.get("use_mock_when_provider_unavailable", True)),
    )
    db.session.add(route)
    _audit("route_created", "ai_runtime", route_id, actor, "Route created.", {})
    db.session.commit()
    return route


def update_route(route_id: str, payload: dict, actor: str) -> AITaskRoute:
    route = AITaskRoute.query.get(route_id)
    if route is None:
        raise governance_error("route_not_found", f"Route '{route_id}' not found.", 404, {"route_id": route_id})
    for field in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
        if field in payload:
            _ensure_model_exists(payload.get(field))
            setattr(route, field, payload.get(field))
    for field in ("task_kind", "workflow_scope", "is_enabled", "use_mock_when_provider_unavailable"):
        if field in payload:
            setattr(route, field, payload.get(field))
    route.updated_at = datetime.now(timezone.utc)
    _audit("route_updated", "ai_runtime", route_id, actor, "Route updated.", {})
    db.session.commit()

    # After route update, trigger world-engine rebind to pick up the change
    try:
        from app.services.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config
        if has_complete_play_service_config():
            reload_play_story_runtime_governed_config()
    except Exception as exc:  # noqa: BLE001 — best-effort rebind must not fail the route update
        import logging
        logging.getLogger(__name__).warning("Route update succeeded but world-engine rebind failed: %s", exc)

    return route


def _current_bootstrap() -> BootstrapConfig:
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        bootstrap = BootstrapConfig(
            bootstrap_state="uninitialized",
            bootstrap_locked=False,
            selected_preset=None,
            secret_storage_mode="same_db_encrypted",
            runtime_profile="safe_local",
            generation_execution_mode="mock_only",
            retrieval_execution_mode="disabled",
            validation_execution_mode="schema_only",
            provider_selection_mode="local_only",
            reopen_requires_elevated_auth=True,
            trust_anchor_metadata_json={},
        )
        db.session.add(bootstrap)
        _seed_default_presets()
        db.session.commit()
    return bootstrap


def get_runtime_modes() -> dict:
    bootstrap = _current_bootstrap()
    return {
        "generation_execution_mode": bootstrap.generation_execution_mode,
        "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
        "validation_execution_mode": bootstrap.validation_execution_mode,
        "provider_selection_mode": bootstrap.provider_selection_mode,
        "runtime_profile": bootstrap.runtime_profile,
    }


def update_runtime_modes(payload: dict, actor: str) -> dict:
    bootstrap = _current_bootstrap()
    updates = {
        "generation_execution_mode": payload.get("generation_execution_mode", bootstrap.generation_execution_mode),
        "retrieval_execution_mode": payload.get("retrieval_execution_mode", bootstrap.retrieval_execution_mode),
        "validation_execution_mode": payload.get("validation_execution_mode", bootstrap.validation_execution_mode),
        "provider_selection_mode": payload.get("provider_selection_mode", bootstrap.provider_selection_mode),
        "runtime_profile": payload.get("runtime_profile", bootstrap.runtime_profile),
    }
    _validate_runtime_modes(updates)
    for key, value in updates.items():
        setattr(bootstrap, key, value)
    _audit("runtime_modes_updated", "ai_runtime", "runtime_modes", actor, "Runtime modes updated.", updates)
    db.session.commit()
    return {"updated": True, "runtime_profile": bootstrap.runtime_profile, "effective_generation_execution_mode": bootstrap.generation_execution_mode}


def _validate_runtime_modes(modes: dict) -> None:
    generation_mode = modes["generation_execution_mode"]
    providers = AIProviderConfig.query.filter_by(is_enabled=True).all()
    routes = AITaskRoute.query.filter_by(is_enabled=True).all()
    real_provider_ids = {p.provider_id for p in providers if p.provider_type != "mock" and p.credential_configured}
    route_models: set[str] = set()
    has_mock_fallback = False
    for route in routes:
        for mid in (route.preferred_model_id, route.fallback_model_id):
            if mid:
                model = AIModelConfig.query.get(mid)
                if model and model.provider_id in real_provider_ids and model.is_enabled:
                    route_models.add(mid)
        if route.mock_model_id:
            model = AIModelConfig.query.get(route.mock_model_id)
            if model and model.is_enabled and model.model_role == "mock":
                has_mock_fallback = True
    if generation_mode in {"ai_only", "routed_llm_slm"} and (not real_provider_ids or not route_models):
        raise governance_error(
            "generation_mode_invalid",
            "This generation mode needs at least one enabled non-mock provider with a stored credential, "
            "and at least one enabled AI task route whose preferred or fallback model uses that provider. "
            "Create a provider, save its API key, add models and routes, or stay on mock_only until then.",
            400,
            {"generation_execution_mode": generation_mode},
        )
    if generation_mode == "hybrid_routed_with_mock_fallback" and not has_mock_fallback:
        raise governance_error(
            "route_requires_mock_model_for_hybrid_mode",
            "Hybrid mode requires a mock-capable fallback route.",
            409,
            {},
        )


def _resolve_provider_selection(providers: list[AIProviderConfig], provider_selection_mode: str) -> list[AIProviderConfig]:
    if provider_selection_mode == "local_only":
        selected = [p for p in providers if p.is_local]
    elif provider_selection_mode == "remote_preferred":
        remote = [p for p in providers if not p.is_local]
        selected = remote or providers
    else:
        selected = providers
    return selected


def _validate_and_resolve_routes(*, routes: list[AITaskRoute], models_by_id: dict[str, AIModelConfig], selected_provider_ids: set[str], generation_execution_mode: str) -> list[dict]:
    """Validate route model references and return resolved route payload."""
    missing_required_tasks = {task for task in _REQUIRED_TASK_KINDS}
    resolved_routes: list[dict] = []
    for route in routes:
        missing_required_tasks.discard(route.task_kind)
        for ref_name in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
            ref_id = getattr(route, ref_name)
            if ref_id is None:
                continue
            model = models_by_id.get(ref_id)
            if model is None:
                raise governance_error("resolved_config_generation_failed", "Route references missing model.", 500, {"route_id": route.route_id, "model_id": ref_id})
            if model.provider_id not in selected_provider_ids and model.model_role != "mock":
                raise governance_error(
                    "resolved_config_generation_failed",
                    "Route references model whose provider is not currently selectable.",
                    500,
                    {"route_id": route.route_id, "model_id": ref_id, "provider_id": model.provider_id},
                )
        resolved_routes.append(
            {
                "route_id": route.route_id,
                "task_kind": route.task_kind,
                "workflow_scope": route.workflow_scope,
                "preferred_model_id": route.preferred_model_id,
                "fallback_model_id": route.fallback_model_id,
                "mock_model_id": route.mock_model_id,
                "effective_strategy": "hybrid" if route.use_mock_when_provider_unavailable else "strict",
            }
        )
    if missing_required_tasks and generation_execution_mode != "mock_only":
        raise governance_error(
            "resolved_config_generation_failed",
            "Not all required task kinds have enabled routes.",
            500,
            {"missing_task_kinds": sorted(missing_required_tasks)},
        )
    return resolved_routes


def _serialize_provider_rows(providers: list[AIProviderConfig]) -> list[dict]:
    out: list[dict] = []
    for provider in providers:
        contract = _provider_contract(provider.provider_type)

        out.append(
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type,
                "base_url": _normalize_provider_url(provider.base_url, contract),
                "credential_configured": provider.credential_configured,
                "credential_endpoint": f"/api/v1/internal/provider-credential/{provider.provider_id}" if provider.credential_configured else None,
                "is_enabled": True,
                "health_status": provider.health_status,
                "auth_mode": contract.get("auth_mode"),
                "required_headers": contract.get("required_headers", []),
                "static_headers": contract.get("static_headers", {}),
                "capabilities": contract.get("capabilities", {}),
                "supports_model_discovery": bool(contract.get("supports_model_discovery")),
                "openai_compatible": bool(contract.get("openai_compatible")),
            }
        )
    return out


def _serialize_model_rows(models: list[AIModelConfig], selected_provider_ids: set[str]) -> list[dict]:
    return [
        {
            "model_id": model.model_id,
            "provider_id": model.provider_id,
            "model_name": model.model_name,
            "model_role": model.model_role,
            "timeout_seconds": model.timeout_seconds,
            "structured_output_capable": model.structured_output_capable,
        }
        for model in models
        if model.provider_id in selected_provider_ids
    ]


def _collect_scope_settings() -> dict[str, dict]:
    return {
        "backend_settings": read_scope_settings("backend"),
        "world_engine_settings": read_scope_settings("world_engine"),
        "retrieval_settings": read_scope_settings("retrieval"),
        "cost_settings": read_scope_settings("costs"),
        "notification_settings": read_scope_settings("notifications"),
    }


def _persist_resolved_snapshot(*, config_version: str, bootstrap: BootstrapConfig, resolved: dict, actor: str) -> None:
    ResolvedRuntimeConfigSnapshot.query.filter_by(is_active=True).update({"is_active": False})
    db.session.add(
        ResolvedRuntimeConfigSnapshot(
            snapshot_id=f"snap_{uuid4().hex}",
            config_version=config_version,
            generation_execution_mode=bootstrap.generation_execution_mode,
            retrieval_execution_mode=bootstrap.retrieval_execution_mode,
            validation_execution_mode=bootstrap.validation_execution_mode,
            runtime_profile=bootstrap.runtime_profile,
            provider_selection_mode=bootstrap.provider_selection_mode,
            resolved_config_json=resolved,
            is_active=True,
        )
    )
    _audit("resolved_config_rebuilt", "ai_runtime", config_version, actor, "Resolved runtime config rebuilt.", {})
    db.session.commit()


def build_resolved_runtime_config(*, persist_snapshot: bool, actor: str) -> dict:
    """Resolve active runtime config and validate route completeness."""
    bootstrap = _current_bootstrap()
    providers = AIProviderConfig.query.filter_by(is_enabled=True).all()
    providers = _resolve_provider_selection(providers, bootstrap.provider_selection_mode)
    models = AIModelConfig.query.filter_by(is_enabled=True).all()
    models_by_id = {m.model_id: m for m in models}
    selected_provider_ids = {p.provider_id for p in providers}
    routes = AITaskRoute.query.filter_by(is_enabled=True).all()
    resolved_routes = _validate_and_resolve_routes(
        routes=routes,
        models_by_id=models_by_id,
        selected_provider_ids=selected_provider_ids,
        generation_execution_mode=bootstrap.generation_execution_mode,
    )
    providers_out = _serialize_provider_rows(providers)
    models_out = _serialize_model_rows(models, selected_provider_ids)
    scoped_settings = _collect_scope_settings()

    generated_at = datetime.now(timezone.utc)
    config_version = f"cfg_{generated_at.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    resolved = {
        "config_version": config_version,
        "generated_at": generated_at.isoformat(),
        "generation_execution_mode": bootstrap.generation_execution_mode,
        "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
        "validation_execution_mode": bootstrap.validation_execution_mode,
        "runtime_profile": bootstrap.runtime_profile,
        "provider_selection_mode": bootstrap.provider_selection_mode,
        "providers": providers_out,
        "models": models_out,
        "routes": resolved_routes,
        **scoped_settings,
    }
    if persist_snapshot:
        _persist_resolved_snapshot(
            config_version=config_version,
            bootstrap=bootstrap,
            resolved=resolved,
            actor=actor,
        )
        rebind: dict[str, object] = {"attempted": False, "skipped": True}
        try:
            from app.services.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config

            if has_complete_play_service_config():
                rebind["skipped"] = False
                rebind["attempted"] = True
                rebind.update(reload_play_story_runtime_governed_config())
        except Exception as exc:  # noqa: BLE001 — operator-facing best-effort rebind must not roll back DB snapshot
            rebind["skipped"] = False
            rebind["attempted"] = True
            rebind["ok"] = False
            rebind["error"] = str(exc)[:500]
        resolved["world_engine_story_runtime_rebind"] = rebind
    return resolved


def get_active_runtime_snapshot() -> dict | None:
    """Return active resolved snapshot, if one exists."""
    row = ResolvedRuntimeConfigSnapshot.query.filter_by(is_active=True).order_by(ResolvedRuntimeConfigSnapshot.generated_at.desc()).first()
    if row is None:
        return None
    return row.resolved_config_json or None


def _ensure_default_mock_path(actor: str) -> None:
    provider = AIProviderConfig.query.get("mock_default")
    if provider is None:
        provider = AIProviderConfig(
            provider_id="mock_default",
            provider_type="mock",
            display_name="Mock Default",
            is_enabled=True,
            is_local=True,
            supports_structured_output=True,
            credential_configured=False,
            health_status="healthy",
        )
        db.session.add(provider)
    model = AIModelConfig.query.get("mock_deterministic")
    if model is None:
        model = AIModelConfig(
            model_id="mock_deterministic",
            provider_id=provider.provider_id,
            model_name="mock-deterministic",
            display_name="Mock Deterministic",
            model_role="mock",
            is_enabled=True,
            structured_output_capable=True,
            timeout_seconds=5,
            cost_method="none",
        )
        db.session.add(model)
    for task_kind in _REQUIRED_TASK_KINDS:
        route_id = f"{task_kind}_global"
        if AITaskRoute.query.get(route_id) is None:
            db.session.add(
                AITaskRoute(
                    route_id=route_id,
                    task_kind=task_kind,
                    workflow_scope="global",
                    preferred_model_id=model.model_id,
                    fallback_model_id=model.model_id,
                    mock_model_id=model.model_id,
                    is_enabled=True,
                    use_mock_when_provider_unavailable=True,
                )
            )
    _audit("mock_path_seeded", "ai_runtime", "mock_default", actor, "Default mock path ensured.", {})


def read_scope_settings(scope: str) -> dict:
    rows = SystemSettingRecord.query.filter_by(scope=scope).all()
    return {row.setting_key: row.setting_value_json for row in rows}


def update_scope_settings(scope: str, payload: dict, actor: str) -> dict:
    for setting_key, setting_value in payload.items():
        setting_id = _slug(f"{scope}_{setting_key}")
        row = SystemSettingRecord.query.get(setting_id)
        if row is None:
            row = SystemSettingRecord(
                setting_id=setting_id,
                scope=scope,
                setting_key=setting_key,
                setting_value_json=setting_value,
                is_secret_backed=False,
                is_user_visible=True,
                updated_by=actor,
            )
            db.session.add(row)
        else:
            row.setting_value_json = setting_value
            row.updated_by = actor
            row.updated_at = datetime.now(timezone.utc)
        _audit("setting_updated", scope, setting_key, actor, "Setting updated.", {"scope": scope})
    db.session.commit()
    return read_scope_settings(scope)


def ingest_usage_event(payload: dict, actor: str) -> dict:
    event = AIUsageEvent(
        usage_event_id=payload.get("usage_event_id") or f"evt_{uuid4().hex}",
        provider_id=payload.get("provider_id"),
        model_id=payload.get("model_id"),
        task_kind=payload["task_kind"],
        workflow_scope=payload.get("workflow_scope") or "global",
        request_id=payload["request_id"],
        success=bool(payload.get("success", True)),
        latency_ms=payload.get("latency_ms"),
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        provider_reported_cost=Decimal(str(payload["provider_reported_cost"])) if payload.get("provider_reported_cost") is not None else None,
        estimated_cost=Decimal(str(payload["estimated_cost"])) if payload.get("estimated_cost") is not None else None,
        cost_method_used=payload.get("cost_method_used") or "none",
        degraded_mode_used=bool(payload.get("degraded_mode_used", False)),
        retry_used=bool(payload.get("retry_used", False)),
        fallback_used=bool(payload.get("fallback_used", False)),
    )
    db.session.add(event)
    _audit("usage_event_ingested", "costs", event.usage_event_id, actor, "Usage event ingested.", {})
    db.session.commit()
    return {"usage_event_id": event.usage_event_id, "created_at": event.created_at.isoformat() if event.created_at else None}


def list_usage_events(limit: int = 100) -> list[dict]:
    rows = AIUsageEvent.query.order_by(AIUsageEvent.created_at.desc()).limit(limit).all()
    return [
        {
            "usage_event_id": row.usage_event_id,
            "provider_id": row.provider_id,
            "model_id": row.model_id,
            "task_kind": row.task_kind,
            "workflow_scope": row.workflow_scope,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "provider_reported_cost": str(row.provider_reported_cost) if row.provider_reported_cost is not None else None,
            "estimated_cost": str(row.estimated_cost) if row.estimated_cost is not None else None,
            "cost_method_used": row.cost_method_used,
            "fallback_used": row.fallback_used,
            "retry_used": row.retry_used,
            "degraded_mode_used": row.degraded_mode_used,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def upsert_budget(policy_id: str | None, payload: dict, actor: str) -> CostBudgetPolicy:
    warning = int(payload.get("warning_threshold_percent", 80))
    if warning < 1 or warning > 100:
        raise governance_error("budget_invalid_threshold", "warning_threshold_percent must be between 1 and 100.", 400, {"warning_threshold_percent": warning})
    budget_policy_id = policy_id or f"budget_{uuid4().hex}"
    budget = CostBudgetPolicy.query.get(budget_policy_id)
    if budget is None:
        budget = CostBudgetPolicy(
            budget_policy_id=budget_policy_id,
            scope_kind=(payload.get("scope_kind") or "global").strip(),
            scope_ref=(payload.get("scope_ref") or "").strip() or None,
        )
        db.session.add(budget)
    budget.daily_limit = Decimal(str(payload["daily_limit"])) if payload.get("daily_limit") is not None else None
    budget.monthly_limit = Decimal(str(payload["monthly_limit"])) if payload.get("monthly_limit") is not None else None
    budget.warning_threshold_percent = warning
    budget.hard_stop_enabled = bool(payload.get("hard_stop_enabled", False))
    _audit("budget_updated", "costs", budget_policy_id, actor, "Budget policy upserted.", {})
    db.session.commit()
    return budget


def list_budgets() -> list[dict]:
    rows = CostBudgetPolicy.query.order_by(CostBudgetPolicy.scope_kind.asc(), CostBudgetPolicy.scope_ref.asc()).all()
    return [
        {
            "budget_policy_id": row.budget_policy_id,
            "scope_kind": row.scope_kind,
            "scope_ref": row.scope_ref,
            "daily_limit": str(row.daily_limit) if row.daily_limit is not None else None,
            "monthly_limit": str(row.monthly_limit) if row.monthly_limit is not None else None,
            "warning_threshold_percent": row.warning_threshold_percent,
            "hard_stop_enabled": row.hard_stop_enabled,
        }
        for row in rows
    ]


def rebuild_rollups(actor: str) -> list[dict]:
    """Rebuild daily rollups from usage events."""
    rows = AIUsageEvent.query.all()
    grouped: dict[tuple[date, str | None, str | None, str | None], list[AIUsageEvent]] = defaultdict(list)
    for row in rows:
        if row.created_at is None:
            continue
        grouped[(row.created_at.date(), row.provider_id, row.model_id, row.workflow_scope)].append(row)
    CostRollup.query.delete()
    out: list[dict] = []
    for key, events in grouped.items():
        rollup_date, provider_id, model_id, workflow_scope = key
        estimated_total = Decimal("0")
        provider_total: Decimal | None = Decimal("0")
        for event in events:
            if event.estimated_cost is not None:
                estimated_total += event.estimated_cost
            if event.provider_reported_cost is None:
                provider_total = None
            elif provider_total is not None:
                provider_total += event.provider_reported_cost
        rollup = CostRollup(
            rollup_id=f"roll_{uuid4().hex}",
            rollup_date=rollup_date,
            provider_id=provider_id,
            model_id=model_id,
            workflow_scope=workflow_scope,
            request_count=len(events),
            estimated_cost_total=estimated_total,
            provider_reported_cost_total=provider_total,
            retry_count=sum(1 for event in events if event.retry_used),
            fallback_count=sum(1 for event in events if event.fallback_used),
        )
        db.session.add(rollup)
        out.append(
            {
                "rollup_id": rollup.rollup_id,
                "rollup_date": rollup_date.isoformat(),
                "provider_id": provider_id,
                "model_id": model_id,
                "workflow_scope": workflow_scope,
                "request_count": rollup.request_count,
                "estimated_cost_total": str(rollup.estimated_cost_total),
                "provider_reported_cost_total": str(rollup.provider_reported_cost_total) if rollup.provider_reported_cost_total is not None else None,
                "retry_count": rollup.retry_count,
                "fallback_count": rollup.fallback_count,
            }
        )
    _audit("cost_rollup_rebuilt", "costs", "cost_rollups", actor, "Cost rollups rebuilt.", {"count": len(out)})
    db.session.commit()
    return out


def list_rollups(limit: int = 100) -> list[dict]:
    rows = CostRollup.query.order_by(CostRollup.rollup_date.desc()).limit(limit).all()
    return [
        {
            "rollup_id": row.rollup_id,
            "rollup_date": row.rollup_date.isoformat(),
            "provider_id": row.provider_id,
            "model_id": row.model_id,
            "workflow_scope": row.workflow_scope,
            "request_count": row.request_count,
            "estimated_cost_total": str(row.estimated_cost_total),
            "provider_reported_cost_total": str(row.provider_reported_cost_total) if row.provider_reported_cost_total is not None else None,
            "retry_count": row.retry_count,
            "fallback_count": row.fallback_count,
        }
        for row in rows
    ]


def list_audit_events(limit: int = 200) -> list[dict]:
    rows = SettingAuditEvent.query.order_by(SettingAuditEvent.changed_at.desc()).limit(limit).all()
    return [row.to_dict() for row in rows]


def enforce_budget_guard(provider_id: str | None, workflow_scope: str | None) -> None:
    """Raise if hard-stop budget has been exceeded."""
    today = datetime.now(timezone.utc).date()
    day_rollups = CostRollup.query.filter(CostRollup.rollup_date == today).all()
    totals = Decimal("0")
    for roll in day_rollups:
        if provider_id and roll.provider_id not in {provider_id, None}:
            continue
        if workflow_scope and roll.workflow_scope not in {workflow_scope, None}:
            continue
        totals += roll.provider_reported_cost_total or roll.estimated_cost_total
    budgets = CostBudgetPolicy.query.filter_by(hard_stop_enabled=True).all()
    for budget in budgets:
        if budget.scope_kind == "provider" and budget.scope_ref and provider_id != budget.scope_ref:
            continue
        if budget.scope_kind == "workflow" and budget.scope_ref and workflow_scope != budget.scope_ref:
            continue
        if budget.daily_limit is not None and totals > budget.daily_limit:
            raise governance_error(
                "budget_limit_exceeded",
                "Hard-stop budget policy blocks this runtime action.",
                409,
                {"scope_kind": budget.scope_kind, "scope_ref": budget.scope_ref, "daily_limit": str(budget.daily_limit), "current_total": str(totals)},
            )


def record_operational_activity(actor_user, action: str, message: str, metadata: dict | None = None) -> None:
    """Mirror key governance events to shared activity log."""
    log_activity(
        actor=actor_user,
        category="governance",
        action=action,
        status="success",
        message=message,
        route="governance",
        method="SYSTEM",
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

    provider = AIProviderConfig.query.get(provider_id)
    if provider is None:
        print(f"DEBUG: Provider {provider_id} not found", flush=True)
        return None

    if not provider.credential_configured:
        print(f"DEBUG: Provider {provider_id} has no credential configured", flush=True)
        return None

    from app.models.governance_core import AIProviderCredential

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
        print(f"DEBUG: Successfully decrypted credential for {provider_id}: key={api_key[:20] if api_key else 'None'}...", flush=True)
        return api_key
    except Exception as e:
        print(f"DEBUG: Failed to decrypt credential for {provider_id}: {e}", flush=True)
        return None
