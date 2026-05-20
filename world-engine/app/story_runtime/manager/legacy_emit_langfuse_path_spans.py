"""Legacy Langfuse path-span facade.

Exports the compatibility wrapper for emitting Langfuse path spans while the observability path remains source-chunked.
"""
from __future__ import annotations

from ._deps import *
from ._legacy_loader import exec_top_level

exec_top_level(__name__, '_emit_langfuse_path_spans')


__all__ = ['_emit_langfuse_path_spans']
