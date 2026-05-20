"""Compatibility facade for the split LangGraph runtime executor."""
from __future__ import annotations

import sys as _sys

from ai_stack.langgraph.runtime_executor import public as _public

globals().update(_public.__dict__)
_sys.modules[__name__] = _public
