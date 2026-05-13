"""Tests for Langfuse per-trace environment resolution."""

from __future__ import annotations

import os

import pytest

from story_runtime_core.langfuse_tracing_environment import (
    WOS_LANGFUSE_ENV_AI_TESTING,
    WOS_LANGFUSE_ENV_TESTS,
    resolve_langfuse_environment,
)


def test_live_ui_live_tier_uses_backend_default_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WOS_AI_AGENT_TESTING", raising=False)
    assert (
        resolve_langfuse_environment("live_ui", "live", default="staging")
        == "staging"
    )


def test_pytest_without_agent_returns_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo (path)")
    monkeypatch.delenv("WOS_AI_AGENT_TESTING", raising=False)
    assert resolve_langfuse_environment(None, None, default="development") == WOS_LANGFUSE_ENV_TESTS


def test_pytest_with_agent_flag_returns_ai_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo (path)")
    monkeypatch.setenv("WOS_AI_AGENT_TESTING", "1")
    assert (
        resolve_langfuse_environment(None, None, default="development")
        == WOS_LANGFUSE_ENV_AI_TESTING
    )


def test_live_ui_live_under_pytest_uses_tests_not_backend_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pytest is detected before live_ui routing so Langfuse test traces stay in ``tests``."""
    monkeypatch.delenv("WOS_LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo (path)")
    monkeypatch.delenv("WOS_AI_AGENT_TESTING", raising=False)
    assert resolve_langfuse_environment("live_ui", "live", default="staging") == WOS_LANGFUSE_ENV_TESTS


def test_explicit_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_LANGFUSE_TRACING_ENVIRONMENT", "staging-qa")
    assert resolve_langfuse_environment("live_ui", "live", default="development") == "staging-qa"
