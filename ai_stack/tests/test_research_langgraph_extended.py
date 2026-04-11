"""Extended tests for research_langgraph.py covering all graph nodes and state transitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai_stack.research_fixtures import fixture_f_full_run_input
from ai_stack.research_langgraph import (
    _canon_relevance_hint,
    _review_safe_flag,
    build_review_bundle,
    exploration_graph,
    get_run,
    inspect_canon_issue,
    inspect_source,
    list_claims,
    preview_canon_improvement,
    propose_canon_improvement,
    research_store_from_repo_root,
    run_research_pipeline,
    build_research_bundle,
)
from ai_stack.research_store import ResearchStore


class TestReviewSafeFlag:
    """Tests for _review_safe_flag helper function."""

    def test_review_safe_all_conditions_pass(self) -> None:
        """Test safe review when all conditions are met."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is True

    def test_review_unsafe_hard_conflict_claim(self) -> None:
        """Test unsafe review when claim has hard_conflict contradiction status (line 19)."""
        claims = [
            {
                "contradiction_status": "hard_conflict",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_missing_evidence_anchor_ids(self) -> None:
        """Test unsafe review when claim lacks evidence_anchor_ids (line 20)."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": [],
            }
        ]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_missing_evidence_anchor_ids_key(self) -> None:
        """Test unsafe review when claim is missing evidence_anchor_ids key (line 20)."""
        claims = [{"contradiction_status": "none"}]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_token_budget_exhausted(self) -> None:
        """Test unsafe review when token budget exhausted (line 25)."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {"abort_reason": "token_budget_exhausted"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_llm_budget_exhausted(self) -> None:
        """Test unsafe review when LLM budget exhausted."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {"abort_reason": "llm_budget_exhausted"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_time_budget_exhausted(self) -> None:
        """Test unsafe review when time budget exhausted."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {"abort_reason": "time_budget_exhausted"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_safe_other_abort_reasons(self) -> None:
        """Test safe review with other abort reasons (not in unsafe list)."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        for abort_reason in ["depth_limit_reached", "branch_budget_exhausted", "redundancy_abort"]:
            exploration_summary = {"abort_reason": abort_reason}
            assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is True

    def test_review_safe_missing_abort_reason(self) -> None:
        """Test safe review when abort_reason is missing."""
        claims = [
            {
                "contradiction_status": "none",
                "evidence_anchor_ids": ["anchor_1"],
            }
        ]
        exploration_summary = {}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is True

    def test_review_unsafe_multiple_claims_one_has_hard_conflict(self) -> None:
        """Test with multiple claims where one has hard_conflict."""
        claims = [
            {"contradiction_status": "none", "evidence_anchor_ids": ["a1"]},
            {"contradiction_status": "hard_conflict", "evidence_anchor_ids": ["a2"]},
        ]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_unsafe_empty_claims_list_but_missing_evidence(self) -> None:
        """Test with claims that have no evidence_anchor_ids."""
        claims = [
            {"contradiction_status": "none"},
            {"contradiction_status": "none", "evidence_anchor_ids": ["a1"]},
        ]
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is False

    def test_review_safe_with_empty_claims_list(self) -> None:
        """Test with empty claims list (vacuous truth)."""
        claims: list[dict[str, Any]] = []
        exploration_summary = {"abort_reason": "completed_within_budget"}
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is True


class TestCanonRelevanceHint:
    """Tests for _canon_relevance_hint helper function."""

    def test_canon_relevance_hint_improvement_probe(self) -> None:
        """Test node with 'improvement_probe' in hypothesis."""
        node = {"hypothesis": "This is an improvement_probe hypothesis"}
        assert _canon_relevance_hint(node) is True

    def test_canon_relevance_hint_tension_probe(self) -> None:
        """Test node with 'tension_probe' in hypothesis."""
        node = {"hypothesis": "This is a tension_probe analysis"}
        assert _canon_relevance_hint(node) is True

    def test_canon_relevance_hint_improvement_probe_case_insensitive(self) -> None:
        """Test case insensitivity for improvement_probe."""
        node = {"hypothesis": "This is an IMPROVEMENT_PROBE hypothesis"}
        assert _canon_relevance_hint(node) is True

    def test_canon_relevance_hint_tension_probe_case_insensitive(self) -> None:
        """Test case insensitivity for tension_probe."""
        node = {"hypothesis": "This is a TENSION_PROBE analysis"}
        assert _canon_relevance_hint(node) is True

    def test_canon_relevance_hint_no_probe(self) -> None:
        """Test node without probe keywords."""
        node = {"hypothesis": "This is a regular hypothesis"}
        assert _canon_relevance_hint(node) is False

    def test_canon_relevance_hint_missing_hypothesis(self) -> None:
        """Test node without hypothesis key."""
        node: dict[str, Any] = {}
        assert _canon_relevance_hint(node) is False

    def test_canon_relevance_hint_none_hypothesis(self) -> None:
        """Test node with None hypothesis."""
        node = {"hypothesis": None}
        assert _canon_relevance_hint(node) is False

    def test_canon_relevance_hint_empty_hypothesis(self) -> None:
        """Test node with empty hypothesis."""
        node = {"hypothesis": ""}
        assert _canon_relevance_hint(node) is False


class TestBuildReviewBundle:
    """Tests for build_review_bundle function."""

    def test_build_review_bundle_basic_structure(self) -> None:
        """Test basic review bundle structure."""
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[{"source_id": "src_1"}],
            anchors=[{"anchor_id": "anc_1", "source_id": "src_1"}],
            aspects=[],
            claims=[],
            issues=[],
            proposals=[],
            exploration_summary={"abort_reason": "completed_within_budget"},
        )
        assert bundle["bundle_schema_version"] == "research_review_bundle_v1"
        assert bundle["run_id"] == "run_1"
        assert bundle["work_id"] == "work_1"
        assert bundle["module_id"] == "module_1"
        assert tuple(bundle["sections"]) == (
            "intake",
            "aspects",
            "exploration",
            "verification",
            "canon_improvement",
            "governance",
        )

    def test_build_review_bundle_contradiction_summary(self) -> None:
        """Test contradiction_summary aggregation with multiple statuses (lines 48-50)."""
        claims = [
            {"contradiction_status": "none"},
            {"contradiction_status": "none"},
            {"contradiction_status": "hard_conflict"},
            {"contradiction_status": "unresolved"},
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=claims,
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["verification"]["contradiction_summary"] == {
            "none": 2,
            "hard_conflict": 1,
            "unresolved": 1,
        }

    def test_build_review_bundle_status_summary(self) -> None:
        """Test status_summary aggregation with multiple statuses (lines 52-54)."""
        claims = [
            {"status": "approved"},
            {"status": "approved"},
            {"status": "pending"},
            {"status": "unknown"},
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=claims,
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["verification"]["status_summary"] == {
            "approved": 2,
            "pending": 1,
            "unknown": 1,
        }

    def test_build_review_bundle_empty_contradiction_summary(self) -> None:
        """Test contradiction_summary with claims lacking status."""
        claims = [{"claim_id": "c1"}]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=claims,
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["verification"]["contradiction_summary"] == {"none": 1}

    def test_build_review_bundle_empty_status_summary(self) -> None:
        """Test status_summary with claims lacking status."""
        claims = [{"claim_id": "c1"}]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=claims,
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["verification"]["status_summary"] == {"unknown": 1}

    def test_build_review_bundle_perspective_summary(self) -> None:
        """Test perspective_summary aggregation."""
        aspects = [
            {"perspective": "actor"},
            {"perspective": "director"},
            {"perspective": "actor"},
            {"perspective": "unknown"},
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=aspects,
            claims=[],
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["aspects"]["perspective_summary"] == {
            "actor": 2,
            "director": 1,
            "unknown": 1,
        }

    def test_build_review_bundle_source_ids_sorting(self) -> None:
        """Test source_ids are sorted."""
        sources = [{"source_id": "src_3"}, {"source_id": "src_1"}, {"source_id": "src_2"}]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=sources,
            anchors=[],
            aspects=[],
            claims=[],
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["intake"]["source_ids"] == ["src_1", "src_2", "src_3"]

    def test_build_review_bundle_source_ids_with_aspects(self) -> None:
        """Test source_ids_with_aspects filtering."""
        aspects = [
            {"aspect_id": "a1", "source_id": "src_1"},
            {"aspect_id": "a2", "source_id": "src_1"},
            {"aspect_id": "a3", "source_id": "src_2"},
            {"aspect_id": "a4"},  # Missing source_id
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=aspects,
            claims=[],
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["aspects"]["source_ids_with_aspects"] == ["src_1", "src_2"]

    def test_build_review_bundle_proposal_types(self) -> None:
        """Test proposal_types aggregation."""
        proposals = [
            {"proposal_type": "add_note"},
            {"proposal_type": "refine_staging"},
            {"proposal_type": "add_note"},
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=[],
            issues=[],
            proposals=proposals,
            exploration_summary={},
        )
        assert bundle["canon_improvement"]["proposal_types"] == ["add_note", "refine_staging"]

    def test_build_review_bundle_review_safe_flag_integration(self) -> None:
        """Test review_safe flag integration."""
        claims = [
            {"contradiction_status": "hard_conflict", "evidence_anchor_ids": ["a1"]}
        ]
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=claims,
            issues=[],
            proposals=[],
            exploration_summary={"abort_reason": "completed_within_budget"},
        )
        assert bundle["governance"]["review_safe"] is False

    def test_build_review_bundle_governance_structure(self) -> None:
        """Test governance section structure."""
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[],
            anchors=[],
            aspects=[],
            claims=[],
            issues=[],
            proposals=[],
            exploration_summary={},
        )
        assert bundle["governance"]["canon_mutation_permitted"] is False
        assert bundle["governance"]["silent_mutation_blocked"] is True


class TestInspectSourceErrorPaths:
    """Tests for inspect_source function error handling."""

    def test_inspect_source_not_found(self, tmp_path: Path) -> None:
        """Test inspecting non-existent source (line 227-229)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = inspect_source(store=store, source_id="nonexistent")
        assert result["error"] == "source_not_found"
        assert result["source_id"] == "nonexistent"

    def test_inspect_source_with_empty_anchors_and_aspects(self, tmp_path: Path) -> None:
        """Test inspecting source with no anchors or aspects."""
        store = ResearchStore(tmp_path / "test_store.json")
        # Create source through store
        store.upsert_source({
            "source_id": "src_test",
            "work_id": "work_1",
            "source_type": "note",
            "title": "Test",
            "provenance": {"origin": "test"},
            "visibility": "internal",
            "copyright_posture": "internal_approved",
            "segment_index_status": "completed",
            "metadata": {"test": "value"},
        })
        result = inspect_source(store=store, source_id="src_test")
        assert result["source"]["source_id"] == "src_test"
        assert len(result["anchors"]) == 0
        assert len(result["aspects"]) == 0


class TestListClaimsErrorPaths:
    """Tests for list_claims function."""

    def test_list_claims_empty_store(self, tmp_path: Path) -> None:
        """Test listing claims from empty store."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = list_claims(store=store)
        assert result["claims"] == []

    def test_list_claims_filter_with_no_matching_work_id(self, tmp_path: Path) -> None:
        """Test filtering claims with no matches (line 241-242)."""
        store = ResearchStore(tmp_path / "test_store.json")
        # Store has no claims, so filtering will also return empty
        result = list_claims(store=store, work_id="nonexistent")
        assert len(result["claims"]) == 0


class TestGetRunErrorPaths:
    """Tests for get_run function."""

    def test_get_run_not_found(self, tmp_path: Path) -> None:
        """Test getting non-existent run (line 247-249)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = get_run(store=store, run_id="nonexistent")
        assert result["error"] == "run_not_found"
        assert result["run_id"] == "nonexistent"


class TestExplorationGraphErrorPaths:
    """Tests for exploration_graph function."""

    def test_exploration_graph_run_not_found(self, tmp_path: Path) -> None:
        """Test exploration_graph with non-existent run (line 254-256)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = exploration_graph(store=store, run_id="nonexistent")
        assert result["error"] == "run_not_found"
        assert result["run_id"] == "nonexistent"

    def test_exploration_graph_empty_nodes(self, tmp_path: Path) -> None:
        """Test exploration_graph with run but no nodes (lines 258-268)."""
        store = ResearchStore(tmp_path / "test_store.json")
        run_data = {
            "run_id": "run_1",
            "mode": "research_full",
            "source_ids": ["src_1"],
            "seed_question": "test?",
            "budget": {"max_depth": 2},
            "outputs": {
                "exploration_node_ids": [],
            },
            "audit_refs": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        store.upsert_run(run_data)
        result = exploration_graph(store=store, run_id="run_1")
        assert result["run_id"] == "run_1"
        assert len(result["nodes"]) == 0
        assert len(result["edges"]) == 0


class TestInspectCanonIssueErrorPaths:
    """Tests for inspect_canon_issue function."""

    def test_inspect_canon_issue_all(self, tmp_path: Path) -> None:
        """Test listing all issues without module filter."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = inspect_canon_issue(store=store)
        assert "issues" in result
        assert result["issues"] == []

    def test_inspect_canon_issue_filter_no_matches(self, tmp_path: Path) -> None:
        """Test filtering issues by module_id with no matches (line 274-275)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = inspect_canon_issue(store=store, module_id="nonexistent")
        assert len(result["issues"]) == 0


class TestBuildResearchBundleErrorPaths:
    """Tests for build_research_bundle function."""

    def test_build_research_bundle_run_not_found(self, tmp_path: Path) -> None:
        """Test bundle building with non-existent run (line 280-282)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = build_research_bundle(store=store, run_id="nonexistent")
        assert result["error"] == "run_not_found"
        assert result["run_id"] == "nonexistent"

    def test_build_research_bundle_missing_bundle(self, tmp_path: Path) -> None:
        """Test when run exists but bundle is missing (line 285-286)."""
        store = ResearchStore(tmp_path / "test_store.json")
        run_data = {
            "run_id": "run_1",
            "mode": "research_full",
            "source_ids": ["src_1"],
            "seed_question": "test?",
            "budget": {"max_depth": 2},
            "outputs": {"result": "test"},
            "audit_refs": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        store.upsert_run(run_data)
        result = build_research_bundle(store=store, run_id="run_1")
        assert result["error"] == "bundle_missing"
        assert result["run_id"] == "run_1"

    def test_build_research_bundle_bundle_not_dict(self, tmp_path: Path) -> None:
        """Test when bundle is not a dict (line 285)."""
        store = ResearchStore(tmp_path / "test_store.json")
        run_data = {
            "run_id": "run_1",
            "mode": "research_full",
            "source_ids": ["src_1"],
            "seed_question": "test?",
            "budget": {"max_depth": 2},
            "outputs": {"bundle": "not a dict"},
            "audit_refs": [],
            "created_at": "2024-01-01T00:00:00Z",
        }
        store.upsert_run(run_data)
        result = build_research_bundle(store=store, run_id="run_1")
        assert result["error"] == "bundle_missing"


class TestPreviewCanonImprovementErrorPaths:
    """Tests for preview_canon_improvement function."""

    def test_preview_canon_improvement_no_proposals(self, tmp_path: Path) -> None:
        """Test with no proposals for module (line 297)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = preview_canon_improvement(store=store, module_id="nonexistent")
        assert result["module_id"] == "nonexistent"
        assert result["preview"] == []


class TestProposeCanonImprovementErrorPaths:
    """Tests for propose_canon_improvement function."""

    def test_propose_canon_improvement_empty_claims(self, tmp_path: Path) -> None:
        """Test propose_canon_improvement with no CANON_APPLICABLE claims (line 291)."""
        store = ResearchStore(tmp_path / "test_store.json")
        result = propose_canon_improvement(store=store, module_id="module_1")
        # Result should be from derive_canon_improvements with empty claims
        assert isinstance(result, dict)


class TestResearchStoreFromRepoRoot:
    """Tests for research_store_from_repo_root function."""

    def test_research_store_from_repo_root_creates_store(self, tmp_path: Path) -> None:
        """Test that function creates/returns ResearchStore (line 223)."""
        # Create a minimal repo structure
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        store = research_store_from_repo_root(repo_root)
        assert isinstance(store, ResearchStore)


class TestFullPipelineIntegration:
    """Integration tests for complete research pipeline."""

    def test_run_research_pipeline_full_execution(self, tmp_path: Path) -> None:
        """Test full research pipeline execution with fixtures."""
        store = ResearchStore(tmp_path / "research_store.json")
        fixture = fixture_f_full_run_input()

        run = run_research_pipeline(
            store=store,
            work_id=fixture["work_id"],
            module_id=fixture["module_id"],
            source_inputs=fixture["source_inputs"],
            seed_question=fixture["seed_question"],
            budget_payload=fixture["budget"],
            run_id="run_full_integration",
        )

        # Verify output structure
        assert run["run_id"] == "run_full_integration"
        assert "outputs" in run
        assert "bundle" in run["outputs"]
        assert "exploration_summary" in run["outputs"]


class TestEdgeCasesAndErrorPaths:
    """Test edge cases and error handling."""

    def test_review_safe_flag_with_string_values(self) -> None:
        """Test _review_safe_flag with non-standard string values."""
        claims = [{"contradiction_status": "  hard_conflict  ", "evidence_anchor_ids": ["a1"]}]
        exploration_summary = {"abort_reason": "completed"}
        # Should not match because of whitespace (str.get() preserves whitespace)
        assert _review_safe_flag(claims=claims, exploration_summary=exploration_summary) is True

    def test_canon_relevance_hint_with_mixed_case_probe(self) -> None:
        """Test _canon_relevance_hint with various case combinations."""
        node = {"hypothesis": "This IMPROVEMENT_probe test"}
        assert _canon_relevance_hint(node) is True

    def test_build_review_bundle_with_null_values(self) -> None:
        """Test build_review_bundle handles None values gracefully."""
        bundle = build_review_bundle(
            run_id="run_1",
            work_id="work_1",
            module_id="module_1",
            sources=[{"source_id": None}],
            anchors=[{"anchor_id": None}],
            aspects=[{"perspective": None}],
            claims=[{"contradiction_status": None, "status": None}],
            issues=[],
            proposals=[],
            exploration_summary={"abort_reason": None},
        )
        assert "verification" in bundle
        assert "aspects" in bundle
