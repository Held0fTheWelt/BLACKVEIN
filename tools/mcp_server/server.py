"""MCP server: JSON-RPC main loop, dispatch, rate limiting."""

import json
import sys
import time
from typing import Any, Optional

from .errors import (
    JsonRpcError,
    TOOL_NOT_FOUND,
    RATE_LIMITED,
    PERMISSION_DENIED,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    INTERNAL_ERROR,
    ToolNotFoundError,
    RateLimitedError,
    PermissionDeniedError,
    InvalidInputError,
)
from ai_stack.mcp_canonical_surface import (
    McpToolClass,
    operating_profile_allows_write_capable,
    resolve_active_mcp_suite_filter,
    resolve_mcp_operating_profile,
)

from .backend_client import BackendClient
from .config import Config
from .fs_tools import FileSystemTools
from .logging_utils import generate_trace_id, log_request, log_response, log_tool_call
from .rate_limiter import RateLimiter
from .resource_prompt_support import (
    McpResourceReader,
    get_prompt_messages,
    list_prompt_descriptors,
    list_resource_descriptors,
)
from .tools_registry import create_default_registry


class McpServer:
    """JSON-RPC 2.0 MCP server."""

    def __init__(self) -> None:
        self._suite_filter = resolve_active_mcp_suite_filter()
        config = Config()
        self._backend = BackendClient(base_url=config.backend_url, bearer_token=config.bearer_token)
        self._fs = FileSystemTools(config)
        self.registry = create_default_registry(
            suite_filter=self._suite_filter,
            backend=self._backend,
            fs=self._fs,
        )
        self._resource_reader = McpResourceReader(self._backend, self._fs)
        self.rate_limiter = RateLimiter(max_calls=30, window_seconds=60)

    def validate_input(self, tool: Any, arguments: dict) -> None:
        """Simple JSON schema validation."""
        schema = tool.input_schema
        if schema.get("type") == "object":
            required = schema.get("required", [])
            for field in required:
                if field not in arguments:
                    raise InvalidInputError(f"Missing required field: {field}")

    def handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list request."""
        return {"tools": self.registry.list_tools()}

    def handle_tools_call(self, params: dict, trace_id: str) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            raise InvalidInputError("Missing 'name' parameter")

        tool = self.registry.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        profile = resolve_mcp_operating_profile()
        if tool.tool_class == McpToolClass.write_capable and not operating_profile_allows_write_capable(
            profile
        ):
            raise PermissionDeniedError(
                f"Tool {tool_name} is write_capable; denied under operating profile {profile.value}"
            )

        # Validate input
        self.validate_input(tool, arguments)

        # Call handler
        start = time.time()
        audit_kw = dict(
            tool_class=tool.tool_class.value,
            authority_source=tool.authority_source,
            operating_profile=profile.value,
        )
        try:
            result = tool.handler(arguments)
            duration_ms = (time.time() - start) * 1000
            log_tool_call(trace_id, tool_name, duration_ms, "success", **audit_kw)
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            log_tool_call(trace_id, tool_name, duration_ms, "error", "TOOL_ERROR", **audit_kw)
            raise

    def handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        suite_meta = "all" if self._suite_filter is None else self._suite_filter.value
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "wos-mcp-server",
                "version": "0.1.0",
                "wos_mcp_suite": suite_meta,
            },
        }

    def handle_resources_list(self, params: dict) -> dict:
        return {"resources": list_resource_descriptors(self._suite_filter)}

    def handle_resources_read(self, params: dict, trace_id: str) -> dict:
        uri = params.get("uri")
        if not uri or not isinstance(uri, str):
            raise InvalidInputError("Missing or invalid 'uri' for resources/read")
        try:
            mime, text = self._resource_reader.read(uri.strip(), trace_id)
        except ValueError as exc:
            raise InvalidInputError(str(exc)) from exc
        return {"contents": [{"uri": uri, "mimeType": mime, "text": text}]}

    def handle_prompts_list(self, params: dict) -> dict:
        return {"prompts": list_prompt_descriptors(self._suite_filter)}

    def handle_prompts_get(self, params: dict) -> dict:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise InvalidInputError("Missing or invalid 'name' for prompts/get")
        body = get_prompt_messages(name.strip(), self._suite_filter)
        if body is None:
            raise ToolNotFoundError(f"Prompt not found: {name}")
        return body

    def dispatch(self, request: dict, trace_id: str) -> dict:
        """Dispatch JSON-RPC request to handler."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        start = time.time()
        log_request(trace_id, method, params)

        try:
            # Check rate limit
            if not self.rate_limiter.is_allowed(trace_id):
                raise RateLimitedError("Rate limit exceeded (30 calls/min)")

            # Dispatch
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params, trace_id)
            elif method == "resources/list":
                result = self.handle_resources_list(params)
            elif method == "resources/read":
                result = self.handle_resources_read(params, trace_id)
            elif method == "prompts/list":
                result = self.handle_prompts_list(params)
            elif method == "prompts/get":
                result = self.handle_prompts_get(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "success", duration_ms)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }

        except ToolNotFoundError as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "TOOL_NOT_FOUND")
            error = JsonRpcError(TOOL_NOT_FOUND, str(e), {"tool_name": str(params.get("name"))})
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except RateLimitedError as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "RATE_LIMITED")
            error = JsonRpcError(RATE_LIMITED, str(e))
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except PermissionDeniedError as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "PERMISSION_DENIED")
            error = JsonRpcError(PERMISSION_DENIED, str(e))
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except InvalidInputError as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "INVALID_INPUT")
            error = JsonRpcError(INVALID_PARAMS, str(e))
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except ValueError as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "METHOD_NOT_FOUND")
            error = JsonRpcError(METHOD_NOT_FOUND, str(e))
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            log_response(trace_id, method, "error", duration_ms, "INTERNAL_ERROR")
            error = JsonRpcError(INTERNAL_ERROR, f"Internal error: {str(e)}")
            return {"jsonrpc": "2.0", "id": request_id, "error": error.to_dict()}

    def run(self) -> None:
        """Main REPL: read JSON-RPC from stdin, write response to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                trace_id = request.get("trace_id") or generate_trace_id()
                response = self.dispatch(request, trace_id)
                print(json.dumps(response))
            except json.JSONDecodeError as e:
                error = JsonRpcError(-32700, f"Parse error: {str(e)}")
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": error.to_dict()}))


if __name__ == "__main__":
    server = McpServer()
    server.run()
