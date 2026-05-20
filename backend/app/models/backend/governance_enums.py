"""Canonical enums for operational settings and runtime governance."""

from __future__ import annotations

from enum import Enum


class BootstrapState(str, Enum):
    """Lifecycle states for trust-anchor/bootstrap initialization."""

    uninitialized = "uninitialized"
    initializing = "initializing"
    initialized = "initialized"
    bootstrap_locked = "bootstrap_locked"
    bootstrap_recovery_required = "bootstrap_recovery_required"


class SecretStorageMode(str, Enum):
    """Secret backend choices supported by the MVP."""

    same_db_encrypted = "same_db_encrypted"
    separate_secret_db_encrypted = "separate_secret_db_encrypted"
    external_secret_manager = "external_secret_manager"


class GenerationExecutionMode(str, Enum):
    """Generation runtime behavior governed by admin settings."""

    mock_only = "mock_only"
    ai_only = "ai_only"
    routed_llm_slm = "routed_llm_slm"
    hybrid_routed_with_mock_fallback = "hybrid_routed_with_mock_fallback"


class RetrievalExecutionMode(str, Enum):
    """Retrieval strategy selected by operator policy."""

    disabled = "disabled"
    sparse_only = "sparse_only"
    hybrid_dense_sparse = "hybrid_dense_sparse"


class ValidationExecutionMode(str, Enum):
    """Validation strictness choices for runtime evaluation."""

    schema_only = "schema_only"
    schema_plus_semantic = "schema_plus_semantic"
    strict_rule_engine = "strict_rule_engine"


class ProviderSelectionMode(str, Enum):
    """Provider selection constraints for runtime resolution."""

    local_only = "local_only"
    remote_allowed = "remote_allowed"
    remote_preferred = "remote_preferred"
    restricted_by_route = "restricted_by_route"


class AIProviderType(str, Enum):
    """Provider classes available in governance CRUD."""

    openai = "openai"
    ollama = "ollama"
    openrouter = "openrouter"
    anthropic = "anthropic"
    custom_http = "custom_http"
    mock = "mock"


class AIModelRole(str, Enum):
    """Model role used for routing semantics."""

    llm = "llm"
    slm = "slm"
    mock = "mock"


class CostMethod(str, Enum):
    """How runtime cost gets determined for a model usage event."""

    provider_reported = "provider_reported"
    price_table_estimated = "price_table_estimated"
    flat_per_request = "flat_per_request"
    none = "none"


class RuntimeProfile(str, Enum):
    """High-level runtime posture selected by operators."""

    safe_local = "safe_local"
    balanced = "balanced"
    cost_aware = "cost_aware"
    quality_first = "quality_first"
    custom = "custom"


class HealthStatus(str, Enum):
    """Administrative health status for providers and integrations."""

    unknown = "unknown"
    healthy = "healthy"
    degraded = "degraded"
    failing = "failing"
    disabled = "disabled"


class SettingScope(str, Enum):
    """Scope of a governed setting row."""

    bootstrap = "bootstrap"
    backend = "backend"
    world_engine = "world_engine"
    ai_runtime = "ai_runtime"
    retrieval = "retrieval"
    notifications = "notifications"
    costs = "costs"
