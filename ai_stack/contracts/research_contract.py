"""Canonical research contracts for the Research-and-Canon-Improvement MVP.

Single-source-of-truth:
- status enums
- contradiction enums
- exploration abort reasons
- issue/proposal taxonomies
- legal status transitions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        """``StrEnum`` groups related behaviour; callers should read members for contracts and threading assumptions.
        """
        def __str__(self) -> str:
            """``__str__`` — see implementation for behaviour and contracts.
            
            Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
            
            Returns:
                str:
                    Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
            """
            return self.value


class ResearchStatus(StrEnum):
    """``ResearchStatus`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    EXPLORATORY = "exploratory"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    APPROVED_RESEARCH = "approved_research"
    CANON_APPLICABLE = "canon_applicable"
    CANON_ADOPTED = "canon_adopted"


class ContradictionStatus(StrEnum):
    """``ContradictionStatus`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    NONE = "none"
    COUNTERVIEW_PRESENT = "counterview_present"
    SOFT_CONFLICT = "soft_conflict"
    HARD_CONFLICT = "hard_conflict"
    UNRESOLVED = "unresolved"


class Perspective(StrEnum):
    """``Perspective`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    PLAYWRIGHT = "playwright"
    DIRECTOR = "director"
    ACTOR = "actor"
    DRAMATURG = "dramaturg"


class CopyrightPosture(StrEnum):
    """``CopyrightPosture`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    INTERNAL_APPROVED = "internal_approved"
    INTERNAL_RESTRICTED = "internal_restricted"
    EXTERNAL_BLOCKED = "external_blocked"
    EXTERNAL_WHITELISTED_FUTURE = "external_whitelisted_future"


class ExplorationRelationType(StrEnum):
    """``ExplorationRelationType`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    EXTEND = "extend"
    CONTRAST = "contrast"
    COUNTERREAD = "counterread"
    STAGING_IMPLICATION = "staging_implication"
    THEME_LINK = "theme_link"
    CHARACTER_MOTIVE_LINK = "character_motive_link"
    STRUCTURAL_ANALOGY = "structural_analogy"
    TENSION_SOURCE_PROBE = "tension_source_probe"
    IMPROVEMENT_PROBE = "improvement_probe"


class ExplorationOutcome(StrEnum):
    """``ExplorationOutcome`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    KEPT_FOR_VALIDATION = "kept_for_validation"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"
    MERGED_PATTERN = "merged_into_existing_pattern"
    PROMOTED_CANDIDATE = "promoted_to_research_claim_candidate"


class ExplorationAbortReason(StrEnum):
    """``ExplorationAbortReason`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    DEPTH_LIMIT_REACHED = "depth_limit_reached"
    NODE_BUDGET_EXHAUSTED = "node_budget_exhausted"
    BRANCH_BUDGET_EXHAUSTED = "branch_budget_exhausted"
    LLM_BUDGET_EXHAUSTED = "llm_budget_exhausted"
    TOKEN_BUDGET_EXHAUSTED = "token_budget_exhausted"
    TIME_BUDGET_EXHAUSTED = "time_budget_exhausted"
    LOW_EVIDENCE_LIMIT_REACHED = "low_evidence_limit_reached"
    REDUNDANCY_ABORT = "redundancy_abort"
    SPECULATIVE_DRIFT_ABORT = "speculative_drift_abort"
    COMPLETED_WITHIN_BUDGET = "completed_within_budget"


class CanonIssueType(StrEnum):
    """``CanonIssueType`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    WEAK_ESCALATION = "weak_escalation"
    UNCLEAR_SCENE_FUNCTION = "unclear_scene_function"
    INSUFFICIENT_SUBTEXT = "insufficient_subtext"
    REDUNDANT_DIALOGUE = "redundant_dialogue"
    MISSING_PAYOFF_PREPARATION = "missing_payoff_preparation"
    UNDERPOWERED_STATUS_SHIFT = "underpowered_status_shift"
    NARROW_ACTION_SPACE = "narrow_action_space"
    THEME_NOT_EMBODIED = "theme_not_embodied"
    MOTIVATION_GAP = "motivation_gap"
    UNUSED_STAGING_POTENTIAL = "unused_staging_potential"


