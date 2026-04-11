from __future__ import annotations

from typing import Any, Callable, NamedTuple


class _AiTurnOrchestrationLogBundle(NamedTuple):
    """Shared orchestration attachments for fallback, tool-loop recovery, and success logging."""

    tool_loop_summary: dict[str, Any] | None
    tool_call_transcript: list[dict[str, Any]]
    last_successful_tool_sequence: int | None
    preview_diagnostics: dict[str, Any] | None
    supervisor_plan: Any
    subagent_invocations: Any
    subagent_results: Any
    merge_finalization: Any
    orchestration_budget_summary: Any
    orchestration_failover: Any
    orchestration_cache: Any
    tool_audit: Any
    model_routing_trace: dict[str, Any] | None
    runtime_stage_traces_for_log: list[dict[str, Any]] | None
    runtime_orchestration_summary_for_log: dict[str, Any] | None
    operator_audit_for_log: dict[str, Any] | None


class _SupervisorOrchestrationBranchOutcome(NamedTuple):
    response: Any
    current_attempt: int
    supervisor_plan: Any
    subagent_invocations: Any
    subagent_results: Any
    merge_finalization: Any
    orchestration_budget_summary: Any
    orchestration_failover: Any
    orchestration_cache: Any
    tool_audit: Any
    tool_loop_summary: dict[str, Any]


class _RoutingAndGenerationBundle(NamedTuple):
    execution_adapter: Any
    model_routing_trace: dict[str, Any] | None
    runtime_stage_traces_for_log: list[dict[str, Any]] | None
    runtime_orchestration_summary_for_log: dict[str, Any] | None
    staged_result_holder: Any
    operator_audit_for_log: dict[str, Any] | None
    generate_with_runtime_policy: Callable[..., tuple[Any, int]]


class _ToolLoopSectionOutcome(NamedTuple):
    response: Any
    tool_call_transcript: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    tool_call_count: int
    tool_loop_stop_reason: Any
    tool_limit_hit: bool
    finalized_after_tool_use: bool
    last_successful_tool_sequence: int | None
    tool_loop_summary: dict[str, Any] | None


class _FirstAdapterResponseOutcome(NamedTuple):
    response: Any
    current_attempt: int
    supervisor_plan: Any
    subagent_invocations: Any
    subagent_results: Any
    merge_finalization: Any
    orchestration_budget_summary: Any
    orchestration_failover: Any
    orchestration_cache: Any
    tool_audit: Any
    tool_loop_summary: dict[str, Any] | None
