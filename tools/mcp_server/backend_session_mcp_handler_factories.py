"""Factory functions for backend session MCP tool handlers (DS-008)."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from tools.mcp_server.backend_client import BackendClient
from tools.mcp_server.errors import JsonRpcError


def make_handle_system_health(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_system_health(arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            trace_id = str(uuid.uuid4())
            result = backend.health(trace_id=trace_id)
            return {"status": "healthy", "backend": result}
        except JsonRpcError as e:
            return {"status": "error", "message": e.message}

    return handle_system_health


def make_handle_session_create(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_create(arguments: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key in (
            "run_id",
            "template_id",
            "runtime_profile_id",
            "selected_player_role",
            "session_input_language",
            "session_output_language",
        ):
            if arguments.get(key) is not None:
                payload[key] = arguments.get(key)
        module_id = arguments.get("module_id")
        if module_id and not payload.get("runtime_profile_id") and not payload.get("template_id"):
            payload["runtime_profile_id"] = module_id
        if not any(payload.get(k) for k in ("run_id", "template_id", "runtime_profile_id")):
            return {"error": "run_id, template_id, runtime_profile_id, or module_id required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._post(
                f"{backend.base_url}/api/v1/game/player-sessions",
                trace_id,
                json=payload,
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}

    return handle_session_create


def _run_id_from_args(arguments: dict[str, Any]) -> str:
    return str(arguments.get("run_id") or arguments.get("session_id") or "").strip()


def _story_session_id_from_args(arguments: dict[str, Any]) -> str:
    return str(
        arguments.get("story_session_id")
        or arguments.get("runtime_session_id")
        or arguments.get("world_engine_story_session_id")
        or ""
    ).strip()


def make_handle_session_get(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_get(arguments: dict[str, Any]) -> dict[str, Any]:
        """Runtime-safe player-session snapshot (read-only, authority-respecting)."""
        run_id = _run_id_from_args(arguments)
        if not run_id:
            return {"error": "run_id or session_id required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._get(
                f"{backend.base_url}/api/v1/game/player-sessions/{run_id}",
                trace_id,
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_get failed: {str(e)}"}

    return handle_session_get


def make_handle_session_diag(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_diag(arguments: dict[str, Any]) -> dict[str, Any]:
        """Runtime-safe World-Engine story-session evidence."""
        run_id = _run_id_from_args(arguments)
        story_session_id = _story_session_id_from_args(arguments)
        if not story_session_id and run_id:
            try:
                trace_id = str(uuid.uuid4())
                snapshot = backend._get(
                    f"{backend.base_url}/api/v1/game/player-sessions/{run_id}",
                    trace_id,
                )
                story_session_id = str(snapshot.get("runtime_session_id") or "").strip()
            except JsonRpcError as e:
                return {"error": e.message}
        if not story_session_id:
            return {"error": "story_session_id/runtime_session_id or run_id required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._get(
                f"{backend.base_url}/api/v1/admin/ai-stack/session-evidence/{story_session_id}",
                trace_id,
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_diag failed: {str(e)}"}

    return handle_session_diag


def make_handle_session_logs(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_logs(arguments: dict[str, Any]) -> dict[str, Any]:
        """Player-session story entries (read-only, authority-respecting)."""
        run_id = _run_id_from_args(arguments)
        limit = arguments.get("limit", 100)
        if not run_id:
            return {"error": "run_id or session_id required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._get(
                f"{backend.base_url}/api/v1/game/player-sessions/{run_id}",
                trace_id,
            )
            try:
                lim = int(limit)
            except (TypeError, ValueError):
                lim = 100
            entries = result.get("story_entries") if isinstance(result.get("story_entries"), list) else []
            return {
                "run_id": result.get("run_id") or run_id,
                "runtime_session_id": result.get("runtime_session_id"),
                "history": entries[-lim:],
            }
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_logs failed: {str(e)}"}

    return handle_session_logs


def make_handle_session_state(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_state(arguments: dict[str, Any]) -> dict[str, Any]:
        """Player-session state snapshot from the canonical game route."""
        run_id = _run_id_from_args(arguments)
        if not run_id:
            return {"error": "run_id or session_id required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._get(
                f"{backend.base_url}/api/v1/game/player-sessions/{run_id}",
                trace_id,
            )
            return {
                "run_id": result.get("run_id") or run_id,
                "runtime_session_id": result.get("runtime_session_id"),
                "state": result.get("shell_state_view") or result.get("state") or {},
                "story_entries": result.get("story_entries") or [],
            }
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_state failed: {str(e)}"}

    return handle_session_state


def make_handle_session_execute_turn(backend: BackendClient) -> Callable[..., dict[str, Any]]:
    def handle_session_execute_turn(arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute turn through the canonical player-session route."""
        run_id = _run_id_from_args(arguments)
        player_input = (
            (arguments.get("player_input") or arguments.get("prompt") or arguments.get("input") or "")
            .strip()
        )
        if not run_id:
            return {"error": "run_id or session_id required"}
        if not player_input:
            return {"error": "player_input or prompt is required"}
        try:
            trace_id = str(uuid.uuid4())
            result = backend._post(
                f"{backend.base_url}/api/v1/game/player-sessions/{run_id}/turns",
                trace_id,
                json={"player_input": player_input},
            )
            return result
        except JsonRpcError as e:
            return {"error": e.message}
        except Exception as e:
            return {"error": f"session_execute_turn failed: {str(e)}"}

    return handle_session_execute_turn