class ImprovementProposalType(StrEnum):
    """``ImprovementProposalType`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    TIGHTEN_CONFLICT_CORE = "tighten_conflict_core"
    INTRODUCE_EARLIER_TACTIC_SHIFT = "introduce_earlier_tactic_shift"
    STRENGTHEN_STATUS_REVERSAL = "strengthen_status_reversal"
    CONVERT_EXPOSITION_TO_PLAYABLE_ACTION = "convert_exposition_to_playable_action"
    IMPROVE_PAYOFF_PREPARATION = "improve_payoff_preparation"
    SHARPEN_SUBTEXT = "sharpen_subtext"
    WIDEN_ACTION_SPACE = "widen_action_space"
    EMBODY_THEME_THROUGH_FRICTION = "embody_theme_through_friction"
    RESTRUCTURE_PRESSURE_CURVE = "restructure_pressure_curve"
    ACTIVATE_STAGING_LEVERAGE = "activate_staging_leverage"


MANDATORY_EXPLORATION_BUDGET_FIELDS: tuple[str, ...] = (
    "max_depth",
    "max_branches_per_node",
    "max_total_nodes",
    "max_low_evidence_expansions",
    "llm_call_budget",
    "token_budget",
    "time_budget_ms",
    "abort_on_redundancy",
    "abort_on_speculative_drift",
    "model_profile",
)


LEGAL_STATUS_TRANSITIONS: dict[ResearchStatus, set[ResearchStatus]] = {
    ResearchStatus.EXPLORATORY: {ResearchStatus.CANDIDATE},
    ResearchStatus.CANDIDATE: {ResearchStatus.VALIDATED},
    ResearchStatus.VALIDATED: {ResearchStatus.APPROVED_RESEARCH},
    ResearchStatus.APPROVED_RESEARCH: {ResearchStatus.CANON_APPLICABLE},
    ResearchStatus.CANON_APPLICABLE: {ResearchStatus.CANON_ADOPTED},
    ResearchStatus.CANON_ADOPTED: set(),
}


def utc_now_iso() -> str:
    """Describe what ``utc_now_iso`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return datetime.now(timezone.utc).isoformat()


def deterministic_digest(payload: dict[str, Any], *, prefix: str) -> str:
    """``deterministic_digest`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        payload: ``payload`` (dict[str, Any]); meaning follows the type and call sites.
        prefix: ``prefix`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:16]}"


def ensure_non_empty_str(name: str, value: Any) -> str:
    """``ensure_non_empty_str`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        name: ``name`` (str); meaning follows the type and call sites.
        value: ``value`` (Any); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_or_empty_{name}")
    return value.strip()


