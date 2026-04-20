from __future__ import annotations

from ai_stack.canon_improvement_engine import derive_canon_improvements
from ai_stack.research_fixtures import fixture_a_intake_input, fixture_d_candidate_payloads, fixture_e_module_id
from ai_stack.research_golden_cases import EXPECTED_ISSUE_TYPES, EXPECTED_PROPOSAL_TYPES
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore
from ai_stack.research_validation import verify_and_promote_claims


def test_fixture_e_canon_issue_and_proposal_taxonomy(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    intake = ingest_resource(
        store=store,
        normalized_source=normalize_resource(**fixture_a_intake_input()),
        segment_target_words=16,
        segment_overlap_words=4,
    )
    candidates = fixture_d_candidate_payloads([row["anchor_id"] for row in intake["anchors"]])
    verified = verify_and_promote_claims(
        store=store,
        work_id="god_of_carnage",
        candidate_payloads=candidates,
        support_threshold=0.1,
    )
    result = derive_canon_improvements(
        store=store,
        module_id=fixture_e_module_id(),
        claims=verified["claims"],
    )
    assert result["issues"]
    assert result["proposals"]
    issue_types = {row["issue_type"] for row in result["issues"]}
    proposal_types = {row["proposal_type"] for row in result["proposals"]}
    assert issue_types <= EXPECTED_ISSUE_TYPES
    assert proposal_types <= EXPECTED_PROPOSAL_TYPES
    assert issue_types == {"unclear_scene_function"}
    assert proposal_types == {"tighten_conflict_core"}
    assert all(row["status"] == "approved_research" for row in result["issues"])
    assert all(row["status"] == "approved_research" for row in result["proposals"])
    assert all(row["module_id"] == fixture_e_module_id() for row in result["issues"])
    assert all(row["module_id"] == fixture_e_module_id() for row in result["proposals"])
    assert all(row["preview_patch_ref"]["mutation_allowed"] is False for row in result["proposals"])
