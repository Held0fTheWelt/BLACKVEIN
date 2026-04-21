"""
Turn execution decorator that integrates AI reasoning with player routes.

Wraps player turn routes to:
- Check if AI is enabled for player
- Run orchestrator before/after turn execution
- Collect reasoning diagnostics
- Gracefully fallback on AI failure (Law 6: fail-closed)
- Never break the core turn execution (Law 10: degraded-safe)

Constitutional Laws:
- Law 6: Fail closed - AI errors don't break turns
- Law 10: Catastrophic failure - AI failures are handled gracefully
"""

from functools import wraps
from typing import Callable, Any, Dict, Optional
import logging
from datetime import datetime, timezone

from ai_stack.langgraph_orchestrator import GameOrchestrator
from ai_stack.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

logger = logging.getLogger(__name__)


class AIReasoningDiagnostics:
    """Diagnostics collected during AI reasoning."""

    def __init__(self):
        """Initialize diagnostics."""
        self.ai_enabled = False
        self.reasoning_started_at = None
        self.reasoning_duration_ms = None
        self.reasoning_error = None
        self.reasoning_degraded = False
        self.pre_turn_state = None
        self.post_turn_state = None
        self.decision_made = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostics to dict."""
        return {
            "ai_enabled": self.ai_enabled,
            "reasoning_started_at": self.reasoning_started_at.isoformat() if self.reasoning_started_at else None,
            "reasoning_duration_ms": self.reasoning_duration_ms,
            "reasoning_error": self.reasoning_error,
            "reasoning_degraded": self.reasoning_degraded,
            "decision_made": self.decision_made
        }


class WithAIReasoning:
    """Decorator to wrap turn execution with AI reasoning."""

    def __init__(
        self,
        mcp_interface: Optional[MCPAgentInterface] = None,
        prompt_catalog: Optional[CanonicalPromptCatalog] = None,
        enabled_by_default: bool = False
    ):
        """
        Initialize AI reasoning decorator.

        Args:
            mcp_interface: MCP interface for orchestrator (optional)
            prompt_catalog: Canonical prompt catalog (optional)
            enabled_by_default: Whether AI is enabled by default
        """
        self.mcp_interface = mcp_interface
        self.prompt_catalog = prompt_catalog or CanonicalPromptCatalog()
        self.enabled_by_default = enabled_by_default
        self._orchestrator = None
        self._player_ai_config = {}  # player_id -> ai_enabled

    def set_player_ai_enabled(self, player_id: str, enabled: bool):
        """Enable/disable AI for specific player."""
        self._player_ai_config[player_id] = enabled

    def is_ai_enabled(self, player_id: str) -> bool:
        """Check if AI is enabled for player."""
        return self._player_ai_config.get(player_id, self.enabled_by_default)

    def _get_orchestrator(self) -> Optional[GameOrchestrator]:
        """Get or create orchestrator."""
        if self.mcp_interface is None:
            return None

        if self._orchestrator is None:
            self._orchestrator = GameOrchestrator(self.mcp_interface, self.prompt_catalog)

        return self._orchestrator

    def __call__(self, route_func: Callable) -> Callable:
        """
        Decorate a route function with AI reasoning.

        Args:
            route_func: Flask route function

        Returns:
            Wrapped function
        """
        @wraps(route_func)
        def wrapper(*args, **kwargs) -> Any:
            """Wrapper that injects AI reasoning."""
            diagnostics = AIReasoningDiagnostics()

            try:
                # Get player_id from kwargs or function context
                # This assumes the route has access to player_id
                player_id = kwargs.get("player_id")
                session_id = kwargs.get("session_id")

                # Check if AI is enabled
                if player_id:
                    diagnostics.ai_enabled = self.is_ai_enabled(player_id)

                # Run AI reasoning before turn (if enabled)
                if diagnostics.ai_enabled and player_id and session_id:
                    diagnostics.reasoning_started_at = datetime.now(timezone.utc)

                    try:
                        orchestrator = self._get_orchestrator()
                        if orchestrator:
                            # Run reasoning on current state
                            # Convert player_id to int if it's numeric
                            try:
                                player_id_int = int(player_id)
                            except (ValueError, TypeError):
                                player_id_int = hash(player_id) % 10000000

                            ai_state = orchestrator.run(session_id, player_id_int)
                            diagnostics.reasoning_degraded = ai_state.is_degraded
                            diagnostics.decision_made = ai_state.action_selected
                        else:
                            # No orchestrator available
                            diagnostics.reasoning_error = "Orchestrator not configured"

                    except Exception as e:
                        # Law 6: Fail closed - capture error but don't break
                        logger.warning(
                            f"AI reasoning failed for player {player_id}: {str(e)}"
                        )
                        diagnostics.reasoning_error = str(e)
                        diagnostics.reasoning_degraded = True

                    finally:
                        # Record duration
                        if diagnostics.reasoning_started_at:
                            duration = datetime.now(timezone.utc) - diagnostics.reasoning_started_at
                            diagnostics.reasoning_duration_ms = int(duration.total_seconds() * 1000)

                # Execute the original route function
                # Law 10: Never break core turn execution
                result = route_func(*args, **kwargs)

                # If result is a tuple (response, status_code), inject diagnostics
                if isinstance(result, tuple) and len(result) >= 2:
                    response_data, status_code = result[0], result[1]
                    if isinstance(response_data, dict):
                        response_data["ai_diagnostics"] = diagnostics.to_dict()
                    return (response_data, status_code) + result[2:]
                else:
                    # Single response object (shouldn't happen in Flask routes)
                    return result

            except Exception as e:
                # Law 6: Fail closed - always return to original function
                logger.error(
                    f"Decorator error: {str(e)}",
                    exc_info=True
                )
                # Call original function without AI
                return route_func(*args, **kwargs)

        return wrapper


# Module-level decorator instance
_ai_reasoning_decorator = WithAIReasoning()


def with_ai_reasoning(route_func: Callable) -> Callable:
    """
    Decorator to wrap turn execution with AI reasoning.

    Usage:
        @api_v1_bp.route("/player/execute_action", methods=["POST"])
        @with_ai_reasoning
        def execute_action():
            ...

    Features:
    - Checks if AI enabled for player
    - Runs orchestrator before/after turn
    - Collects diagnostics
    - Gracefully falls back on AI failure
    - Never breaks core turn execution

    Constitutional Laws:
    - Law 6: Fail closed on AI errors
    - Law 10: Degraded-safe on catastrophic failure
    """
    return _ai_reasoning_decorator(route_func)


def set_orchestrator(mcp_interface: MCPAgentInterface, catalog: CanonicalPromptCatalog):
    """Configure orchestrator for AI reasoning."""
    global _ai_reasoning_decorator
    _ai_reasoning_decorator = WithAIReasoning(mcp_interface, catalog)


def enable_ai_for_player(player_id: str):
    """Enable AI for specific player."""
    _ai_reasoning_decorator.set_player_ai_enabled(player_id, True)


def disable_ai_for_player(player_id: str):
    """Disable AI for specific player."""
    _ai_reasoning_decorator.set_player_ai_enabled(player_id, False)


def is_ai_enabled_for_player(player_id: str) -> bool:
    """Check if AI is enabled for player."""
    return _ai_reasoning_decorator.is_ai_enabled(player_id)
