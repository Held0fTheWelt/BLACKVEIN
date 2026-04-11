from __future__ import annotations

from ai_stack.research_fixtures import fixture_f_full_run_input
from ai_stack.research_golden_cases import EXPECTED_BUNDLE_SECTIONS
from ai_stack.research_langgraph import run_research_pipeline
from ai_stack.research_store import ResearchStore


def test_fixture_f_review_bundle_structure_and_review_safety(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    fixture = fixture_f_full_run_input()
    run = run_research_pipeline(
        store=store,
        work_id=fixture["work_id"],
        module_id=fixture["module_id"],
        source_inputs=fixture["source_inputs"],
        seed_question=fixture["seed_question"],
        budget_payload=fixture["budget"],
        run_id="run_fixture_f",
    )
    outputs = run["outputs"]
    bundle = outputs["bundle"]
    assert bundle["bundle_schema_version"] == "research_review_bundle_v1"
    assert tuple(bundle["sections"]) == EXPECTED_BUNDLE_SECTIONS
    assert bundle["intake"]["source_count"] == 2
    assert bundle["intake"]["anchor_count"] == 2
    assert bundle["aspects"]["aspect_count"] == 16
    assert bundle["aspects"]["perspective_summary"] == {
        "playwright": 4,
        "director": 4,
        "actor": 4,
        "dramaturg": 4,
    }
    assert bundle["governance"]["review_safe"] is True
    assert bundle["governance"]["canon_mutation_permitted"] is False
    assert bundle["governance"]["silent_mutation_blocked"] is True
    assert bundle["verification"]["claim_count"] == len(outputs["claim_ids"])
    assert bundle["canon_improvement"]["proposal_count"] == len(outputs["proposal_ids"])
