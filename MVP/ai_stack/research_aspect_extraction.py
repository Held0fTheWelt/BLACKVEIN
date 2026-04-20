"""Deterministic perspective-separated aspect extraction phase."""

from __future__ import annotations

from ai_stack.research_contract import AspectRecord, Perspective, ResearchStatus
from ai_stack.research_perspectives import extract_perspective_aspects
from ai_stack.research_store import ResearchStore


def extract_and_store_aspects(
    *,
    store: ResearchStore,
    source_id: str,
    segments: list[dict],
) -> list[dict]:
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
