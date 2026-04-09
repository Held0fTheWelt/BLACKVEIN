"""Session API endpoint behavior contracts."""

import json

from app.services.session_service import create_session


def test_get_session_requires_token_and_returns_snapshot(client, test_user, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 401

    response = client.get(
        f"/api/v1/sessions/{session_id}",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "session_id" in data


def test_post_execute_turn_proxies_to_world_engine(client, test_user, monkeypatch):
    session = create_session("god_of_carnage")
    session_id = session.session_id

    monkeypatch.setattr(
        "app.api.v1.session_routes.create_story_session",
        lambda **_: {"session_id": "we_story_1"},
    )
    monkeypatch.setattr(
        "app.api.v1.session_routes.compile_module",
        lambda *_args, **_kwargs: type(
            "Compiled",
            (),
            {
                "runtime_projection": type(
                    "Projection",
                    (),
                    {"model_dump": staticmethod(lambda **_: {"start_scene_id": "scene_1"})},
                )()
            },
        )(),
    )
    monkeypatch.setattr(
        "app.api.v1.session_routes.execute_story_turn_in_engine",
        lambda **_: {"turn": {"turn_number": 1, "raw_input": "test action"}},
    )
    monkeypatch.setattr(
        "app.api.v1.session_routes.get_story_state",
        lambda *_, **__: {"turn_counter": 1, "current_scene_id": "scene_1"},
    )
    monkeypatch.setattr(
        "app.api.v1.session_routes.get_story_diagnostics",
        lambda *_, **__: {"diagnostics": [{"interpreted_input": {"kind": "action"}}]},
    )

    response = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"player_input": "test action"},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["world_engine_story_session_id"] == "we_story_1"
    assert data["turn"]["turn_number"] == 1


def test_get_logs_requires_token_and_returns_events(client, test_user, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    response = client.get(f"/api/v1/sessions/{session_id}/logs")
    assert response.status_code == 401

    response = client.get(
        f"/api/v1/sessions/{session_id}/logs",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "events" in data


def test_get_state_requires_token_and_returns_canonical_state(client, test_user, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    response = client.get(f"/api/v1/sessions/{session_id}/state")
    assert response.status_code == 401

    response = client.get(
        f"/api/v1/sessions/{session_id}/state",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "canonical_state" in data


def test_create_session_still_works(client, test_user):
    response = client.post(
        "/api/v1/sessions",
        json={"module_id": "god_of_carnage"},
        content_type="application/json",
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert "session_id" in data
    assert data["module_id"] == "god_of_carnage"
