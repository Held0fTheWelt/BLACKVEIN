"""
MCP Agent Interface - Safe wrapper for AI to call MCP tools.

This module provides a fail-closed interface for LangGraph agents to access
MCP tools without direct access to the MCP client. All calls are logged,
validated, and return dicts (never raise exceptions).

Constitutional Laws:
- Law 9: AI composition bounds - AI acts only through MCP tools
- Law 6: Fail closed on authority seams - unknown response → error dict
- Law 10: Runtime catastrophic failure - tool errors don't crash system
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MCPAgentInterface:
    """Safe MCP tool wrapper for AI agents.

    All tool calls:
    1. Validate input parameters
    2. Call MCP client
    3. Log call and result
    4. Return dict (success or error, never raise)

    Key guarantees:
    - No exceptions propagate to caller
    - All responses are dicts
    - Error responses include error field
    - Tool calls are auditable via diagnostics
    """

    def __init__(self, mcp_client: Optional[Any] = None):
        """Initialize MCP agent interface.

        Args:
            mcp_client: MCP client instance for tool calls
        """
        self.mcp_client = mcp_client
        self._call_history: List[Dict[str, Any]] = []
        self._error_count = 0
        self._success_count = 0

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with fail-closed error handling.

        Args:
            tool_name: Name of MCP tool (e.g., "session_get")
            params: Tool parameters dict

        Returns:
            Dict with success=bool and data/error field
        """
        try:
            if self.mcp_client is None:
                raise ValueError("MCP client not initialized")

            # Call tool
            result = self.mcp_client.call_tool(tool_name, params)

            # Validate response is dict
            if not isinstance(result, dict):
                return self._error_response(
                    f"Tool returned non-dict: {type(result).__name__}"
                )

            # Log successful call
            self._log_call(tool_name, params, result, success=True)
            self._success_count += 1

            # Return result directly (client already returns success/data structure)
            return result

        except ValueError as e:
            return self._handle_error(f"ValueError: {e}", tool_name, params)
        except ConnectionError as e:
            return self._handle_error(f"ConnectionError: {e}", tool_name, params)
        except TimeoutError as e:
            return self._handle_error(f"TimeoutError: {e}", tool_name, params)
        except TypeError as e:
            return self._handle_error(f"TypeError: {e}", tool_name, params)
        except Exception as e:
            return self._handle_error(f"Unexpected error: {e}", tool_name, params)

    def call_session_get(self, session_id: str) -> Dict[str, Any]:
        """Get session info.

        Args:
            session_id: Session identifier

        Returns:
            Dict with success and session data
        """
        return self.call_tool("session_get", {"session_id": session_id})

    def call_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current game state for session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with success and world/player state
        """
        return self.call_tool("session_state", {"session_id": session_id})

    def call_execute_turn(
        self,
        session_id: str,
        player_id: int,
        action: str
    ) -> Dict[str, Any]:
        """Execute a player action turn.

        Args:
            session_id: Session identifier
            player_id: Player identifier
            action: Action to execute

        Returns:
            Dict with success and turn result
        """
        return self.call_tool(
            "execute_turn",
            {
                "session_id": session_id,
                "player_id": player_id,
                "action": action
            }
        )

    def call_session_logs(self, session_id: str) -> Dict[str, Any]:
        """Get session logs.

        Args:
            session_id: Session identifier

        Returns:
            Dict with success and logs
        """
        return self.call_tool("session_logs", {"session_id": session_id})

    def call_session_diag(self, session_id: str) -> Dict[str, Any]:
        """Get session diagnostics.

        Args:
            session_id: Session identifier

        Returns:
            Dict with success and diagnostics
        """
        return self.call_tool("session_diag", {"session_id": session_id})

    def _handle_error(
        self,
        error_msg: str,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tool call error with logging and diagnostics.

        Args:
            error_msg: Error message
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Error response dict
        """
        self._log_call(tool_name, params, None, success=False, error=error_msg)
        self._error_count += 1
        return self._error_response(error_msg)

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create standardized error response.

        Args:
            error_msg: Error message

        Returns:
            Error response dict
        """
        return {
            "success": False,
            "error": error_msg
        }

    def _log_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log tool call for diagnostics.

        Args:
            tool_name: Tool name
            params: Tool parameters
            result: Tool result
            success: Whether call succeeded
            error: Error message (if any)
        """
        call_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "success": success,
            "error": error
        }
        self._call_history.append(call_record)

        # Log to application logger
        if success:
            logger.info(f"MCP tool call succeeded: {tool_name}")
        else:
            logger.warning(f"MCP tool call failed: {tool_name} - {error}")

    def get_diagnostics(self) -> Dict[str, Any]:
        """Get call diagnostics for this session.

        Returns:
            Dict with call history, counts, and metrics
        """
        return {
            "call_count": len(self._call_history),
            "success_count": self._success_count,
            "error_count": self._error_count,
            "call_history": self._call_history
        }

    def reset_diagnostics(self) -> None:
        """Reset call history and counters."""
        self._call_history = []
        self._error_count = 0
        self._success_count = 0
