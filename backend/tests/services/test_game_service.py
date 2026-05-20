"""Tests for game_service.py - Play service integration."""
from unittest.mock import MagicMock, patch
import pytest

from app.services.game.game_service import (
    GameServiceError,
    GameServiceConfigError,
    PlayJoinContext,
    has_complete_play_service_config,
    get_play_service_public_url,
    get_play_service_websocket_url,
    _unexpected,
    _parse_create_run_v1,
    _parse_run_details_v1,
    _parse_terminate_v1,
    _require_configured_url,
    _internal_headers,
)


class TestGameServiceError:
    """Tests for GameServiceError exception."""

    def test_error_with_custom_status(self):
        """Test creating error with custom status code."""
        error = GameServiceError("Test error", status_code=503)
        assert str(error) == "Test error"
        assert error.status_code == 503

    def test_error_default_status(self):
        """Test default status code is 502."""
        error = GameServiceError("Test error")
        assert error.status_code == 502


class TestGameServiceConfigError:
    """Tests for GameServiceConfigError exception."""

    def test_config_error_status(self):
        """Test that config error has status code 500."""
        error = GameServiceConfigError("Config missing")
        assert str(error) == "Config missing"
        assert error.status_code == 500


class TestUnexpectedHelper:
    """Tests for _unexpected helper function."""

    def test_unexpected_error_message(self):
        """Test error message format."""
        error = _unexpected("payload")
        assert "unexpected payload" in str(error)
        assert isinstance(error, GameServiceError)

    def test_unexpected_with_different_kinds(self):
        """Test with various kind parameters."""
        for kind in ["create_run", "run detail", "terminate"]:
            error = _unexpected(kind)
            assert kind in str(error)


class TestParseCreateRunV1:
    """Tests for _parse_create_run_v1 function."""

    def test_valid_payload(self):
        """Test parsing valid create_run payload."""
        payload = {
            "run": {"id": "run-123"},
            "run_id": "run-123",
            "store": {},
            "hint": "test hint",
        }
        result = _parse_create_run_v1(payload)
        assert result == payload

    def test_missing_run_dict(self):
        """Test error when run dict is missing."""
        payload = {"store": {}, "hint": "test"}
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_missing_run_id_in_run(self):
        """Test error when run.id is missing."""
        payload = {"run": {}, "store": {}, "hint": "test"}
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_empty_run_id(self):
        """Test error when run.id is empty string."""
        payload = {"run": {"id": "   "}, "store": {}, "hint": "test"}
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_contradictory_run_ids(self):
        """Test error when run_id doesn't match run.id."""
        payload = {
            "run": {"id": "run-123"},
            "run_id": "run-456",
            "store": {},
            "hint": "test",
        }
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_missing_store(self):
        """Test error when store is missing."""
        payload = {"run": {"id": "run-123"}, "hint": "test"}
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_missing_hint(self):
        """Test error when hint is missing."""
        payload = {"run": {"id": "run-123"}, "store": {}}
        with pytest.raises(GameServiceError):
            _parse_create_run_v1(payload)

    def test_not_dict_payload(self):
        """Test error when payload is not a dict."""
        with pytest.raises(GameServiceError):
            _parse_create_run_v1("not a dict")


