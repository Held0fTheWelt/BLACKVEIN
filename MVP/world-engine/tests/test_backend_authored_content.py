from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from conftest import build_test_app


def test_backend_published_content_overrides_builtin(tmp_path, monkeypatch):
    # Set environment variables before app build
    monkeypatch.setenv('BACKEND_CONTENT_SYNC_ENABLED', 'true')
    monkeypatch.setenv('BACKEND_CONTENT_FEED_URL', 'https://backend.example/api/v1/game/content/published')
    monkeypatch.setenv('BACKEND_CONTENT_TIMEOUT_SECONDS', '5.0')
    monkeypatch.setenv('BACKEND_CONTENT_SYNC_INTERVAL_SECONDS', '0.0')

    def fake_loader(url: str, timeout: float = 10.0):
        from app.content.models import ExperienceTemplate
        payload = {
            'id': 'god_of_carnage_solo',
            'title': 'God of Carnage — Authored Publish',
            'kind': 'solo_story',
            'join_policy': 'owner_only',
            'summary': 'Published authored payload from backend.',
            'max_humans': 1,
            'min_humans_to_start': 1,
            'persistent': False,
            'initial_beat_id': 'courtesy',
            'roles': [
                {
                    'id': 'visitor', 'display_name': 'Visitor', 'description': 'Player role', 'mode': 'human', 'initial_room_id': 'hallway', 'can_join': True,
                },
                {
                    'id': 'veronique', 'display_name': 'Véronique', 'description': 'NPC', 'mode': 'npc', 'initial_room_id': 'living_room',
                },
            ],
            'rooms': [
                {'id': 'hallway', 'name': 'Hallway', 'description': 'Start', 'exits': [{'direction': 'inside', 'target_room_id': 'living_room', 'label': 'Inside'}], 'prop_ids': [], 'action_ids': [], 'artwork_prompt': None},
                {'id': 'living_room', 'name': 'Living Room', 'description': 'Conflict room', 'exits': [], 'prop_ids': [], 'action_ids': [], 'artwork_prompt': None},
            ],
            'props': [],
            'actions': [],
            'beats': [{'id': 'courtesy', 'name': 'Courtesy', 'description': 'Start beat', 'summary': 'Summary'}],
            'tags': ['authored'],
            'style_profile': 'retro_pulp',
        }
        return {'god_of_carnage_solo': ExperienceTemplate.model_validate(payload)}

    # Patch load_published_templates where it's imported
    backend_loader = importlib.import_module('app.content.backend_loader')
    original_loader = backend_loader.load_published_templates
    monkeypatch.setattr(backend_loader, 'load_published_templates', fake_loader)
    app = build_test_app(tmp_path)
    manager = app.state.manager
    template = manager.get_template('god_of_carnage_solo')
    assert template.title == 'God of Carnage — Authored Publish'
    assert manager.template_sources['god_of_carnage_solo'] == 'backend_published'

    # Restore original function and reset env to prevent interference with other tests
    monkeypatch.setattr(backend_loader, 'load_published_templates', original_loader)
    monkeypatch.delenv('BACKEND_CONTENT_SYNC_ENABLED', raising=False)
    monkeypatch.delenv('BACKEND_CONTENT_FEED_URL', raising=False)
    monkeypatch.delenv('BACKEND_CONTENT_TIMEOUT_SECONDS', raising=False)
    monkeypatch.delenv('BACKEND_CONTENT_SYNC_INTERVAL_SECONDS', raising=False)

    # Reload config and manager to pick up cleared env vars and restored function
    import app.config
    importlib.reload(app.config)
    import app.runtime.manager
    importlib.reload(app.runtime.manager)


def test_delete_run_endpoint_terminates_runtime_instance(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAY_SERVICE_INTERNAL_API_KEY', 'ops-key')
    import app.config as config_module
    monkeypatch.setattr(config_module, 'PLAY_SERVICE_INTERNAL_API_KEY', 'ops-key', raising=False)
    app = build_test_app(tmp_path)
    client = TestClient(app)
    create = client.post('/api/runs', json={'template_id': 'god_of_carnage_solo', 'display_name': 'Bruno'})
    assert create.status_code == 200
    run_id = create.json()['run']['id']

    unauthorized = client.delete(f'/api/runs/{run_id}')
    assert unauthorized.status_code == 401

    terminated = client.delete(f'/api/runs/{run_id}', headers={'X-Play-Service-Key': 'ops-key'})
    assert terminated.status_code == 200
    assert terminated.json()['terminated'] is True

    missing = client.get(f'/api/runs/{run_id}')
    assert missing.status_code == 404
