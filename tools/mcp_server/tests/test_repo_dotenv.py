"""Tests for repo-root ``.env`` bootstrap (INTERNAL_RUNTIME_CONFIG_TOKEN from docker-up)."""

from __future__ import annotations

from pathlib import Path


def test_bootstrap_repo_environment_loads_internal_token(monkeypatch, tmp_path: Path) -> None:
    from tools.mcp_server import repo_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text(
        'INTERNAL_RUNTIME_CONFIG_TOKEN="tok-from-dotenv"\n'
        "OTHER_SECRET=skip\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("tools.mcp_server.config.get_repo_root", lambda: tmp_path)
    monkeypatch.delenv("INTERNAL_RUNTIME_CONFIG_TOKEN", raising=False)

    repo_dotenv.bootstrap_repo_environment()

    import os

    assert os.environ.get("INTERNAL_RUNTIME_CONFIG_TOKEN") == "tok-from-dotenv"


def test_bootstrap_does_not_override_existing_token(monkeypatch, tmp_path: Path) -> None:
    from tools.mcp_server import repo_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("INTERNAL_RUNTIME_CONFIG_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setattr("tools.mcp_server.config.get_repo_root", lambda: tmp_path)
    monkeypatch.setenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "preset")

    repo_dotenv.bootstrap_repo_environment()

    import os

    assert os.environ.get("INTERNAL_RUNTIME_CONFIG_TOKEN") == "preset"


def test_fallback_parse_dotenv(monkeypatch, tmp_path: Path) -> None:
    from tools.mcp_server import repo_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text("INTERNAL_RUNTIME_CONFIG_TOKEN=fallback-val\n", encoding="utf-8")
    monkeypatch.delenv("INTERNAL_RUNTIME_CONFIG_TOKEN", raising=False)

    repo_dotenv._fallback_parse_dotenv(env_file)

    import os

    assert os.environ.get("INTERNAL_RUNTIME_CONFIG_TOKEN") == "fallback-val"
