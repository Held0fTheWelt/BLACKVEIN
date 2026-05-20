"""Test coverage for research_exploration_bounded — bounded exploration runner, contradiction scanning, and exploration result."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from ai_stack.research.research_exploration_bounded import (
    ExplorationResult,
    deterministic_contradiction_scan,
    run_bounded_exploration,
)
from ai_stack.research.research_contract import (
    ContradictionStatus,
    ExplorationAbortReason,
    ExplorationBudget,
    Perspective,
    ResearchStatus,
    ExplorationOutcome,
    ExplorationRelationType,
)


class TestExplorationResult:
    """Tests for ExplorationResult dataclass."""

    def test_exploration_result_initialization(self):
        """Create ExplorationResult with all fields."""
        result = ExplorationResult(
            nodes=[{"node_id": "n1"}],
            edges=[{"edge_id": "e1"}],
            abort_reason=ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value,
            promoted_candidate_count=5,
            rejected_branch_count=2,
            unresolved_branch_count=1,
            pruned_branch_count=3,
            consumed_budget={
                "llm_calls": 10,
                "tokens": 500,
                "nodes": 1,
                "branches": 2,
                "low_evidence_expansions": 0,
                "elapsed_wall_time_ms": 100,
            },
        )

        assert result.nodes == [{"node_id": "n1"}]
        assert result.edges == [{"edge_id": "e1"}]
        assert result.abort_reason == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value
        assert result.promoted_candidate_count == 5
        assert result.rejected_branch_count == 2
        assert result.unresolved_branch_count == 1
        assert result.pruned_branch_count == 3

    def test_exploration_result_to_dict(self):
        """Convert ExplorationResult to dict."""
        result = ExplorationResult(
            nodes=[{"node_id": "n1"}, {"node_id": "n2"}],
            edges=[],
            abort_reason=ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value,
            promoted_candidate_count=10,
            rejected_branch_count=5,
            unresolved_branch_count=2,
            pruned_branch_count=4,
            consumed_budget={
                "llm_calls": 20,
                "tokens": 1000,
                "nodes": 2,
                "branches": 5,
                "low_evidence_expansions": 1,
                "elapsed_wall_time_ms": 250,
            },
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["abort_reason"] == ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value
        assert len(result_dict["nodes"]) == 2
        assert result_dict["promoted_candidate_count"] == 10
        assert result_dict["consumed_budget"]["llm_calls"] == 20

    def test_exploration_result_empty_collections(self):
        """Create ExplorationResult with empty nodes and edges."""
        result = ExplorationResult(
            nodes=[],
            edges=[],
            abort_reason=ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value,
            promoted_candidate_count=0,
            rejected_branch_count=0,
            unresolved_branch_count=0,
            pruned_branch_count=0,
            consumed_budget={},
        )

        assert result.nodes == []
        assert result.edges == []
        result_dict = result.to_dict()
        assert result_dict["nodes"] == []


class TestDeterministicContradictionScan:
    """Tests for deterministic_contradiction_scan function."""

    def test_hard_conflict_detection(self):
        """Detect hard_conflict keyword."""
        result = deterministic_contradiction_scan("This contains a hard_conflict")
        assert result == ContradictionStatus.HARD_CONFLICT

    def test_hard_conflict_detection_alternate(self):
        """Detect contradiction keyword for hard conflict."""
        result = deterministic_contradiction_scan("There is a contradiction here")
        assert result == ContradictionStatus.HARD_CONFLICT

    def test_counterview_detection(self):
        """Detect counterread keyword."""
        result = deterministic_contradiction_scan("A counterread perspective")
        assert result == ContradictionStatus.COUNTERVIEW_PRESENT

    def test_counterview_detection_alternate(self):
        """Detect counter_reading keyword."""
        result = deterministic_contradiction_scan("This is a counter_reading")
        assert result == ContradictionStatus.COUNTERVIEW_PRESENT

    def test_unresolved_detection(self):
        """Detect unclear keyword."""
        result = deterministic_contradiction_scan("The meaning is unclear")
        assert result == ContradictionStatus.UNRESOLVED

    def test_unresolved_detection_alternate(self):
        """Detect unresolved keyword."""
        result = deterministic_contradiction_scan("This remains unresolved")
        assert result == ContradictionStatus.UNRESOLVED

    def test_soft_conflict_detection(self):
        """Detect tension keyword."""
        result = deterministic_contradiction_scan("There is tension between the two")
        assert result == ContradictionStatus.SOFT_CONFLICT

    def test_soft_conflict_detection_alternate(self):
        """Detect contrast keyword."""
        result = deterministic_contradiction_scan("A contrast is evident")
        assert result == ContradictionStatus.SOFT_CONFLICT

    def test_no_contradiction(self):
        """Return NONE for clean statement."""
        result = deterministic_contradiction_scan("This is a simple statement")
        assert result == ContradictionStatus.NONE

    def test_case_insensitive_scanning(self):
        """Contradiction detection is case insensitive."""
        result = deterministic_contradiction_scan("THIS CONTAINS HARD_CONFLICT")
        assert result == ContradictionStatus.HARD_CONFLICT

    def test_whitespace_normalization(self):
        """Handle extra whitespace in statement."""
        result = deterministic_contradiction_scan("  lots   of   extra   tension  ")
        assert result == ContradictionStatus.SOFT_CONFLICT

    def test_empty_statement(self):
        """Empty statement returns NONE."""
        result = deterministic_contradiction_scan("")
        assert result == ContradictionStatus.NONE

    def test_contradiction_priority_hard_first(self):
        """hard_conflict takes priority in scanning order."""
        result = deterministic_contradiction_scan("hard_conflict with some tension")
        assert result == ContradictionStatus.HARD_CONFLICT

    def test_contradiction_priority_counterview_second(self):
        """counterread takes priority after hard_conflict."""
        result = deterministic_contradiction_scan("counterread with some tension")
        assert result == ContradictionStatus.COUNTERVIEW_PRESENT

    def test_contradiction_priority_unresolved_third(self):
        """unclear takes priority after counterview."""
        result = deterministic_contradiction_scan("unclear with some tension")
        assert result == ContradictionStatus.UNRESOLVED

    def test_contradiction_none_when_no_match(self):
        """All patterns can return NONE."""
        statements = [
            "Normal text without keywords",
            "Simple factual statement",
            "Another claim statement",
        ]
        for stmt in statements:
            result = deterministic_contradiction_scan(stmt)
            assert result == ContradictionStatus.NONE


class TestRunBoundedExploration:
    """Tests for run_bounded_exploration function."""

    def _make_budget(self) -> ExplorationBudget:
        """Create a default exploration budget."""
        return ExplorationBudget(
            max_depth=3,
            max_branches_per_node=4,
            max_total_nodes=50,
            max_low_evidence_expansions=10,
            llm_call_budget=100,
            token_budget=5000,
            time_budget_ms=30000,
            abort_on_redundancy=True,
            abort_on_speculative_drift=False,
            model_profile="fast",
        )

    def test_run_requires_budget(self):
        """Exploration requires non-None budget."""
        with pytest.raises(ValueError, match="exploration_budget_required"):
            run_bounded_exploration(
                seed_aspects=[],
                budget=None,
            )

    def test_run_with_empty_seed_aspects(self):
        """Empty seed aspects returns early with no nodes."""
        budget = self._make_budget()
        result = run_bounded_exploration(
            seed_aspects=[],
            budget=budget,
        )

        assert result.nodes == []
        assert result.edges == []
        assert result.abort_reason == ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value
        assert result.promoted_candidate_count == 0
        assert result.consumed_budget["nodes"] == 0

    def test_run_with_single_seed_aspect(self):
        """Create exploration nodes from seed aspect."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "Character motivation unclear",
                "perspective": Perspective.PLAYWRIGHT.value,
                "evidence_anchor_ids": ["anc_1", "anc_2"],
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 1
        assert result.abort_reason in [
            ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value,
            ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value,
        ]
        assert result.consumed_budget["nodes"] >= 1

    def test_run_with_multiple_seed_aspects(self):
        """Multiple seed aspects create multiple nodes."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "First aspect",
                "perspective": Perspective.PLAYWRIGHT.value,
                "evidence_anchor_ids": ["anc_1"],
            },
            {
                "aspect_id": "asp_2",
                "statement": "Second aspect",
                "perspective": Perspective.DIRECTOR.value,
                "evidence_anchor_ids": ["anc_2"],
            },
            {
                "aspect_id": "asp_3",
                "statement": "Third aspect",
                "perspective": Perspective.DRAMATURG.value,
                "evidence_anchor_ids": [],
            },
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 2
        assert result.consumed_budget["nodes"] >= 2

    def test_run_with_invalid_perspective(self):
        """Invalid perspective raises ValueError."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "Test",
                "perspective": "invalid_perspective",
                "evidence_anchor_ids": ["anc_1"],
            }
        ]

        with pytest.raises(ValueError, match="not a valid Perspective"):
            run_bounded_exploration(
                seed_aspects=seed_aspects,
                budget=budget,
            )

    def test_run_with_missing_optional_fields(self):
        """Handle seed aspects with missing optional fields."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "statement": "Minimal aspect",
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 1

    def test_run_respects_max_total_nodes(self):
        """Exploration stops when max_total_nodes reached."""
        budget = ExplorationBudget(
            max_depth=5,
            max_branches_per_node=10,
            max_total_nodes=2,
            max_low_evidence_expansions=0,
            llm_call_budget=100,
            token_budget=5000,
            time_budget_ms=30000,
            abort_on_redundancy=False,
            abort_on_speculative_drift=False,
            model_profile="fast",
        )
        seed_aspects = [
            {
                "aspect_id": f"asp_{i}",
                "statement": f"Aspect {i}",
                "evidence_anchor_ids": ["anc_1"],
            }
            for i in range(5)
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert result.consumed_budget["nodes"] <= 2

    def test_run_seed_aspects_ordered_deterministically(self):
        """Seed aspects are sorted before processing."""
        budget = self._make_budget()
        unordered_aspects = [
            {
                "aspect_id": "asp_c",
                "statement": "Charlie",
                "evidence_anchor_ids": ["anc_1"],
            },
            {
                "aspect_id": "asp_a",
                "statement": "Alice",
                "evidence_anchor_ids": ["anc_1"],
            },
            {
                "aspect_id": "asp_b",
                "statement": "Bob",
                "evidence_anchor_ids": ["anc_1"],
            },
        ]

        result = run_bounded_exploration(
            seed_aspects=unordered_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 3

    def test_run_with_empty_statements(self):
        """Empty statement aspects are skipped."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_empty",
                "statement": "   ",
                "evidence_anchor_ids": ["anc_1"],
            },
            {
                "aspect_id": "asp_valid",
                "statement": "Valid statement",
                "evidence_anchor_ids": ["anc_1"],
            },
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 1

    def test_run_result_consumed_budget_structure(self):
        """Consumed budget has expected structure."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "Test aspect",
                "evidence_anchor_ids": ["anc_1"],
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert "llm_calls" in result.consumed_budget
        assert "tokens" in result.consumed_budget
        assert "nodes" in result.consumed_budget
        assert "branches" in result.consumed_budget
        assert "low_evidence_expansions" in result.consumed_budget
        assert "elapsed_wall_time_ms" in result.consumed_budget

    def test_run_returns_nodes_with_required_fields(self):
        """Exploration nodes have required fields."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "Test",
                "evidence_anchor_ids": ["anc_1"],
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        for node in result.nodes:
            assert "node_id" in node
            assert "hypothesis" in node
            assert "perspective" in node
            assert "status" in node

    def test_run_budget_validation_called(self):
        """Budget is validated during exploration."""
        invalid_budget = MagicMock(spec=ExplorationBudget)
        invalid_budget.validate.side_effect = ValueError("invalid_budget")

        with pytest.raises(ValueError, match="invalid_budget"):
            run_bounded_exploration(
                seed_aspects=[],
                budget=invalid_budget,
            )

    def test_run_exploration_deterministic_with_same_input(self):
        """Same seed produces deterministic results."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_test",
                "statement": "Reproducible test aspect",
                "perspective": Perspective.PLAYWRIGHT.value,
                "evidence_anchor_ids": ["anc_1"],
            }
        ]

        result1 = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        result2 = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result1.nodes) == len(result2.nodes)
        assert result1.abort_reason == result2.abort_reason

    def test_run_aspect_without_anchor_ids(self):
        """Aspects without evidence_anchor_ids are processed."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": "asp_no_anchors",
                "statement": "Aspect without anchors",
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert len(result.nodes) >= 1

    def test_run_with_large_aspect_set(self):
        """Handle large number of seed aspects."""
        budget = self._make_budget()
        seed_aspects = [
            {
                "aspect_id": f"asp_{i}",
                "statement": f"Aspect statement {i}",
                "evidence_anchor_ids": ["anc_1"],
            }
            for i in range(100)
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        assert result.consumed_budget["nodes"] >= 1
        assert result.abort_reason in [
            ExplorationAbortReason.NODE_BUDGET_EXHAUSTED.value,
            ExplorationAbortReason.COMPLETED_WITHIN_BUDGET.value,
        ]


class TestRunBoundedExplorationIntegration:
    """Integration tests for bounded exploration."""

    def test_exploration_result_to_dict_roundtrip(self):
        """ExplorationResult can be serialized and contains expected data."""
        budget = ExplorationBudget(
            max_depth=2,
            max_branches_per_node=2,
            max_total_nodes=10,
            max_low_evidence_expansions=5,
            llm_call_budget=50,
            token_budget=2000,
            time_budget_ms=10000,
            abort_on_redundancy=True,
            abort_on_speculative_drift=True,
            model_profile="balanced",
        )
        seed_aspects = [
            {
                "aspect_id": "asp_1",
                "statement": "Integration test aspect",
                "evidence_anchor_ids": ["anc_1"],
            }
        ]

        result = run_bounded_exploration(
            seed_aspects=seed_aspects,
            budget=budget,
        )

        serialized = result.to_dict()
        assert isinstance(serialized, dict)
        assert serialized["abort_reason"] in [
            reason.value for reason in ExplorationAbortReason
        ]
        assert isinstance(serialized["nodes"], list)
        assert isinstance(serialized["edges"], list)
