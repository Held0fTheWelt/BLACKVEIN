"""Compatibility namespace for tests importing ``world_engine.*``.

This maps to the repository's historical ``world-engine/`` directory so
legacy imports like ``world_engine.app.runtime...`` continue to resolve.
"""

from __future__ import annotations

from pathlib import Path

# Expose world-engine/ as namespace package search root.
_repo_root = Path(__file__).resolve().parents[1]
_legacy_root = _repo_root / "world-engine"
__path__ = [str(_legacy_root)]  # type: ignore[name-defined]

