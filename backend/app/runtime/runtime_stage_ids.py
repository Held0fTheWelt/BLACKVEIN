"""Shared stage identifiers for multi-stage runtime AI orchestration.

Kept separate from ``runtime_ai_stages`` so section helpers can import without cycles.
"""

from __future__ import annotations

from enum import Enum

RUNTIME_STAGE_SCHEMA_VERSION = "1"
RUNTIME_STAGE_META_KEY = "runtime_stage"
RUNTIME_STAGE_SCHEMA_META_KEY = "runtime_stage_schema_version"


class RuntimeStageId(str, Enum):
    """Canonical Runtime pipeline stage identifiers (cross-model orchestration)."""

    preflight = "preflight"
    signal_consistency = "signal_consistency"
    ranking = "ranking"
    synthesis = "synthesis"
    packaging = "packaging"


RANKING_SLM_ONLY_SKIP_REASON = "ranking_not_required_signal_allows_slm_only"
