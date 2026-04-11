"""Retrieval governance turn summary (gate G5)."""

from __future__ import annotations

from ai_stack.retrieval_governance_summary import (
    attach_retrieval_governance_summary,
    dominant_visibility_class_from_counts,
    summarize_retrieval_governance_from_hit_rows,
)
from ai_stack.rag import ContentClass, RETRIEVAL_POLICY_VERSION, SourceVisibilityClass


def test_summary_empty_sources() -> None:
    s = summarize_retrieval_governance_from_hit_rows(None)
    assert s["source_row_count"] == 0
    assert s["authored_truth_refs"] == []
    assert s["derived_artifact_refs"] == []
    assert s["content_class_counts"] == {}
    assert s["dominant_visibility_class"] is None
    assert s["retrieval_policy_version"] == RETRIEVAL_POLICY_VERSION


def test_summary_empty_list_no_hits() -> None:
    s = summarize_retrieval_governance_from_hit_rows([])
    assert s["source_row_count"] == 0
    assert s["authored_truth_refs"] == []
    assert s["derived_artifact_refs"] == []
    assert s["dominant_visibility_class"] is None


def test_summary_counts_lanes_and_derived_only() -> None:
    sources = [
        {
            "chunk_id": "c1",
            "source_path": "/p/policy.md",
            "source_evidence_lane": "supporting",
            "source_visibility_class": "runtime_safe",
            "content_class": "policy_guideline",
        },
        {
            "chunk_id": "c2",
            "source_path": "/p/guideline.md",
            "source_evidence_lane": "supporting",
            "source_visibility_class": "runtime_safe",
            "content_class": "policy_guideline",
        },
    ]
    s = summarize_retrieval_governance_from_hit_rows(sources)
    assert s["source_row_count"] == 2
    assert s["lane_counts"]["supporting"] == 2
    assert s["visibility_counts"]["runtime_safe"] == 2
    assert s["content_class_counts"]["policy_guideline"] == 2
    assert s["authored_truth_refs"] == []
    assert len(s["derived_artifact_refs"]) == 2
    assert s["derived_artifact_refs"][0]["content_class"] == "policy_guideline"
    assert s["dominant_visibility_class"] == "runtime_safe"


def test_summary_mixed_authored_and_derived() -> None:
    sources = [
        {
            "chunk_id": "a1",
            "source_path": "content/modules/x.md",
            "source_evidence_lane": "canonical",
            "source_visibility_class": "runtime_safe",
            "content_class": ContentClass.AUTHORED_MODULE.value,
        },
        {
            "chunk_id": "d1",
            "source_path": "notes/t.md",
            "source_evidence_lane": "supporting",
            "source_visibility_class": "writers_working",
            "content_class": ContentClass.TRANSCRIPT.value,
        },
    ]
    s = summarize_retrieval_governance_from_hit_rows(sources)
    assert len(s["authored_truth_refs"]) == 1
    assert s["authored_truth_refs"][0]["chunk_id"] == "a1"
    assert len(s["derived_artifact_refs"]) == 1
    assert s["derived_artifact_refs"][0]["chunk_id"] == "d1"


def test_dominant_visibility_tie_breaks_by_enum_order() -> None:
    # improvement_diagnostic and writers_working tie at 2; writers_working wins (declared first in SourceVisibilityClass).
    counts = {
        SourceVisibilityClass.IMPROVEMENT_DIAGNOSTIC.value: 2,
        SourceVisibilityClass.WRITERS_WORKING.value: 2,
    }
    assert dominant_visibility_class_from_counts(counts) == SourceVisibilityClass.WRITERS_WORKING.value

    # Three-way tie including runtime_safe — runtime_safe is first in enum, wins.
    counts2 = {
        SourceVisibilityClass.RUNTIME_SAFE.value: 1,
        SourceVisibilityClass.WRITERS_WORKING.value: 1,
        SourceVisibilityClass.IMPROVEMENT_DIAGNOSTIC.value: 1,
    }
    assert dominant_visibility_class_from_counts(counts2) == SourceVisibilityClass.RUNTIME_SAFE.value


def test_dominant_visibility_empty_counts_none() -> None:
    assert dominant_visibility_class_from_counts({}) is None


def test_attach_mutates_retrieval_dict() -> None:
    r: dict = {"sources": [{"source_evidence_lane": "canonical", "content_class": "authored_module"}]}
    attach_retrieval_governance_summary(r)
    assert "retrieval_governance_summary" in r
    g = r["retrieval_governance_summary"]
    assert g["lane_counts"]["canonical"] == 1
    assert len(g["authored_truth_refs"]) == 1
