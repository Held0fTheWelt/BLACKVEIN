"""Backend application package: path bootstrap and public factory entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

try:
    from ai_stack.langchain_reviver_compat import ensure_langchain_reviver_explicit_core

    ensure_langchain_reviver_explicit_core()
except ImportError:
    pass

from app.config import Config
from app.factory_app import create_app

__all__ = ["Config", "REPO_ROOT", "create_app"]
