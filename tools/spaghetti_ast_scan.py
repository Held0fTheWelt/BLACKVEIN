"""Deprecated shim — forwards to the canonical script under ``'fy'-suites/despaghettify/tools/``.

Prefer: ``python -m despaghettify.tools`` (hub CLI) or run
``python "./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"`` from the repo root.
This file will be removed after downstream callers migrate.
"""
from __future__ import annotations

import runpy
import warnings
from pathlib import Path

warnings.warn(
    "tools/spaghetti_ast_scan.py is deprecated; use "
    "`python \"./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py\"` or `python -m despaghettify.tools check`. "
    "This shim will be removed in a future release.",
    DeprecationWarning,
    stacklevel=1,
)

_root = Path(__file__).resolve().parent.parent
_target = _root / "'fy'-suites" / "despaghettify" / "tools" / "spaghetti_ast_scan.py"
if not _target.is_file():
    raise SystemExit(
        f"Missing canonical script: {_target.relative_to(_root)} — restore 'fy'-suites/despaghettify or use "
        "`python -m despaghettify.tools check` from the repo root."
    )
runpy.run_path(str(_target), run_name="__main__")
