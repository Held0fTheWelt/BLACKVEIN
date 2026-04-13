"""Tests for world-engine control center aggregation endpoint."""

from __future__ import annotations

from app.api.v1 import world_engine_console_routes


def test_world_engine_control_center_snapshot(client, moderator_headers, monkeypatch):
    monkeypatch.setattr(
        world_engine_console_routes,
        "build_world_engine_control_center_snapshot",
        lambda app, trace_id=None: {
            "generated_at": "2026-04-14T00:00:00Z",
            "desired_play_service_state": {"mode": "remote"},
            "observed_play_service_state": {"health": "ok", "readiness": "ready"},
            "connectivity": {"backend_to_play_service_ready": {"status": "ready"}, "error": None},
            "active_runtime": {"run_count": 0, "session_count": 0, "runs": {"items": []}, "sessions": {"items": []}},
            "operator_controls": [{"id": "refresh", "path": "/api/v1/admin/world-engine/control-center"}],
            "status": {"control_plane_ok": True, "blocker_count": 0, "warning_count": 0},
            "blockers": [],
            "warnings": [],
        },
    )

    response = client.get("/api/v1/admin/world-engine/control-center", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"]["control_plane_ok"] is True
    assert payload["active_runtime"]["run_count"] == 0
    assert payload["operator_controls"][0]["id"] == "refresh"


def test_world_engine_control_center_live_payload_includes_operator_summary(client, moderator_headers):
    """Integration shape check (no stub): snapshot must expose a narrative operator_summary."""
    response = client.get("/api/v1/admin/world-engine/control-center", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert "operator_summary" in payload
    assert payload["operator_summary"].get("headline")
    assert isinstance(payload["operator_summary"].get("sub_lines"), list)
