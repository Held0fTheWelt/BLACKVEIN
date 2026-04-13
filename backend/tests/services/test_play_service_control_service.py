"""Tests for play_service_control_service.py - Play service control plane."""
from unittest.mock import MagicMock, patch, call
import json
import pytest

from app.services.play_service_control_service import (
    SCHEMA_VERSION,
    MODE_DISABLED,
    MODE_LOCAL,
    MODE_DOCKER,
    MODE_REMOTE,
    UPSTREAM_TIMEOUT_S,
    _utc_iso,
    _empty_document,
    _load_raw_document,
    _persist_document,
    _valid_http_url,
    validate_desired_payload,
    _desired_from_env_baseline,
    _secret_present_in_app,
    _api_key_present_in_app,
    _attach_presence_fields,
    _finalize_desired_record,
    _sync_flask_config_from_desired,
    _clear_control_flags_default,
    _snapshot_play_config,
    _restore_play_config,
    bootstrap_play_service_control,
    validate_play_service_env_pairing,
    get_capabilities,
    _probe_play_http,
    run_connectivity_test,
    build_observed_state,
    get_control_payload,
    save_desired,
    apply_desired,
    run_test_persist,
)


class TestUtilities:
    """Tests for utility functions."""

    def test_utc_iso_format(self):
        """Test UTC ISO format generation."""
        result = _utc_iso()
        assert isinstance(result, str)
        assert result.endswith("Z")
        assert "T" in result
        assert ":" in result
        assert "-" in result

    def test_empty_document_structure(self):
        """Test empty document has correct structure."""
        doc = _empty_document()
        assert doc["version"] == SCHEMA_VERSION
        assert doc["desired"] is None
        assert doc["applied_desired"] is None
        assert doc["apply_ok"] is None
        assert doc["apply_message"] is None
        assert doc["applied_at"] is None
        assert doc["applied_by_user_id"] is None
        assert doc["last_test"] is None

    def test_valid_http_url_valid(self):
        """Test valid HTTP/HTTPS URL detection."""
        assert _valid_http_url("http://example.com") is True
        assert _valid_http_url("https://example.com") is True
        assert _valid_http_url("https://example.com:8443") is True
        assert _valid_http_url("http://localhost:8080/path") is True

    def test_valid_http_url_invalid(self):
        """Test invalid URL detection."""
        assert _valid_http_url("") is False
        assert _valid_http_url("   ") is False
        assert _valid_http_url(None) is False
        assert _valid_http_url("ftp://example.com") is False
        assert _valid_http_url("javascript:alert()") is False
        assert _valid_http_url("example.com") is False


class TestSecretAndKeyDetection:
    """Tests for secret and API key detection."""

    def test_secret_present_in_app_true(self):
        """Test secret detection when present."""
        app = MagicMock()
        app.config.get.return_value = "secret-key-123"
        assert _secret_present_in_app(app) is True

    def test_secret_present_in_app_false(self):
        """Test secret detection when absent."""
        app = MagicMock()
        app.config.get.return_value = None
        assert _secret_present_in_app(app) is False

    def test_secret_present_in_app_empty_string(self):
        """Test secret detection with empty string."""
        app = MagicMock()
        app.config.get.return_value = "   "
        assert _secret_present_in_app(app) is False

    def test_api_key_present_in_app_true(self):
        """Test API key detection when present."""
        app = MagicMock()
        app.config.get.return_value = "api-key-abc"
        assert _api_key_present_in_app(app) is True

    def test_api_key_present_in_app_false(self):
        """Test API key detection when absent."""
        app = MagicMock()
        app.config.get.return_value = None
        assert _api_key_present_in_app(app) is False


