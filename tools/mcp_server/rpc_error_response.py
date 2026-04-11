"""Map MCP server exceptions to JSON-RPC error payloads (DS-029)."""

from __future__ import annotations

import time
from typing import Any

from .errors import (
    INVALID_PARAMS,
    INTERNAL_ERROR,
    METHOD_NOT_FOUND,
    PERMISSION_DENIED,
    RATE_LIMITED,
    TOOL_NOT_FOUND,
    InvalidInputError,
    JsonRpcError,
    PermissionDeniedError,
    RateLimitedError,
    ToolNotFoundError,
)
from .logging_utils import log_response


def jsonrpc_error_response(
    *,
    request_id: Any,
    method: str | None,
    trace_id: str,
    start: float,
    log_code: str,
    rpc_error: JsonRpcError,
) -> dict:
    duration_ms = (time.time() - start) * 1000
    log_response(trace_id, method, "error", duration_ms, log_code)
    return {"jsonrpc": "2.0", "id": request_id, "error": rpc_error.to_dict()}


def exception_to_jsonrpc_response(
    exc: BaseException,
    *,
    request_id: Any,
    method: str | None,
    trace_id: str,
    start: float,
    params: dict,
) -> dict:
    if isinstance(exc, ToolNotFoundError):
        return jsonrpc_error_response(
            request_id=request_id,
            method=method,
            trace_id=trace_id,
            start=start,
            log_code="TOOL_NOT_FOUND",
            rpc_error=JsonRpcError(TOOL_NOT_FOUND, str(exc), {"tool_name": str(params.get("name"))}),
        )
    if isinstance(exc, RateLimitedError):
        return jsonrpc_error_response(
            request_id=request_id,
            method=method,
            trace_id=trace_id,
            start=start,
            log_code="RATE_LIMITED",
            rpc_error=JsonRpcError(RATE_LIMITED, str(exc)),
        )
    if isinstance(exc, PermissionDeniedError):
        return jsonrpc_error_response(
            request_id=request_id,
            method=method,
            trace_id=trace_id,
            start=start,
            log_code="PERMISSION_DENIED",
            rpc_error=JsonRpcError(PERMISSION_DENIED, str(exc)),
        )
    if isinstance(exc, InvalidInputError):
        return jsonrpc_error_response(
            request_id=request_id,
            method=method,
            trace_id=trace_id,
            start=start,
            log_code="INVALID_INPUT",
            rpc_error=JsonRpcError(INVALID_PARAMS, str(exc)),
        )
    if isinstance(exc, ValueError):
        return jsonrpc_error_response(
            request_id=request_id,
            method=method,
            trace_id=trace_id,
            start=start,
            log_code="METHOD_NOT_FOUND",
            rpc_error=JsonRpcError(METHOD_NOT_FOUND, str(exc)),
        )
    return jsonrpc_error_response(
        request_id=request_id,
        method=method,
        trace_id=trace_id,
        start=start,
        log_code="INTERNAL_ERROR",
        rpc_error=JsonRpcError(INTERNAL_ERROR, f"Internal error: {str(exc)}"),
    )
