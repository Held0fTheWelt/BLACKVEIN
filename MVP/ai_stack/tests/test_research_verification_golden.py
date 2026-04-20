from __future__ import annotations

from ai_stack.research_fixtures import fixture_a_intake_input, fixture_d_candidate_payloads
from ai_stack.research_golden_cases import EXPECTED_CONTRADICTION_CLASSES, EXPECTED_VERIFICATION_STATUSES
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore
from ai_stack.research_validation import verify_and_promote_claims


def test_fixture_d_verification_support_contradiction_unresolved(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    intake = ingest_resource(
        store=store,
        normalized_source=normalize_resource(**fixture_a_intake_input()),
        segment_target_words=16,
        segment_overlap_words=4,
    )
    anchor_ids = [row["anchor_id"] for row in intake["anchors"]]
    candidates = fixture_d_candidate_payloads(anchor_ids)
    result = verify_and_promote_claims(
        store=store,
        work_id="god_of_carnage",
        candidate_payloads=candidates,
        support_threshold=0.1,
    )
    decisions = result["decisions"]
    assert [decision["statement"] for decision in decisions] == [
        "hard_conflict contradiction candidate",
        "supported claim about conflict pressure",
        "unresolved ambiguous unclear thread",
    ]
    assert decisions[0]["decision"] == "blocked"
    assert decisions[0]["reason"] == "hard_conflict"
    assert decisions[1]["decision"] == "promoted"
    assert decisions[1]["status"] == "canon_applicable"
    assert decisions[2]["decision"] == "blocked"
    assert decisions[2]["reason"] == "unresolved_mandatory_blocker"
    statuses = {claim["status"] for claim in result["claims"]}
    assert statuses <= EXPECTED_VERIFICATION_STATUSES
    assert statuses == {"canon_applicable"}
    contradiction = {claim["contradiction_status"] for claim in result["claims"]}
    assert contradiction <= EXPECTED_CONTRADICTION_CLASSES
    assert contradiction == {"none"}
