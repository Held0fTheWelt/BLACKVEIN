from __future__ import annotations

from ai_stack.research_aspect_extraction import extract_and_store_aspects
from ai_stack.research_contract import ExplorationBudget
from ai_stack.research_exploration import run_bounded_exploration
from ai_stack.research_fixtures import fixture_b_aspect_input, fixture_c_exploration_budget
from ai_stack.research_golden_cases import EXPECTED_EXPLORATION_ABORT_REASONS
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore


def test_fixture_c_exploration_bounded_deterministic_shape(tmp_path):
    store = ResearchStore(tmp_path / "research_store.json")
    normalized = normalize_resource(**fixture_b_aspect_input())
    intake = ingest_resource(store=store, normalized_source=normalized, segment_target_words=16, segment_overlap_words=4)
    aspects = extract_and_store_aspects(
        store=store,
        source_id=intake["source"]["source_id"],
        segments=intake["segments"],
    )
    budget = ExplorationBudget.from_payload(fixture_c_exploration_budget())
    result = run_bounded_exploration(seed_aspects=aspects, budget=budget)

    assert result.abort_reason == "node_budget_exhausted"
    assert result.abort_reason in EXPECTED_EXPLORATION_ABORT_REASONS
    assert len(result.nodes) == 12
    assert len(result.edges) == 0
    assert result.promoted_candidate_count == 0
    assert len(result.nodes) <= budget.max_total_nodes
    assert result.consumed_budget["llm_calls"] <= budget.llm_call_budget
    assert result.consumed_budget["tokens"] <= budget.token_budget
    assert result.consumed_budget["nodes"] == len(result.nodes)
    assert result.consumed_budget["branches"] == len(result.edges)
    assert result.consumed_budget["elapsed_wall_time_ms"] <= budget.time_budget_ms
