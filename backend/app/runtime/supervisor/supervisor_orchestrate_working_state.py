"""Mutable working state for one supervisor orchestration turn (DS-014 split)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord


@dataclass
class SupervisorOrchestrateWorkingState:
    invocations: list[AgentInvocationRecord] = field(default_factory=list)
    results: list[AgentResultRecord] = field(default_factory=list)
    tool_transcript: list[dict[str, Any]] = field(default_factory=list)
    policy_violations: list[str] = field(default_factory=list)
    parsed_decisions: dict[str, Any] = field(default_factory=dict)
    failover_events: list[dict[str, Any]] = field(default_factory=list)
    tool_audit: list[dict[str, Any]] = field(default_factory=list)
    consumed_agent_calls: int = 0
    consumed_tool_calls: int = 0
    failed_agent_calls: int = 0
    degraded_steps: int = 0
    consumed_token_proxy: int = 0
    consumed_total_tokens: int = 0
    exact_usage_count: int = 0
    proxy_fallback_count: int = 0
    shared_preview_feedback: list[dict[str, Any]] = field(default_factory=list)
