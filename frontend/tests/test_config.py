"""Tests for frontend configuration helpers."""
from __future__ import annotations

from app.config import env_bool


def test_env_bool_truthy(monkeypatch):
    monkeypatch.setenv("MY_TEST_FLAG", "on")
    assert env_bool("MY_TEST_FLAG", False) is True


def test_env_bool_falsey_unknown(monkeypatch):
    monkeypatch.setenv("MY_TEST_FLAG", "maybe")
    assert env_bool("MY_TEST_FLAG", True) is False


def test_env_bool_empty_uses_default(monkeypatch):
    monkeypatch.delenv("MY_TEST_FLAG_ABSENT", raising=False)
    assert env_bool("MY_TEST_FLAG_ABSENT", True) is True
