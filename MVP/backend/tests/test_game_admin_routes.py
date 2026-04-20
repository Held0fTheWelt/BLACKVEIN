from __future__ import annotations

import uuid

from app.extensions import db
from app.models import GameExperienceTemplate


def _payload(template_id: str, kind: str = 'solo_story') -> dict:
    return {
        'id': template_id,
        'title': 'Apartment Incident',
        'kind': kind,
        'join_policy': 'owner_only' if kind == 'solo_story' else ('public' if kind == 'open_world' else 'invited_party'),
        'summary': 'Structured content payload for the runtime.',
        'max_humans': 1 if kind == 'solo_story' else 4,
        'initial_beat_id': 'intro',
        'roles': [
            {
                'id': 'visitor',
                'display_name': 'Visitor',
                'description': 'Human viewpoint role',
                'mode': 'human',
                'initial_room_id': 'hallway',
                'can_join': True,
            }
        ],
        'rooms': [
            {
                'id': 'hallway',
                'name': 'Hallway',
                'description': 'A narrow hallway.',
                'exits': [],
                'prop_ids': [],
                'action_ids': [],
            }
        ],
        'props': [],
        'actions': [],
        'beats': [
            {
                'id': 'intro',
                'name': 'Intro',
                'description': 'Opening beat',
                'summary': 'Opening beat',
            }
        ],
    }


def test_game_admin_create_and_publish_experience(client, moderator_headers, app):
    create_response = client.post(
        '/api/v1/game-admin/experiences',
        json={
            'key': 'god_of_carnage_group_authored',
            'title': 'God of Carnage — Authored Group',
            'experience_type': 'group_story',
            'summary': 'Author-managed group story.',
            'tags': ['group', 'authored'],
            'style_profile': 'retro_drama',
            'draft_payload': _payload('god_of_carnage_group_authored', kind='group_story'),
        },
        headers=moderator_headers,
    )
    assert create_response.status_code == 201
    item = create_response.get_json()
    assert item['template_id'] == 'god_of_carnage_group_authored'
    assert item['is_published'] is False
    assert item.get('content_lifecycle') == 'draft'

    assert client.post(
        f"/api/v1/game-admin/experiences/{item['id']}/governance/submit-review",
        json={},
        headers=moderator_headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/game-admin/experiences/{item['id']}/governance/decision",
        json={'decision': 'approve'},
        headers=moderator_headers,
    ).status_code == 200

    publish_response = client.post(
        f"/api/v1/game-admin/experiences/{item['id']}/publish",
        headers=moderator_headers,
    )
    assert publish_response.status_code == 200
    published = publish_response.get_json()
    assert published['is_published'] is True
    assert published['published_at'] is not None

    public_feed = client.get('/api/v1/game-content/templates')
    assert public_feed.status_code == 200
    feed_items = public_feed.get_json()['items']
    assert any(row['id'] == 'god_of_carnage_group_authored' for row in feed_items)


