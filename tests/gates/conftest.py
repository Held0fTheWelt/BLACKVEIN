"""Gate test path configuration.

Prepends ``backend/`` then inserts ``world-engine/`` on ``sys.path`` so
``import app`` resolves to the Flask backend (governance, builtins) while
world-engine sources remain importable for paths that do not clash with
``app`` (see gate docstrings / ``backend.app`` imports).

World-engine's ``app`` package and backend's ``app`` package are distinct;
only one can own the ``app`` name. Gate tests that need world-engine imports
must use ``backend.app``-style paths, repo-relative file checks, or LDSS
(``ai_stack``) seams where applicable.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
WORLD_ENGINE_DIR = REPO_ROOT / "world-engine"

# Backend ``app`` must win over world-engine's ``app`` for ``from app.governance`` / builtins gates.
_backend_str = str(BACKEND_DIR)
if BACKEND_DIR.exists() and _backend_str not in sys.path:
    sys.path.insert(0, _backend_str)

# Only add world-engine if it's not already on the path
_world_engine_str = str(WORLD_ENGINE_DIR)
if WORLD_ENGINE_DIR.exists() and _world_engine_str not in sys.path:
    sys.path.insert(1, _world_engine_str)
