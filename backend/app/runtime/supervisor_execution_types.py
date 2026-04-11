"""Return type for supervisor orchestration (kept separate to avoid import cycles)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.runtime_models import (
    AgentInvocationRecord,
    AgentResultRecord,
    MergeFinalizationRecord,
    SupervisorPlan,
)


@dataclass
class SupervisorExecutionResult:
    """Bounded output of supervisor orchestration."""

    final_response: AdapterResponse
    plan: SupervisorPlan
    invocations: list[AgentInvocationRecord]
    results: list[AgentResultRecord]
    merge_finalization: MergeFinalizationRecord
    agent_tool_transcript: list[dict[str, Any]]
    policy_violations: list[str]
    budget_summary: dict[str, Any]
    failover_events: list[dict[str, Any]]
    cache_summary: dict[str, Any]
    tool_audit: list[dict[str, Any]]
