from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, NamedTuple

from app.runtime.ai_failure_recovery import StateSnapshot
from app.runtime.ai_turn_constants import (
    DEFAULT_ADAPTER_GENERATE_TIMEOUT_MS,
    METADATA_ADAPTER_GENERATE_TIMEOUT_MS,
)
from app.runtime.runtime_models import DegradedMarker, SessionState
from app.runtime.tool_loop import ToolLoopPolicy, ToolLoopStopReason


class _AiTurnPreAdapterState(NamedTuple):
    """Orchestration flags, mutable lists, and timeout config before adapter invocation."""

    started_at: datetime
    orchestration_enabled: bool
    staged_enabled: bool
    pre_execution_snapshot: StateSnapshot
    tool_loop_policy: ToolLoopPolicy
    tool_loop_enabled: bool
    execution_controls: dict[str, Any]
    tool_call_transcript: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    tool_loop_stop_reason: ToolLoopStopReason
    tool_limit_hit: bool
    finalized_after_tool_use: bool
    last_successful_tool_sequence: int | None
    tool_call_count: int
    tool_loop_summary: dict[str, Any] | None
    preview_records: list[dict[str, Any]]
    adapter_generate_timeout_ms: int
    interpretation_logged: list[bool]


def build_ai_turn_pre_adapter_state(session: SessionState) -> _AiTurnPreAdapterState:
    started_at = datetime.now(timezone.utc)
    orchestration_config = session.metadata.get("agent_orchestration")
    orchestration_enabled = False
    if isinstance(orchestration_config, dict):
        orchestration_enabled = bool(orchestration_config.get("enabled", False))
    elif isinstance(orchestration_config, bool):
        orchestration_enabled = orchestration_config

    pre_execution_snapshot = StateSnapshot(
        turn_number=session.turn_counter,
        canonical_state=deepcopy(session.canonical_state),
        snapshot_reason="pre_ai_execution",
    )

    tool_loop_policy = ToolLoopPolicy.from_session_metadata(session.metadata)
    tool_loop_enabled = (
        session.execution_mode == "ai"
        and tool_loop_policy.enabled
        and not orchestration_enabled
    )
    execution_controls = {
        "agent_orchestration_requested": orchestration_enabled,
        "agent_orchestration_active": orchestration_enabled,
        "tool_loop_requested": tool_loop_policy.enabled,
        "tool_loop_active": tool_loop_enabled,
    }

    adapter_generate_timeout_ms_raw = session.metadata.get(
        METADATA_ADAPTER_GENERATE_TIMEOUT_MS, DEFAULT_ADAPTER_GENERATE_TIMEOUT_MS
    )
    try:
        adapter_generate_timeout_ms = max(int(adapter_generate_timeout_ms_raw), 1)
    except (TypeError, ValueError):
        adapter_generate_timeout_ms = DEFAULT_ADAPTER_GENERATE_TIMEOUT_MS

    staged_enabled = session.metadata.get("runtime_staged_orchestration", True) is not False

    return _AiTurnPreAdapterState(
        started_at=started_at,
        orchestration_enabled=orchestration_enabled,
        staged_enabled=staged_enabled,
        pre_execution_snapshot=pre_execution_snapshot,
        tool_loop_policy=tool_loop_policy,
        tool_loop_enabled=tool_loop_enabled,
        execution_controls=execution_controls,
        tool_call_transcript=[],
        tool_results=[],
        tool_loop_stop_reason=ToolLoopStopReason.FINALIZED,
        tool_limit_hit=False,
        finalized_after_tool_use=False,
        last_successful_tool_sequence=None,
        tool_call_count=0,
        tool_loop_summary=None,
        preview_records=[],
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        interpretation_logged=[False],
    )