class TestValidateDesiredPayload:
    """Tests for validate_desired_payload function."""

    def test_validate_disabled_mode_valid(self):
        """Test validation of disabled mode."""
        body = {
            "mode": "disabled",
            "enabled": False,
            "request_timeout_ms": 30000,
        }
        normalized, errors = validate_desired_payload(body)
        assert len(errors) == 0
        assert normalized["mode"] == MODE_DISABLED
        assert normalized["enabled"] is False

    def test_validate_remote_mode_valid(self):
        """Test validation of remote mode with valid URLs."""
        body = {
            "mode": "remote",
            "enabled": True,
            "public_url": "https://public.example.com",
            "internal_url": "https://internal.example.com",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
        }
        normalized, errors = validate_desired_payload(body)
        assert len(errors) == 0
        assert normalized["mode"] == MODE_REMOTE
        assert normalized["enabled"] is True

    def test_validate_invalid_mode(self):
        """Test validation rejects invalid mode."""
        body = {"mode": "invalid_mode"}
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert len(errors) > 0
        assert "mode must be one of" in errors[0]

    def test_validate_disabled_mode_enabled_false_required(self):
        """Test disabled mode must have enabled=False."""
        body = {
            "mode": "disabled",
            "enabled": True,
        }
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert any("When mode is disabled" in e for e in errors)

    def test_validate_remote_mode_requires_enabled_true(self):
        """Test remote mode requires enabled=True."""
        body = {
            "mode": "remote",
            "enabled": False,
            "public_url": "https://public.example.com",
            "internal_url": "https://internal.example.com",
        }
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert any("enabled must be true" in e for e in errors)

    def test_validate_remote_mode_requires_urls(self):
        """Test remote mode requires valid URLs."""
        body = {
            "mode": "remote",
            "enabled": True,
            "public_url": "invalid",
            "internal_url": "also-invalid",
        }
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert any("public_url must be a valid" in e for e in errors)
        assert any("internal_url must be a valid" in e for e in errors)

    def test_validate_timeout_bounds(self):
        """Test request timeout bounds validation."""
        # Too low
        body = {
            "mode": "disabled",
            "enabled": False,
            "request_timeout_ms": 500,
        }
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert any("between 1000 and 600000" in e for e in errors)

        # Too high
        body["request_timeout_ms"] = 700000
        normalized, errors = validate_desired_payload(body)
        assert normalized is None
        assert any("between 1000 and 600000" in e for e in errors)

    def test_validate_timeout_default(self):
        """Test request timeout default value."""
        body = {
            "mode": "disabled",
            "enabled": False,
        }
        normalized, errors = validate_desired_payload(body)
        assert normalized["request_timeout_ms"] == 30000


