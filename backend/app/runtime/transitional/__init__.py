"""Deprecated transitional ``app.runtime`` modules (in-process session / turn / AI execution).

``from app.runtime.transitional import turn_executor`` loads ``app.runtime.turn_executor``.
These paths support tests, operator tooling, and MCP — **not** the World Engine live runtime.

See ``docs/technical/architecture/backend-runtime-classification.md`` and
``app.runtime.package_classification.TRANSITIONAL_RUNTIME_MODULE_NAMES``.
"""

from __future__ import annotations

import importlib
from typing import Any

from app.runtime.package_classification import TRANSITIONAL_RUNTIME_MODULE_NAMES

__all__ = sorted(TRANSITIONAL_RUNTIME_MODULE_NAMES)


def __getattr__(name: str) -> Any:
    if name not in TRANSITIONAL_RUNTIME_MODULE_NAMES:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}; "
            f"see app.runtime.package_classification.TRANSITIONAL_RUNTIME_MODULE_NAMES"
        )
    return importlib.import_module(f"app.runtime.{name}")


def __dir__() -> list[str]:
    return sorted(__all__)