class TestParseRunDetailsV1:
    """Tests for _parse_run_details_v1 function."""

    def test_valid_payload(self):
        """Test parsing valid run details payload."""
        payload = {
            "run": {"id": "run-123"},
            "template_source": "source",
            "template": {
                "id": "tpl-1",
                "title": "Template",
                "kind": "narrative",
                "join_policy": "open",
                "min_humans_to_start": 1,
            },
            "store": {},
        }
        result = _parse_run_details_v1(payload, requested_run_id="run-123")
        assert result == payload

    def test_run_id_mismatch(self):
        """Test error when run.id doesn't match requested_run_id."""
        payload = {
            "run": {"id": "run-456"},
            "template_source": "source",
            "template": {
                "id": "tpl-1",
                "title": "Template",
                "kind": "narrative",
                "join_policy": "open",
                "min_humans_to_start": 1,
            },
            "store": {},
        }
        with pytest.raises(GameServiceError):
            _parse_run_details_v1(payload, requested_run_id="run-123")

    def test_contradictory_top_run_id(self):
        """Test error when top-level run_id contradicts run.id."""
        payload = {
            "run": {"id": "run-123"},
            "run_id": "run-456",
            "template_source": "source",
            "template": {
                "id": "tpl-1",
                "title": "Template",
                "kind": "narrative",
                "join_policy": "open",
                "min_humans_to_start": 1,
            },
            "store": {},
        }
        with pytest.raises(GameServiceError):
            _parse_run_details_v1(payload, requested_run_id="run-123")

    def test_missing_template_field(self):
        """Test error when template is missing required fields."""
        payload = {
            "run": {"id": "run-123"},
            "template_source": "source",
            "template": {
                "id": "tpl-1",
                "title": "Template",
                # missing 'kind'
            },
            "store": {},
        }
        with pytest.raises(GameServiceError):
            _parse_run_details_v1(payload, requested_run_id="run-123")

    def test_optional_lobby_field(self):
        """Test that lobby field is optional."""
        payload = {
            "run": {"id": "run-123"},
            "template_source": "source",
            "template": {
                "id": "tpl-1",
                "title": "Template",
                "kind": "narrative",
                "join_policy": "open",
                "min_humans_to_start": 1,
            },
            "store": {},
            "lobby": None,
        }
        result = _parse_run_details_v1(payload, requested_run_id="run-123")
        assert result["lobby"] is None


class TestParseTerminateV1:
    """Tests for _parse_terminate_v1 function."""

    def test_valid_payload(self):
        """Test parsing valid terminate payload."""
        payload = {
            "terminated": True,
            "run_id": "run-123",
            "template_id": "tpl-1",
            "actor_display_name": "Admin",
            "reason": "Test termination",
        }
        result = _parse_terminate_v1(payload, requested_run_id="run-123")
        assert result == payload

    def test_missing_terminated_flag(self):
        """Test error when terminated is not True."""
        payload = {
            "terminated": False,
            "run_id": "run-123",
            "template_id": "tpl-1",
            "actor_display_name": "Admin",
            "reason": "Test",
        }
        with pytest.raises(GameServiceError):
            _parse_terminate_v1(payload, requested_run_id="run-123")

    def test_run_id_mismatch(self):
        """Test error when run_id doesn't match requested."""
        payload = {
            "terminated": True,
            "run_id": "run-456",
            "template_id": "tpl-1",
            "actor_display_name": "Admin",
            "reason": "Test",
        }
        with pytest.raises(GameServiceError):
            _parse_terminate_v1(payload, requested_run_id="run-123")

    def test_empty_run_id(self):
        """Test error when run_id is empty."""
        payload = {
            "terminated": True,
            "run_id": "   ",
            "template_id": "tpl-1",
            "actor_display_name": "Admin",
            "reason": "Test",
        }
        with pytest.raises(GameServiceError):
            _parse_terminate_v1(payload, requested_run_id="run-123")

    def test_missing_actor_display_name(self):
        """Test error when actor_display_name is missing."""
        payload = {
            "terminated": True,
            "run_id": "run-123",
            "template_id": "tpl-1",
            "reason": "Test",
        }
        with pytest.raises(GameServiceError):
            _parse_terminate_v1(payload, requested_run_id="run-123")


