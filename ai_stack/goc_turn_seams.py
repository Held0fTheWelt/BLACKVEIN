"""Compatibility shim for the story-runtime turn seam package move."""

from __future__ import annotations

from importlib import import_module

_module = import_module("ai_stack.story_runtime.turn.goc_turn_seams")

for _name, _value in vars(_module).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

__all__ = list(getattr(_module, "__all__", [name for name in globals() if not name.startswith("__")]))
