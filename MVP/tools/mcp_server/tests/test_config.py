import os
import pytest
from pathlib import Path
from tools.mcp_server.config import Config, get_repo_root


def test_config_loads_backend_url_from_env(monkeypatch):
    monkeypatch.setenv("BACKEND_BASE_URL", "http://example.com")
    config = Config()
    assert config.backend_url == "http://example.com"


def test_config_has_default_backend_url(monkeypatch):
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)
    config = Config()
    assert config.backend_url is not None
    assert config.backend_url.startswith("http")


def test_config_reads_bearer_token_optional(monkeypatch):
    monkeypatch.delenv("BACKEND_BEARER_TOKEN", raising=False)
    config = Config()
    assert config.bearer_token is None


def test_config_loads_bearer_token_from_env(monkeypatch):
    monkeypatch.setenv("BACKEND_BEARER_TOKEN", "token123")
    config = Config()
    assert config.bearer_token == "token123"


def test_get_repo_root_detects_content_folder():
    root = get_repo_root()
    assert root is not None
    assert (root / "content").exists()


def test_get_repo_root_override_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    root = get_repo_root()
    assert root == tmp_path


def test_config_request_timeout():
    config = Config()
    assert config.request_timeout_s == 5
