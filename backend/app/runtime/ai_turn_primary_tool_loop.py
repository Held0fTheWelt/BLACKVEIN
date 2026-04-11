"""Primary-model bounded tool loop (execute_turn_with_ai) — extracted for clarity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_turn_preview import build_preview_snapshot
from app.runtime.tool_loop import (
    HostToolContext,
    ToolCallStatus,
    ToolLoopPolicy,
    ToolLoopStopReason,
    detect_tool_request_payload,
    execute_tool_request,
)

PRIMARY_AI_AGENT_ID = "primary_ai"
_PREVIEW_DELTA_TOOL = "wos.guard.preview_delta"


@dataclass
class PrimaryToolLoopOutcome:
    response: AdapterResponse
    tool_call_transcript: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    tool_call_count: int = 0
    tool_loop_stop_reason: str = ToolLoopStopReason.FINALIZED
    tool_limit_hit: bool = False
    finalized_after_tool_use: bool = False
    last_successful_tool_sequence: int | None = None
    preview_records: list[dict[str, Any]] = field(default_factory=list)


def run_primary_tool_loop(
    *,
    initial_response: AdapterResponse,
    tool_loop_policy: ToolLoopPolicy,
    tool_context: HostToolContext,
    generate_pair: Callable[[], tuple[AdapterResponse, int]],
) -> PrimaryToolLoopOutcome:
    """Run detect → execute → re-generate until final payload or policy stop."""
    response = initial_response
    transcript: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    tool_call_count = 0
    tool_loop_stop_reason = ToolLoopStopReason.FINALIZED
    tool_limit_hit = False
    finalized_after_tool_use = False
    last_successful_tool_sequence: int | None = None
    preview_records: list[dict[str, Any]] = []

    while True:
        tool_request = detect_tool_request_payload(
            response.structured_payload,
            sequence_index=tool_call_count + 1,
        )
        if tool_request is None:
            tool_loop_stop_reason = ToolLoopStopReason.FINALIZED
            finalized_after_tool_use = tool_call_count > 0
            break

        if tool_call_count >= tool_loop_policy.max_tool_calls_per_turn:
            tool_loop_stop_reason = ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
            tool_limit_hit = True
            break

        if tool_request.tool_name == _PREVIEW_DELTA_TOOL:
            tool_request.arguments.setdefault("requested_by_agent_id", PRIMARY_AI_AGENT_ID)

        transcript_entry, tool_result = execute_tool_request(
            tool_request,
            policy=tool_loop_policy,
            context=tool_context,
        )
        transcript_entry_payload = transcript_entry.model_dump()
        transcript_entry_payload["agent_id"] = PRIMARY_AI_AGENT_ID
        tool_results.append(tool_result)
        tool_call_count += 1
        if (
            tool_result.get("tool_name") == _PREVIEW_DELTA_TOOL
            and tool_result.get("status") == ToolCallStatus.SUCCESS
            and isinstance(tool_result.get("result"), dict)
        ):
            preview_result = tool_result["result"]
            transcript_entry_payload["preview_request_id"] = tool_result.get("request_id")
            transcript_entry_payload["preview_result_summary"] = build_preview_snapshot(preview_result)
            preview_records.append(
                {
                    "sequence_index": transcript_entry.sequence_index,
                    "request_id": tool_result.get("request_id"),
                    "requesting_agent_id": PRIMARY_AI_AGENT_ID,
                    "request_summary": transcript_entry_payload.get("sanitized_arguments") or {},
                    "result": preview_result,
                }
            )
        transcript.append(transcript_entry_payload)

        if transcript_entry.status == ToolCallStatus.SUCCESS:
            last_successful_tool_sequence = transcript_entry.sequence_index
        elif transcript_entry.status == ToolCallStatus.REJECTED:
            tool_loop_stop_reason = ToolLoopStopReason.POLICY_REJECTED
            break
        elif transcript_entry.status == ToolCallStatus.TIMEOUT:
            tool_loop_stop_reason = ToolLoopStopReason.TOOL_TIMEOUT_EXHAUSTED
            break
        elif transcript_entry.status == ToolCallStatus.ERROR:
            tool_loop_stop_reason = ToolLoopStopReason.TOOL_ERROR_EXHAUSTED
            break

        if tool_call_count >= tool_loop_policy.max_tool_calls_per_turn:
            tool_loop_stop_reason = ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
            tool_limit_hit = True
            break

        response, _ = generate_pair()
        if response.error or (not response.raw_output or not response.raw_output.strip()):
            tool_loop_stop_reason = ToolLoopStopReason.TOOL_ERROR_EXHAUSTED
            break

    if tool_loop_stop_reason == ToolLoopStopReason.FINALIZED and last_successful_tool_sequence:
        for entry in transcript:
            if entry.get("sequence_index") == last_successful_tool_sequence:
                entry["influenced_final_output"] = True
                break

    return PrimaryToolLoopOutcome(
        response=response,
        tool_call_transcript=transcript,
        tool_results=tool_results,
        tool_call_count=tool_call_count,
        tool_loop_stop_reason=tool_loop_stop_reason,
        tool_limit_hit=tool_limit_hit,
        finalized_after_tool_use=finalized_after_tool_use,
        last_successful_tool_sequence=last_successful_tool_sequence,
        preview_records=preview_records,
    )
