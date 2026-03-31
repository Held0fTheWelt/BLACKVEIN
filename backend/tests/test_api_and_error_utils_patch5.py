from __future__ import annotations

from app.utils.errors import ERROR_CODES, api_error, api_success


def test_api_error_infers_status_code_and_allows_override(app):
    with app.app_context():
        response, status = api_error("User missing", "USER_NOT_FOUND")
        assert status == 404
        assert response.get_json() == {"error": "User missing", "code": "USER_NOT_FOUND"}

        response, status = api_error("Explicit", "INVALID_INPUT", status_code=422)
        assert status == 422
        assert response.get_json() == {"error": "Explicit", "code": "INVALID_INPUT"}


def test_api_error_falls_back_to_400_for_unknown_codes(app):
    with app.app_context():
        response, status = api_error("Unknown", "SOMETHING_NEW")
        assert status == 400
        assert response.get_json()["code"] == "SOMETHING_NEW"
        assert ERROR_CODES["USER_NOT_FOUND"] == 404
        assert ERROR_CODES["INVALID_INPUT"] == 400


def test_api_success_supports_data_message_and_empty_payload(app):
    with app.app_context():
        response, status = api_success({"id": 7}, message="created", status_code=201)
        assert status == 201
        assert response.get_json() == {"id": 7, "message": "created"}

        response, status = api_success(message="ok")
        assert status == 200
        assert response.get_json() == {"message": "ok"}

        response, status = api_success()
        assert status == 200
        assert response.get_json() == {}
