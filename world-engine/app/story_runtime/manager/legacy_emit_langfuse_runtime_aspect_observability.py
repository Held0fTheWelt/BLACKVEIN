"""Legacy runtime-aspect observability facade.

Exports compatibility runtime-aspect Langfuse emission assembled from ordered legacy source chunks.
"""
from __future__ import annotations

from ._deps import *
from ._legacy_loader import exec_top_level

exec_top_level(__name__, '_emit_langfuse_runtime_aspect_observability')


__all__ = ['_emit_langfuse_runtime_aspect_observability']
