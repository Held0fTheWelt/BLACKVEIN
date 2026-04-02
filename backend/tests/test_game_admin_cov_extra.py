"""Extra game_admin_routes error branches."""
import pytest


def test_game_admin_get_experience_404(client, moderator_headers, monkeypatch):
    from app.services.game_content_service import GameContentNotFoundError

    def boom(_id, include_payload=True):
        raise GameContentNotFoundError("missing")

    monkeypatch.setattr("app.api.v1.game_admin_routes.get_experience", boom)
    r = client.get("/api/v1/game-admin/experiences/99999", headers=moderator_headers)
    assert r.status_code == 404


def test_game_admin_update_experience_404_message(client, moderator_headers, monkeypatch):
    def boom(*_a, **_kw):
        raise ValueError("Experience not found for update")

    monkeypatch.setattr("app.api.v1.game_admin_routes.update_experience", boom)
    r = client.put(
        "/api/v1/game-admin/experiences/1",
        json={"draft_payload": {"id": "x", "title": "T", "kind": "solo_story"}},
        headers=moderator_headers,
    )
    assert r.status_code == 404


def test_game_admin_publish_404(client, moderator_headers, monkeypatch):
    def boom(*_a, **_kw):
        raise ValueError("not found")

    monkeypatch.setattr("app.api.v1.game_admin_routes.publish_experience", boom)
    r = client.post("/api/v1/game-admin/experiences/1/publish", headers=moderator_headers)
    assert r.status_code == 404


def test_game_admin_runtime_detail_transcript_terminate_errors(client, moderator_headers, monkeypatch):
    from app.services.game_service import GameServiceError

    monkeypatch.setattr("app.api.v1.game_admin_routes.list_play_runs", lambda: [])
    monkeypatch.setattr(
        "app.api.v1.game_admin_routes.get_run_details",
        lambda _rid: (_ for _ in ()).throw(GameServiceError("e", status_code=502)),
    )
    assert client.get("/api/v1/game-admin/runtime/runs/r1", headers=moderator_headers).status_code == 502

    monkeypatch.setattr(
        "app.api.v1.game_admin_routes.get_run_transcript",
        lambda _rid: (_ for _ in ()).throw(GameServiceError("e", status_code=503)),
    )
    assert client.get("/api/v1/game-admin/runtime/runs/r1/transcript", headers=moderator_headers).status_code == 503

    monkeypatch.setattr(
        "app.api.v1.game_admin_routes.terminate_run",
        lambda *_a, **_kw: (_ for _ in ()).throw(GameServiceError("e", status_code=504)),
    )
    assert client.post("/api/v1/game-admin/runtime/runs/r1/terminate", json={}, headers=moderator_headers).status_code == 504
