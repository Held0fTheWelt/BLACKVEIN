"""Legacy play UI compatibility tests."""


def test_play_start_redirects_to_frontend(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/play", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/play"


def test_play_execute_post_redirects_to_frontend_shell(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.post("/play/session-123/execute", data={"operator_input": "look"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/play/session-123"
