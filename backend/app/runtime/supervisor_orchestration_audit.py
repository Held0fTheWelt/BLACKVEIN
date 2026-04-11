"""Tool-audit rows and cross-agent preview feedback accumulation for supervisor orchestration."""

from __future__ import annotations

from typing import Any, Protocol

from app.runtime.tool_loop import ToolCallStatus


class _AgentLike(Protocol):
    agent_id: str


def append_tool_audit_rows_for_invocation(
    *,
    agent: _AgentLike,
    tool_transcript: list[dict[str, Any]],
    consume_budget_on_failed_tool_call: bool,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """Build tool_audit rows, count billable tool calls, append shared preview feedback."""
    rows: list[dict[str, Any]] = []
    preview_appends: list[dict[str, Any]] = []
    counted_tool_calls = 0
    for entry in tool_transcript:
        tool_status = str(entry.get("status", "unknown"))
        counted = tool_status == ToolCallStatus.SUCCESS or consume_budget_on_failed_tool_call
        if counted:
            counted_tool_calls += 1
        rows.append(
            {
                "agent_id": agent.agent_id,
                "tool_name": entry.get("tool_name"),
                "duration_ms": int(entry.get("duration_ms", 0)),
                "status": tool_status,
                "counted_against_hard_limits": counted,
                "cache_hit": bool(entry.get("cache_hit", False)),
            }
        )
        if entry.get("tool_name") == "wos.guard.preview_delta":
            preview_summary = entry.get("preview_result_summary")
            if isinstance(preview_summary, dict):
                preview_appends.append(
                    {
                        "request_id": entry.get("preview_request_id"),
                        "requesting_agent_id": entry.get("agent_id", agent.agent_id),
                        "sequence_index": entry.get("sequence_index"),
                        "result_summary": preview_summary,
                    }
                )
    return rows, counted_tool_calls, preview_appends


def enrich_preview_delta_transcript_entry(
    entry_dict: dict[str, Any],
    tool_result: dict[str, Any],
) -> None:
    """Mutate transcript entry with preview_delta summary fields (supervisor tool loop)."""
    entry_dict["preview_request_id"] = tool_result.get("request_id")
    result_payload = tool_result.get("result")
    if isinstance(result_payload, dict):
        entry_dict["preview_result_summary"] = {
            "preview_allowed": bool(result_payload.get("preview_allowed", False)),
            "guard_outcome": result_payload.get("guard_outcome"),
            "accepted_delta_count": int(result_payload.get("accepted_delta_count", 0)),
            "rejected_delta_count": int(result_payload.get("rejected_delta_count", 0)),
            "partial_acceptance": bool(result_payload.get("partial_acceptance", False)),
            "rejection_reasons": list((result_payload.get("rejection_reasons") or [])[:5]),
            "suggested_corrections": list((result_payload.get("suggested_corrections") or [])[:5]),
            "input_targets": list((result_payload.get("input_targets") or [])[:20]),
            "summary": result_payload.get("summary"),
            "preview_safe_no_write": bool(result_payload.get("preview_safe_no_write", True)),
        }