class TestConfigFunctions:
    """Tests for configuration validation functions."""

    def test_has_complete_play_service_config_all_present(self):
        """Test when all config is present."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            def mock_config_get(key, default=None):
                config = {
                    "PLAY_SERVICE_CONTROL_DISABLED": False,
                    "PLAY_SERVICE_PUBLIC_URL": "https://play.example.com",
                    "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
                    "PLAY_SERVICE_SHARED_SECRET": "secret123",
                }
                return config.get(key, default)

            mock_app.config.get = mock_config_get

            result = has_complete_play_service_config()
            assert result is True

    def test_has_complete_play_service_config_disabled(self):
        """Test when service is explicitly disabled."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            def mock_config_get(key, default=None):
                config = {
                    "PLAY_SERVICE_CONTROL_DISABLED": True,
                }
                return config.get(key, default)

            mock_app.config.get = mock_config_get

            result = has_complete_play_service_config()
            assert result is False

    def test_has_complete_play_service_config_missing_url(self):
        """Test when public URL is missing."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            def mock_config_get(key, default=None):
                config = {
                    "PLAY_SERVICE_CONTROL_DISABLED": False,
                    "PLAY_SERVICE_PUBLIC_URL": None,
                    "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
                    "PLAY_SERVICE_SHARED_SECRET": "secret123",
                }
                return config.get(key, default)

            mock_app.config.get = mock_config_get

            result = has_complete_play_service_config()
            assert result is False

    def test_require_configured_url_public(self):
        """Test getting public URL when configured."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            def mock_config_get(key, default=None):
                config = {
                    "PLAY_SERVICE_PUBLIC_URL": "https://public.example.com/",
                }
                return config.get(key, default)

            mock_app.config.get = mock_config_get

            result = _require_configured_url("public")
            assert result == "https://public.example.com"

    def test_require_configured_url_not_configured(self):
        """Test error when URL not configured."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            mock_app.config.get = lambda key, default=None: None

            with pytest.raises(GameServiceConfigError):
                _require_configured_url("public")


class TestPublicUrlFunctions:
    """Tests for public URL retrieval functions."""

    def test_get_play_service_public_url(self):
        """Test retrieving public URL."""
        with patch("app.services.game.game_service._require_configured_url") as mock_require:
            mock_require.return_value = "https://play.example.com"

            result = get_play_service_public_url()
            assert result == "https://play.example.com"
            mock_require.assert_called_once_with("public")

    def test_get_play_service_websocket_url_https(self):
        """Test converting HTTPS to WSS."""
        with patch("app.services.game.game_service.get_play_service_public_url") as mock_get:
            mock_get.return_value = "https://play.example.com:8443/path"

            result = get_play_service_websocket_url()
            assert result.startswith("wss://")
            assert "example.com" in result

    def test_get_play_service_websocket_url_http(self):
        """Test converting HTTP to WS."""
        with patch("app.services.game.game_service.get_play_service_public_url") as mock_get:
            mock_get.return_value = "http://play.example.com:8080"

            result = get_play_service_websocket_url()
            assert result.startswith("ws://")
            assert "example.com" in result


class TestInternalHeaders:
    """Tests for internal headers generation."""

    def test_headers_without_api_key(self):
        """Test headers when no API key configured."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            mock_app.config.get = lambda key, default=None: None

            headers = _internal_headers()
            assert headers["Accept"] == "application/json"
            assert "X-Play-Service-Key" not in headers

    def test_headers_with_api_key(self):
        """Test headers when API key is configured."""
        with patch("app.services.game.game_service.current_app") as mock_app:
            def mock_config_get(key, default=None):
                config = {
                    "PLAY_SERVICE_INTERNAL_API_KEY": "api-key-123",
                }
                return config.get(key, default)

            mock_app.config.get = mock_config_get

            headers = _internal_headers()
            assert headers["Accept"] == "application/json"
            assert headers["X-Play-Service-Key"] == "api-key-123"


class TestPlayJoinContext:
    """Tests for PlayJoinContext dataclass."""

    def test_context_creation(self):
        """Test creating join context."""
        context = PlayJoinContext(
            run_id="run-123",
            participant_id="p-1",
            role_id="role-1",
            display_name="Player",
        )

        assert context.run_id == "run-123"
        assert context.participant_id == "p-1"
        assert context.role_id == "role-1"
        assert context.display_name == "Player"
        assert context.account_id is None
        assert context.character_id is None

    def test_context_with_optional_fields(self):
        """Test creating context with optional fields."""
        context = PlayJoinContext(
            run_id="run-123",
            participant_id="p-1",
            role_id="role-1",
            display_name="Player",
            account_id="acc-1",
            character_id="char-1",
        )

        assert context.account_id == "acc-1"
        assert context.character_id == "char-1"
