"""Removed backend play UI route tests."""


def test_play_start_route_removed(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/play", follow_redirects=False)
    assert response.status_code == 404


def test_play_execute_route_removed(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.post("/play/session-123/execute", data={"operator_input": "look"}, follow_redirects=False)
    assert response.status_code == 404
