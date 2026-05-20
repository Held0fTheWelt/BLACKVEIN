"""
RAG layer: shared StrEnum types, governance view record, and domain
errors (DS-003 split from rag.py).
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback
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


class RetrievalDomain(StrEnum):
    """``RetrievalDomain`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    RUNTIME = "runtime"
    WRITERS_ROOM = "writers_room"
    IMPROVEMENT = "improvement"
    RESEARCH = "research"


class RetrievalStatus(StrEnum):
    """``RetrievalStatus`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    OK = "ok"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


class ContentClass(StrEnum):
    """``ContentClass`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    AUTHORED_MODULE = "authored_module"
    RUNTIME_PROJECTION = "runtime_projection"
    CHARACTER_PROFILE = "character_profile"
    TRANSCRIPT = "transcript"
    REVIEW_NOTE = "review_note"
    EVALUATION_ARTIFACT = "evaluation_artifact"
    POLICY_GUIDELINE = "policy_guideline"


class SourceEvidenceLane(StrEnum):
    """Stable governance lane derived from content class and corpus signals
    (not a ranking score).
    """

    CANONICAL = "canonical"
    SUPPORTING = "supporting"
    DRAFT_WORKING = "draft_working"
    INTERNAL_REVIEW = "internal_review"
    EVALUATIVE = "evaluative"


class SourceVisibilityClass(StrEnum):
    """Who this material is intended for at a visibility (not authorization)
    level.
    """

    RUNTIME_SAFE = "runtime_safe"
    WRITERS_WORKING = "writers_working"
    IMPROVEMENT_DIAGNOSTIC = "improvement_diagnostic"


class RetrievalDegradationMode(StrEnum):
    """Stable labels for retrieval health (sparse vs hybrid and why)."""

    HYBRID_OK = "hybrid_ok"
    SPARSE_FALLBACK_NO_BACKEND = "sparse_fallback_due_to_no_backend"
    SPARSE_FALLBACK_ENCODE_FAILURE = "sparse_fallback_due_to_encode_failure"
    SPARSE_FALLBACK_INVALID_OR_MISSING_DENSE_INDEX = "sparse_fallback_due_to_invalid_or_missing_dense_index"
    REBUILT_DENSE_INDEX = "rebuilt_dense_index"
    DEGRADED_PARTIAL_PERSISTENCE = "degraded_due_to_partial_persistence_problem"
    CORPUS_EMPTY = "corpus_empty"


class RetrievalDomainError(ValueError):
    """``RetrievalDomainError`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    pass


@dataclass(frozen=True, slots=True)
class SourceGovernanceView:
    """Compact, inspectable policy view for one chunk (pure function of chunk
    fields).
    """

    evidence_lane: SourceEvidenceLane
    visibility_class: SourceVisibilityClass
    derivation_note: str
