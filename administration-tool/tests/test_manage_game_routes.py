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


def test_manage_ai_stack_governance_returns_200(client):
    response = client.get('/manage/ai-stack/governance')
    assert response.status_code == 200


def test_manage_ai_stack_governance_renders_template(app, client):
    with captured_templates(app) as templates:
        response = client.get('/manage/ai-stack/governance')
    assert response.status_code == 200
    assert templates[-1][0] == 'manage/ai_stack_governance.html'
    html = response.get_data(as_text=True)
    assert 'ai-stack-load-closure-cockpit' in html
    assert '/admin/ai-stack/closure-cockpit' in html
    assert 'ai-stack-aggregate-summary' in html
    assert 'ai-stack-blockers-panel' in html
    assert 'ai-stack-gate-stack' in html
    assert 'ai-stack-load-release-readiness' in html
    assert '/admin/ai-stack/release-readiness' in html
