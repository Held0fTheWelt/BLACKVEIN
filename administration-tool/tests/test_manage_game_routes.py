from __future__ import annotations

from conftest import captured_templates


def test_manage_game_content_returns_200(client):
    response = client.get('/manage/game/content')
    assert response.status_code == 200


def test_manage_game_content_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get('/manage/game/content')
    assert response.status_code == 200
    assert templates[-1][0] == 'manage/game_content.html'


def test_manage_game_operations_returns_200(client):
    response = client.get('/manage/game/operations')
    assert response.status_code == 200


def test_manage_game_operations_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get('/manage/game/operations')
    assert response.status_code == 200
    assert templates[-1][0] == 'manage/game_operations.html'


def test_manage_ai_stack_governance_redirects_to_workbench(client):
    response = client.get('/manage/ai-stack/governance', follow_redirects=False)
    assert response.status_code == 308
    assert response.headers.get("Location", "").endswith("/manage/inspector-workbench")


def test_manage_inspector_workbench_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get('/manage/inspector-workbench')
    assert response.status_code == 200
    assert templates[-1][0] == 'manage/inspector_workbench.html'
    html = response.get_data(as_text=True)
    assert 'inspector-load-all' in html
    assert '/api/v1/admin/ai-stack/inspector/turn/' in html
    assert '/api/v1/admin/ai-stack/inspector/timeline/' in html
