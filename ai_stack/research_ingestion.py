"""Deterministic intake and source normalization for Research MVP."""

from __future__ import annotations

from typing import Any

from ai_stack.research_contract import (
    CopyrightPosture,
    EvidenceAnchorRecord,
    ResearchSourceRecord,
    deterministic_digest,
)
from ai_stack.research_perspectives import estimate_anchor_confidence, segment_text_deterministically, summarize_segment_for_anchor
from ai_stack.research_store import ResearchStore


MVP_ALLOWED_INPUT_POSTURES: frozenset[CopyrightPosture] = frozenset(
    {
        CopyrightPosture.INTERNAL_APPROVED,
        CopyrightPosture.INTERNAL_RESTRICTED,
    }
)


def _resolve_posture(value: str | None) -> CopyrightPosture:
    raw = (value or CopyrightPosture.INTERNAL_APPROVED.value).strip()
    try:
        return CopyrightPosture(raw)
    except ValueError as exc:
        raise ValueError(f"invalid_copyright_posture:{raw}") from exc


def enforce_mvp_copyright_posture(posture: CopyrightPosture) -> None:
    if posture not in MVP_ALLOWED_INPUT_POSTURES:
        raise ValueError(f"copyright_posture_blocked_in_mvp:{posture.value}")


def normalize_resource(
    *,
    work_id: str,
    source_type: str,
    title: str,
    raw_text: str,
    provenance: dict[str, Any] | None = None,
    visibility: str = "internal",
    copyright_posture: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    posture = _resolve_posture(copyright_posture)
    enforce_mvp_copyright_posture(posture)
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("empty_source_text")
    normalized = {
        "work_id": work_id.strip(),
        "source_type": source_type.strip(),
        "title": title.strip(),
        "text": text,
        "provenance": dict(provenance or {}),
        "visibility": visibility.strip() or "internal",
        "copyright_posture": posture.value,
        "metadata": dict(metadata or {}),
    }
    normalized["source_id"] = deterministic_digest(
        {
            "work_id": normalized["work_id"],
            "source_type": normalized["source_type"],
            "title": normalized["title"],
            "text": normalized["text"],
            "provenance": normalized["provenance"],
            "visibility": normalized["visibility"],
            "copyright_posture": normalized["copyright_posture"],
            "metadata": normalized["metadata"],
        },
        prefix="source",
    )
    return normalized


def ingest_resource(
    *,
    store: ResearchStore,
    normalized_source: dict[str, Any],
    segment_target_words: int = 90,
    segment_overlap_words: int = 15,
) -> dict[str, Any]:
    source_record = ResearchSourceRecord(
        source_id=normalized_source["source_id"],
        work_id=normalized_source["work_id"],
        source_type=normalized_source["source_type"],
        title=normalized_source["title"],
        provenance=normalized_source["provenance"],
        visibility=normalized_source["visibility"],
        copyright_posture=CopyrightPosture(normalized_source["copyright_posture"]),
        segment_index_status="indexed",
        metadata=normalized_source["metadata"],
    )
    stored_source = store.upsert_source(source_record)

    segments = segment_text_deterministically(
        normalized_source["text"],
        target_words=segment_target_words,
        overlap_words=segment_overlap_words,
    )
    if not segments:
        raise ValueError("segmentation_produced_no_segments")

    indexed_segments: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    for idx, segment_text in enumerate(segments):
        anchor_id = store.next_id("anchor")
        segment_ref = f"seg_{idx + 1:04d}"
        anchor = EvidenceAnchorRecord(
            anchor_id=anchor_id,
            source_id=source_record.source_id,
            segment_ref=segment_ref,
            span_ref=f"w{idx * max(1, segment_target_words)}-w{(idx + 1) * max(1, segment_target_words)}",
            paraphrase_or_excerpt=summarize_segment_for_anchor(segment_text),
            confidence=estimate_anchor_confidence(segment_text),
            notes="deterministic_segment_anchor",
        )
        stored_anchor = store.upsert_anchor(anchor)
        anchor_rows.append(stored_anchor)
        indexed_segments.append(
            {
                "source_id": source_record.source_id,
                "segment_ref": segment_ref,
                "text": segment_text,
                "anchor_ids": [stored_anchor["anchor_id"]],
            }
        )

    return {
        "source": stored_source,
        "segments": indexed_segments,
        "anchors": anchor_rows,
    }
