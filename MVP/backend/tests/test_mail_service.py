"""Comprehensive pytest tests for mail_service.py (37 tests covering all patterns)."""
import pytest
from unittest.mock import patch, MagicMock, call
from flask import url_for
from app.services.mail_service import _activation_url, send_verification_email, send_password_reset_email
from app.extensions import mail


class TestActivationUrl:
    """Tests for _activation_url() helper function."""

    def test_activation_url_with_app_public_base_url_configured(self, app, test_user):
        """Test _activation_url uses APP_PUBLIC_BASE_URL when configured."""
        with app.app_context():
            app.config["APP_PUBLIC_BASE_URL"] = "https://example.com"
            token = "test_token_123"
            url = _activation_url(token)
            assert url == "https://example.com/activate/test_token_123"

    def test_activation_url_strips_trailing_slash_from_base_url(self, app, test_user):
        """Test _activation_url strips trailing slash from APP_PUBLIC_BASE_URL."""
        with app.app_context():
            app.config["APP_PUBLIC_BASE_URL"] = "https://example.com/"
            token = "test_token_456"
            url = _activation_url(token)
            assert url == "https://example.com/activate/test_token_456"

    def test_activation_url_with_empty_app_public_base_url(self, app, test_user):
        """Test _activation_url falls back to url_for when APP_PUBLIC_BASE_URL is empty string."""
        with app.app_context():
            app.config["APP_PUBLIC_BASE_URL"] = ""
            token = "test_token_789"
            with app.test_request_context():
                url = _activation_url(token)
                expected = url_for("web.activate", token=token, _external=True)
                assert url == expected

    def test_activation_url_with_none_app_public_base_url(self, app, test_user):
        """Test _activation_url falls back to url_for when APP_PUBLIC_BASE_URL is None."""
        with app.app_context():
            app.config["APP_PUBLIC_BASE_URL"] = None
            token = "test_token_fallback"
            with app.test_request_context():
                url = _activation_url(token)
                expected = url_for("web.activate", token=token, _external=True)
                assert url == expected

    def test_activation_url_with_url_for_fallback(self, app, test_user):
        """Test _activation_url returns correct url_for format when no base URL."""
        with app.app_context():
            app.config.pop("APP_PUBLIC_BASE_URL", None)
            token = "external_token"
            with app.test_request_context():
                url = _activation_url(token)
                assert "/activate/" in url
                assert "external_token" in url
                assert url.startswith("http")


class TestSendVerificationEmailDevMode:
    """Tests for send_verification_email() in dev/testing modes."""

    def test_verification_email_testing_mode_true(self, app, test_user):
        """Test send_verification_email returns True and logs in TESTING=True mode."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            app.config["MAIL_ENABLED"] = True
            token = "test_token_verify"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    result = send_verification_email(user, token)
                    assert result is True
                    mock_logger.warning.assert_called_once()
                    call_args = mock_logger.warning.call_args
                    assert "TESTING" in call_args[0][0]
                    assert user.username in call_args[0]

    def test_verification_email_testing_mode_logs_username_not_token(self, app, test_user):
        """Test send_verification_email logs username but NOT token for security."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            token = "secret_token_12345"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    send_verification_email(user, token)
                    call_args = mock_logger.warning.call_args
                    logged_text = str(call_args)
                    assert token not in logged_text
                    assert user.username in call_args[0]

    def test_verification_email_mail_enabled_false(self, app, test_user):
        """Test send_verification_email returns True when MAIL_ENABLED=False."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = False
            token = "test_token_disabled"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    result = send_verification_email(user, token)
                    assert result is True
                    mock_logger.warning.assert_called_once()
                    call_args = mock_logger.warning.call_args
                    assert "MAIL_ENABLED=False" in call_args[0][0]

    def test_verification_email_dev_mode_does_not_call_mail_send(self, app, test_user):
        """Test send_verification_email does not call mail.send() in dev modes."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            app.config["MAIL_ENABLED"] = False
            token = "test_token_nosend"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_verification_email(user, token)
                    mock_send.assert_not_called()


class TestSendVerificationEmailExceptions:
    """Tests for send_verification_email() exception handling."""

    @pytest.mark.parametrize("exception_type", [
        RuntimeError,
        ConnectionError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
    ])
    def test_verification_email_catches_runtime_error(self, app, test_user, exception_type):
        """Test send_verification_email catches RuntimeError and returns False."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "test_token_error"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=exception_type("Mail error")):
                    with patch("app.services.mail_service.logger") as mock_logger:
                        result = send_verification_email(user, token)
                        assert result is False
                        mock_logger.exception.assert_called_once()

    def test_verification_email_exception_logs_user_id_not_token(self, app, test_user):
        """Test send_verification_email logs user.id on exception, NOT token."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "secret_token_exception"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=RuntimeError("SMTP error")):
                    with patch("app.services.mail_service.logger") as mock_logger:
                        send_verification_email(user, token)
                        call_args = mock_logger.exception.call_args
                        assert user.id in call_args[0]
                        assert token not in str(call_args)

    def test_verification_email_exception_never_reraised(self, app, test_user):
        """Test send_verification_email catches all exceptions and never re-raises."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "test_token_reraise"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=Exception("Unhandled error")):
                    # Should not raise, should return False
                    result = send_verification_email(user, token)
                    assert result is False

    @pytest.mark.parametrize("exception_type", [
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
    ])
    def test_verification_email_catches_smtp_and_connection_errors(self, app, test_user, exception_type):
        """Test send_verification_email catches SMTP and connection exceptions."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "test_token_smtp"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=exception_type("SMTP failed")):
                    result = send_verification_email(user, token)
                    assert result is False


