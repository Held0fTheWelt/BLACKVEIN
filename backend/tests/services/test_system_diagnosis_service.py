"""Tests for system_diagnosis_service.py - System health diagnosis."""
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pytest

from app.services.system_diagnosis_service import (
    _utc_now_iso,
    _play_internal_headers_from_config,
    _internal_base_url_from_config,
    _check_backend_api,
    _check_database,
    _check_play_service_configuration,
    _check_published_feed,
    _check_ai_stack_readiness,
    _run_with_timeout,
    _check_ai_stack_readiness_bounded,
    _check_published_feed_bounded,
    _check_database_bounded,
    _prereq_skip_play_runtime,
    _prereq_skip_play_ready,
    _resolve_overall,
    _summary_counts,
    _build_diagnosis,
    get_system_diagnosis,
    reset_diagnosis_cache_for_tests,
)


class TestUtilities:
    """Tests for utility functions."""

    def test_utc_now_iso_format(self):
        """Test UTC ISO format generation."""
        result = _utc_now_iso()
        assert isinstance(result, str)
        assert result.endswith("Z")
        assert "T" in result
        # Should parse as ISO format
        datetime.fromisoformat(result.replace("Z", "+00:00"))

    def test_play_internal_headers_without_key(self):
        """Test headers without API key."""
        cfg = {}
        headers = _play_internal_headers_from_config(cfg)
        assert headers["Accept"] == "application/json"
        assert "X-Play-Service-Key" not in headers

    def test_play_internal_headers_with_key(self):
        """Test headers with API key."""
        cfg = {"PLAY_SERVICE_INTERNAL_API_KEY": "api-key-123"}
        headers = _play_internal_headers_from_config(cfg)
        assert headers["Accept"] == "application/json"
        assert headers["X-Play-Service-Key"] == "api-key-123"

    def test_play_internal_headers_empty_key(self):
        """Test headers with empty API key."""
        cfg = {"PLAY_SERVICE_INTERNAL_API_KEY": "   "}
        headers = _play_internal_headers_from_config(cfg)
        assert "X-Play-Service-Key" not in headers

    def test_internal_base_url_valid(self):
        """Test extracting valid base URL."""
        cfg = {"PLAY_SERVICE_INTERNAL_URL": "https://internal.example.com/"}
        result = _internal_base_url_from_config(cfg)
        assert result == "https://internal.example.com"

    def test_internal_base_url_empty(self):
        """Test with empty or missing URL."""
        cfg = {}
        result = _internal_base_url_from_config(cfg)
        assert result is None

    def test_internal_base_url_whitespace(self):
        """Test with whitespace-only URL."""
        cfg = {"PLAY_SERVICE_INTERNAL_URL": "   "}
        result = _internal_base_url_from_config(cfg)
        assert result is None


