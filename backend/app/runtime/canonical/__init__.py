"""Canonical reusable ``app.runtime`` modules (schemas, policies, presenters, contracts).

Import a submodule by name, e.g. ``from app.runtime.canonical import runtime_models`` loads
``app.runtime.runtime_models``. This namespace does **not** imply the Flask backend hosts
authoritative live play; see ``docs/technical/architecture/backend-runtime-classification.md``.

The authoritative module list is ``app.runtime.package_classification.CANONICAL_RUNTIME_MODULE_NAMES``.
"""

from __future__ import annotations

import importlib
from typing import Any

from app.runtime.package_classification import CANONICAL_RUNTIME_MODULE_NAMES

__all__ = sorted(CANONICAL_RUNTIME_MODULE_NAMES)


def __getattr__(name: str) -> Any:
    if name not in CANONICAL_RUNTIME_MODULE_NAMES:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}; "
            f"see app.runtime.package_classification.CANONICAL_RUNTIME_MODULE_NAMES"
        )
    return importlib.import_module(f"app.runtime.{name}")


def __dir__() -> list[str]:
    return sorted(__all__)
