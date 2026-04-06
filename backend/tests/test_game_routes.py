import pytest

from app.extensions import db
from app.models import GameCharacter, GameExperienceTemplate, GameSaveSlot
from app.services.game_service import PlayJoinContext


def test_game_menu_compat_returns_410_without_frontend_url(client, app):
    app.config["FRONTEND_URL"] = None
    response = client.get("/game-menu")
    assert response.status_code == 410
    assert response.get_json()["error"] == "Legacy UI route disabled."


def test_game_menu_compat_redirects_when_frontend_url_set(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/game-menu", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/game-menu"



def test_game_templates_requires_auth(client):
    response = client.get("/api/v1/game/templates")
    assert response.status_code == 401
    assert "error" in response.get_json()



def test_game_bootstrap_returns_templates_runs_characters_and_save_slots(client, auth_headers, test_user, app, monkeypatch):
    user, _ = test_user
    app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
    app.config["PLAY_SERVICE_INTERNAL_URL"] = "https://play.example.com"
    with app.app_context():
        character = GameCharacter(user_id=user.id, name="Bruno", display_name="Bruno Houille", is_default=True)
        save_slot = GameSaveSlot(
            user_id=user.id,
            character=character,
            slot_key="slot-1",
            title="Apartment checkpoint",
            template_id="god_of_carnage_solo",
            template_title="God of Carnage",
            run_id="run-1",
            kind="solo_story",
            status="active",
            metadata_json={"beat_id": "arrival"},
        )
        db.session.add_all([character, save_slot])
        db.session.commit()

    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_templates",
        lambda: [{"id": "god_of_carnage_solo", "title": "God of Carnage", "kind": "solo_story"}],
    )
    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_runs",
        lambda: [{"id": "run-1", "template_title": "God of Carnage", "beat_id": "arrival", "total_humans": 1}],
    )
    monkeypatch.setattr("app.api.v1.game_routes.get_play_service_websocket_url", lambda: "wss://play.example.com")

    response = client.get("/api/v1/game/bootstrap", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["profile"]["account_id"] == str(user.id)
    assert data["templates"][0]["kind_label"] == "Solo Story"
    assert data["runs"][0]["id"] == "run-1"
    assert data["characters"][0]["name"] == "Bruno"
    assert data["save_slots"][0]["slot_key"] == "slot-1"
    assert data["play_service"]["configured"] is True



def test_game_templates_proxy_uses_jwt(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_templates",
        lambda: [{"id": "god_of_carnage_solo", "title": "God of Carnage", "kind": "solo_story"}],
    )

    response = client.get("/api/v1/game/templates", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["templates"][0]["id"] == "god_of_carnage_solo"



def test_game_character_crud(client, auth_headers):
    create_response = client.post(
        "/api/v1/game/characters",
        json={"name": "Veronique", "display_name": "Veronique Houille", "bio": "Writer and idealist."},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    character = create_response.get_json()["character"]
    assert character["is_default"] is True

    update_response = client.patch(
        f"/api/v1/game/characters/{character['id']}",
        json={"display_name": "Veronique H."},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["character"]["display_name"] == "Veronique H."

    archive_response = client.delete(
        f"/api/v1/game/characters/{character['id']}",
        headers=auth_headers,
    )
    assert archive_response.status_code == 200
    assert archive_response.get_json()["archived"] is True



def test_game_save_slot_upsert_and_delete(client, auth_headers):
    character_response = client.post(
        "/api/v1/game/characters",
        json={"name": "Annette", "display_name": "Annette Reille"},
        headers=auth_headers,
    )
    character_id = character_response.get_json()["character"]["id"]

    save_response = client.post(
        "/api/v1/game/save-slots",
        json={
            "slot_key": "group-slot-a",
            "title": "Apartment argument",
            "template_id": "apartment_confrontation_group",
            "template_title": "Apartment Confrontation",
            "run_id": "run-group-1",
            "kind": "group_story",
            "character_id": character_id,
            "metadata": {"ready_count": 2},
        },
        headers=auth_headers,
    )
    assert save_response.status_code == 200
    slot = save_response.get_json()["save_slot"]
    assert slot["run_id"] == "run-group-1"
    assert slot["metadata"]["ready_count"] == 2

    list_response = client.get("/api/v1/game/save-slots", headers=auth_headers)
    assert list_response.status_code == 200
    assert list_response.get_json()["save_slots"][0]["slot_key"] == "group-slot-a"

    delete_response = client.delete(f"/api/v1/game/save-slots/{slot['id']}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True



def test_game_ticket_uses_selected_backend_character_and_returns_ws_url(client, auth_headers, test_user, app, monkeypatch):
    user, _ = test_user
    with app.app_context():
        character = GameCharacter(user_id=user.id, name="Bruno", display_name="Bruno Houille", is_default=True)
        db.session.add(character)
        db.session.commit()
        character_id = character.id

    captured = {}

    def fake_join_context(**kwargs):
        captured.update(kwargs)
        return PlayJoinContext(
            run_id=kwargs["run_id"],
            participant_id="participant-1",
            role_id="mediator",
            display_name=kwargs["display_name"],
            account_id=kwargs["account_id"],
            character_id=kwargs.get("character_id"),
        )

    monkeypatch.setattr("app.api.v1.game_routes.resolve_join_context", fake_join_context)
    monkeypatch.setattr("app.api.v1.game_routes.issue_play_ticket", lambda payload: f"signed-for-{payload['participant_id']}")
    monkeypatch.setattr("app.api.v1.game_routes.get_play_service_websocket_url", lambda: "wss://play.example.com")

    response = client.post(
        "/api/v1/game/tickets",
        json={"run_id": "run-1", "character_id": character_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ticket"] == "signed-for-participant-1"
    assert data["ws_base_url"] == "wss://play.example.com"
    assert data["display_name"] == "Bruno Houille"
    assert captured["character_id"] == str(character_id)
    assert captured["display_name"] == "Bruno Houille"



def test_game_bootstrap_marks_play_service_unconfigured_when_secret_missing(client, auth_headers, app):
    app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
    app.config["PLAY_SERVICE_INTERNAL_URL"] = "https://play-internal.example.com"
    app.config["PLAY_SERVICE_SHARED_SECRET"] = None

    response = client.get("/api/v1/game/bootstrap", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["play_service"]["configured"] is False
    assert data["play_service"]["public_url"] == "https://play.example.com"


def test_game_content_endpoints_seed_and_publish(client, moderator_headers):
    list_response = client.get('/api/v1/game/content/experiences', headers=moderator_headers)
    assert list_response.status_code == 200
    experiences = list_response.get_json()['experiences']
    assert experiences
    seed = experiences[0]
    assert seed['template_id'] == 'god_of_carnage_solo'
    assert seed['is_published'] is True
    assert seed.get('content_lifecycle') == 'published'
    assert seed['payload']['title'] == 'God of Carnage'

    new_payload = seed['payload'].copy()
    new_payload['id'] = 'god_of_carnage_side_story'
    new_payload['slug'] = 'god-of-carnage-side-story'
    new_payload['title'] = 'God of Carnage — Side Story'
    create_response = client.post('/api/v1/game/content/experiences', json={'payload': new_payload}, headers=moderator_headers)
    assert create_response.status_code == 201
    created = create_response.get_json()['experience']
    assert created['is_published'] is False
    assert created.get('content_lifecycle') == 'draft'

    blocked = client.post(f"/api/v1/game/content/experiences/{created['id']}/publish", headers=moderator_headers)
    assert blocked.status_code == 409
    blocked_body = blocked.get_json()
    assert blocked_body.get('code') == 'lifecycle_blocks_publish'

    assert client.post(
        f"/api/v1/game/content/experiences/{created['id']}/governance/submit-review",
        json={},
        headers=moderator_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/game/content/experiences/{created['id']}/governance/decision",
        json={'decision': 'approve'},
        headers=moderator_headers,
    ).status_code == 200

    new_payload['summary'] = 'Updated summary for authored content.'
    update_response = client.patch(f"/api/v1/game/content/experiences/{created['id']}", json={'payload': new_payload}, headers=moderator_headers)
    assert update_response.status_code == 200
    assert update_response.get_json()['experience']['version'] == 2

    publish_response = client.post(f"/api/v1/game/content/experiences/{created['id']}/publish", headers=moderator_headers)
    assert publish_response.status_code == 200
    assert publish_response.get_json()['experience']['is_published'] is True
    assert publish_response.get_json()['experience'].get('content_lifecycle') == 'published'

    published_feed = client.get('/api/v1/game/content/published')
    assert published_feed.status_code == 200
    template_ids = {item['id'] for item in published_feed.get_json()['templates']}
    assert 'god_of_carnage_solo' in template_ids
    assert 'god_of_carnage_side_story' in template_ids



def test_game_content_requires_moderator_or_admin(client, auth_headers):
    response = client.get('/api/v1/game/content/experiences', headers=auth_headers)
    assert response.status_code == 403



def test_game_ops_proxy_endpoints(client, moderator_headers, monkeypatch):
    monkeypatch.setattr('app.api.v1.game_routes.list_play_runs', lambda: [{'id': 'run-123', 'template_title': 'God of Carnage', 'status': 'running'}])
    monkeypatch.setattr('app.api.v1.game_routes.get_play_run_details', lambda run_id: {'run': {'id': run_id}, 'template_source': 'backend_published'})
    monkeypatch.setattr('app.api.v1.game_routes.get_play_run_transcript', lambda run_id: {'run_id': run_id, 'entries': [{'text': 'One line.'}]})
    monkeypatch.setattr(
        'app.api.v1.game_routes.terminate_play_run',
        lambda run_id, **kwargs: {
            'run_id': run_id,
            'terminated': True,
            'template_id': 'god_of_carnage_solo',
            'actor_display_name': kwargs.get('actor_display_name') or '',
            'reason': kwargs.get('reason') or '',
        },
    )

    runs_response = client.get('/api/v1/game/ops/runs', headers=moderator_headers)
    assert runs_response.status_code == 200
    assert runs_response.get_json()['runs'][0]['id'] == 'run-123'

    detail_response = client.get('/api/v1/game/ops/runs/run-123', headers=moderator_headers)
    assert detail_response.status_code == 200
    assert detail_response.get_json()['template_source'] == 'backend_published'

    transcript_response = client.get('/api/v1/game/ops/runs/run-123/transcript', headers=moderator_headers)
    assert transcript_response.status_code == 200
    assert transcript_response.get_json()['entries'][0]['text'] == 'One line.'

    terminate_response = client.post('/api/v1/game/ops/runs/run-123/terminate', headers=moderator_headers)
    assert terminate_response.status_code == 200
    assert terminate_response.get_json()['terminated'] is True


def test_game_create_run_requires_template_id(client, auth_headers):
    r = client.post("/api/v1/game/runs", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_game_templates_unknown_kind_gets_title_case_label(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_templates",
        lambda: [{"id": "x", "title": "T", "kind": "weird_kind"}],
    )
    r = client.get("/api/v1/game/templates", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["templates"][0]["kind_label"] == "Weird Kind"


def test_game_bootstrap_marks_unconfigured_when_ws_url_fails(
    client, auth_headers, test_user, app, monkeypatch
):
    from app.services.game_service import GameServiceConfigError

    app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
    app.config["PLAY_SERVICE_INTERNAL_URL"] = "https://play.example.com"
    monkeypatch.setattr("app.api.v1.game_routes.has_complete_play_service_config", lambda: True)
    monkeypatch.setattr("app.api.v1.game_routes.list_play_templates", lambda: [])
    monkeypatch.setattr("app.api.v1.game_routes.list_play_runs", lambda: [])

    def bad_ws():
        raise GameServiceConfigError("ws url missing")

    monkeypatch.setattr("app.api.v1.game_routes.get_play_service_websocket_url", bad_ws)
    r = client.get("/api/v1/game/bootstrap", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["play_service"]["configured"] is False


def test_error_response_branches():
    from app.api.v1 import game_routes
    from app.services.game_content_service import (
        GameContentConflictError,
        GameContentNotFoundError,
        GameContentValidationError,
    )
    from app.services.game_profile_service import NotFoundError, OwnershipError, ValidationError
    from app.services.game_service import GameServiceConfigError, GameServiceError

    body, code = game_routes._error_response(PermissionError("Authentication required."))
    assert code == 401
    body, code = game_routes._error_response(PermissionError("Account is restricted."))
    assert code == 403
    body, code = game_routes._error_response(NotFoundError("nf"))
    assert code == 404
    body, code = game_routes._error_response(OwnershipError("own"))
    assert code == 400
    body, code = game_routes._error_response(ValidationError("val"))
    assert code == 400
    body, code = game_routes._error_response(GameContentValidationError("gv"))
    assert code == 400
    body, code = game_routes._error_response(GameContentNotFoundError())
    assert code == 404
    body, code = game_routes._error_response(GameContentConflictError())
    assert code == 409
    body, code = game_routes._error_response(GameServiceError("cfg", status_code=422))
    assert code == 422
    body, code = game_routes._error_response(GameServiceError("svc", status_code=502))
    assert code == 502
    body, code = game_routes._error_response(GameServiceConfigError("bad config"))
    assert code == 500
    body, code = game_routes._error_response(RuntimeError("weird"))
    assert code == 500


def test_play_service_bootstrap_config_error(app, monkeypatch):
    from app.api.v1 import game_routes

    def boom():
        from app.services.game_service import GameServiceConfigError

        raise GameServiceConfigError("no ws")

    monkeypatch.setattr(game_routes, "has_complete_play_service_config", lambda: True)
    monkeypatch.setattr(game_routes, "get_play_service_websocket_url", boom)
    with app.app_context():
        data = game_routes._play_service_bootstrap()
    assert data["configured"] is False


def test_resolve_identity_invalid_character_id(app, test_user, monkeypatch):
    from app.api.v1 import game_routes
    from app.models import User

    user = test_user[0] if isinstance(test_user, tuple) else test_user

    with app.app_context():
        u = User.query.get(user.id)
        with pytest.raises(Exception):
            game_routes._resolve_identity_context(u, {"character_id": "not-int"})


def test_game_content_get_not_found(client, moderator_headers, monkeypatch):
    from app.services.game_content_service import GameContentNotFoundError

    monkeypatch.setattr(
        "app.api.v1.game_routes.get_experience",
        lambda *_a, **_kw: (_ for _ in ()).throw(GameContentNotFoundError()),
    )
    r = client.get("/api/v1/game/content/experiences/999", headers=moderator_headers)
    assert r.status_code == 404


def test_current_user_from_session_user_id(app, test_user, monkeypatch):
    from app.api.v1 import game_routes

    user, _ = test_user
    monkeypatch.setattr(game_routes, "session", {"user_id": user.id})
    with app.app_context():
        u = game_routes._current_user()
    assert u is not None and u.id == user.id


def test_current_user_none_when_jwt_verify_raises(app, monkeypatch):
    from app.api.v1 import game_routes

    monkeypatch.setattr(game_routes, "session", {})
    monkeypatch.setattr(
        game_routes,
        "verify_jwt_in_request",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("jwt")),
    )
    with app.app_context():
        assert game_routes._current_user() is None


def test_current_user_none_when_jwt_identity_missing(app, monkeypatch):
    from app.api.v1 import game_routes

    monkeypatch.setattr(game_routes, "session", {})
    monkeypatch.setattr(game_routes, "verify_jwt_in_request", lambda **kwargs: None)
    monkeypatch.setattr(game_routes, "get_jwt_identity", lambda: None)
    with app.app_context():
        assert game_routes._current_user() is None


def test_require_game_user_banned(app, test_user, monkeypatch):
    from app.api.v1 import game_routes
    from app.extensions import db
    from app.models import User

    user, _ = test_user
    monkeypatch.setattr(game_routes, "session", {"user_id": user.id})
    with app.app_context():
        row = db.session.get(User, user.id)
        row.is_banned = True
        db.session.commit()
        with pytest.raises(PermissionError, match="restricted"):
            game_routes._require_game_user()


def test_parse_optional_int(app):
    from app.api.v1 import game_routes
    from app.services.game_profile_service import ValidationError

    with app.app_context():
        assert game_routes._parse_optional_int(None, field_name="x") is None
        assert game_routes._parse_optional_int("42", field_name="x") == 42
        with pytest.raises(ValidationError, match="valid integer"):
            game_routes._parse_optional_int("nope", field_name="x")


def test_game_create_ticket_requires_run_id(client, auth_headers):
    r = client.post("/api/v1/game/tickets", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_game_runs_list_ok(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_runs",
        lambda: [{"id": "r1"}],
    )
    r = client.get("/api/v1/game/runs", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["runs"][0]["id"] == "r1"


def test_game_characters_list_ok(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.game_routes.list_characters_for_user", lambda uid: [])
    r = client.get("/api/v1/game/characters", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["characters"] == []
