"""
Curated runtime/MVP contract spine attachments for World of Shadows.

This module promotes the high-value runtime/MVP contract family into
explicit, related, evidence-attached Contractify records without broad
repository mining. The inventory is intentionally bounded to avoid graph
explosion.
"""
from __future__ import annotations

from pathlib import Path

from contractify.tools.adr_governance import first_existing_relative
from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord, RelationEdge


RUNTIME_AUTHORITY = "runtime_authority"
SLICE_NORMATIVE = "slice_normative"
IMPLEMENTATION_EVIDENCE = "implementation_evidence"
VERIFICATION_EVIDENCE = "verification_evidence"
PROJECTION_LOW = "projection_low"


PRECEDENCE_RULES: list[dict[str, object]] = [
    {
        "tier": RUNTIME_AUTHORITY,
        "rank": 1,
        "summary": "Highest-order runtime authority and boundary contracts. These outrank slice detail, implementation observations, and projections when authority clashes are reviewed.",
    },
    {
        "tier": SLICE_NORMATIVE,
        "rank": 2,
        "summary": "Binding MVP / slice contracts and accepted slice-scoped ADRs. These govern GoC behavior beneath the runtime authority layer.",
    },
    {
        "tier": IMPLEMENTATION_EVIDENCE,
        "rank": 3,
        "summary": "Observed code surfaces that embody or operationalize contracts but do not replace normative authority.",
    },
    {
        "tier": VERIFICATION_EVIDENCE,
        "rank": 4,
        "summary": "Test and verification surfaces that support claims about implementation and documented paths.",
    },
    {
        "tier": PROJECTION_LOW,
        "rank": 5,
        "summary": "Lower-weight audience projections and convenience summaries. Useful for navigation, never equal to runtime authority or slice contracts.",
    },
]


def _existing(repo: Path, *rels: str) -> list[str]:
    """Existing the requested operation.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        *rels: Primary rels used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[str] = []
    # Process rel one item at a time so _existing applies the same rule across the full
    # collection.
    for rel in rels:
        rel = rel.replace("\\", "/")
        # Branch on (repo / rel).is_file() so _existing only continues along the
        # matching state path.
        if (repo / rel).is_file():
            out.append(rel)
    return out

def _one_of(repo: Path, *rels: str) -> list[str]:
    """One of.

    Args:
        repo: Primary repo used by this step.
        *rels: Primary rels used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    rel = first_existing_relative(repo, *rels)
    return [rel] if rel else []

def _adr0001(repo: Path) -> str:
    """Adr0001 the requested operation.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0001-runtime-authority-in-world-engine.md",
    )

def _adr0002(repo: Path) -> str:
    """Adr0002 the requested operation.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0002-backend-session-surface-quarantine.md",
    )

def _adr0003(repo: Path) -> str:
    """Adr0003 the requested operation.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return first_existing_relative(
        repo,
        "docs/ADR/adr-0003-scene-identity-canonical-surface.md",
    )

def _make_review_conflict(
    *,
    repo: Path,
    conflict_id: str,
    conflict_type: str,
    summary: str,
    notes: str,
    classification: str,
    kind: str,
    severity: str,
    normative_candidates: list[str],
    observed_candidates: list[str],
    confidence: float = 0.8,
) -> ConflictFinding | None:
    """Return a bounded review conflict only when current-repo evidence exists."""
    normative_sources = [item for item in normative_candidates if item and (repo / item).is_file()]
    observed_sources = [item for item in observed_candidates if item and (repo / item).is_file()]
    if not normative_sources or not observed_sources:
        return None
    return ConflictFinding(
        id=conflict_id,
        conflict_type=conflict_type,
        summary=summary,
        sources=[*normative_sources, *observed_sources],
        confidence=confidence,
        requires_human_review=True,
        notes=notes,
        classification=classification,
        normative_sources=normative_sources,
        observed_or_projection_sources=observed_sources,
        kind=kind,
        severity=severity,
        normative_candidates=normative_sources,
        observed_candidates=observed_sources,
    )

def _path_target_id(path_to_id: dict[str, str], rel: str) -> str:
    """Path target id.

    Args:
        path_to_id: Identifier used to select an existing run or record.
        rel: Primary rel used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    rel = rel.replace("\\", "/")
    return path_to_id.get(rel, f"ART:{rel}")