class TestSendVerificationEmailProduction:
    """Tests for send_verification_email() in production mode."""

    def test_verification_email_production_sends_message(self, app, test_user):
        """Test send_verification_email sends Message in production mode."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "prod_token_verify"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    result = send_verification_email(user, token)
                    assert result is True
                    mock_send.assert_called_once()

    def test_verification_email_message_has_correct_subject(self, app, test_user):
        """Test sent message has correct subject."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "token_subject"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_verification_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert msg.subject == "World of Shadows – Verify your email"

    def test_verification_email_message_has_correct_recipient(self, app, test_user):
        """Test sent message has correct recipient email."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "token_recipient"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_verification_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert msg.recipients == [user.email]

    def test_verification_email_message_body_contains_username(self, app, test_user):
        """Test sent message body contains user's username."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "token_body_user"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_verification_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert user.username in msg.body

    def test_verification_email_message_body_contains_activation_url(self, app, test_user):
        """Test sent message body contains activation URL."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            app.config["APP_PUBLIC_BASE_URL"] = "https://example.com"
            token = "token_url_body"
            with patch("app.services.mail_service.mail.send") as mock_send:
                send_verification_email(user, token)
                msg = mock_send.call_args[0][0]
                assert "https://example.com/activate/token_url_body" in msg.body

    def test_verification_email_returns_true_on_successful_send(self, app, test_user):
        """Test send_verification_email returns True when mail.send succeeds."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_ENABLED"] = True
            token = "token_success"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send"):
                    result = send_verification_email(user, token)
                    assert result is True


class TestSendPasswordResetEmailDevMode:
    """Tests for send_password_reset_email() in dev/testing modes."""

    def test_password_reset_email_testing_mode_true(self, app, test_user):
        """Test send_password_reset_email returns True and logs in TESTING=True mode."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            token = "test_token_reset"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    result = send_password_reset_email(user, token)
                    assert result is True
                    mock_logger.info.assert_called_once()
                    call_args = mock_logger.info.call_args
                    assert "TESTING" in call_args[0][0]
                    assert user.username in call_args[0]

    def test_password_reset_email_testing_mode_logs_username_not_token(self, app, test_user):
        """Test send_password_reset_email logs username but NOT token."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            token = "secret_reset_token"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    send_password_reset_email(user, token)
                    call_args = mock_logger.info.call_args
                    logged_text = str(call_args)
                    assert token not in logged_text
                    assert user.username in call_args[0]

    def test_password_reset_email_localhost_with_no_username(self, app, test_user):
        """Test send_password_reset_email dev fallback: localhost + no MAIL_USERNAME."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "localhost"
            app.config["MAIL_USERNAME"] = None
            token = "test_token_localhost"
            with app.test_request_context():
                with patch("app.services.mail_service.logger") as mock_logger:
                    result = send_password_reset_email(user, token)
                    assert result is True
                    mock_logger.info.assert_called_once()

    def test_password_reset_email_localhost_with_username_sends(self, app, test_user):
        """Test send_password_reset_email sends when MAIL_USERNAME is set (localhost override)."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "localhost"
            app.config["MAIL_USERNAME"] = "localuser"
            token = "test_token_local_user"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    result = send_password_reset_email(user, token)
                    # Should attempt to send (not fallback to logging)
                    mock_send.assert_called_once()

    def test_password_reset_email_dev_mode_does_not_call_mail_send(self, app, test_user):
        """Test send_password_reset_email does not call mail.send() in TESTING mode."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = True
            token = "test_token_nosend_reset"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    mock_send.assert_not_called()

    def test_password_reset_email_localhost_no_username_no_send(self, app, test_user):
        """Test send_password_reset_email does not send with localhost + no MAIL_USERNAME."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "localhost"
            app.config["MAIL_USERNAME"] = None
            token = "test_token_localhost_nosend"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    mock_send.assert_not_called()


