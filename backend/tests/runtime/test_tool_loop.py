"""Tests for bounded MCP-style in-process tool loop behavior."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.runtime.adapter_registry import clear_registry
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_turn_executor import execute_turn_with_ai
from .staged_test_payloads import maybe_staged_prelude_response
from app.runtime.tool_loop import (
    HostToolContext,
    ToolCallStatus,
    ToolLoopPolicy,
    ToolLoopStopReason,
    ToolRequest,
    execute_tool_request,
)


@pytest.fixture(autouse=True)
def _clear_adapter_registry_for_tool_loop_tests() -> None:
    """Prevent Task 2A model specs from prior tests from hijacking staged routing."""
    clear_registry()
    yield
    clear_registry()


FINAL_PAYLOAD = {
    "scene_interpretation": "Finalized after tool use.",
    "detected_triggers": [],
    "proposed_state_deltas": [],
    "rationale": "Deterministic test finalization",
}


class SequencedToolLoopAdapter(StoryAIAdapter):
    """Deterministic adapter returning configured payload sequence."""

    def __init__(self, payloads: list[dict[str, Any]]):
        self._payloads = payloads
        self._index = 0

    @property
    def adapter_name(self) -> str:
        return "sequenced-tool-loop-adapter"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        prelude = maybe_staged_prelude_response(request)
        if prelude is not None:
            return prelude
        payload = self._payloads[min(self._index, len(self._payloads) - 1)]
        self._index += 1
        return AdapterResponse(
            raw_output=f"[tool-loop] idx={self._index}",
            structured_payload=payload,
        )


class ForeverToolRequestAdapter(StoryAIAdapter):
    """Adapter that keeps requesting tools forever."""

    @property
    def adapter_name(self) -> str:
        return "forever-tool-request-adapter"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        prelude = maybe_staged_prelude_response(request)
        if prelude is not None:
            return prelude
        return AdapterResponse(
            raw_output="[tool-loop] forever",
            structured_payload={
                "type": "tool_request",
                "tool_name": "wos.read.current_scene",
                "arguments": {},
            },
        )


def test_execute_tool_request_timeout_retries_are_bounded():
    """A timed-out tool call retries deterministically and stops."""

    def slow_tool(_args: dict[str, Any], _ctx: HostToolContext) -> dict[str, Any]:
        time.sleep(0.03)
        return {"ok": True}

    policy = ToolLoopPolicy(
        enabled=True,
        allowed_tools=["wos.read.current_scene"],
        per_tool_timeout_ms=1,
        max_retries_per_tool_call=1,
    )
    request = ToolRequest(
        sequence_index=1,
        tool_name="wos.read.current_scene",
        arguments={},
    )
    ctx = HostToolContext(session=object(), module=object(), current_turn=1, recent_events=[])

    entry, result = execute_tool_request(
        request,
        policy=policy,
        context=ctx,
        registry={"wos.read.current_scene": slow_tool},
    )

    assert entry.status == ToolCallStatus.TIMEOUT
    assert entry.attempts == 2
    assert "timed out" in (entry.error_summary or "")
    assert result["status"] == ToolCallStatus.TIMEOUT


def test_tool_loop_disabled_leaves_ai_path_unchanged(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Disabled tool loop keeps normal AI behavior and no transcript."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {"enabled": False}

    adapter = SequencedToolLoopAdapter(payloads=[FINAL_PAYLOAD])
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    log = session.metadata["ai_decision_logs"][-1]
    assert log.tool_loop_summary is None
    assert log.tool_call_transcript is None


def test_allowed_tool_request_then_finalize_records_influence(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Allowed tool executes, model finalizes, transcript marks influence."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 3,
    }
    state_before = session.canonical_state.copy()

    adapter = SequencedToolLoopAdapter(
        payloads=[
            {
                "type": "tool_request",
                "tool_name": "wos.read.current_scene",
                "arguments": {},
            },
            FINAL_PAYLOAD,
        ]
    )
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.updated_canonical_state == state_before
    log = session.metadata["ai_decision_logs"][-1]
    assert log.tool_loop_summary is not None
    assert log.tool_loop_summary["stop_reason"] == ToolLoopStopReason.FINALIZED
    assert log.tool_loop_summary["finalized_after_tool_use"] is True
    assert len(log.tool_call_transcript or []) == 1
    assert log.tool_call_transcript[0]["status"] == ToolCallStatus.SUCCESS
    assert log.tool_call_transcript[0]["influenced_final_output"] is True


def test_disallowed_tool_is_rejected_and_counted(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Disallowed tool request is rejected and transcripted without execution."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.allowed_actions"],
        "max_tool_calls_per_turn": 3,
    }

    adapter = SequencedToolLoopAdapter(
        payloads=[
            {
                "type": "tool_request",
                "tool_name": "wos.read.current_scene",
                "arguments": {},
            },
            FINAL_PAYLOAD,
        ]
    )
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "system_error"
    assert result.failure_reason is not None
    log = session.metadata["ai_decision_logs"][-1]
    assert len(log.tool_call_transcript or []) == 1
    assert log.tool_call_transcript[0]["status"] == ToolCallStatus.REJECTED
    assert log.tool_loop_summary["total_calls"] == 1
    assert log.tool_loop_summary["stop_reason"] == ToolLoopStopReason.POLICY_REJECTED


def test_forever_tool_requests_stop_at_limit_deterministically(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Infinite tool requests are stopped by max_tool_calls_per_turn."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 2,
    }

    adapter = ForeverToolRequestAdapter()
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "system_error"
    assert result.failure_reason is not None
    log = session.metadata["ai_decision_logs"][-1]
    assert log.tool_loop_summary["stop_reason"] == ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
    assert log.tool_loop_summary["limit_hit"] is True
    assert log.tool_loop_summary["total_calls"] == 2


def test_preview_tool_feedback_can_drive_corrected_final_output(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Preview rejection can be followed by a corrected finalized proposal."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.guard.preview_delta"],
        "max_tool_calls_per_turn": 3,
    }

    adapter = SequencedToolLoopAdapter(
        payloads=[
            {
                "type": "tool_request",
                "tool_name": "wos.guard.preview_delta",
                "arguments": {
                    "scene_id": session.current_scene_id,
                    "proposed_state_deltas": [
                        {
                            "target_path": "characters.nonexistent.emotional_state",
                            "next_value": 77,
                            "delta_type": "state_update",
                        }
                    ],
                },
            },
            {
                "scene_interpretation": "Corrected after preview",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": 77,
                        "delta_type": "state_update",
                    }
                ],
                "rationale": "Correction applied",
            },
        ]
    )
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    log = session.metadata["ai_decision_logs"][-1]
    assert log.preview_diagnostics is not None
    assert log.preview_diagnostics["preview_count"] >= 1
    assert log.preview_diagnostics["revised_after_preview"] is True
    assert log.preview_diagnostics["improved_acceptance_vs_last_preview"] is True


def test_endless_preview_requests_are_bounded(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Infinite preview recursion is stopped by deterministic call limits."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.guard.preview_delta"],
        "max_tool_calls_per_turn": 2,
    }

    adapter = SequencedToolLoopAdapter(
        payloads=[
            {
                "type": "tool_request",
                "tool_name": "wos.guard.preview_delta",
                "arguments": {"proposed_state_deltas": []},
            }
        ]
    )
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )
    assert result.execution_status == "system_error"
    assert result.failure_reason is not None
    log = session.metadata["ai_decision_logs"][-1]
    assert log.tool_loop_summary["stop_reason"] == ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED


def test_tool_loop_zero_budget_triggers_recovery_without_ambiguous_parse(
    god_of_carnage_module_with_state, god_of_carnage_module,
):
    """Non-finalized stop with zero executed tool calls must use explicit recovery path."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 0,
    }
    adapter = ForeverToolRequestAdapter()
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )
    assert result.execution_status == "system_error"
    assert result.failure_reason is not None
    log = session.metadata["ai_decision_logs"][-1]
    assert log.tool_loop_summary is not None
    assert log.tool_loop_summary["total_calls"] == 0
    assert log.tool_loop_summary["stop_reason"] == ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
    assert log.guard_notes and "tool_loop_failure_recovery_active: true" in log.guard_notes
