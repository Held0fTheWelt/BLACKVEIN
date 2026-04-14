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
from app.services.runtime_status_semantics import STATUS_SEMANTICS


def _utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _yn(value: object) -> str:
    return "yes" if value else "no"


def _posture_at_a_glance(desired: dict, observed: dict) -> dict[str, list[str]]:
    """Operator-facing lines without echoing raw URLs or secrets."""
    desired_lines: list[str] = []
    if not desired:
        desired_lines.append("No desired document loaded; check Play-Service control.")
    else:
        desired_lines.append(
            f"Mode {desired.get('mode', '?')} · operator enabled flag: {_yn(desired.get('enabled'))}"
        )
        pub = (desired.get("public_url") or "").strip()
        inn = (desired.get("internal_url") or "").strip()
        desired_lines.append(f"Public URL: {'set' if pub else 'missing'} · internal URL: {'set' if inn else 'missing'}")
        desired_lines.append(
            f"Shared secret (env layer): {'present' if desired.get('shared_secret_present') else 'missing'} · "
            f"internal API key hint: {'present' if desired.get('internal_api_key_present') else 'missing'}"
        )
        desired_lines.append(f"Allow new sessions (desired): {_yn(desired.get('allow_new_sessions', True))}")

    observed_lines: list[str] = [
        f"Config complete at app layer: {_yn(observed.get('config_complete'))}",
        f"Effective mode: {observed.get('effective_mode', '?')} · effective enabled: {_yn(observed.get('effective_enabled'))}",
        f"Health probe: {observed.get('health', '?')} · readiness probe: {observed.get('readiness', '?')}",
        f"Allow new sessions (effective): {_yn(observed.get('allow_new_sessions_effective'))}",
        f"Shared secret present: {_yn(observed.get('shared_secret_present'))} · internal API key present: {_yn(observed.get('internal_api_key_present'))}",
    ]
    return {"desired_lines": desired_lines, "observed_lines": observed_lines}


DRILL_DOWN_PAGES: list[dict[str, str]] = [
    {
        "label": "Play-Service control",
        "path": "/manage/play-service-control",
        "hint": "Set internal/public URLs, align shared secret, then test and apply.",
    },
    {
        "label": "World Engine console",
        "path": "/manage/world-engine-console",
        "hint": "Per-run and per-session detail; terminate a run when you have operate/author rights.",
    },
    {
        "label": "System diagnosis",
        "path": "/manage/diagnosis",
        "hint": "Aggregated cross-service health (read-only from the browser).",
    },
    {
        "label": "AI Runtime Governance",
        "path": "/manage/ai-runtime-governance",
        "hint": "Canonical governed providers, models, routes, runtime modes, and readiness.",
    },
]


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
                "suggested_action": "Open **Play-Service control**, set the internal URL and shared secret, then **Test** and **Apply** the desired configuration.",
            }
        )
    if observed.get("health") not in {"ok", "ready"}:
        warnings.append(
            {
                "code": "play_service_health_not_ok",
                "message": f"Observed play-service health is '{observed.get('health', 'unknown')}'.",
                "suggested_action": "Compare desired vs observed posture, then run **Test desired config** (or fix the play service process) before applying changes.",
            }
        )
    if observed.get("readiness") != "ready":
        warnings.append(
            {
                "code": "play_service_readiness_not_ready",
                "message": f"Observed play-service readiness is '{observed.get('readiness', 'unknown')}'.",
                "suggested_action": "Check connectivity JSON below, confirm the engine is up, and re-test from **Play-Service control**.",
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
                "suggested_action": "Verify the play service is running, URLs match **Play-Service control**, and shared secrets are aligned, then use **Test desired config** above.",
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
                "suggested_action": "Open **World Engine console** once connectivity is healthy — run listing uses the same backend proxy path.",
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
                "suggested_action": "Retry after play-service health is green; use **World Engine console** for session-level detail when listing works.",
            }
        )

    control_plane_ok = not blockers
    state = "healthy"
    if blockers:
        state = "blocked"
    elif warnings:
        state = "degraded"
    headline = (
        "Play-service control plane looks healthy from the backend perspective."
        if control_plane_ok
        else "Play-service control plane has blocking issues that need configuration or connectivity fixes."
    )
    sub_lines: list[str] = []
    if observed.get("config_complete"):
        sub_lines.append("Observed configuration is complete (URLs and secrets present at the application layer).")
    else:
        sub_lines.append("Observed configuration is incomplete — finish Play-Service control inputs before expecting healthy runs.")
    if ready_probe_error is None and ready_probe:
        sub_lines.append("Backend successfully reached the play-service ready probe.")
    elif ready_probe_error:
        sub_lines.append("Backend could not complete the ready probe — see blockers.")

    posture_at_a_glance = _posture_at_a_glance(desired, observed)

    return {
        "generated_at": _utc_iso(),
        "desired_play_service_state": desired,
        "observed_play_service_state": observed,
        "posture_at_a_glance": posture_at_a_glance,
        "drill_down": list(DRILL_DOWN_PAGES),
        "operator_summary": {
            "headline": headline,
            "sub_lines": sub_lines,
            "deep_dive_hint": "Use **World Engine console** for per-run termination and session drill-down; use **Diagnosis** for cross-service health; use **AI Runtime Governance** for provider/model/route readiness.",
        },
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
            {
                "id": "refresh",
                "label": "Refresh control center",
                "method": "GET",
                "path": "/api/v1/admin/world-engine/control-center",
                "ui_surface": "control_center_refresh_button",
            },
            {
                "id": "test_play_service",
                "label": "Test play-service desired configuration",
                "method": "POST",
                "path": "/api/v1/admin/play-service-control/test",
                "ui_surface": "control_center_test_button",
            },
            {
                "id": "apply_play_service",
                "label": "Apply desired play-service configuration",
                "method": "POST",
                "path": "/api/v1/admin/play-service-control/apply",
                "ui_surface": "control_center_apply_button",
            },
            {
                "id": "terminate_run",
                "label": "Terminate selected run",
                "method": "POST",
                "path": "/api/v1/admin/world-engine/runs/<run_id>/terminate",
                "requires_path_parameter": "run_id",
                "ui_surface": "world_engine_console",
                "note": "Requires a concrete run id; invoke from World Engine console after selecting a run.",
            },
        ],
        "status": {
            "state": state,
            "control_plane_ok": control_plane_ok,
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "status_semantics": STATUS_SEMANTICS,
        "blockers": blockers,
        "warnings": warnings,
    }
