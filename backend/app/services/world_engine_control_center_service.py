"""World-Engine Control Center aggregation for administration operations."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask

from app.services.game_service import (
    GameServiceError,
    get_play_service_ready,
    list_runs,
    list_story_sessions,
)
from app.services.play_service_control_service import get_control_payload


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_world_engine_control_center_snapshot(app: Flask, *, trace_id: str | None = None) -> dict:
    """Build one coherent operational snapshot for the control center page."""
    control_payload = get_control_payload(app)
    desired = control_payload.get("desired_state") or {}
    observed = control_payload.get("observed_state") or {}

    blockers: list[dict] = []
    warnings: list[dict] = []

    if not observed.get("config_complete"):
        blockers.append(
            {
                "code": "play_service_config_incomplete",
                "message": "Play-service integration is not fully configured (URL and/or shared secret missing).",
            }
        )
    if observed.get("health") not in {"ok", "ready"}:
        warnings.append(
            {
                "code": "play_service_health_not_ok",
                "message": f"Observed play-service health is '{observed.get('health', 'unknown')}'.",
            }
        )
    if observed.get("readiness") != "ready":
        warnings.append(
            {
                "code": "play_service_readiness_not_ready",
                "message": f"Observed play-service readiness is '{observed.get('readiness', 'unknown')}'.",
            }
        )

    ready_probe: dict = {}
    ready_probe_error: dict | None = None
    try:
        ready_probe = get_play_service_ready(trace_id=trace_id)
    except GameServiceError as exc:
        ready_probe_error = {"message": str(exc), "status_code": exc.status_code}
        blockers.append(
            {
                "code": "backend_to_play_service_connectivity_failed",
                "message": f"Backend could not retrieve play-service ready state: {exc}",
            }
        )

    runs_payload: dict = {"items": []}
    runs_error: dict | None = None
    try:
        runs_payload = {"items": list_runs()}
    except GameServiceError as exc:
        runs_error = {"message": str(exc), "status_code": exc.status_code}
        warnings.append(
            {
                "code": "runs_listing_unavailable",
                "message": f"Run listing failed: {exc}",
            }
        )

    sessions_payload: dict = {"items": []}
    sessions_error: dict | None = None
    try:
        sessions_payload = list_story_sessions(trace_id=trace_id)
    except GameServiceError as exc:
        sessions_error = {"message": str(exc), "status_code": exc.status_code}
        warnings.append(
            {
                "code": "session_listing_unavailable",
                "message": f"Story-session listing failed: {exc}",
            }
        )

    return {
        "generated_at": _utc_iso(),
        "desired_play_service_state": desired,
        "observed_play_service_state": observed,
        "connectivity": {
            "backend_to_play_service_ready": ready_probe,
            "error": ready_probe_error,
        },
        "active_runtime": {
            "runs": runs_payload,
            "sessions": sessions_payload,
            "runs_error": runs_error,
            "sessions_error": sessions_error,
            "run_count": len(runs_payload.get("items") or []),
            "session_count": len(sessions_payload.get("items") or []),
        },
        "operator_controls": [
            {"id": "refresh", "label": "Refresh control center", "method": "GET", "path": "/api/v1/admin/world-engine/control-center"},
            {"id": "test_play_service", "label": "Test play-service desired configuration", "method": "POST", "path": "/api/v1/admin/play-service-control/test"},
            {"id": "apply_play_service", "label": "Apply desired play-service configuration", "method": "POST", "path": "/api/v1/admin/play-service-control/apply"},
            {"id": "terminate_run", "label": "Terminate selected run", "method": "POST", "path": "/api/v1/admin/world-engine/runs/<run_id>/terminate"},
        ],
        "status": {
            "control_plane_ok": not blockers,
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "blockers": blockers,
        "warnings": warnings,
    }