class TestAttachPresenceFields:
    """Tests for _attach_presence_fields function."""

    def test_attach_presence_fields_with_secrets(self):
        """Test attaching presence fields when secrets present."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: "secret" if "SECRET" in key else "key"

        d = {"mode": "remote"}
        result = _attach_presence_fields(d, app)

        assert result["shared_secret_present"] is True
        assert result["internal_api_key_present"] is True
        assert result["mode"] == "remote"  # Original fields preserved

    def test_attach_presence_fields_without_secrets(self):
        """Test attaching presence fields when no secrets."""
        app = MagicMock()
        app.config.get.return_value = None

        d = {"mode": "disabled"}
        result = _attach_presence_fields(d, app)

        assert result["shared_secret_present"] is False
        assert result["internal_api_key_present"] is False


class TestFinalizeDesiredRecord:
    """Tests for _finalize_desired_record function."""

    def test_finalize_with_user_id(self):
        """Test finalizing record with user ID."""
        base = {"mode": "remote", "enabled": True}
        result = _finalize_desired_record(base, user_id=123)

        assert result["mode"] == "remote"
        assert result["updated_by_user_id"] == 123
        assert "updated_at" in result
        assert result["updated_at"] is not None

    def test_finalize_without_user_id(self):
        """Test finalizing record without user ID."""
        base = {"mode": "disabled"}
        result = _finalize_desired_record(base, user_id=None)

        assert result["mode"] == "disabled"
        assert result["updated_by_user_id"] is None
        assert "updated_at" in result


class TestLoadAndPersistDocument:
    """Tests for document loading and persistence."""

    def test_load_raw_document_empty(self):
        """Test loading empty document when no setting exists."""
        with patch("app.services.play_service_control_service.db") as mock_db:
            mock_db.session.get.return_value = None
            doc = _load_raw_document()
            assert doc["version"] == SCHEMA_VERSION
            assert doc["desired"] is None

    def test_load_raw_document_existing(self):
        """Test loading existing document."""
        existing_data = {
            "version": SCHEMA_VERSION,
            "desired": {"mode": "remote"},
            "applied_desired": None,
        }
        row = MagicMock(value=json.dumps(existing_data))

        with patch("app.services.play_service_control_service.db") as mock_db:
            mock_db.session.get.return_value = row
            doc = _load_raw_document()
            assert doc["desired"]["mode"] == "remote"

    def test_load_raw_document_invalid_json(self):
        """Test loading document with invalid JSON."""
        row = MagicMock(value="invalid json{")

        with patch("app.services.play_service_control_service.db") as mock_db:
            mock_db.session.get.return_value = row
            doc = _load_raw_document()
            assert doc["version"] == SCHEMA_VERSION
            assert doc["desired"] is None

    def test_persist_document_new(self):
        """Test persisting new document."""
        with patch("app.services.play_service_control_service.db") as mock_db:
            mock_db.session.get.return_value = None
            doc = {"version": SCHEMA_VERSION, "desired": {"mode": "remote"}}
            _persist_document(doc)

            mock_db.session.add.assert_called_once()
            mock_db.session.commit.assert_called_once()

    def test_persist_document_existing(self):
        """Test persisting existing document."""
        with patch("app.services.play_service_control_service.db") as mock_db:
            mock_db.session.get.return_value = MagicMock()
            doc = {"version": SCHEMA_VERSION, "desired": {"mode": "remote"}}
            _persist_document(doc)

            mock_db.session.commit.assert_called_once()


class TestFlaskConfigSync:
    """Tests for Flask config synchronization."""

    def test_sync_flask_config_disabled_mode(self):
        """Test syncing config for disabled mode."""
        app = MagicMock()
        desired = {"mode": MODE_DISABLED, "enabled": False, "allow_new_sessions": True}

        _sync_flask_config_from_desired(app, desired)

        app.config.__setitem__.assert_any_call("PLAY_SERVICE_CONTROL_DISABLED", True)
        app.config.__setitem__.assert_any_call("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True)

    def test_sync_flask_config_remote_mode(self):
        """Test syncing config for remote mode."""
        app = MagicMock()
        desired = {
            "mode": MODE_REMOTE,
            "enabled": True,
            "public_url": "https://public.example.com",
            "internal_url": "https://internal.example.com",
            "request_timeout_ms": 45000,
            "allow_new_sessions": False,
        }

        _sync_flask_config_from_desired(app, desired)

        assert app.config.__setitem__.call_count >= 4

    def test_clear_control_flags_default(self):
        """Test clearing control flags to defaults."""
        app = MagicMock()
        _clear_control_flags_default(app)

        app.config.__setitem__.assert_any_call("PLAY_SERVICE_CONTROL_DISABLED", False)
        app.config.__setitem__.assert_any_call("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True)

    def test_snapshot_and_restore_play_config(self):
        """Test snapshotting and restoring config."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_CONTROL_DISABLED": False,
            "PLAY_SERVICE_ALLOW_NEW_SESSIONS": True,
            "PLAY_SERVICE_PUBLIC_URL": "https://public.example.com",
            "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
            "PLAY_SERVICE_REQUEST_TIMEOUT": 30,
        }.get(key)

        snap = _snapshot_play_config(app)
        assert len(snap) == 5

        _restore_play_config(app, snap)
        assert app.config.__setitem__.call_count >= 5


class TestBootstrap:
    """Tests for bootstrap_play_service_control."""

    def test_bootstrap_with_valid_applied_state(self):
        """Test bootstrap loads applied state from database."""
        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._sync_flask_config_from_desired") as mock_sync:
                app = MagicMock()
                doc = {
                    "applied_desired": {"mode": MODE_REMOTE, "enabled": True},
                    "apply_ok": True,
                }
                mock_load.return_value = doc

                bootstrap_play_service_control(app)

                mock_sync.assert_called_once()

    def test_bootstrap_with_no_state(self):
        """Test bootstrap clears flags when no applied state."""
        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._clear_control_flags_default") as mock_clear:
                app = MagicMock()
                mock_load.return_value = {"applied_desired": None, "apply_ok": False}

                bootstrap_play_service_control(app)

                mock_clear.assert_called_once()

    def test_bootstrap_with_exception(self):
        """Test bootstrap clears flags on exception."""
        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._clear_control_flags_default") as mock_clear:
                app = MagicMock()
                mock_load.side_effect = Exception("DB error")

                bootstrap_play_service_control(app)

                mock_clear.assert_called_once()


