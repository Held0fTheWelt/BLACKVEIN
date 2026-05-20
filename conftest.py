"""Repository-root pytest path hygiene for monorepo test execution."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

# world-engine ``app.config`` fails fast when ``PLAY_SERVICE_SECRET`` is unset unless
# ``FLASK_ENV`` is exactly ``test``. Suites such as ``ai_stack/tests`` import
# ``app.story_runtime`` without loading ``world-engine/tests/conftest.py``; align env here
# so those imports work in CI and ``python -m pytest`` from the repo root.
_flask_env = (os.getenv("FLASK_ENV") or "").strip().lower()
_play_secret = (
    os.getenv("PLAY_SERVICE_SECRET") or os.getenv("PLAY_SERVICE_SHARED_SECRET") or ""
).strip()
if _flask_env not in {"production", "staging"} and not _play_secret:
    os.environ["FLASK_ENV"] = "test"
    os.environ.setdefault("PLAY_SERVICE_SECRET", "test-secret-key-for-unit-tests")

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
WORLD_ENGINE_DIR = REPO_ROOT / "world-engine"

# Match tests/gates/conftest.py: backend ``app`` must win over world-engine ``app`` for
# ``from app.governance`` / ``from app.content.builtins`` in foundation gates.
# world-engine stays importable at index 1 for repo-relative scans and ``backend.app.*``.
_backend_str = str(BACKEND_DIR)
if BACKEND_DIR.exists() and _backend_str not in sys.path:
    sys.path.insert(0, _backend_str)
_world_engine_str = str(WORLD_ENGINE_DIR)
if WORLD_ENGINE_DIR.exists() and _world_engine_str not in sys.path:
    sys.path.insert(1, _world_engine_str)

for candidate in (REPO_ROOT, REPO_ROOT / "'fy'-suites"):
    text = str(candidate)
    if candidate.exists() and text not in sys.path:
        sys.path.append(text)


def _available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _active_pytest_suite() -> str:
    return (os.environ.get("WOS_PYTEST_SUITE") or "").strip().lower()


_BACKEND_RUNTIME_READY = _available("flask") and _available("sqlalchemy")

# Gate tests (tests/gates/*) do not use backend Flask/db fixtures; they need path hygiene
# only (see tests/gates/conftest.py). Loading backend.tests.conftest at collection time
# forces ``from app import create_app`` before path order is stable and breaks collect-only.
_LIGHTWEIGHT_ROOT_SUITES = frozenset(
    {
        "gates",
        "ai_stack",
        "story_runtime_core",
        "root_core",
        "root_integration",
        "root_branching",
        "root_tools",
        "root_requirements_hygiene",
        "root_experience_scoring",
    }
)
_suite = _active_pytest_suite()
_LOAD_BACKEND_CONFTEST_PLUGIN = (
    _BACKEND_RUNTIME_READY
    and _suite not in _LIGHTWEIGHT_ROOT_SUITES
    and _suite != "gates"
)
pytest_plugins = ["backend.tests.conftest"] if _LOAD_BACKEND_CONFTEST_PLUGIN else []
