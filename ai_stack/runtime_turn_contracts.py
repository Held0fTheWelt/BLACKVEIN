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

RAW_FALLBACK_BYPASS_NOTE = (
    "Graph-managed fallback uses raw adapter.generate (no LangChain structured parse) because the "
    "default mock adapter returns non-JSON text; primary invoke_model still uses LangChain."
)
