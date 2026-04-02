"""Extra coverage for game_routes helpers and branches."""
import pytest


def test_error_response_branches():
    from app.api.v1 import game_routes
    from app.services.game_content_service import (
        GameContentConflictError,
        GameContentNotFoundError,
        GameContentValidationError,
    )
    from app.services.game_profile_service import NotFoundError, OwnershipError, ValidationError
    from app.services.game_service import GameServiceConfigError, GameServiceError

    body, code = game_routes._error_response(PermissionError("Authentication required."))
    assert code == 401
    body, code = game_routes._error_response(PermissionError("Account is restricted."))
    assert code == 403
    body, code = game_routes._error_response(NotFoundError("nf"))
    assert code == 404
    body, code = game_routes._error_response(OwnershipError("own"))
    assert code == 400
    body, code = game_routes._error_response(ValidationError("val"))
    assert code == 400
    body, code = game_routes._error_response(GameContentValidationError("gv"))
    assert code == 400
    body, code = game_routes._error_response(GameContentNotFoundError())
    assert code == 404
    body, code = game_routes._error_response(GameContentConflictError())
    assert code == 409
    body, code = game_routes._error_response(GameServiceError("cfg", status_code=422))
    assert code == 422
    body, code = game_routes._error_response(GameServiceError("svc", status_code=502))
    assert code == 502
    body, code = game_routes._error_response(GameServiceConfigError("bad config"))
    assert code == 500
    body, code = game_routes._error_response(RuntimeError("weird"))
    assert code == 500


def test_play_service_bootstrap_config_error(app, monkeypatch):
    from app.api.v1 import game_routes

    def boom():
        from app.services.game_service import GameServiceConfigError

        raise GameServiceConfigError("no ws")

    monkeypatch.setattr(game_routes, "has_complete_play_service_config", lambda: True)
    monkeypatch.setattr(game_routes, "get_play_service_websocket_url", boom)
    with app.app_context():
        data = game_routes._play_service_bootstrap()
    assert data["configured"] is False


def test_resolve_identity_invalid_character_id(app, test_user, monkeypatch):
    from app.api.v1 import game_routes
    from app.models import User

    user = test_user[0] if isinstance(test_user, tuple) else test_user

    with app.app_context():
        u = User.query.get(user.id)
        with pytest.raises(Exception):
            game_routes._resolve_identity_context(u, {"character_id": "not-int"})


def test_game_content_get_not_found(client, moderator_headers, monkeypatch):
    from app.services.game_content_service import GameContentNotFoundError

    monkeypatch.setattr(
        "app.api.v1.game_routes.get_experience",
        lambda *_a, **_kw: (_ for _ in ()).throw(GameContentNotFoundError()),
    )
    r = client.get("/api/v1/game/content/experiences/999", headers=moderator_headers)
    assert r.status_code == 404


def test_current_user_from_session_user_id(app, test_user, monkeypatch):
    from app.api.v1 import game_routes

    user, _ = test_user
    monkeypatch.setattr(game_routes, "session", {"user_id": user.id})
    with app.app_context():
        u = game_routes._current_user()
    assert u is not None and u.id == user.id


def test_current_user_none_when_jwt_verify_raises(app, monkeypatch):
    from app.api.v1 import game_routes

    monkeypatch.setattr(game_routes, "session", {})
    monkeypatch.setattr(
        game_routes,
        "verify_jwt_in_request",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("jwt")),
    )
    with app.app_context():
        assert game_routes._current_user() is None


def test_current_user_none_when_jwt_identity_missing(app, monkeypatch):
    from app.api.v1 import game_routes

    monkeypatch.setattr(game_routes, "session", {})
    monkeypatch.setattr(game_routes, "verify_jwt_in_request", lambda **kwargs: None)
    monkeypatch.setattr(game_routes, "get_jwt_identity", lambda: None)
    with app.app_context():
        assert game_routes._current_user() is None


def test_require_game_user_banned(app, test_user, monkeypatch):
    from app.api.v1 import game_routes
    from app.extensions import db
    from app.models import User

    user, _ = test_user
    monkeypatch.setattr(game_routes, "session", {"user_id": user.id})
    with app.app_context():
        row = db.session.get(User, user.id)
        row.is_banned = True
        db.session.commit()
        with pytest.raises(PermissionError, match="restricted"):
            game_routes._require_game_user()


def test_parse_optional_int(app):
    from app.api.v1 import game_routes
    from app.services.game_profile_service import ValidationError

    with app.app_context():
        assert game_routes._parse_optional_int(None, field_name="x") is None
        assert game_routes._parse_optional_int("42", field_name="x") == 42
        with pytest.raises(ValidationError, match="valid integer"):
            game_routes._parse_optional_int("nope", field_name="x")


def test_game_create_run_requires_template_id(client, auth_headers):
    r = client.post("/api/v1/game/runs", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_game_create_ticket_requires_run_id(client, auth_headers):
    r = client.post("/api/v1/game/tickets", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_game_runs_list_ok(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.game_routes.list_play_runs",
        lambda: [{"id": "r1"}],
    )
    r = client.get("/api/v1/game/runs", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["runs"][0]["id"] == "r1"


def test_game_characters_list_ok(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.api.v1.game_routes.list_characters_for_user", lambda uid: [])
    r = client.get("/api/v1/game/characters", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["characters"] == []
