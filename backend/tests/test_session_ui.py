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
