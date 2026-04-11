"""Tests for World Engine console admin proxy (JWT + hierarchical feature flags)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def _patch_game_service_ok(monkeypatch):
    import app.api.v1.world_engine_console_routes as we

    def fake_ready(**_kw):
        return {"status": "ready", "run_count": 0}

    def fake_list_runs():
        return [{"id": "run-1"}]

    def fake_list_story(**_kw):
        return {"items": [{"session_id": "s1", "module_id": "m1"}], "total": 1}

    monkeypatch.setattr(we, "get_play_service_ready", fake_ready)
    monkeypatch.setattr(we, "list_runs", fake_list_runs)
    monkeypatch.setattr(we, "list_story_sessions", fake_list_story)
    monkeypatch.setattr(we, "list_templates", lambda: [])
    monkeypatch.setattr(
        we,
        "get_run_details",
        lambda rid: {"run": {"id": rid}, "template": {}, "template_source": "x", "store": {}},
    )
    monkeypatch.setattr(we, "get_run_transcript", lambda rid: {"run_id": rid, "entries": []})
    monkeypatch.setattr(we, "terminate_run", lambda *a, **k: {"terminated": True, "run_id": "r", "template_id": "t", "actor_display_name": "", "reason": ""})
    monkeypatch.setattr(we, "get_story_state", lambda sid, **k: {"session_id": sid})
    monkeypatch.setattr(we, "get_story_diagnostics", lambda sid, **k: {"session_id": sid, "diagnostics": []})
    monkeypatch.setattr(
        we,
        "create_story_session",
        lambda **k: {"session_id": "new", "module_id": k["module_id"], "turn_counter": 0, "current_scene_id": "", "warnings": []},
    )
    monkeypatch.setattr(we, "execute_story_turn", lambda **k: {"session_id": k["session_id"], "turn": {}})


def test_world_engine_health_requires_auth(client):
    r = client.get("/api/v1/admin/world-engine/health")
    assert r.status_code == 401


def test_world_engine_health_forbidden_without_feature(client, moderator_headers, monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(fr, "user_can_access_world_engine_capability", lambda u, c: False)
    r = client.get("/api/v1/admin/world-engine/health", headers=moderator_headers)
    assert r.status_code == 403


def test_world_engine_health_ok(client, moderator_headers, _patch_game_service_ok, monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(fr, "user_can_access_world_engine_capability", lambda u, c: c == "observe")
    r = client.get("/api/v1/admin/world-engine/health", headers=moderator_headers)
    assert r.status_code == 200
    assert r.get_json().get("status") == "ready"


def test_story_sessions_list_ok(client, moderator_headers, _patch_game_service_ok, monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(fr, "user_can_access_world_engine_capability", lambda u, c: c == "observe")
    r = client.get("/api/v1/admin/world-engine/story/sessions", headers=moderator_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 1


def test_story_turn_requires_author(client, moderator_headers, _patch_game_service_ok, monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(
        fr,
        "user_can_access_world_engine_capability",
        lambda u, c: c == "observe",
    )
    r = client.post(
        "/api/v1/admin/world-engine/story/sessions/s1/turns",
        headers=moderator_headers,
        json={"player_input": "hello"},
    )
    assert r.status_code == 403

    monkeypatch.setattr(
        fr,
        "user_can_access_world_engine_capability",
        lambda u, c: c == "author",
    )
    r2 = client.post(
        "/api/v1/admin/world-engine/story/sessions/s1/turns",
        headers=moderator_headers,
        json={"player_input": "hello"},
    )
    assert r2.status_code == 200
