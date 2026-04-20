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
