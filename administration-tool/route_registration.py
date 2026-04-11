"""Flask routes, proxy, and security handlers for administration-tool (DS-015 facade)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from flask import Flask

# administration-tool lädt diese Datei per importlib ohne Paketkontext — Geschwister-Module importierbar machen.
_rp_dir = str(Path(__file__).resolve().parent)
if _rp_dir not in sys.path:
    sys.path.insert(0, _rp_dir)

from route_registration_manage import register_manage_routes
from route_registration_pages import register_public_and_forum_routes
from route_registration_proxy import (
    PROXY_ALLOWED_HEADERS,
    PROXY_ALLOWLIST_PREFIXES,
    PROXY_DANGEROUS_HEADERS,
    PROXY_DENYLIST_PREFIXES,
    register_proxy_routes,
)
from route_registration_security import register_security_hooks

__all__ = [
    "PROXY_ALLOWLIST_PREFIXES",
    "PROXY_DENYLIST_PREFIXES",
    "PROXY_DANGEROUS_HEADERS",
    "PROXY_ALLOWED_HEADERS",
    "register_routes",
]


def register_routes(
    app: Flask,
    *,
    inject_config: Callable[[], dict[str, Any]],
    backend_origin_fn: Callable[[], str | None],
    app_module: ModuleType,
) -> None:
    @app.context_processor
    def _inject_config_processor():
        """Register inject_config as a context processor."""
        return inject_config()

    register_proxy_routes(app, app_module)
    register_public_and_forum_routes(app)
    register_manage_routes(app)
    register_security_hooks(app, backend_origin_fn=backend_origin_fn)
