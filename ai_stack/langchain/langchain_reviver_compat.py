"""Default ``Reviver(allowed_objects='core')`` before LangGraph imports serde.

LangGraph instantiates ``LC_REVIVER = Reviver()`` in ``checkpoint/serde/jsonplus``.
Since langchain-core 1.3.3, ``Reviver()`` with implicit ``allowed_objects=None`` emits
``LangChainPendingDeprecationWarning`` even though behavior already matches ``'core'``.
We mirror that default explicitly so the warning is never issued.
"""
from __future__ import annotations

import functools
from typing import Any

_applied: bool = False


def ensure_langchain_reviver_explicit_core() -> None:
    """Patch ``Reviver.__init__`` once per interpreter (idempotent)."""
    global _applied
    if _applied:
        return
    from langchain_core.load.load import Reviver

    _original_init = Reviver.__init__

    @functools.wraps(_original_init)
    def _patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
        if "allowed_objects" in kwargs:
            if kwargs.get("allowed_objects") is None:
                kwargs = {**kwargs, "allowed_objects": "core"}
            return _original_init(self, *args, **kwargs)
        if len(args) >= 1:
            if args[0] is None:
                return _original_init(self, *("core", *args[1:]), **kwargs)
            return _original_init(self, *args, **kwargs)
        return _original_init(self, *args, allowed_objects="core", **kwargs)

    Reviver.__init__ = _patched_init  # type: ignore[method-assign]
    _applied = True
