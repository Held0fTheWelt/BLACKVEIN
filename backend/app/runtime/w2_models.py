"""Temporary compatibility bridge for legacy imports of ``app.runtime.w2_models``.

Prefer ``from app.runtime.runtime_models import ...`` for new code.
"""

from __future__ import annotations

from app.runtime.runtime_models import *  # noqa: F403
from app.runtime import runtime_models

__all__ = list(runtime_models.__all__)
