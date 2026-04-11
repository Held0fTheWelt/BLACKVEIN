"""Bounded exploration — Re-Export; Implementierung in research_exploration_bounded_core (DS-022)."""

from __future__ import annotations

from ai_stack.research_exploration_bounded_core import (
    ExplorationResult,
    deterministic_contradiction_scan,
    run_bounded_exploration,
)

__all__ = [
    "ExplorationResult",
    "deterministic_contradiction_scan",
    "run_bounded_exploration",
]
