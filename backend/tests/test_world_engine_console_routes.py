"""Tests for World Engine console admin proxy (JWT + hierarchical feature flags)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.observability


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
        "get_story_w5_snapshot",
        lambda sid, **k: {
            "status": "ok",
            "snapshot_id": "w5s_route",
            "stats": {"actor_count": 1, "has_how": True, "has_inferred_why": True},
            "actor_summaries": {"michel": {"actor_type": "npc"}},
            "raw_w5_history_exposed": False,
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        we,
        "get_story_w5_actor",
        lambda sid, actor_id, **k: {
            "status": "ok",
            "actor_id": actor_id,
            "dimensions": {
                "who": {"actor_id": actor_id},
                "where": {"facts": [{"key": "scene_location", "value": "study"}]},
                "what": {"facts": [{"key": "current_action", "value": "listens"}]},
                "how": {"facts": [{"key": "tone", "value": "dry"}]},
                "why": {"facts": [{"key": "motive", "truth_label": "soft_inferred"}]},
            },
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        we,
        "get_story_w5_conflicts",
        lambda sid, **k: {
            "status": "ok",
            "unresolved_count": 1,
            "conflicts": [{"conflict_id": "c1", "resolution_status": "unresolved"}],
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        we,
        "get_story_w5_narrator_projection",
        lambda sid, **k: {
            "status": "ok",
            "projection": {"target_consumer": "narrator", "how_summary": {"facts": {"tone": "dry"}}},
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        we,
        "get_story_w5_npc_projection",
        lambda sid, actor_id, **k: {
            "status": "ok",
            "actor_id": actor_id,
            "projection": {"target_consumer": "npc", "actor_id": actor_id},
            "read_only": True,
        },
    )
    monkeypatch.setattr(
        we,
        "get_story_w5_validation",
        lambda sid, **k: {
            "status": "ok",
            "validation": {"w5_validation_enabled": False, "w5_validation_failure_codes": []},
            "read_only": True,
        },
    )
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


def test_w5_admin_routes_are_observe_only_and_read_only(client, moderator_headers, _patch_game_service_ok, monkeypatch):
    from app.auth import feature_registry as fr

    monkeypatch.setattr(fr, "user_can_access_world_engine_capability", lambda u, c: c == "observe")

    snapshot = client.get("/api/v1/admin/w5/s1/snapshot", headers=moderator_headers)
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.get_json()
    assert snapshot_payload["snapshot_id"] == "w5s_route"
    assert snapshot_payload["stats"]["has_how"] is True
    assert snapshot_payload["raw_w5_history_exposed"] is False
    assert snapshot_payload["read_only"] is True

    actor = client.get("/api/v1/admin/w5/s1/actor/michel", headers=moderator_headers)
    assert actor.status_code == 200
    actor_payload = actor.get_json()
    assert actor_payload["dimensions"]["where"]["facts"][0]["value"] == "study"
    assert actor_payload["dimensions"]["how"]["facts"][0]["value"] == "dry"
    assert actor_payload["dimensions"]["why"]["facts"][0]["truth_label"] == "soft_inferred"

    narrator = client.get("/api/v1/admin/w5/s1/narrator-projection", headers=moderator_headers)
    assert narrator.status_code == 200
    assert narrator.get_json()["projection"]["target_consumer"] == "narrator"

    npc = client.get("/api/v1/admin/w5/s1/npc-projection/michel", headers=moderator_headers)
    assert npc.status_code == 200
    assert npc.get_json()["projection"]["actor_id"] == "michel"

    validation = client.get("/api/v1/admin/w5/s1/validation", headers=moderator_headers)
    assert validation.status_code == 200
    assert validation.get_json()["validation"]["w5_validation_enabled"] is False
