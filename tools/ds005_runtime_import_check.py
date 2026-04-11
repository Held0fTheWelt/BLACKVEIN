#!/usr/bin/env python3
"""DS-005: import frozen runtime modules in fixed order (cycle regression check).

Run from repository root:
  python tools/ds005_runtime_import_check.py

Prepends ``backend/`` on sys.path so ``app.*`` resolves without installing the package.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Order matches despaghettify/state/artifacts/.../session_*_DS-005b_pre_scope_frozen_modules.txt
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
]


def main() -> int:
    for name in FROZEN_RUNTIME_MODULES:
        importlib.import_module(name)
        print(f"import_ok\t{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
