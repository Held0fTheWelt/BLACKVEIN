"""Internal helper functions for ai_stack evidence scoring — cycle-breaking leaf module.

Extracted from ai_stack_evidence_service.py to break the 5-file SCC:
  evidence_service → readiness_report → ... → signal_extractors → evidence_service

This module has no app.services imports.
"""
from __future__ import annotations

from typing import Any


def _retrieval_tier_strong_enough_for_governance(tier: Any) -> bool:
    return tier in ("moderate", "strong")


def _writers_room_retrieval_trace_tier(writers_room_review: dict[str, Any] | None) -> Any:
    if not writers_room_review:
        return None
    rt = writers_room_review.get("retrieval_trace")
    if not isinstance(rt, dict):
        return None
    return rt.get("evidence_tier")


def _improvement_evidence_strength_map(package: dict[str, Any] | None) -> dict[str, Any] | None:
    if not package:
        return None
    m = package.get("evidence_strength_map")
    return m if isinstance(m, dict) else None
