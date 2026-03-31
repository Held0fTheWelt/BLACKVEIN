"""MCP enrichment client for calling operator endpoints."""

from typing import Protocol
import requests
from requests.exceptions import RequestException, Timeout


class MCPToolError(Exception):
    """Error from MCP tool call."""

    def __init__(self, tool_name: str, reason: str):
        """Initialize MCPToolError.

        Args:
            tool_name: Name of the tool that failed
            reason: Reason for failure (e.g., "timeout", "not_found", "http_error")
        """
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"MCP tool '{tool_name}' failed: {reason}")


class MCPEnrichmentClient(Protocol):
    """Protocol for MCP tool calling client."""

    def call_tool(
        self, tool_name: str, arguments: dict | None = None, *, timeout_seconds: float = 5.0
    ) -> dict:
        """Call a MCP tool and return result.

        Args:
            tool_name: Name of the tool to call
            arguments: Optional arguments dict
            timeout_seconds: Timeout for the call

        Returns:
            Tool result as dict

        Raises:
            MCPToolError: If tool call fails
        """
        ...


class OperatorEndpointClient:
    """HTTP client for operator endpoints (A1.3)."""

    # Tool name to endpoint path mapping
    _TOOL_MAP = {
        "wos.session.get": "/api/v1/sessions/{session_id}",
        "wos.session.state": "/api/v1/sessions/{session_id}/state",
        "wos.session.logs": "/api/v1/sessions/{session_id}/logs",
        "wos.session.diag": "/api/v1/sessions/{session_id}/diagnostics",
    }

    def __init__(self, base_url: str = "http://localhost:5000", token: str | None = None):
        """Initialize OperatorEndpointClient.

        Args:
            base_url: Base URL for operator endpoints
            token: Service token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _resolve_url(self, tool_name: str, session_id: str) -> str:
        """Resolve tool name to endpoint URL.

        Args:
            tool_name: Tool name (e.g., "wos.session.get")
            session_id: Session ID

        Returns:
            Full URL to endpoint

        Raises:
            MCPToolError: If tool is not recognized
        """
        if tool_name not in self._TOOL_MAP:
            raise MCPToolError(tool_name, "tool_not_found")

        path = self._TOOL_MAP[tool_name]
        path = path.replace("{session_id}", session_id)
        return f"{self.base_url}{path}"

    def call_tool(
        self, tool_name: str, arguments: dict | None = None, *, timeout_seconds: float = 5.0
    ) -> dict:
        """Call operator endpoint and return result.

        Args:
            tool_name: Tool name (must be in _TOOL_MAP)
            arguments: Arguments dict with at minimum "session_id"
            timeout_seconds: Timeout for the call

        Returns:
            Response data as dict

        Raises:
            MCPToolError: If call fails
        """
        arguments = arguments or {}
        session_id = arguments.get("session_id")

        if not session_id:
            raise MCPToolError(tool_name, "missing_session_id")

        try:
            url = self._resolve_url(tool_name, session_id)
        except MCPToolError:
            raise

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json()
        except Timeout:
            raise MCPToolError(tool_name, "timeout")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise MCPToolError(tool_name, "unauthorized")
            elif e.response.status_code == 404:
                raise MCPToolError(tool_name, "not_found")
            else:
                raise MCPToolError(tool_name, f"http_{e.response.status_code}")
        except RequestException as e:
            raise MCPToolError(tool_name, f"request_error: {str(e)}")
        except ValueError as e:
            raise MCPToolError(tool_name, f"invalid_json: {str(e)}")
