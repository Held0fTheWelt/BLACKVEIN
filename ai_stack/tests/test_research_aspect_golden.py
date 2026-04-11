from __future__ import annotations

from ai_stack.research_aspect_extraction import extract_and_store_aspects
from ai_stack.research_fixtures import fixture_b_aspect_input
from ai_stack.research_golden_cases import EXPECTED_PERSPECTIVES
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore


def test_fixture_b_aspect_extraction_perspective_separation(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    normalized = normalize_resource(**fixture_b_aspect_input())
    intake = ingest_resource(
        store=store,
        normalized_source=normalized,
        segment_target_words=16,
        segment_overlap_words=4,
    )
    aspects = extract_and_store_aspects(
        store=store,
        source_id=intake["source"]["source_id"],
        segments=intake["segments"],
    )
    assert len(aspects) == 14
    perspectives = sorted({row["perspective"] for row in aspects})
    assert tuple(perspectives) == EXPECTED_PERSPECTIVES
    assert all(row["statement"].startswith(f"{row['perspective']}:") for row in aspects)
    assert all(row["aspect_type"] for row in aspects)
    assert all(row["evidence_anchor_ids"] for row in aspects)
    assert all(row["status"] == "exploratory" for row in aspects)
