"""Deterministic perspective-separated aspect extraction phase."""

from __future__ import annotations

from ai_stack.contracts.research_contract import AspectRecord, Perspective, ResearchStatus
from ai_stack.research.research_perspectives import extract_perspective_aspects
from ai_stack.research.research_store import ResearchStore


def extract_and_store_aspects(
    *,
    store: ResearchStore,
    source_id: str,
    segments: list[dict],
) -> list[dict]:
    """Describe what ``extract_and_store_aspects`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        store: ``store`` (ResearchStore); meaning follows the type and call sites.
        source_id: ``source_id`` (str); meaning follows the type and call sites.
        segments: ``segments`` (list[dict]); meaning follows the type and call sites.
    
    Returns:
        list[dict]:
            Returns a value of type ``list[dict]``; see the function body for structure, error paths, and sentinels.
    """
    generated = extract_perspective_aspects(
        source_id=source_id,
        segments=segments,
        aspect_id_factory=store.next_id,
    )
    stored: list[dict] = []
    for row in generated:
        record = AspectRecord(
            aspect_id=row["aspect_id"],
            source_id=row["source_id"],
            perspective=Perspective(row["perspective"]),
            aspect_type=row["aspect_type"],
            statement=row["statement"],
            evidence_anchor_ids=list(row["evidence_anchor_ids"]),
            tags=list(row["tags"]),
            status=ResearchStatus.EXPLORATORY,
        )
        stored.append(store.upsert_aspect(record))
    return sorted(stored, key=lambda r: r["aspect_id"])
