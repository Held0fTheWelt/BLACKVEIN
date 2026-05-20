from __future__ import annotations

import os
from typing import Any

from ai_stack.actor_tracking import build_w5_projection_for_player_shell


def _w5_ast_frontend_player_view_enabled() -> bool:
    raw = (os.environ.get("W5_AST_FRONTEND_PLAYER_VIEW_ENABLED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _player_actor_id_from_projection(runtime_projection: dict[str, Any] | None) -> str | None:
    projection = runtime_projection if isinstance(runtime_projection, dict) else {}
    for key in ("human_actor_id", "selected_player_role", "player_actor_id", "viewer_actor_id"):
        value = str(projection.get(key) or "").strip()
        if value:
            return value
    return None


def _w5_player_view_location(view: dict[str, Any] | None) -> str | None:
    if not isinstance(view, dict):
        return None
    where = view.get("where_summary") if isinstance(view.get("where_summary"), dict) else {}
    for key in ("current_visible_location", "current_location"):
        value = str(where.get(key) or "").strip()
        if value:
            return value
    scene_location = where.get("scene_location")
    if isinstance(scene_location, dict):
        value = str(scene_location.get("value") or "").strip()
        if value:
            return value
    facts = where.get("facts") if isinstance(where.get("facts"), dict) else {}
    value = str(facts.get("scene_location") or "").strip()
    return value or None


def _w5_projection_has_inferred_why(view: dict[str, Any] | None) -> bool:
    if not isinstance(view, dict):
        return False
    truth = view.get("truth_attribution")
    if not isinstance(truth, dict):
        return False
    return any(path.startswith("why_summary.") and value == "inferred" for path, value in truth.items())


def _fallback_current_room_id(session: Any) -> str | None:
    runtime_world = session.runtime_world if isinstance(session.runtime_world, dict) else {}
    environment_state = session.environment_state if isinstance(session.environment_state, dict) else {}
    value = str(
        runtime_world.get("current_room_id")
        or environment_state.get("current_room_id")
        or environment_state.get("current_area")
        or ""
    ).strip()
    return value or None


def _maybe_build_w5_player_view_for_session(session: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not _w5_ast_frontend_player_view_enabled():
        return None, None
    player_actor_id = _player_actor_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    fallback_current_room_id = _fallback_current_room_id(session)
    try:
        if not isinstance(session.w5_latest_snapshot, dict):
            raise ValueError("missing_w5_latest_snapshot")
        projection = build_w5_projection_for_player_shell(
            session.w5_latest_snapshot,
            player_actor_id=player_actor_id,
        )
        view = projection.to_dict()
        location = _w5_player_view_location(view)
        used = bool(location)
        diagnostics = {
            "w5_player_view_used": used,
            "w5_player_view_failed": None if used else "missing_player_visible_location",
            "w5_snapshot_id": projection.where_summary.get("w5_snapshot_id")
            if isinstance(projection.where_summary, dict)
            else None,
            "w5_player_view_source": "w5_projection" if used else "fallback",
            "w5_player_view_has_how": bool(projection.how_summary.get("facts"))
            if isinstance(projection.how_summary, dict)
            else False,
            "w5_player_view_has_inferred_why": _w5_projection_has_inferred_why(view),
            "current_room_source": "w5_player_view" if used else "fallback_current_room",
            "fallback_current_room_id": fallback_current_room_id,
        }
        return view if used else None, diagnostics
    except Exception as exc:
        return None, {
            "w5_player_view_used": False,
            "w5_player_view_failed": str(exc),
            "w5_snapshot_id": None,
            "w5_player_view_source": "fallback",
            "w5_player_view_has_how": False,
            "w5_player_view_has_inferred_why": False,
            "current_room_source": "fallback_current_room",
            "fallback_current_room_id": fallback_current_room_id,
        }
