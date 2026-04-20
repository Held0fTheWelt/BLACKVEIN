from __future__ import annotations

from ai_stack.research_fixtures import fixture_a_intake_input
from ai_stack.research_golden_cases import EXPECTED_INTAKE_SEGMENT_COUNT
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore


def test_fixture_a_intake_normalization_and_policy_enforcement(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    payload = fixture_a_intake_input()
    normalized = normalize_resource(**payload)
    assert normalized["source_id"] == "source_e1e0a634e6e9a014"
    assert normalized["copyright_posture"] == "internal_approved"

    intake = ingest_resource(
        store=store,
        normalized_source=normalized,
        segment_target_words=16,
        segment_overlap_words=4,
    )
    assert intake["source"]["segment_index_status"] == "indexed"
    assert intake["source"]["metadata"]["fixture"] == "A"
    assert len(intake["segments"]) == EXPECTED_INTAKE_SEGMENT_COUNT
    assert len(intake["anchors"]) == EXPECTED_INTAKE_SEGMENT_COUNT
    assert [segment["segment_ref"] for segment in intake["segments"]] == ["seg_0001", "seg_0002", "seg_0003"]
    assert all(segment["source_id"] == intake["source"]["source_id"] for segment in intake["segments"])
    first_anchor = intake["anchors"][0]
    assert first_anchor["source_id"] == intake["source"]["source_id"]
    assert first_anchor["paraphrase_or_excerpt"] == intake["segments"][0]["text"]
