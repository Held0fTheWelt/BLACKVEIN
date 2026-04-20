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


def _contract(
    *,
    cid: str,
    title: str,
    summary: str,
    contract_type: str,
    layer: str,
    authority_level: str,
    anchor_kind: str,
    anchor_location: str,
    precedence_tier: str,
    tags: list[str],
    owner_or_area: str,
    scope: str,
    source_of_truth: bool = True,
    status: str = "active",
    version: str = "unversioned",
    confidence: float = 0.95,
    derived_from: list[str] | None = None,
    implemented_by: list[str] | None = None,
    validated_by: list[str] | None = None,
    documented_in: list[str] | None = None,
    projected_as: list[str] | None = None,
    notes: str = "",
) -> ContractRecord:
    """Contract the requested operation.

    Args:
        cid: Primary cid used by this step.
        title: Primary title used by this step.
        summary: Structured data carried through this workflow.
        contract_type: Primary contract type used by this step.
        layer: Primary layer used by this step.
        authority_level: Primary authority level used by this step.
        anchor_kind: Primary anchor kind used by this step.
        anchor_location: Primary anchor location used by this step.
        precedence_tier: Primary precedence tier used by this step.
        tags: Primary tags used by this step.
        owner_or_area: Primary owner or area used by this step.
        scope: Primary scope used by this step.
        source_of_truth: Whether to enable this optional behavior.
        status: Named status for this operation.
        version: Primary version used by this step.
        confidence: Primary confidence used by this step.
        derived_from: Primary derived from used by this step.
        implemented_by: Primary implemented by used by this step.
        validated_by: Primary validated by used by this step.
        documented_in: Primary documented in used by this step.
        projected_as: Primary projected as used by this step.
        notes: Primary notes used by this step.

    Returns:
        ContractRecord:
            Value produced by this callable as
            ``ContractRecord``.
    """
    return ContractRecord(
        id=cid,
        title=title,
        summary=summary,
        contract_type=contract_type,
        layer=layer,
        status=status,
        version=version,
        authority_level=authority_level,
        anchor_kind=anchor_kind,
        anchor_location=anchor_location,
        source_of_truth=source_of_truth,
        derived_from=derived_from or [],
        implemented_by=implemented_by or [],
        validated_by=validated_by or [],
        documented_in=documented_in or [],
        projected_as=projected_as or [],
        audiences=["developer", "architect"],
        modes=["specialist"],
        scope=scope,
        owner_or_area=owner_or_area,
        confidence=confidence,
        drift_signals=[],
        notes=notes,
        last_verified="",
        change_risk="unknown",
        tags=tags,
        discovery_reason="Curated runtime/MVP spine attachment inventory.",
        precedence_tier=precedence_tier,
    )

def _projection(
    *,
    pid: str,
    title: str,
    path: str,
    source_contract_id: str,
    audience: str,
    mode: str,
    evidence: str,
    anchor_location: str,
    confidence: float = 0.82,
) -> ProjectionRecord:
    """Projection the requested operation.

    Args:
        pid: Primary pid used by this step.
        title: Primary title used by this step.
        path: Filesystem path to the file or directory being processed.
        source_contract_id: Identifier used to select an existing run or
            record.
        audience: Free-text input that shapes this operation.
        mode: Named mode for this operation.
        evidence: Primary evidence used by this step.
        anchor_location: Primary anchor location used by this step.
        confidence: Primary confidence used by this step.

    Returns:
        ProjectionRecord:
            Value produced by this callable as
            ``ProjectionRecord``.
    """
    return ProjectionRecord(
        id=pid,
        title=title,
        path=path,
        audience=audience,
        mode=mode,
        source_contract_id=source_contract_id,
        anchor_location=anchor_location,
        authoritative=False,
        confidence=confidence,
        evidence=evidence,
        precedence_tier=PROJECTION_LOW,
    )

def _field_edges(records: list[ContractRecord], path_to_id: dict[str, str]) -> list[RelationEdge]:
    """Field edges.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        records: Primary records used by this step.
        path_to_id: Identifier used to select an existing run or record.

    Returns:
        list[RelationEdge]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[RelationEdge] = []
    for rec in records:
        for dep in rec.derived_from:
            out.append(
                RelationEdge(
                    relation="derives_from",
                    source_id=rec.id,
                    target_id=dep,
                    evidence=f"{rec.anchor_location} declares derived_from={dep} in curated runtime/MVP spine metadata.",
                    confidence=0.96,
                )
            )
        for rel in rec.implemented_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="implemented_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to implementation surface {rel}.",
                    confidence=0.93,
                )
            )
            out.append(
                RelationEdge(
                    relation="implements",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Implementation surface {rel} materially embodies {rec.anchor_location}.",
                    confidence=0.93,
                )
            )
        for rel in rec.validated_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="validated_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to verification surface {rel}.",
                    confidence=0.91,
                )
            )
            out.append(
                RelationEdge(
                    relation="validates",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Verification surface {rel} is cited as direct evidence for {rec.anchor_location}.",
                    confidence=0.91,
                )
            )
        for rel in rec.documented_in:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="documented_in",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment records {rel} as supporting documentation for {rec.anchor_location}.",
                    confidence=0.86,
                )
            )
        for rel in rec.projected_as:
            out.append(
                RelationEdge(
                    relation="projected_as",
                    source_id=rec.id,
                    target_id=f"PRJPATH:{rel}",
                    evidence=f"Curated attachment records {rel} as a lower-weight projection of {rec.anchor_location}.",
                    confidence=0.8,
                )
            )
    return out

