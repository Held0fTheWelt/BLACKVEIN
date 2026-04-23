"""Shared constants and types for the runtime turn LangGraph executor.

Keeps diagnostics vocabulary stable for tests, logs, and gate reports.
"""

from __future__ import annotations

from typing import Literal

# How the model adapter was invoked for this generation (final or primary-before-fallback state).
AdapterInvocationMode = Literal[
    "langchain_structured_primary",
    "raw_adapter_graph_managed_fallback",
    "degraded_no_fallback_adapter",
]

ADAPTER_INVOCATION_LANGCHAIN_PRIMARY: AdapterInvocationMode = "langchain_structured_primary"
ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK: AdapterInvocationMode = "raw_adapter_graph_managed_fallback"
ADAPTER_INVOCATION_DEGRADED_NO_FALLBACK: AdapterInvocationMode = "degraded_no_fallback_adapter"

# Package-output execution_health (graph_diagnostics.execution_health).
ExecutionHealth = Literal["healthy", "graph_error", "model_fallback", "degraded_generation"]

EXECUTION_HEALTH_HEALTHY: ExecutionHealth = "healthy"
EXECUTION_HEALTH_GRAPH_ERROR: ExecutionHealth = "graph_error"
EXECUTION_HEALTH_MODEL_FALLBACK: ExecutionHealth = "model_fallback"
EXECUTION_HEALTH_DEGRADED_GENERATION: ExecutionHealth = "degraded_generation"

EXECUTION_HEALTH_VALUES: tuple[ExecutionHealth, ...] = (
    EXECUTION_HEALTH_HEALTHY,
    EXECUTION_HEALTH_GRAPH_ERROR,
    EXECUTION_HEALTH_MODEL_FALLBACK,
    EXECUTION_HEALTH_DEGRADED_GENERATION,
)

# Canonical per-turn runtime quality posture.
QualityClass = Literal["healthy", "weak_but_legal", "degraded", "failed"]

QUALITY_CLASS_HEALTHY: QualityClass = "healthy"
QUALITY_CLASS_WEAK_BUT_LEGAL: QualityClass = "weak_but_legal"
QUALITY_CLASS_DEGRADED: QualityClass = "degraded"
QUALITY_CLASS_FAILED: QualityClass = "failed"

QUALITY_CLASS_VALUES: tuple[QualityClass, ...] = (
    QUALITY_CLASS_HEALTHY,
    QUALITY_CLASS_WEAK_BUT_LEGAL,
    QUALITY_CLASS_DEGRADED,
    QUALITY_CLASS_FAILED,
)

# Canonical degradation signal taxonomy (controlled, non-free-form).
DegradationSignal = Literal[
    "fallback_used",
    "weak_signal_accepted",
    "non_factual_staging",
    "degraded_commit",
    "actor_lanes_validation_gated",
    "prose_only_recovery",
    "thin_prose_override",
    "retry_exhausted",
]

DEGRADATION_SIGNAL_FALLBACK_USED: DegradationSignal = "fallback_used"
DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED: DegradationSignal = "weak_signal_accepted"
DEGRADATION_SIGNAL_NON_FACTUAL_STAGING: DegradationSignal = "non_factual_staging"
DEGRADATION_SIGNAL_DEGRADED_COMMIT: DegradationSignal = "degraded_commit"
DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED: DegradationSignal = "actor_lanes_validation_gated"
DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY: DegradationSignal = "prose_only_recovery"
DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE: DegradationSignal = "thin_prose_override"
DEGRADATION_SIGNAL_RETRY_EXHAUSTED: DegradationSignal = "retry_exhausted"

DEGRADATION_SIGNAL_VALUES: tuple[DegradationSignal, ...] = (
    DEGRADATION_SIGNAL_FALLBACK_USED,
    DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED,
    DEGRADATION_SIGNAL_NON_FACTUAL_STAGING,
    DEGRADATION_SIGNAL_DEGRADED_COMMIT,
    DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED,
    DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY,
    DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE,
    DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
)

RAW_FALLBACK_BYPASS_NOTE = (
    "Graph-managed fallback uses raw adapter.generate (no LangChain structured parse) because the "
    "default mock adapter returns non-JSON text; primary invoke_model still uses LangChain."
)
