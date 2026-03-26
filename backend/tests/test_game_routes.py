from app.extensions import db
from app.models import GameCharacter, GameExperienceTemplate, GameSaveSlot
from app.services.game_service import PlayJoinContext



def _login_session(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )



def test_game_menu_logged_in_renders_launcher(client, test_user):
    user, password = test_user
    _login_session(client, user.username, password)
    response = client.get("/game-menu")
    assert response.status_code == 200
    assert b"Game Menu" in response.data
    assert b"game_menu.js" in response.data
    assert b"Character workshop" in response.data



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



def test_game_templates_proxy_uses_logged_in_session(client, test_user, monkeypatch):
    user, password = test_user
    _login_session(client, user.username, password)

    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_templates",
        lambda: [{"id": "god_of_carnage_solo", "title": "God of Carnage", "kind": "solo_story"}],
    )

    response = client.get("/api/v1/game/templates")
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


def test_game_menu_marks_play_service_unconfigured_without_complete_bridge(client, test_user, app):
    user, password = test_user
    _login_session(client, user.username, password)
    app.config["PLAY_SERVICE_PUBLIC_URL"] = "https://play.example.com"
    app.config["PLAY_SERVICE_INTERNAL_URL"] = None
    app.config["PLAY_SERVICE_SHARED_SECRET"] = None

    response = client.get("/game-menu")
    assert response.status_code == 200
    assert b"PLAY_SERVICE_SHARED_SECRET" in response.data


def test_game_content_endpoints_seed_and_publish(client, moderator_headers):
    list_response = client.get('/api/v1/game/content/experiences', headers=moderator_headers)
    assert list_response.status_code == 200
    experiences = list_response.get_json()['experiences']
    assert experiences
    seed = experiences[0]
    assert seed['template_id'] == 'god_of_carnage_solo'
    assert seed['is_published'] is True
    assert seed['payload']['title'] == 'God of Carnage — Single Adventure'

    new_payload = seed['payload'].copy()
    new_payload['id'] = 'god_of_carnage_side_story'
    new_payload['slug'] = 'god-of-carnage-side-story'
    new_payload['title'] = 'God of Carnage — Side Story'
    create_response = client.post('/api/v1/game/content/experiences', json={'payload': new_payload}, headers=moderator_headers)
    assert create_response.status_code == 201
    created = create_response.get_json()['experience']
    assert created['is_published'] is False

    new_payload['summary'] = 'Updated summary for authored content.'
    update_response = client.patch(f"/api/v1/game/content/experiences/{created['id']}", json={'payload': new_payload}, headers=moderator_headers)
    assert update_response.status_code == 200
    assert update_response.get_json()['experience']['version'] == 2

    publish_response = client.post(f"/api/v1/game/content/experiences/{created['id']}/publish", headers=moderator_headers)
    assert publish_response.status_code == 200
    assert publish_response.get_json()['experience']['is_published'] is True

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
    monkeypatch.setattr('app.api.v1.game_routes.terminate_play_run', lambda run_id: {'run_id': run_id, 'terminated': True})

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
