"""Langfuse verification MCP handlers.

The monolithic registry handler is split into named source slices in this
package.  The package exports the same helper and builder functions while each
physical file stays small enough for the handler-maintenance gate.
"""

from __future__ import annotations

from .loader import load_into as _load_langfuse_verify_slices

_load_langfuse_verify_slices(globals())

_EXPORTED_PREFIXES = (
    "_extract_",
    "_get_",
    "_langfuse_",
    "_runtime_aspect_",
    "_trace_summary",
)

__all__ = sorted(
    name
    for name in globals()
    if name == "build_langfuse_verify_mcp_handlers"
    or name.startswith(_EXPORTED_PREFIXES)
)
