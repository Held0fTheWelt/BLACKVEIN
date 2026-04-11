"""RAG source governance: evidence lane and visibility from chunk fields (DS-003 split from rag.py)."""

from __future__ import annotations

from typing import Protocol

from ai_stack.rag_types import (
    ContentClass,
    SourceEvidenceLane,
    SourceGovernanceView,
    SourceVisibilityClass,
)


class GovernanceChunkView(Protocol):
    """Structural type for anything passed to ``governance_view_for_chunk`` (e.g. ``CorpusChunk``)."""

    content_class: ContentClass
    source_path: str
    canonical_priority: int


def governance_view_for_chunk(chunk: GovernanceChunkView) -> SourceGovernanceView:
    """Map persisted chunk fields to evidence lane and visibility (deterministic, no I/O)."""
    cc = chunk.content_class
    path = chunk.source_path.replace("\\", "/").lower()
    cp = chunk.canonical_priority

    if cc == ContentClass.EVALUATION_ARTIFACT:
        return SourceGovernanceView(
            SourceEvidenceLane.EVALUATIVE,
            SourceVisibilityClass.IMPROVEMENT_DIAGNOSTIC,
            "content_class=evaluation_artifact",
        )
    if cc == ContentClass.REVIEW_NOTE:
        return SourceGovernanceView(
            SourceEvidenceLane.INTERNAL_REVIEW,
            SourceVisibilityClass.WRITERS_WORKING,
            "content_class=review_note",
        )
    if cc == ContentClass.POLICY_GUIDELINE:
        return SourceGovernanceView(
            SourceEvidenceLane.SUPPORTING,
            SourceVisibilityClass.RUNTIME_SAFE,
            "content_class=policy_guideline",
        )
    if cc in (ContentClass.TRANSCRIPT, ContentClass.RUNTIME_PROJECTION, ContentClass.CHARACTER_PROFILE):
        return SourceGovernanceView(
            SourceEvidenceLane.SUPPORTING,
            SourceVisibilityClass.RUNTIME_SAFE,
            f"content_class={cc.value}",
        )
    if cc == ContentClass.AUTHORED_MODULE:
        # source_path is repo-relative (``content/published/...``), while canonical_priority
        # is computed from absolute paths at ingest; accept both relative and absolute shapes.
        in_published = "content/published/" in path
        in_modules = "content/modules/" in path
        if cp >= 4 and in_published:
            return SourceGovernanceView(
                SourceEvidenceLane.CANONICAL,
                SourceVisibilityClass.RUNTIME_SAFE,
                "authored_published_tree",
            )
        if cp >= 3 and in_modules:
            return SourceGovernanceView(
                SourceEvidenceLane.DRAFT_WORKING,
                SourceVisibilityClass.WRITERS_WORKING,
                "authored_modules_tree_draft",
            )
        return SourceGovernanceView(
            SourceEvidenceLane.DRAFT_WORKING,
            SourceVisibilityClass.WRITERS_WORKING,
            "authored_flat_or_nonstandard_path",
        )
    return SourceGovernanceView(
        SourceEvidenceLane.SUPPORTING,
        SourceVisibilityClass.RUNTIME_SAFE,
        "fallback_unknown_content_class",
    )
