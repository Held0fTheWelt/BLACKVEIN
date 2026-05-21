"""Bounded semantic scene planner for the GoC runtime.

This module is the stable public import path. The implementation lives in real
modules under ``ai_stack.story_runtime.semantic_planner.semantic_scene_plan``.
"""

from __future__ import annotations

from .semantic_scene_plan import (
    SEMANTIC_SCENE_PLANNER_VERSION,
    build_semantic_scene_plan_enrichment,
)

__all__ = [
    "SEMANTIC_SCENE_PLANNER_VERSION",
    "build_semantic_scene_plan_enrichment",
]
