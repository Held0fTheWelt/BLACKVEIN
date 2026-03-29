# backend/tests/test_session_ui.py
def _login_session(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=False)

def test_play_page_requires_login(client):
    response = client.get("/play")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_play_page_renders_for_logged_in_user(client, test_user):
    user, password = test_user
    _login_session(client, user.username, password)
    response = client.get("/play")
    assert response.status_code == 200
    assert b"god_of_carnage" in response.data

def test_play_page_contains_start_form(client, test_user):
    user, password = test_user
    _login_session(client, user.username, password)
    response = client.get("/play")
    assert b"<form" in response.data
    assert b"/play/start" in response.data


import re

def _get_csrf_token(client, path, username, password):
    _login_session(client, username, password)
    response = client.get(path)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode())
    return match.group(1) if match else ""

def test_post_play_start_creates_session_and_redirects(client, test_user):
    user, password = test_user
    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/play/" in response.headers["Location"]

def test_post_play_start_missing_module_flashes_error(client, test_user):
    user, password = test_user
    csrf = _get_csrf_token(client, "/play", user.username, password)
    response = client.post(
        "/play/start",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"module" in response.data.lower() or b"select" in response.data.lower()

def test_post_play_start_stores_session_in_cookie(client, test_user):
    user, password = test_user
    csrf = _get_csrf_token(client, "/play", user.username, password)
    with client.session_transaction() as s:
        assert "active_session" not in s
    client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    with client.session_transaction() as s:
        assert "active_session" in s
        assert s["active_session"]["module_id"] == "god_of_carnage"