def ensure_non_empty_list(name: str, value: Any) -> list[Any]:
    """``ensure_non_empty_list`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        name: ``name`` (str); meaning follows the type and call sites.
        value: ``value`` (Any); meaning follows the type and call sites.
    
    Returns:
        list[Any]:
            Returns a value of type ``list[Any]``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(value, list) or not value:
        raise ValueError(f"invalid_or_empty_{name}")
    return value


def ensure_status_transition_allowed(from_status: ResearchStatus, to_status: ResearchStatus) -> None:
    """Describe what ``ensure_status_transition_allowed`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        from_status: ``from_status`` (ResearchStatus); meaning follows the type and call sites.
        to_status: ``to_status`` (ResearchStatus); meaning follows the type and call sites.
    """
    legal_targets = LEGAL_STATUS_TRANSITIONS.get(from_status, set())
    if to_status not in legal_targets:
        raise ValueError(f"illegal_status_transition:{from_status.value}->{to_status.value}")


@dataclass(slots=True)
class ExplorationBudget:
    """``ExplorationBudget`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    max_depth: int
    max_branches_per_node: int
    max_total_nodes: int
    max_low_evidence_expansions: int
    llm_call_budget: int
    token_budget: int
    time_budget_ms: int
    abort_on_redundancy: bool
    abort_on_speculative_drift: bool
    model_profile: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ExplorationBudget":
        """``from_payload`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            payload: ``payload`` (dict[str, Any]); meaning follows the type and call sites.
        
        Returns:
            ExplorationBudget:
                Returns a value of type ``ExplorationBudget``; see the function body for structure, error paths, and sentinels.
        """
        missing = [f for f in MANDATORY_EXPLORATION_BUDGET_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"missing_exploration_budget_fields:{','.join(sorted(missing))}")
        budget = cls(
            max_depth=int(payload["max_depth"]),
            max_branches_per_node=int(payload["max_branches_per_node"]),
            max_total_nodes=int(payload["max_total_nodes"]),
            max_low_evidence_expansions=int(payload["max_low_evidence_expansions"]),
            llm_call_budget=int(payload["llm_call_budget"]),
            token_budget=int(payload["token_budget"]),
            time_budget_ms=int(payload["time_budget_ms"]),
            abort_on_redundancy=bool(payload["abort_on_redundancy"]),
            abort_on_speculative_drift=bool(payload["abort_on_speculative_drift"]),
            model_profile=ensure_non_empty_str("model_profile", payload["model_profile"]),
        )
        budget.validate()
        return budget

    def validate(self) -> None:
        """``validate`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        """
        if self.max_depth < 0:
            raise ValueError("invalid_budget:max_depth")
        if self.max_branches_per_node <= 0:
            raise ValueError("invalid_budget:max_branches_per_node")
        if self.max_total_nodes <= 0:
            raise ValueError("invalid_budget:max_total_nodes")
        if self.max_low_evidence_expansions < 0:
            raise ValueError("invalid_budget:max_low_evidence_expansions")
        if self.llm_call_budget < 0:
            raise ValueError("invalid_budget:llm_call_budget")
        if self.token_budget < 0:
            raise ValueError("invalid_budget:token_budget")
        if self.time_budget_ms <= 0:
            raise ValueError("invalid_budget:time_budget_ms")

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "max_depth": self.max_depth,
            "max_branches_per_node": self.max_branches_per_node,
            "max_total_nodes": self.max_total_nodes,
            "max_low_evidence_expansions": self.max_low_evidence_expansions,
            "llm_call_budget": self.llm_call_budget,
            "token_budget": self.token_budget,
            "time_budget_ms": self.time_budget_ms,
            "abort_on_redundancy": self.abort_on_redundancy,
            "abort_on_speculative_drift": self.abort_on_speculative_drift,
            "model_profile": self.model_profile,
        }


@dataclass(slots=True)
class ResearchSourceRecord:
    """``ResearchSourceRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    source_id: str
    work_id: str
    source_type: str
    title: str
    provenance: dict[str, Any]
    visibility: str
    copyright_posture: CopyrightPosture
    segment_index_status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "source_id": self.source_id,
            "work_id": self.work_id,
            "source_type": self.source_type,
            "title": self.title,
            "provenance": dict(self.provenance),
            "visibility": self.visibility,
            "copyright_posture": self.copyright_posture.value,
            "segment_index_status": self.segment_index_status,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class EvidenceAnchorRecord:
    """``EvidenceAnchorRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    anchor_id: str
    source_id: str
    segment_ref: str
    span_ref: str
    paraphrase_or_excerpt: str
    confidence: float
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "anchor_id": self.anchor_id,
            "source_id": self.source_id,
            "segment_ref": self.segment_ref,
            "span_ref": self.span_ref,
            "paraphrase_or_excerpt": self.paraphrase_or_excerpt,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass(slots=True)
