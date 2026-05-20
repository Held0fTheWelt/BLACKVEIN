"""Compatibility package for NPC agency modules moved under story_runtime."""

from __future__ import annotations

from importlib import import_module
import sys

_MODULE_NAMES = (
    "goc_npc_transcript_projection",
    "npc_agency_claim_readiness",
    "npc_agency_contracts",
    "npc_agency_long_horizon",
    "npc_agency_planner",
    "npc_agency_realization",
    "npc_motivation_score_engine",
)

for _name in _MODULE_NAMES:
    _module = import_module(f"ai_stack.story_runtime.npc_agency.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module

__all__ = list(_MODULE_NAMES)
