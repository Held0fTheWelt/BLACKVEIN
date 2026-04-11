"""Golden expectations for deterministic research fixture packs A-F."""

from __future__ import annotations

from ai_stack.research_contract import (
    CanonIssueType,
    ContradictionStatus,
    ImprovementProposalType,
    ResearchStatus,
)


EXPECTED_INTAKE_SEGMENT_COUNT = 3

EXPECTED_PERSPECTIVES = ("actor", "director", "dramaturg", "playwright")

EXPECTED_EXPLORATION_ABORT_REASONS = {
    "depth_limit_reached",
    "node_budget_exhausted",
    "branch_budget_exhausted",
    "llm_budget_exhausted",
    "token_budget_exhausted",
    "time_budget_exhausted",
    "low_evidence_limit_reached",
    "redundancy_abort",
    "speculative_drift_abort",
    "completed_within_budget",
}

EXPECTED_VERIFICATION_STATUSES = {
    ResearchStatus.CANON_APPLICABLE.value,
    ResearchStatus.APPROVED_RESEARCH.value,
}

EXPECTED_CONTRADICTION_CLASSES = {
    ContradictionStatus.NONE.value,
    ContradictionStatus.HARD_CONFLICT.value,
    ContradictionStatus.UNRESOLVED.value,
}

EXPECTED_ISSUE_TYPES = {e.value for e in CanonIssueType}
EXPECTED_PROPOSAL_TYPES = {e.value for e in ImprovementProposalType}

EXPECTED_BUNDLE_SECTIONS = (
    "intake",
    "aspects",
    "exploration",
    "verification",
    "canon_improvement",
    "governance",
)
