"""Repository-root pytest path hygiene for monorepo test execution."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
for candidate in (REPO_ROOT, REPO_ROOT / "backend", REPO_ROOT / "'fy'-suites"):
    text = str(candidate)
    if candidate.exists() and text not in sys.path:
        sys.path.insert(0, text)


def _available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


_BACKEND_RUNTIME_READY = _available("flask") and _available("sqlalchemy")
pytest_plugins = ["backend.tests.conftest"] if _BACKEND_RUNTIME_READY else []