class AspectRecord:
    """``AspectRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    aspect_id: str
    source_id: str
    perspective: Perspective
    aspect_type: str
    statement: str
    evidence_anchor_ids: list[str]
    tags: list[str]
    status: ResearchStatus = ResearchStatus.EXPLORATORY

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "aspect_id": self.aspect_id,
            "source_id": self.source_id,
            "perspective": self.perspective.value,
            "aspect_type": self.aspect_type,
            "statement": self.statement,
            "evidence_anchor_ids": list(self.evidence_anchor_ids),
            "tags": list(self.tags),
            "status": self.status.value,
        }


@dataclass(slots=True)
class ExplorationNodeRecord:
    """``ExplorationNodeRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    node_id: str
    parent_node_id: str | None
    seed_aspect_id: str
    perspective: Perspective
    hypothesis: str
    rationale: str
    speculative_level: float
    evidence_anchor_ids: list[str]
    novelty_score: float
    status: ResearchStatus
    outcome: ExplorationOutcome

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "node_id": self.node_id,
            "parent_node_id": self.parent_node_id,
            "seed_aspect_id": self.seed_aspect_id,
            "perspective": self.perspective.value,
            "hypothesis": self.hypothesis,
            "rationale": self.rationale,
            "speculative_level": self.speculative_level,
            "evidence_anchor_ids": list(self.evidence_anchor_ids),
            "novelty_score": self.novelty_score,
            "status": self.status.value,
            "outcome": self.outcome.value,
        }


@dataclass(slots=True)
class ExplorationEdgeRecord:
    """``ExplorationEdgeRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    edge_id: str
    from_node_id: str
    to_node_id: str
    relation_type: ExplorationRelationType

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "edge_id": self.edge_id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "relation_type": self.relation_type.value,
        }


@dataclass(slots=True)
class ResearchClaimRecord:
    """``ResearchClaimRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    claim_id: str
    work_id: str
    perspective: Perspective
    claim_type: str
    statement: str
    evidence_anchor_ids: list[str]
    support_level: float
    contradiction_status: ContradictionStatus
    status: ResearchStatus
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "claim_id": self.claim_id,
            "work_id": self.work_id,
            "perspective": self.perspective.value,
            "claim_type": self.claim_type,
            "statement": self.statement,
            "evidence_anchor_ids": list(self.evidence_anchor_ids),
            "support_level": self.support_level,
            "contradiction_status": self.contradiction_status.value,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass(slots=True)
class CanonIssueRecord:
    """``CanonIssueRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    issue_id: str
    module_id: str
    issue_type: CanonIssueType
    severity: str
    description: str
    supporting_claim_ids: list[str]
    status: ResearchStatus

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "issue_id": self.issue_id,
            "module_id": self.module_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "description": self.description,
            "supporting_claim_ids": list(self.supporting_claim_ids),
            "status": self.status.value,
        }


@dataclass(slots=True)
class ImprovementProposalRecord:
    """``ImprovementProposalRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    proposal_id: str
    module_id: str
    proposal_type: ImprovementProposalType
    rationale: str
    expected_effect: str
    supporting_claim_ids: list[str]
    preview_patch_ref: dict[str, Any]
    status: ResearchStatus

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "proposal_id": self.proposal_id,
            "module_id": self.module_id,
            "proposal_type": self.proposal_type.value,
            "rationale": self.rationale,
            "expected_effect": self.expected_effect,
            "supporting_claim_ids": list(self.supporting_claim_ids),
            "preview_patch_ref": dict(self.preview_patch_ref),
            "status": self.status.value,
        }


@dataclass(slots=True)
class ResearchRunRecord:
    """``ResearchRunRecord`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    run_id: str
    mode: str
    source_ids: list[str]
    seed_question: str
    budget: dict[str, Any]
    outputs: dict[str, Any]
    audit_refs: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Describe what ``to_dict`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "source_ids": list(self.source_ids),
            "seed_question": self.seed_question,
            "budget": dict(self.budget),
            "outputs": dict(self.outputs),
            "audit_refs": list(self.audit_refs),
            "created_at": self.created_at,
        }