class TestBackendHealthCheck:
    """Tests for _check_backend_api function."""

    def test_check_backend_api_success(self):
        """Test successful backend health check."""
        with patch("app.services.system_diagnosis_service.httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _check_backend_api("https://localhost:5000")

            assert result["id"] == "backend_api"
            assert result["status"] == "running"
            assert result["critical"] is True
            assert "latency_ms" in result

    def test_check_backend_api_http_error(self):
        """Test backend health check with HTTP error."""
        with patch("app.services.system_diagnosis_service.httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _check_backend_api("https://localhost:5000")

            assert result["status"] == "fail"
            assert "500" in result["message"]
            assert result["critical"] is True

    def test_check_backend_api_invalid_response(self):
        """Test backend health check with invalid JSON response."""
        with patch("app.services.system_diagnosis_service.httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{}'
            mock_response.json.return_value = {}
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _check_backend_api("https://localhost:5000")

            assert result["status"] == "fail"
            assert "missing status ok" in result["message"]

    def test_check_backend_api_timeout(self):
        """Test backend health check timeout."""
        with patch("app.services.system_diagnosis_service.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("timeout")
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = _check_backend_api("https://localhost:5000")

            assert result["status"] == "fail"
            assert result["critical"] is True


class TestDatabaseHealthCheck:
    """Tests for _check_database function."""

    def test_check_database_success(self):
        """Test successful database health check."""
        with patch("app.services.system_diagnosis_service.db") as mock_db:
            mock_db.session.execute.return_value.scalar.return_value = 1

            result = _check_database()

            assert result["id"] == "database"
            assert result["status"] == "running"
            assert result["critical"] is True
            assert "latency_ms" in result

    def test_check_database_error(self):
        """Test database health check with error."""
        with patch("app.services.system_diagnosis_service.db") as mock_db:
            mock_db.session.execute.side_effect = Exception("Connection failed")

            result = _check_database()

            assert result["id"] == "database"
            assert result["status"] == "fail"
            assert result["critical"] is True


class TestPlayServiceConfigCheck:
    """Tests for _check_play_service_configuration function."""

    def test_play_service_config_complete(self):
        """Test when play service config is complete."""
        with patch("app.services.system_diagnosis_service.has_complete_play_service_config") as mock_check:
            mock_check.return_value = True

            result = _check_play_service_configuration()

            assert result["id"] == "play_service_configuration"
            assert result["status"] == "running"
            assert result["critical"] is True

    def test_play_service_config_incomplete(self):
        """Test when play service config is incomplete."""
        with patch("app.services.system_diagnosis_service.has_complete_play_service_config") as mock_check:
            mock_check.return_value = False

            result = _check_play_service_configuration()

            assert result["id"] == "play_service_configuration"
            assert result["status"] == "fail"
            assert result["critical"] is True


class TestPublishedFeedCheck:
    """Tests for _check_published_feed function."""

    def test_check_published_feed_success(self):
        """Test successful published feed check."""
        with patch("app.services.system_diagnosis_service.list_published_experience_payloads") as mock_list:
            mock_list.return_value = [{"id": "exp1"}, {"id": "exp2"}]

            result = _check_published_feed()

            assert result["id"] == "published_experiences_feed"
            assert result["status"] == "running"
            assert "latency_ms" in result

    def test_check_published_feed_empty(self):
        """Test published feed check with no experiences."""
        with patch("app.services.system_diagnosis_service.list_published_experience_payloads") as mock_list:
            mock_list.return_value = []

            result = _check_published_feed()

            assert result["id"] == "published_experiences_feed"
            assert result["status"] == "initialized"

    def test_check_published_feed_error(self):
        """Test published feed check with error."""
        with patch("app.services.system_diagnosis_service.list_published_experience_payloads") as mock_list:
            mock_list.side_effect = Exception("Database error")

            result = _check_published_feed()

            assert result["id"] == "published_experiences_feed"
            assert result["status"] == "fail"


class TestAIStackReadinessCheck:
    """Tests for _check_ai_stack_readiness function."""

    def test_check_ai_stack_readiness_success(self):
        """Test successful AI stack readiness check."""
        with patch("app.services.system_diagnosis_service.build_release_readiness_report") as mock_report:
            mock_report.return_value = {
                "overall_status": "ready",  # Correct key
                "components": [],
            }

            result = _check_ai_stack_readiness(trace_id="trace-123")

            assert result["id"] == "ai_stack_release_readiness"
            assert result["status"] == "running"
            assert "latency_ms" in result

    def test_check_ai_stack_readiness_error(self):
        """Test AI stack readiness check with error."""
        with patch("app.services.system_diagnosis_service.build_release_readiness_report") as mock_report:
            mock_report.side_effect = Exception("Build failed")

            result = _check_ai_stack_readiness(trace_id="trace-123")

            assert result["id"] == "ai_stack_release_readiness"
            assert result["status"] == "fail"


class TestRunWithTimeout:
    """Tests for _run_with_timeout function."""

    def test_run_with_timeout_success(self):
        """Test function completes within timeout."""
        def quick_func():
            return "success"

        with patch("app.services.system_diagnosis_service.ThreadPoolExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_future = MagicMock()
            mock_future.result.return_value = "success"
            mock_executor.submit.return_value = mock_future
            mock_executor_class.return_value.__enter__.return_value = mock_executor

            result = _run_with_timeout(quick_func, 1.0)
            assert result == "success"

    def test_run_with_timeout_exceeded(self):
        """Test function exceeds timeout."""
        def slow_func():
            import time
            time.sleep(10)

        with patch("app.services.system_diagnosis_service.ThreadPoolExecutor") as mock_executor_class:
            mock_executor = MagicMock()
            mock_future = MagicMock()
            from concurrent.futures import TimeoutError
            mock_future.result.side_effect = TimeoutError()
            mock_executor.submit.return_value = mock_future
            mock_executor_class.return_value.__enter__.return_value = mock_executor

            result = _run_with_timeout(slow_func, 0.1)
            assert result is None


class TestPrerequiteSkips:
    """Tests for prerequisite skip functions."""

    def test_prereq_skip_play_runtime(self):
        """Test play runtime skip response."""
        result = _prereq_skip_play_runtime("Config incomplete")
        assert result["id"] == "play_service_health"
        assert result["status"] == "fail"
        assert "Config incomplete" in result["message"]

    def test_prereq_skip_play_ready(self):
        """Test play ready skip response."""
        result = _prereq_skip_play_ready("Config incomplete")
        assert result["id"] == "play_service_readiness"
        assert result["status"] == "fail"
        assert "Config incomplete" in result["message"]


class TestOverallResolution:
    """Tests for _resolve_overall function."""

    def test_resolve_overall_all_running(self):
        """Test with all checks running."""
        checks = [
            {"status": "running"},
            {"status": "running"},
        ]
        result = _resolve_overall(checks)
        assert result == "running"

    def test_resolve_overall_with_initialized(self):
        """Test with initialized status."""
        checks = [
            {"status": "running"},
            {"status": "initialized"},
        ]
        result = _resolve_overall(checks)
        assert result == "initialized"

    def test_resolve_overall_with_failure(self):
        """Test with critical failure."""
        checks = [
            {"status": "running"},
            {"status": "fail", "critical": True},
        ]
        result = _resolve_overall(checks)
        assert result == "fail"

    def test_resolve_overall_non_critical_failure(self):
        """Test with non-critical failure."""
        checks = [
            {"status": "running", "critical": True},
            {"status": "fail"},  # non-critical failure
        ]
        result = _resolve_overall(checks)
        assert result == "initialized"

    def test_resolve_overall_empty(self):
        """Test with empty checks."""
        result = _resolve_overall([])
        # all() on empty sequence returns True, so "running" is returned
        assert result == "running"


class TestSummaryCounts:
    """Tests for _summary_counts function."""

    def test_summary_counts_mixed(self):
        """Test counting mixed statuses."""
        checks = [
            {"status": "running"},
            {"status": "running"},
            {"status": "initialized"},
            {"status": "fail"},
        ]
        result = _summary_counts(checks)
        assert result["running"] == 2
        assert result["initialized"] == 1
        assert result["fail"] == 1

    def test_summary_counts_empty(self):
        """Test counting empty checks."""
        result = _summary_counts([])
        assert result == {"running": 0, "initialized": 0, "fail": 0}


class TestBuildDiagnosis:
    """Tests for _build_diagnosis function."""

    def test_build_diagnosis_structure(self):
        """Test diagnosis structure generation."""
        with patch("app.services.system_diagnosis_service._check_backend_api") as mock_backend:
            with patch("app.services.system_diagnosis_service._check_database_bounded") as mock_db:
                with patch("app.services.system_diagnosis_service._check_play_service_configuration") as mock_play_cfg:
                    with patch("app.services.system_diagnosis_service._build_diagnosis") as mock_build:
                        mock_backend.return_value = {"id": "backend", "status": "running", "critical": True}
                        mock_db.return_value = {"id": "database", "status": "running", "critical": True}
                        mock_play_cfg.return_value = {"id": "play_cfg", "status": "ok"}
                        mock_build.return_value = {
                            "checks": [],
                            "overall_status": "ok",
                            "timestamp": "2026-01-01T00:00:00Z",
                        }

                        app = MagicMock()
                        result = _build_diagnosis(app, "https://localhost:5000", "trace-123")

                        assert isinstance(result, dict)
                        assert result.get("overall_status") == "ok"
                        assert "timestamp" in result
                        assert "checks" in result


class TestGetSystemDiagnosis:
    """Tests for get_system_diagnosis function."""

    def test_get_system_diagnosis_cache_hit(self):
        """Test diagnosis with cache."""
        reset_diagnosis_cache_for_tests()

        with patch("app.services.system_diagnosis_service._build_diagnosis") as mock_build:
            mock_build.return_value = {"status": "ok"}

            app = MagicMock()
            result1 = get_system_diagnosis(
                app,
                self_base_url="https://localhost:5000",
                refresh=False,
                trace_id="trace-123"
            )

            result2 = get_system_diagnosis(
                app,
                self_base_url="https://localhost:5000",
                refresh=False,
                trace_id="trace-123"
            )

            # With caching, build should be called only once
            assert isinstance(result1, dict)
            assert isinstance(result2, dict)
            assert mock_build.call_count == 1

    def test_get_system_diagnosis_force_refresh(self):
        """Test diagnosis with forced refresh."""
        reset_diagnosis_cache_for_tests()

        with patch("app.services.system_diagnosis_service._build_diagnosis") as mock_build:
            mock_build.return_value = {"status": "ok"}

            app = MagicMock()
            result = get_system_diagnosis(
                app,
                self_base_url="https://localhost:5000",
                refresh=True,
                trace_id="trace-123"
            )

            assert isinstance(result, dict)

    def test_reset_diagnosis_cache_for_tests(self):
        """Test cache reset function."""
        # Verify reset doesn't raise and cache is cleared
        with patch("app.services.system_diagnosis_service._build_diagnosis") as mock_build:
            mock_build.return_value = {"status": "ok"}

            # Fill cache
            app = MagicMock()
            get_system_diagnosis(app, self_base_url="https://localhost:5000", refresh=False, trace_id="trace-1")
            initial_call_count = mock_build.call_count

            # Reset should clear cache
            reset_diagnosis_cache_for_tests()

            # Next call should rebuild (not from cache)
            get_system_diagnosis(app, self_base_url="https://localhost:5000", refresh=False, trace_id="trace-1")
            assert mock_build.call_count > initial_call_count
