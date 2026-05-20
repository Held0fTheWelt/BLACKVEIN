"""MCP handlers for backend health and canonical player-session HTTP mirrors."""

from __future__ import annotations

from typing import Any, Callable

from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.backend_session_mcp_handler_factories import (
    make_handle_session_create,
    make_handle_session_diag,
    make_handle_session_execute_turn,
    make_handle_session_get,
    make_handle_session_logs,
    make_handle_session_state,
    make_handle_system_health,
)


def build_backend_session_mcp_handlers(
    backend: BackendClient,
) -> dict[str, Callable[..., dict[str, Any]]]:
    return {
        "wos.system.health": make_handle_system_health(backend),
        "wos.session.create": make_handle_session_create(backend),
        "wos.session.get": make_handle_session_get(backend),
        "wos.session.logs": make_handle_session_logs(backend),
        "wos.session.state": make_handle_session_state(backend),
        "wos.session.execute_turn": make_handle_session_execute_turn(backend),
        "wos.session.diag": make_handle_session_diag(backend),
    }