class TestSendPasswordResetEmailExceptions:
    """Tests for send_password_reset_email() exception handling."""

    @pytest.mark.parametrize("exception_type", [
        RuntimeError,
        ConnectionError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
    ])
    def test_password_reset_email_catches_exception(self, app, test_user, exception_type):
        """Test send_password_reset_email catches exceptions and returns False."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "smtp.example.com"
            app.config["MAIL_USERNAME"] = "mailuser"
            token = "test_token_reset_error"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=exception_type("Error")):
                    with patch("app.services.mail_service.logger") as mock_logger:
                        result = send_password_reset_email(user, token)
                        assert result is False
                        mock_logger.exception.assert_called_once()

    def test_password_reset_email_exception_logs_user_id_not_token(self, app, test_user):
        """Test send_password_reset_email logs user.id, NOT token on error."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "smtp.example.com"
            app.config["MAIL_USERNAME"] = "mailuser"
            token = "secret_reset_exception"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send", side_effect=RuntimeError("SMTP")):
                    with patch("app.services.mail_service.logger") as mock_logger:
                        send_password_reset_email(user, token)
                        call_args = mock_logger.exception.call_args
                        assert user.id in call_args[0]
                        assert token not in str(call_args)

    def test_password_reset_email_exception_never_reraised(self, app, test_user):
        """Test send_password_reset_email catches all exceptions and never re-raises."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "test_token_reset_reraise"
                with patch("app.services.mail_service.mail.send", side_effect=Exception("Crash")):
                    result = send_password_reset_email(user, token)
                    assert result is False

    @pytest.mark.parametrize("exception_type", [
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
    ])
    def test_password_reset_email_catches_network_errors(self, app, test_user, exception_type):
        """Test send_password_reset_email catches network exceptions."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "test_network_error"
                with patch("app.services.mail_service.mail.send", side_effect=exception_type("Network")):
                    result = send_password_reset_email(user, token)
                    assert result is False


class TestSendPasswordResetEmailProduction:
    """Tests for send_password_reset_email() in production mode."""

    def test_password_reset_email_production_sends_message(self, app, test_user):
        """Test send_password_reset_email sends Message in production mode."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "prod_token_reset"
                with patch("app.services.mail_service.mail.send") as mock_send:
                    result = send_password_reset_email(user, token)
                    assert result is True
                    mock_send.assert_called_once()

    def test_password_reset_email_message_has_correct_subject(self, app, test_user):
        """Test sent message has correct subject."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "token_reset_subject"
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert msg.subject == "World of Shadows – Password reset"

    def test_password_reset_email_message_has_correct_recipient(self, app, test_user):
        """Test sent message has correct recipient email."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "token_reset_recipient"
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert msg.recipients == [user.email]

    def test_password_reset_email_message_body_contains_username(self, app, test_user):
        """Test sent message body contains user's username."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "token_reset_body_user"
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert user.username in msg.body

    def test_password_reset_email_message_body_contains_reset_url(self, app, test_user):
        """Test sent message body contains reset URL."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "smtp.example.com"
            app.config["MAIL_USERNAME"] = "mailuser"
            token = "token_reset_url_body"
            with patch("app.services.mail_service.mail.send") as mock_send:
                with app.test_request_context():
                    send_password_reset_email(user, token)
                    msg = mock_send.call_args[0][0]
                    # Body should contain a reset URL (from url_for)
                    assert "/reset-password/" in msg.body or "reset" in msg.body.lower()

    def test_password_reset_email_message_body_mentions_expiration(self, app, test_user):
        """Test sent message body mentions token expiration time."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "token_reset_expiration"
                with patch("app.services.mail_service.mail.send") as mock_send:
                    send_password_reset_email(user, token)
                    msg = mock_send.call_args[0][0]
                    assert "60 minutes" in msg.body

    def test_password_reset_email_returns_true_on_successful_send(self, app, test_user):
        """Test send_password_reset_email returns True when mail.send succeeds."""
        user, _ = test_user
        with app.app_context():
            with app.test_request_context():
                app.config["TESTING"] = False
                app.config["MAIL_SERVER"] = "smtp.example.com"
                app.config["MAIL_USERNAME"] = "mailuser"
                token = "token_reset_success"
                with patch("app.services.mail_service.mail.send"):
                    result = send_password_reset_email(user, token)
                    assert result is True

    def test_password_reset_email_with_url_for_in_request_context(self, app, test_user):
        """Test send_password_reset_email uses url_for correctly in request context."""
        user, _ = test_user
        with app.app_context():
            app.config["TESTING"] = False
            app.config["MAIL_SERVER"] = "smtp.example.com"
            app.config["MAIL_USERNAME"] = "mailuser"
            token = "test_token_urlfor"
            with app.test_request_context():
                with patch("app.services.mail_service.mail.send") as mock_send:
                    result = send_password_reset_email(user, token)
                    assert result is True
                    msg = mock_send.call_args[0][0]
                    expected_url = url_for("web.reset_password", token=token, _external=True)
                    assert expected_url in msg.body
