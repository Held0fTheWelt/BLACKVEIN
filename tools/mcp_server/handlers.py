"""Tool handlers for MCP surface."""

from typing import Dict, Any


def session_get_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wos.session.get tool call."""
    session_id = input_data.get("session_id")
    if not session_id:
        raise ValueError("session_id required")

    # This would call backend.session_service.get_session(session_id)
    # For now, return placeholder
    return {
        "session_id": session_id,
        "state": {},
        "turn_number": 0,
        "created_at": "2026-04-20T14:00:00Z"
    }


def session_state_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wos.session.state tool call."""
    session_id = input_data.get("session_id")
    if not session_id:
        raise ValueError("session_id required")

    return {
        "state": {},
        "version": 0
    }


def session_logs_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wos.session.logs tool call."""
    session_id = input_data.get("session_id")
    limit = input_data.get("limit", 10)

    if not session_id:
        raise ValueError("session_id required")

    return {
        "history": []
    }


def session_diag_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wos.session.diag tool call."""
    session_id = input_data.get("session_id")

    if not session_id:
        raise ValueError("session_id required")

    return {
        "diagnostics": {},
        "errors": [],
        "degraded": False
    }


def session_execute_turn_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wos.session.execute_turn tool call."""
    session_id = input_data.get("session_id")
    player_id = input_data.get("player_id")
    action = input_data.get("action")

    if not session_id or not player_id or not action:
        raise ValueError("session_id, player_id, and action required")

    # This would call world_engine.turn_executor.execute_turn()
    return {
        "success": True,
        "new_turn_number": 1,
        "state_delta": {}
    }
