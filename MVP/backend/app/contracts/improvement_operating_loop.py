"""Improvement operating loop stages (``docs/ROADMAP_MVP_GoC.md`` §6.8, gate G8)."""

from __future__ import annotations

from enum import Enum


class ImprovementLoopStage(str, Enum):
    """Roadmap §6.8 — bounded improvement loop phases (typed audit surface)."""

    issue_selection = "issue_selection"
    evidence_collection = "evidence_collection"
    bounded_proposal_generation = "bounded_proposal_generation"
    semantic_compliance_validation = "semantic_compliance_validation"
    approval_rejection = "approval_rejection"
    publication = "publication"
    post_change_verification = "post_change_verification"


IMPROVEMENT_OPERATING_LOOP_CONTRACT_VERSION = "goc_improvement_operating_loop_v1"
