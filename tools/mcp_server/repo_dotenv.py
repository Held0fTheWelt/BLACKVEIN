"""Bootstrap MCP process env from the repository-root ``.env``.

After ``docker-up.py init-env`` / ``up``, the shared platform secret
``INTERNAL_RUNTIME_CONFIG_TOKEN`` (internal runtime / "transaction" trust token
used by world-engine, play-service, and Langfuse credential fetch) lives there.
MCP stdio loads it automatically so operators need no extra token generation step.
"""

from __future__ import annotations

import os
from pathlib import Path

# Keys MCP commonly needs from the same `.env` as Docker services (only fill if unset).
_DOTENV_KEYS = frozenset(
    {
        "INTERNAL_RUNTIME_CONFIG_TOKEN",
        "BACKEND_INTERNAL_RUNTIME_CONFIG_TOKEN",
        "RUNTIME_CONFIG_TOKEN",
        "BACKEND_BASE_URL",
        "BACKEND_RUNTIME_CONFIG_URL",
        "BACKEND_INTERNAL_URL",
        "LANGFUSE_MCP_ENABLED",
        "LANGFUSE_MCP_BASE_URL",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_HOST",
        "MCP_SERVICE_TOKEN",
        "BACKEND_BEARER_TOKEN",
    }
)


def bootstrap_repo_environment() -> None:
    """Load ``<repo>/.env`` into the process environment (does not override existing vars)."""
    from tools.mcp_server.config import get_repo_root

    env_path = get_repo_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        _fallback_parse_dotenv(env_path)


def _fallback_parse_dotenv(path: Path) -> None:
    """Minimal parser when ``python-dotenv`` is not installed."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if key not in _DOTENV_KEYS or key in os.environ:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val
