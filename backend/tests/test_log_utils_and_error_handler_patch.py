from __future__ import annotations

from types import SimpleNamespace

from app.services import log_utils
from app.utils import error_handler


class DummyExc(Exception):
    pass


def test_is_sensitive_field_detects_partial_matches_and_non_strings():
    assert log_utils.is_sensitive_field("password") is True
    assert log_utils.is_sensitive_field("user_api_key") is True
    assert log_utils.is_sensitive_field("AuthorizationHeader") is True
    assert log_utils.is_sensitive_field("display_name") is False
    assert log_utils.is_sensitive_field(None) is False
    assert log_utils.is_sensitive_field(123) is False


def test_redact_dict_redacts_nested_sensitive_fields_and_preserves_other_values():
    payload = {
        "user_id": 7,
        "profile": {
            "display_name": "Hollywood",
            "password": "secret",
            "nested": {"api_token": "abc", "theme": "dark"},
        },
        "email": "user@example.com",
    }

    result = log_utils.redact_dict(payload)

    assert result["user_id"] == 7
    assert result["profile"]["display_name"] == "Hollywood"
    assert result["profile"]["password"] == "***REDACTED***"
    assert result["profile"]["nested"]["api_token"] == "***REDACTED***"
    assert result["profile"]["nested"]["theme"] == "dark"
    assert result["email"] == "user@example.com"
    assert payload["profile"]["password"] == "secret"


def test_safe_log_dict_uses_requested_level_and_redacts_extra(monkeypatch):
    captured: dict[str, object] = {}

    def fake_warning(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(log_utils.logger, "warning", fake_warning)

    log_utils.safe_log_dict(
        "Attempted action",
        {"username": "neo", "refresh_token": "token-value", "count": 3},
        level="warning",
    )

    assert captured["message"] == "Attempted action"
    assert captured["extra"] == {
        "username": "neo",
        "refresh_token": "***REDACTED***",
        "count": 3,
    }


def test_safe_log_user_logs_only_id_and_username(monkeypatch):
    captured: dict[str, object] = {}

    def fake_info(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(log_utils.logger, "info", fake_info)

    user = SimpleNamespace(id=42, username="cypher", email="secret@example.com", password="hidden")
    log_utils.safe_log_user("User context", user)

    assert captured["message"] == "User context"
    assert captured["extra"] == {"user_id": 42, "username": "cypher"}


def test_safe_log_request_omits_headers_and_optional_method(monkeypatch):
    captured: dict[str, object] = {}

    def fake_info(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(log_utils.logger, "info", fake_info)

    request_obj = SimpleNamespace(
        path="/api/v1/admin/users",
        remote_addr="127.0.0.1",
        method="POST",
        headers={"Authorization": "Bearer secret"},
        json={"password": "hidden"},
    )

    log_utils.safe_log_request("Request", request_obj, include_method=False)

    assert captured["message"] == "Request"
    assert captured["extra"] == {"path": "/api/v1/admin/users", "remote_addr": "127.0.0.1"}


def test_sanitize_exception_message_filters_sensitive_details():
    assert error_handler.sanitize_exception_message(DummyExc("SELECT * FROM users")) == "Invalid request"
    assert error_handler.sanitize_exception_message(DummyExc("C:/app/config.py missing")) == "Invalid request"
    assert error_handler.sanitize_exception_message(DummyExc("Friendly validation message")) == "Friendly validation message"


def test_safe_error_response_logs_context_for_warning(monkeypatch):
    captured: dict[str, object] = {}

    def fake_warning(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(error_handler.logger, "warning", fake_warning)

    message, status = error_handler.safe_error_response(
        DummyExc("database exploded"),
        generic_message="Operation failed",
        log_level="warning",
        context={"operation": "user_lookup"},
    )

    assert (message, status) == ("Operation failed", 500)
    assert captured["message"] == "Handled exception"
    assert captured["extra"]["exception_type"] == "DummyExc"
    assert captured["extra"]["exception_message"] == "database exploded"
    assert captured["extra"]["context"] == {"operation": "user_lookup"}


def test_safe_error_response_uses_exception_logger_when_requested(monkeypatch):
    captured: dict[str, object] = {}

    def fake_exception(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(error_handler.logger, "exception", fake_exception)

    message, status = error_handler.safe_error_response(
        DummyExc("boom"),
        generic_message="Something broke",
        log_level="exception",
    )

    assert (message, status) == ("Something broke", 500)
    assert captured["message"] == "Something broke"
    assert captured["extra"]["exception_type"] == "DummyExc"


def test_log_full_error_includes_request_context(monkeypatch):
    captured: dict[str, object] = {}

    def fake_exception(message: str, *, extra: dict):
        captured["message"] = message
        captured["extra"] = extra

    monkeypatch.setattr(error_handler.logger, "exception", fake_exception)

    error_handler.log_full_error(
        DummyExc("Forbidden"),
        message="Route failed",
        user_id=99,
        route="/api/v1/users/99",
        method="PATCH",
    )

    assert captured["message"] == "Route failed"
    assert captured["extra"] == {
        "user_id": 99,
        "route": "/api/v1/users/99",
        "method": "PATCH",
        "exception_type": "DummyExc",
        "exception_message": "Forbidden",
    }
