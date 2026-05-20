"""Tests for ai_turn_generation.py."""
from unittest.mock import MagicMock, call, patch

import pytest

from app.runtime.ai.ai_failure_recovery import AIFailureClass
from app.runtime.ai_turn.ai_turn_generation import run_adapter_generation_with_retry


class TestRunAdapterGenerationWithRetry:
    """Tests for run_adapter_generation_with_retry function."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter."""
        return MagicMock()

    @pytest.fixture
    def mock_retry_policy(self):
        """Create a mock retry policy."""
        policy = MagicMock()
        policy.MAX_RETRIES = 3
        policy.is_retryable_failure = MagicMock(return_value=True)
        return policy

    @pytest.fixture
    def mock_callbacks(self):
        """Create mock callback functions."""
        return {
            "build_request": MagicMock(),
            "enrich_request": MagicMock(),
            "mark_reduced_context": MagicMock(),
        }

    def test_successful_response_first_attempt(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test successful response on first attempt."""
        success_response = MagicMock(error=None, raw_output="successful output")
        mock_callbacks["build_request"].return_value = MagicMock()

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.return_value = success_response

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success_response
            assert attempt == 1
            mock_callbacks["build_request"].assert_called_once_with(1)
            mock_callbacks["enrich_request"].assert_called_once()
            mock_callbacks["mark_reduced_context"].assert_not_called()

    def test_retry_on_error_then_success(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test retry on error followed by successful response."""
        error_response = MagicMock(error="Some error", raw_output="")
        success_response = MagicMock(error=None, raw_output="recovered output")
        mock_callbacks["build_request"].return_value = MagicMock()

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.side_effect = [error_response, success_response]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success_response
            assert attempt == 2
            assert mock_callbacks["mark_reduced_context"].call_count == 1
            # build_request called twice (attempt 1 and 2)
            assert mock_callbacks["build_request"].call_count == 2

    def test_retry_on_empty_output(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test retry on empty output."""
        empty_response = MagicMock(error=None, raw_output="   ")  # whitespace only
        success_response = MagicMock(error=None, raw_output="valid output")
        mock_callbacks["build_request"].return_value = MagicMock()

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.side_effect = [empty_response, success_response]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success_response
            assert attempt == 2

    def test_timeout_failure_class_detection(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test that timeout errors are correctly classified."""
        timeout_response = MagicMock(
            error="adapter_generate_timeout: 30000ms exceeded", raw_output=""
        )
        success_response = MagicMock(error=None, raw_output="recovered")
        mock_callbacks["build_request"].return_value = MagicMock()

        def is_retryable(failure_class):
            return failure_class in (
                AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE,
                AIFailureClass.ADAPTER_ERROR,
            )

        mock_retry_policy.is_retryable_failure.side_effect = is_retryable

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.side_effect = [timeout_response, success_response]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success_response
            assert attempt == 2

    def test_non_retryable_failure_stops_retrying(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test that non-retryable failures stop the retry loop."""
        error_response = MagicMock(error="Unrecoverable error", raw_output="")
        mock_callbacks["build_request"].return_value = MagicMock()
        mock_retry_policy.is_retryable_failure.return_value = False

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.return_value = error_response

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == error_response
            assert attempt == 1
            # mark_reduced_context should not be called if we don't retry
            mock_callbacks["mark_reduced_context"].assert_not_called()

    def test_max_retries_exhausted(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test that retry loop stops at MAX_RETRIES."""
        error_response = MagicMock(error="Error", raw_output="")
        mock_callbacks["build_request"].return_value = MagicMock()
        mock_retry_policy.is_retryable_failure.return_value = True
        mock_retry_policy.MAX_RETRIES = 3

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.return_value = error_response

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == error_response
            assert attempt == 3  # Should have attempted 3 times max
            assert mock_callbacks["build_request"].call_count == 3

    def test_starting_attempt_parameter(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test that starting_attempt parameter is respected."""
        success_response = MagicMock(error=None, raw_output="output")
        mock_callbacks["build_request"].return_value = MagicMock()

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.return_value = success_response

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
                starting_attempt=2,
            )

            assert response == success_response
            assert attempt == 2
            # build_request called at initialization and once in the loop with starting_attempt > 1
            assert mock_callbacks["build_request"].call_count == 2
            # All calls should be with attempt 2
            for call_obj in mock_callbacks["build_request"].call_args_list:
                assert call_obj[0][0] == 2

    def test_multiple_retries_before_success(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test multiple retries before successful response."""
        error1 = MagicMock(error="Error 1", raw_output="")
        error2 = MagicMock(error="Error 2", raw_output="")
        success = MagicMock(error=None, raw_output="success")
        mock_callbacks["build_request"].return_value = MagicMock()
        mock_retry_policy.is_retryable_failure.return_value = True

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.side_effect = [error1, error2, success]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success
            assert attempt == 3
            assert mock_callbacks["mark_reduced_context"].call_count == 2

    def test_null_output_treated_as_empty(self, mock_adapter, mock_retry_policy, mock_callbacks):
        """Test that None output is treated as empty."""
        null_response = MagicMock(error=None, raw_output=None)
        success_response = MagicMock(error=None, raw_output="output")
        mock_callbacks["build_request"].return_value = MagicMock()
        mock_retry_policy.is_retryable_failure.return_value = True

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            mock_generate.side_effect = [null_response, success_response]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            assert response == success_response
            assert attempt == 2

    def test_enrich_request_called_on_each_attempt(
        self, mock_adapter, mock_retry_policy, mock_callbacks
    ):
        """Test that enrich_request is called for each attempt."""
        success_response = MagicMock(error=None, raw_output="output")
        mock_request = MagicMock()
        mock_callbacks["build_request"].return_value = mock_request
        mock_retry_policy.is_retryable_failure.return_value = True

        with patch(
            "app.runtime.ai_turn.ai_turn_generation.generate_with_timeout"
        ) as mock_generate:
            error_response = MagicMock(error="Error", raw_output="")
            mock_generate.side_effect = [error_response, success_response]

            response, attempt = run_adapter_generation_with_retry(
                execution_adapter=mock_adapter,
                retry_policy=mock_retry_policy,
                adapter_generate_timeout_ms=30000,
                build_request=mock_callbacks["build_request"],
                enrich_request=mock_callbacks["enrich_request"],
                mark_reduced_context=mock_callbacks["mark_reduced_context"],
            )

            # enrich_request should be called twice (once for each attempt)
            assert mock_callbacks["enrich_request"].call_count == 2
