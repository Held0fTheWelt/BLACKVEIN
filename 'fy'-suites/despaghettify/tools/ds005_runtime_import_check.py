#!/usr/bin/env python3
"""
DS-005: import frozen runtime modules in fixed order (cycle regression
check).

Run from repository root: python
"./'fy'-suites/despaghettify/tools/ds005_runtime_import_check.py"

Prepends ``backend/`` on sys.path so ``app.*`` resolves without
installing the package.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import repo_root

try:
    _REPO_ROOT = repo_root()
except RuntimeError:
    _REPO_ROOT = Path.cwd()
BACKEND_ROOT = _REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Frozen order for cycle regression; extend only with evidence (see DS-015 post artefacts).
FROZEN_RUNTIME_MODULES = [
    "app.runtime.turn_executor",
    "app.runtime.turn_executor_validated_pipeline_apply",
    "app.runtime.turn_executor_validated_pipeline_narrative_log",
    "app.runtime.turn_executor_validated_pipeline",
    "app.runtime.validators",
    "app.runtime.role_structured_decision",
    "app.runtime.ai_decision",
    "app.runtime.ai_failure_recovery",
    "app.runtime.ai_turn_executor",
    "app.runtime.turn_dispatcher",
    # DS-015: supervisor entry seam (after dispatcher; must import clean in this order)
    "app.runtime.supervisor_orchestrate_execute",
    "app.runtime.supervisor_orchestrator",
]


def main() -> int:
    """Implement ``main`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Process name one item at a time so main applies the same rule across the full
    # collection.
    for name in FROZEN_RUNTIME_MODULES:
        importlib.import_module(name)
        print(f"import_ok\t{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