def test_game_admin_update_experience_increments_version(client, moderator_headers, app):
    with app.app_context():
        item = GameExperienceTemplate(
            template_id='bt_open_world_authored',
            slug='bt-open-world-authored',
            title='Open World District',
            kind='open_world',
            summary='Initial summary',
            tags_json=['open-world'],
            style_profile='retro_pulp',
            is_published=False,
            version=1,
            payload_json=_payload('bt_open_world_authored', kind='open_world'),
        )
        db.session.add(item)
        db.session.commit()
        template_id = item.id

    response = client.put(
        f'/api/v1/game-admin/experiences/{template_id}',
        json={
            'draft_payload': {
                **_payload('bt_open_world_authored', kind='open_world'),
                'summary': 'Updated payload summary',
            },
        },
        headers=moderator_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body['summary'] == 'Updated payload summary'
    assert body['version'] == 2
    assert body['payload']['summary'] == 'Updated payload summary'


def test_game_admin_runtime_proxy_routes(client, moderator_headers, monkeypatch):
    monkeypatch.setattr('app.api.v1.game_admin_routes.list_play_runs', lambda: [{'id': 'run-1', 'template_id': 'god_of_carnage_solo'}])
    monkeypatch.setattr(
        'app.api.v1.game_admin_routes.get_run_details',
        lambda run_id: {
            'run': {'id': run_id, 'status': 'running', 'participants': []},
            'template_source': 'test',
            'template': {
                'id': 'god_of_carnage_solo',
                'title': 'T',
                'kind': 'solo_story',
                'join_policy': 'public',
                'min_humans_to_start': 1,
            },
            'store': {'backend': 'memory'},
            'lobby': {},
        },
    )
    monkeypatch.setattr('app.api.v1.game_admin_routes.get_run_transcript', lambda run_id: {'run_id': run_id, 'entries': [{'kind': 'speech_committed', 'text': 'hello'}]})
    monkeypatch.setattr(
        'app.api.v1.game_admin_routes.terminate_run',
        lambda run_id, actor_display_name=None, reason=None: {
            'run_id': run_id,
            'terminated': True,
            'template_id': 'god_of_carnage_solo',
            'actor_display_name': actor_display_name or '',
            'reason': reason or '',
        },
    )

    runs = client.get('/api/v1/game-admin/runtime/runs', headers=moderator_headers)
    assert runs.status_code == 200
    assert runs.get_json()['items'][0]['id'] == 'run-1'

    detail = client.get('/api/v1/game-admin/runtime/runs/run-1', headers=moderator_headers)
    assert detail.status_code == 200
    assert detail.get_json()['run']['status'] == 'running'

    transcript = client.get('/api/v1/game-admin/runtime/runs/run-1/transcript', headers=moderator_headers)
    assert transcript.status_code == 200
    assert transcript.get_json()['entries'][0]['kind'] == 'speech_committed'

    terminate = client.post('/api/v1/game-admin/runtime/runs/run-1/terminate', json={'reason': 'Moderation stop'}, headers=moderator_headers)
    assert terminate.status_code == 200
    body = terminate.get_json()
    assert body['terminated'] is True
    assert body['reason'] == 'Moderation stop'


def test_game_admin_list_experiences_query_flags(client, moderator_headers, app):
    tid = f"cov_{uuid.uuid4().hex[:10]}"
    with app.app_context():
        item = GameExperienceTemplate(
            template_id=tid,
            slug=f"{tid}-slug",
            title='Cov List',
            kind='solo_story',
            summary='s',
            tags_json=[],
            style_profile='retro_pulp',
            is_published=False,
            version=1,
            payload_json={'id': tid, 'title': 'Cov', 'kind': 'solo_story'},
        )
        db.session.add(item)
        db.session.commit()

    r = client.get(
        f'/api/v1/game-admin/experiences?q=Cov&status=draft&include_payload=true',
        headers=moderator_headers,
    )
    assert r.status_code == 200
    assert isinstance(r.get_json().get('items'), list)


def test_game_admin_create_experience_errors(client, moderator_headers, monkeypatch):
    assert client.post(
        '/api/v1/game-admin/experiences',
        data='x',
        headers={**moderator_headers, 'Content-Type': 'application/json'},
    ).status_code == 400

    r2 = client.post(
        '/api/v1/game-admin/experiences',
        json={'draft_payload': {}},
        headers=moderator_headers,
    )
    assert r2.status_code == 400

    def raise_exists(**_kwargs):
        raise ValueError('Template id already exists')

    monkeypatch.setattr('app.api.v1.game_admin_routes.create_experience', raise_exists)
    r3 = client.post(
        '/api/v1/game-admin/experiences',
        json={'draft_payload': {'id': 'x', 'title': 'T', 'kind': 'solo_story'}},
        headers=moderator_headers,
    )
    assert r3.status_code == 409


def test_game_admin_runtime_game_service_error(client, moderator_headers, monkeypatch):
    from app.services.game_service import GameServiceError

    def err():
        raise GameServiceError('play down', status_code=503)

    monkeypatch.setattr('app.api.v1.game_admin_routes.list_play_runs', err)
    r = client.get('/api/v1/game-admin/runtime/runs', headers=moderator_headers)
    assert r.status_code == 503


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
