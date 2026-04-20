"""Bounded MCP-shaped in-process tool loop primitives for AI turns."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from app.runtime.decision_policy import AIActionType
from app.runtime.preview_delta import preview_delta_dry_run
from app.runtime.preview_models import PreviewDeltaRequest


class ToolCallStatus:
    """Canonical per-call statuses."""

    SUCCESS = "success"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    ERROR = "error"


class ToolLoopStopReason:
    """Canonical loop stop reasons."""

    FINALIZED = "finalized"
    TOOL_CALL_LIMIT_REACHED = "tool_call_limit_reached"
    POLICY_REJECTED = "policy_rejected"
    TOOL_TIMEOUT_EXHAUSTED = "tool_timeout_exhausted"
    TOOL_ERROR_EXHAUSTED = "tool_error_exhausted"
    FATAL_PARSE = "fatal_parse"


class ToolLoopPolicy(BaseModel):
    """Deterministic bounded policy for one AI turn."""

    enabled: bool = False
    allowed_tools: list[str] = Field(default_factory=list)
    max_tool_calls_per_turn: int = 3
    per_tool_timeout_ms: int = 1500
    max_retries_per_tool_call: int = 1

    @classmethod
    def from_session_metadata(cls, metadata: dict[str, Any] | None) -> "ToolLoopPolicy":
        if not isinstance(metadata, dict):
            return cls()
        raw = metadata.get("tool_loop")
        if not isinstance(raw, dict):
            return cls()
        return cls(
            enabled=bool(raw.get("enabled", False)),
            allowed_tools=[
                str(item)
                for item in raw.get("allowed_tools", [])
                if isinstance(item, str)
            ],
            max_tool_calls_per_turn=int(raw.get("max_tool_calls_per_turn", 3)),
            per_tool_timeout_ms=int(raw.get("per_tool_timeout_ms", 1500)),
            max_retries_per_tool_call=int(raw.get("max_retries_per_tool_call", 1)),
        )


class ToolRequest(BaseModel):
    """Model-requested host tool execution request."""

    request_id: str = Field(default_factory=lambda: uuid4().hex)
    sequence_index: int
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class ToolCallTranscriptEntry(BaseModel):
    """Persistent transcript entry for one host tool request."""

    sequence_index: int
    tool_name: str
    sanitized_arguments: dict[str, Any]
    status: str
    attempts: int
    duration_ms: int
    result_summary: str | None = None
    error_summary: str | None = None
    influenced_final_output: bool = False


class ToolLoopSummary(BaseModel):
    """Persistent summary for the complete tool loop of one turn."""

    enabled: bool
    total_calls: int
    stop_reason: str
    limit_hit: bool
    finalized_after_tool_use: bool


@dataclass(frozen=True)
class HostToolContext:
    """Bounded host context exposed to in-process tools."""

    session: Any
    module: Any
    current_turn: int
    recent_events: list[dict[str, Any]]


HostToolFn = Callable[[dict[str, Any], HostToolContext], dict[str, Any]]


def _truncate_text(value: Any, max_len: int = 160) -> str:
    raw = str(value)
    if len(raw) <= max_len:
        return raw
    return f"{raw[:max_len]}..."


def _sanitize_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, (dict, list)):
            sanitized[key] = _truncate_text(value, 120)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value if not isinstance(value, str) else _truncate_text(value, 120)
        else:
            sanitized[key] = _truncate_text(value, 120)
    return sanitized


def _tool_current_scene(_args: dict[str, Any], ctx: HostToolContext) -> dict[str, Any]:
    return {
        "scene_id": ctx.session.current_scene_id,
        "turn_counter": ctx.session.turn_counter,
    }


def _tool_recent_history(args: dict[str, Any], ctx: HostToolContext) -> dict[str, Any]:
    max_entries = int(args.get("max_entries", 5))
    max_entries = min(max(max_entries, 1), 10)
    history = getattr(ctx.session.context_layers, "session_history", None)
    entries = []
    if history and getattr(history, "entries", None):
        for entry in history.entries[-max_entries:]:
            entries.append(
                {
                    "turn_number": entry.turn_number,
                    "scene_id": entry.scene_id,
                    "guard_outcome": entry.guard_outcome,
                }
            )
    return {"entries": entries, "count": len(entries)}


def _tool_allowed_actions(_args: dict[str, Any], _ctx: HostToolContext) -> dict[str, Any]:
    return {"allowed_action_types": sorted(action.value for action in AIActionType)}


def _tool_preview_delta(args: dict[str, Any], ctx: HostToolContext) -> dict[str, Any]:
    request = PreviewDeltaRequest(**args)
    preview_result = preview_delta_dry_run(
        session=ctx.session,
        module=ctx.module,
        current_turn=ctx.current_turn,
        request=request,
    )
    return preview_result.model_dump()


def build_host_tool_registry() -> dict[str, HostToolFn]:
    return {
        "wos.read.current_scene": _tool_current_scene,
        "wos.read.recent_history": _tool_recent_history,
        "wos.read.allowed_actions": _tool_allowed_actions,
        "wos.guard.preview_delta": _tool_preview_delta,
    }


def detect_tool_request_payload(
    structured_payload: dict[str, Any] | None,
    *,
    sequence_index: int,
) -> ToolRequest | None:
    """Detect tool request payloads without touching final-output parser."""
    if not isinstance(structured_payload, dict):
        return None

    request_payload: dict[str, Any] | None = None
    if isinstance(structured_payload.get("tool_request"), dict):
        request_payload = structured_payload["tool_request"]
    elif structured_payload.get("type") == "tool_request":
        request_payload = structured_payload

    if not request_payload:
        return None

    tool_name = request_payload.get("tool_name")
    arguments = request_payload.get("arguments", {})
    if not isinstance(tool_name, str):
        return None
    if not isinstance(arguments, dict):
        arguments = {}

    request_id = request_payload.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        request_id = uuid4().hex

    rationale = request_payload.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        rationale = str(rationale)

    return ToolRequest(
        request_id=request_id,
        sequence_index=sequence_index,
        tool_name=tool_name,
        arguments=arguments,
        rationale=rationale,
    )


def execute_tool_request(
    request: ToolRequest,
    *,
    policy: ToolLoopPolicy,
    context: HostToolContext,
    registry: dict[str, HostToolFn] | None = None,
) -> tuple[ToolCallTranscriptEntry, dict[str, Any]]:
    """Execute one tool request under bounded deterministic policy."""
    tools = registry or build_host_tool_registry()
    sanitized_args = _sanitize_arguments(request.arguments)

    if request.tool_name not in policy.allowed_tools:
        entry = ToolCallTranscriptEntry(
            sequence_index=request.sequence_index,
            tool_name=request.tool_name,
            sanitized_arguments=sanitized_args,
            status=ToolCallStatus.REJECTED,
            attempts=1,
            duration_ms=0,
            error_summary="Tool rejected by whitelist policy.",
        )
        return entry, {
            "request_id": request.request_id,
            "sequence_index": request.sequence_index,
            "tool_name": request.tool_name,
            "status": ToolCallStatus.REJECTED,
            "error": "tool_rejected_by_policy",
        }

    tool_fn = tools.get(request.tool_name)
    if tool_fn is None:
        entry = ToolCallTranscriptEntry(
            sequence_index=request.sequence_index,
            tool_name=request.tool_name,
            sanitized_arguments=sanitized_args,
            status=ToolCallStatus.REJECTED,
            attempts=1,
            duration_ms=0,
            error_summary="Tool not registered.",
        )
        return entry, {
            "request_id": request.request_id,
            "sequence_index": request.sequence_index,
            "tool_name": request.tool_name,
            "status": ToolCallStatus.REJECTED,
            "error": "tool_not_registered",
        }

    max_attempts = max(1, policy.max_retries_per_tool_call + 1)
    attempts = 0
    start = perf_counter()
    last_error: str | None = None
    last_status = ToolCallStatus.ERROR

    while attempts < max_attempts:
        attempts += 1
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool_fn, request.arguments, context)
            try:
                result = future.result(
                    timeout=max(policy.per_tool_timeout_ms, 1) / 1000.0
                )
                duration_ms = int((perf_counter() - start) * 1000)
                entry = ToolCallTranscriptEntry(
                    sequence_index=request.sequence_index,
                    tool_name=request.tool_name,
                    sanitized_arguments=sanitized_args,
                    status=ToolCallStatus.SUCCESS,
                    attempts=attempts,
                    duration_ms=duration_ms,
                    result_summary=_truncate_text(result, 200),
                )
                return entry, {
                    "request_id": request.request_id,
                    "sequence_index": request.sequence_index,
                    "tool_name": request.tool_name,
                    "status": ToolCallStatus.SUCCESS,
                    "result": result,
                }
            except FutureTimeoutError:
                last_status = ToolCallStatus.TIMEOUT
                last_error = (
                    f"Tool timed out after {policy.per_tool_timeout_ms}ms "
                    f"(attempt {attempts}/{max_attempts})."
                )
            except Exception as exc:  # noqa: BLE001
                last_status = ToolCallStatus.ERROR
                last_error = f"Tool execution failed: {_truncate_text(exc, 180)}"

    duration_ms = int((perf_counter() - start) * 1000)
    entry = ToolCallTranscriptEntry(
        sequence_index=request.sequence_index,
        tool_name=request.tool_name,
        sanitized_arguments=sanitized_args,
        status=last_status,
        attempts=attempts,
        duration_ms=duration_ms,
        error_summary=last_error,
    )
    return entry, {
        "request_id": request.request_id,
        "sequence_index": request.sequence_index,
        "tool_name": request.tool_name,
        "status": last_status,
        "error": last_error or "tool_execution_failed",
    }
