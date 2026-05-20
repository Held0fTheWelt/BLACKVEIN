"""Legacy Langfuse evidence facade.

Exports the compatibility wrapper for emitting evidence observations to Langfuse from legacy source chunks.
"""
from __future__ import annotations

from ._deps import *
from ._legacy_loader import exec_top_level

exec_top_level(__name__, '_emit_langfuse_evidence_observations')


__all__ = ['_emit_langfuse_evidence_observations']