class TestValidatePlayServiceEnvPairing:
    """Tests for validate_play_service_env_pairing."""

    def test_pairing_valid_with_url_and_secret(self):
        """Test pairing validation when both URL and secret present."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_CONTROL_DISABLED": False,
            "PLAY_SERVICE_PUBLIC_URL": "https://example.com",
            "PLAY_SERVICE_SHARED_SECRET": "secret",
        }.get(key)

        # Should not raise
        validate_play_service_env_pairing(app)

    def test_pairing_invalid_url_without_secret(self):
        """Test pairing validation fails when URL without secret."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_CONTROL_DISABLED": False,
            "PLAY_SERVICE_PUBLIC_URL": "https://example.com",
            "PLAY_SERVICE_SHARED_SECRET": None,
        }.get(key)

        with pytest.raises(ValueError, match="PLAY_SERVICE_SHARED_SECRET"):
            validate_play_service_env_pairing(app)

    def test_pairing_skipped_when_disabled(self):
        """Test pairing validation skipped when disabled."""
        app = MagicMock()
        app.config.get.return_value = True

        # Should not raise even without secret
        validate_play_service_env_pairing(app)


class TestCapabilitiesAndProbing:
    """Tests for capabilities and HTTP probing."""

    def test_get_capabilities(self):
        """Test getting capabilities."""
        caps = get_capabilities()
        assert caps["supports_disabled_mode"] is True
        assert caps["supports_local_mode"] is True
        assert caps["supports_docker_mode"] is True
        assert caps["supports_remote_mode"] is True
        assert caps["secrets_source"] == "environment_only"

    def test_probe_play_http_success(self):
        """Test successful HTTP probe."""
        with patch("app.services.play_service_control_service.httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _probe_play_http(
                "https://internal.example.com",
                {"Accept": "application/json"},
                "/api/health"
            )

            assert result["ok"] is True
            assert result["http_status"] == 200
            assert "latency_ms" in result

    def test_probe_play_http_timeout(self):
        """Test HTTP probe timeout handling."""
        with patch("app.services.play_service_control_service.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("timeout")
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _probe_play_http(
                "https://internal.example.com",
                {"Accept": "application/json"},
                "/api/health"
            )

            assert result["ok"] is False
            assert "error" in result
            assert "latency_ms" in result


class TestDesiredFromEnvBaseline:
    """Tests for _desired_from_env_baseline function."""

    def test_desired_from_env_disabled_mode(self):
        """Test baseline when no URLs configured."""
        app = MagicMock()
        app.config.get.return_value = None

        result = _desired_from_env_baseline(app)

        assert result["mode"] == MODE_DISABLED
        assert result["enabled"] is False

    def test_desired_from_env_remote_mode(self):
        """Test baseline when URLs configured."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_PUBLIC_URL": "https://public.example.com",
            "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
            "PLAY_SERVICE_REQUEST_TIMEOUT": 30,
        }.get(key)

        with patch("app.services.play_service_control_service._secret_present_in_app") as mock_secret:
            mock_secret.return_value = True
            result = _desired_from_env_baseline(app)

            assert result["mode"] == MODE_REMOTE
            assert result["enabled"] is True


class TestBuildObservedState:
    """Tests for build_observed_state function."""

    def test_build_observed_state_disabled(self):
        """Test observed state when disabled."""
        app = MagicMock()
        app.config.get.side_effect = lambda key, default=None: {
            "PLAY_SERVICE_CONTROL_DISABLED": True,
        }.get(key, default)

        with patch("app.services.play_service_control_service.has_app_context", return_value=True):
            observed = build_observed_state(app)

            assert observed["effective_mode"] == MODE_DISABLED
            assert observed["effective_enabled"] is False
            assert observed["config_complete"] is False

    def test_build_observed_state_config_complete(self):
        """Test observed state with complete config."""
        app = MagicMock()
        app.config.get.side_effect = lambda key, default=None: {
            "PLAY_SERVICE_CONTROL_DISABLED": False,
            "PLAY_SERVICE_PUBLIC_URL": "https://public.example.com",
            "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
            "PLAY_SERVICE_REQUEST_TIMEOUT": 30,
            "PLAY_SERVICE_ALLOW_NEW_SESSIONS": True,
        }.get(key, default)

        with patch("app.services.play_service_control_service.has_app_context", return_value=True):
            with patch("app.services.play_service_control_service._secret_present_in_app", return_value=True):
                with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
                    with patch("app.services.play_service_control_service.run_connectivity_test") as mock_test:
                        mock_load.return_value = {"applied_desired": {"mode": MODE_REMOTE}}
                        mock_test.return_value = {
                            "checks": [
                                {"id": "health", "ok": True},
                                {"id": "readiness", "ok": True},
                            ]
                        }

                        observed = build_observed_state(app)

                        assert observed["config_complete"] is True
                        assert observed["effective_enabled"] is True


class TestControlPayloadFunctions:
    """Tests for control payload API functions."""

    def test_get_control_payload(self):
        """Test getting complete control payload."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_CONTROL_DISABLED": False,
            "PLAY_SERVICE_PUBLIC_URL": "https://public.example.com",
            "PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com",
            "PLAY_SERVICE_REQUEST_TIMEOUT": 30,
            "PLAY_SERVICE_ALLOW_NEW_SESSIONS": True,
        }.get(key)

        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service.build_observed_state") as mock_obs:
                with patch("app.services.play_service_control_service.has_app_context", return_value=True):
                    mock_load.return_value = {
                        "desired": {"mode": MODE_REMOTE},
                        "applied_at": "2026-01-01T00:00:00Z",
                        "apply_ok": True,
                    }
                    mock_obs.return_value = {"effective_mode": MODE_REMOTE}

                    payload = get_control_payload(app)

                    assert "desired_state" in payload
                    assert "observed_state" in payload
                    assert "capabilities" in payload
                    assert "generated_at" in payload

    def test_save_desired_valid(self):
        """Test saving valid desired state."""
        app = MagicMock()

        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._persist_document") as mock_persist:
                with patch("app.services.play_service_control_service.has_app_context", return_value=True):
                    mock_load.return_value = {}

                    body = {
                        "mode": MODE_REMOTE,
                        "enabled": True,
                        "public_url": "https://public.example.com",
                        "internal_url": "https://internal.example.com",
                        "request_timeout_ms": 30000,
                    }

                    result = save_desired(app, body, user_id=123)

                    assert result["saved"] is True
                    assert "desired_state" in result
                    assert result["validation_errors"] == []

    def test_save_desired_invalid(self):
        """Test saving invalid desired state."""
        app = MagicMock()

        body = {"mode": "invalid_mode"}
        result = save_desired(app, body, user_id=123)

        assert result["saved"] is False
        assert len(result["validation_errors"]) > 0

    def test_apply_desired_success(self):
        """Test successful apply of desired state."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_SHARED_SECRET": "secret",
        }.get(key)

        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._persist_document") as mock_persist:
                with patch("app.services.play_service_control_service.has_app_context", return_value=True):
                    with patch("app.services.play_service_control_service.build_observed_state") as mock_obs:
                        mock_load.return_value = {
                            "desired": {
                                "mode": MODE_REMOTE,
                                "enabled": True,
                                "public_url": "https://public.example.com",
                                "internal_url": "https://internal.example.com",
                                "request_timeout_ms": 30000,
                                "allow_new_sessions": True,
                            }
                        }
                        mock_obs.return_value = {"effective_mode": MODE_REMOTE}

                        result = apply_desired(app, user_id=123)

                        assert result["ok"] is True
                        assert "applied_state" in result

    def test_apply_desired_no_saved_state(self):
        """Test apply fails when no desired state saved."""
        app = MagicMock()

        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service.build_observed_state") as mock_obs:
                with patch("app.services.play_service_control_service.has_app_context", return_value=True):
                    mock_load.return_value = {"desired": None}
                    mock_obs.return_value = {}

                    result = apply_desired(app, user_id=123)

                    assert result["ok"] is False

    def test_run_test_persist_success(self):
        """Test successful test persistence."""
        app = MagicMock()
        app.config.get.side_effect = lambda key: {
            "PLAY_SERVICE_SHARED_SECRET": "secret",
        }.get(key)

        with patch("app.services.play_service_control_service._load_raw_document") as mock_load:
            with patch("app.services.play_service_control_service._persist_document") as mock_persist:
                with patch("app.services.play_service_control_service.has_app_context", return_value=True):
                    with patch("app.services.play_service_control_service.run_connectivity_test") as mock_test:
                        mock_load.return_value = {
                            "desired": {
                                "mode": MODE_REMOTE,
                                "enabled": True,
                                "public_url": "https://public.example.com",
                                "internal_url": "https://internal.example.com",
                                "request_timeout_ms": 30000,
                                "allow_new_sessions": True,
                            }
                        }
                        mock_test.return_value = {"overall_ok": True, "checks": []}

                        result = run_test_persist(app, user_id=123)

                        assert result["ok"] is True
                        mock_persist.assert_called_once()
