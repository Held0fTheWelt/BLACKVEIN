"""Test coverage for capabilities_registry_research_canon_handlers — handler dispatch and payload processing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from ai_stack.capabilities_registry_research_canon_handlers import (
    research_source_inspect_handler,
    research_aspect_extract_handler,
    research_claim_list_handler,
    research_run_get_handler,
    research_exploration_graph_handler,
    canon_issue_inspect_handler,
    research_explore_handler,
    research_validate_handler,
    research_bundle_build_handler,
    canon_improvement_propose_handler,
    canon_improvement_preview_handler,
)


class TestResearchSourceInspectHandler:
    """Handler for inspect_source operation."""

    def test_successful_source_inspection(self):
        """Inspect valid source with store."""
        mock_store = MagicMock()
        payload = {"source_id": "src_12345"}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {
                "source": {"source_id": "src_12345", "title": "Test Source"},
                "anchors": [{"anchor_id": "anc_1"}],
                "aspects": [{"aspect_id": "asp_1"}],
            }
            result = research_source_inspect_handler(mock_store, payload)

        assert result["source"]["source_id"] == "src_12345"
        assert len(result["anchors"]) == 1
        assert len(result["aspects"]) == 1

    def test_source_id_string_conversion(self):
        """Ensure source_id converted to string."""
        mock_store = MagicMock()
        payload = {"source_id": 12345}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {"source": {}, "anchors": [], "aspects": []}
            research_source_inspect_handler(mock_store, payload)
            mock_inspect.assert_called_once_with(store=mock_store, source_id="12345")

    def test_missing_source_error(self):
        """Handler returns error when source not found."""
        mock_store = MagicMock()
        payload = {"source_id": "nonexistent"}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {"error": "source_not_found", "source_id": "nonexistent"}
            result = research_source_inspect_handler(mock_store, payload)

        assert result["error"] == "source_not_found"


class TestResearchAspectExtractHandler:
    """Handler for aspect extraction from source."""

    def test_successful_aspect_extraction(self):
        """Extract aspects from valid source."""
        mock_store = MagicMock()
        payload = {"source_id": "src_789"}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {
                "aspects": [
                    {"aspect_id": "asp_1", "statement": "Test aspect 1"},
                    {"aspect_id": "asp_2", "statement": "Test aspect 2"},
                ]
            }
            result = research_aspect_extract_handler(mock_store, payload)

        assert result["source_id"] == "src_789"
        assert len(result["aspects"]) == 2
        assert result["aspects"][0]["aspect_id"] == "asp_1"

    def test_extraction_with_error_in_inspect(self):
        """Handler propagates error from inspect_source."""
        mock_store = MagicMock()
        payload = {"source_id": "src_bad"}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {"error": "source_not_found"}
            result = research_aspect_extract_handler(mock_store, payload)

        assert result["error"] == "source_not_found"

    def test_extraction_with_missing_aspects(self):
        """Handler returns empty aspects list when not present."""
        mock_store = MagicMock()
        payload = {"source_id": "src_empty"}

        with patch("ai_stack.research_langgraph.inspect_source") as mock_inspect:
            mock_inspect.return_value = {}
            result = research_aspect_extract_handler(mock_store, payload)

        assert result["aspects"] == []


class TestResearchClaimListHandler:
    """Handler for listing research claims."""

    def test_list_all_claims(self):
        """List claims without work_id filter."""
        mock_store = MagicMock()
        payload = {"work_id": None}

        with patch("ai_stack.research_langgraph.list_claims") as mock_list:
            mock_list.return_value = {
                "claims": [
                    {"claim_id": "cl_1", "statement": "Claim 1"},
                    {"claim_id": "cl_2", "statement": "Claim 2"},
                ]
            }
            result = research_claim_list_handler(mock_store, payload)

        assert len(result["claims"]) == 2

    def test_list_claims_filtered_by_work_id(self):
        """List claims for specific work."""
        mock_store = MagicMock()
        payload = {"work_id": "god_of_carnage"}

        with patch("ai_stack.research_langgraph.list_claims") as mock_list:
            mock_list.return_value = {
                "claims": [{"claim_id": "cl_1", "work_id": "god_of_carnage"}]
            }
            result = research_claim_list_handler(mock_store, payload)
            mock_list.assert_called_once_with(store=mock_store, work_id="god_of_carnage")

        assert len(result["claims"]) == 1

    def test_list_claims_missing_work_id(self):
        """Handler uses None when work_id not in payload."""
        mock_store = MagicMock()
        payload = {}

        with patch("ai_stack.research_langgraph.list_claims") as mock_list:
            mock_list.return_value = {"claims": []}
            research_claim_list_handler(mock_store, payload)
            mock_list.assert_called_once_with(store=mock_store, work_id=None)


class TestResearchRunGetHandler:
    """Handler for retrieving research runs."""

    def test_get_valid_run(self):
        """Retrieve run with valid run_id."""
        mock_store = MagicMock()
        payload = {"run_id": "run_123"}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {
                "run": {
                    "run_id": "run_123",
                    "status": "completed",
                }
            }
            result = research_run_get_handler(mock_store, payload)

        assert result["run"]["run_id"] == "run_123"
        assert result["run"]["status"] == "completed"

    def test_run_id_string_conversion(self):
        """Ensure run_id converted to string."""
        mock_store = MagicMock()
        payload = {"run_id": 999}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {"run": {}}
            research_run_get_handler(mock_store, payload)
            mock_get.assert_called_once_with(store=mock_store, run_id="999")

    def test_get_missing_run_error(self):
        """Handler returns error for missing run."""
        mock_store = MagicMock()
        payload = {"run_id": "missing_run"}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {"error": "run_not_found", "run_id": "missing_run"}
            result = research_run_get_handler(mock_store, payload)

        assert result["error"] == "run_not_found"


class TestResearchExplorationGraphHandler:
    """Handler for retrieving exploration graphs."""

    def test_exploration_graph_retrieval(self):
        """Retrieve exploration graph for run."""
        mock_store = MagicMock()
        payload = {"run_id": "run_explore_1"}

        with patch("ai_stack.research_langgraph.exploration_graph") as mock_graph:
            mock_graph.return_value = {
                "run_id": "run_explore_1",
                "nodes": [{"node_id": "n1"}],
                "edges": [{"edge_id": "e1"}],
            }
            result = research_exploration_graph_handler(mock_store, payload)

        assert result["run_id"] == "run_explore_1"
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 1

    def test_run_id_string_conversion_for_graph(self):
        """Ensure run_id converted to string for graph."""
        mock_store = MagicMock()
        payload = {"run_id": 555}

        with patch("ai_stack.research_langgraph.exploration_graph") as mock_graph:
            mock_graph.return_value = {"run_id": "555", "nodes": [], "edges": []}
            research_exploration_graph_handler(mock_store, payload)
            mock_graph.assert_called_once_with(store=mock_store, run_id="555")

    def test_graph_retrieval_not_found(self):
        """Handler returns error when graph not found."""
        mock_store = MagicMock()
        payload = {"run_id": "missing_graph"}

        with patch("ai_stack.research_langgraph.exploration_graph") as mock_graph:
            mock_graph.return_value = {"error": "run_not_found"}
            result = research_exploration_graph_handler(mock_store, payload)

        assert result["error"] == "run_not_found"


class TestCanonIssueInspectHandler:
    """Handler for inspecting canon issues."""

    def test_inspect_canon_issues(self):
        """Inspect canon issues for module."""
        mock_store = MagicMock()
        payload = {"module_id": "mod_example"}

        with patch("ai_stack.research_langgraph.inspect_canon_issue") as mock_inspect:
            mock_inspect.return_value = {
                "issues": [
                    {"issue_id": "iss_1", "module_id": "mod_example"},
                ]
            }
            result = canon_issue_inspect_handler(mock_store, payload)

        assert len(result["issues"]) == 1
        assert result["issues"][0]["module_id"] == "mod_example"

    def test_inspect_canon_issues_missing_module_id(self):
        """Handler accepts None for module_id."""
        mock_store = MagicMock()
        payload = {}

        with patch("ai_stack.research_langgraph.inspect_canon_issue") as mock_inspect:
            mock_inspect.return_value = {"issues": []}
            canon_issue_inspect_handler(mock_store, payload)
            mock_inspect.assert_called_once_with(store=mock_store, module_id=None)


class TestResearchExploreHandler:
    """Handler for running research exploration."""

    def test_explore_with_budget(self):
        """Run exploration with provided budget."""
        mock_store = MagicMock()
        budget_dict = {
            "max_depth": 3,
            "max_branches_per_node": 4,
            "max_total_nodes": 50,
            "max_low_evidence_expansions": 10,
            "llm_call_budget": 100,
            "token_budget": 5000,
            "time_budget_ms": 30000,
            "abort_on_redundancy": True,
            "abort_on_speculative_drift": False,
            "model_profile": "fast",
        }
        payload = {
            "work_id": "work_123",
            "module_id": "mod_456",
            "source_inputs": [
                {"source_type": "note", "raw_text": "Some text"}
            ],
            "seed_question": "What is happening?",
            "budget": budget_dict,
        }

        with patch("ai_stack.research_langgraph.run_research_pipeline") as mock_run:
            mock_run.return_value = {
                "run_id": "run_999",
                "outputs": {
                    "exploration_summary": {
                        "abort_reason": "completed_within_budget",
                        "node_count": 10,
                    }
                },
            }
            result = research_explore_handler(mock_store, payload)

        assert result["run_id"] == "run_999"
        assert "exploration_summary" in result
        assert result["effective_budget"]["max_depth"] == 3

    def test_explore_with_default_empty_budget(self):
        """Handler uses empty budget dict when not provided."""
        mock_store = MagicMock()
        payload = {
            "work_id": "work_123",
            "module_id": "mod_456",
            "source_inputs": [],
            "seed_question": "Q?",
        }

        with patch("ai_stack.research_contract.ExplorationBudget") as mock_budget_cls:
            with patch("ai_stack.research_langgraph.run_research_pipeline") as mock_run:
                mock_budget_cls.from_payload.return_value = MagicMock(to_dict=MagicMock(return_value={}))
                mock_run.return_value = {"run_id": "run_x", "outputs": {"exploration_summary": {}}}
                research_explore_handler(mock_store, payload)
                mock_budget_cls.from_payload.assert_called_once_with({})

    def test_explore_payload_string_conversion(self):
        """Ensure work_id, module_id, seed_question converted to strings."""
        mock_store = MagicMock()
        payload = {
            "work_id": 111,
            "module_id": 222,
            "source_inputs": [],
            "seed_question": 333,
            "budget": {
                "max_depth": 3,
                "max_branches_per_node": 4,
                "max_total_nodes": 50,
                "max_low_evidence_expansions": 10,
                "llm_call_budget": 100,
                "token_budget": 5000,
                "time_budget_ms": 30000,
                "abort_on_redundancy": True,
                "abort_on_speculative_drift": False,
                "model_profile": "fast",
            },
        }

        with patch("ai_stack.research_langgraph.run_research_pipeline") as mock_run:
            mock_run.return_value = {"run_id": "run_y", "outputs": {"exploration_summary": {}}}
            research_explore_handler(mock_store, payload)

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["work_id"] == "111"
            assert call_kwargs["module_id"] == "222"
            assert call_kwargs["seed_question"] == "333"


class TestResearchValidateHandler:
    """Handler for validating research runs."""

    def test_validate_run_success(self):
        """Validate run and extract claims."""
        mock_store = MagicMock()
        payload = {"run_id": "run_validate_1"}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {
                "run": {
                    "run_id": "run_validate_1",
                    "outputs": {
                        "claim_ids": ["cl_1", "cl_2"],
                    },
                }
            }
            result = research_validate_handler(mock_store, payload)

        assert result["run_id"] == "run_validate_1"
        assert result["claims"] == ["cl_1", "cl_2"]
        assert result["status"] == "validated_from_run_outputs"

    def test_validate_run_with_error(self):
        """Handler propagates error from get_run."""
        mock_store = MagicMock()
        payload = {"run_id": "missing_validate"}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {"error": "run_not_found"}
            result = research_validate_handler(mock_store, payload)

        assert result["error"] == "run_not_found"

    def test_validate_run_missing_outputs(self):
        """Handler handles missing outputs gracefully."""
        mock_store = MagicMock()
        payload = {"run_id": "run_no_outputs"}

        with patch("ai_stack.research_langgraph.get_run") as mock_get:
            mock_get.return_value = {"run": {"run_id": "run_no_outputs"}}
            result = research_validate_handler(mock_store, payload)

        assert result["claims"] == []
        assert result["status"] == "validated_from_run_outputs"


class TestResearchBundleBuildHandler:
    """Handler for building research bundles."""

    def test_build_bundle_success(self):
        """Build research bundle from run."""
        mock_store = MagicMock()
        payload = {"run_id": "run_bundle_1"}

        with patch("ai_stack.research_langgraph.build_research_bundle") as mock_build:
            mock_build.return_value = {
                "bundle": {
                    "run_id": "run_bundle_1",
                    "sections": ["intake", "aspects"],
                }
            }
            result = research_bundle_build_handler(mock_store, payload)

        assert result["bundle"]["run_id"] == "run_bundle_1"

    def test_bundle_run_id_string_conversion(self):
        """Ensure run_id converted to string."""
        mock_store = MagicMock()
        payload = {"run_id": 777}

        with patch("ai_stack.research_langgraph.build_research_bundle") as mock_build:
            mock_build.return_value = {"bundle": {}}
            research_bundle_build_handler(mock_store, payload)
            mock_build.assert_called_once_with(store=mock_store, run_id="777")


class TestCanonImprovementProposeHandler:
    """Handler for proposing canon improvements."""

    def test_propose_improvements(self):
        """Propose canon improvements for module."""
        mock_store = MagicMock()
        payload = {"module_id": "mod_improve_1"}

        with patch("ai_stack.research_langgraph.propose_canon_improvement") as mock_propose:
            mock_propose.return_value = {
                "module_id": "mod_improve_1",
                "proposals": [
                    {"proposal_id": "prop_1", "proposal_type": "tighten_conflict_core"},
                ],
            }
            result = canon_improvement_propose_handler(mock_store, payload)

        assert result["module_id"] == "mod_improve_1"
        assert len(result["proposals"]) == 1

    def test_propose_module_id_string_conversion(self):
        """Ensure module_id converted to string."""
        mock_store = MagicMock()
        payload = {"module_id": 888}

        with patch("ai_stack.research_langgraph.propose_canon_improvement") as mock_propose:
            mock_propose.return_value = {"module_id": "888", "proposals": []}
            canon_improvement_propose_handler(mock_store, payload)
            mock_propose.assert_called_once_with(store=mock_store, module_id="888")


class TestCanonImprovementPreviewHandler:
    """Handler for previewing canon improvements."""

    def test_preview_improvements(self):
        """Preview canon improvements for module."""
        mock_store = MagicMock()
        payload = {"module_id": "mod_preview_1"}

        with patch("ai_stack.research_langgraph.preview_canon_improvement") as mock_preview:
            mock_preview.return_value = {
                "module_id": "mod_preview_1",
                "preview": [
                    {
                        "proposal_id": "prop_1",
                        "proposal_type": "tighten_conflict_core",
                        "preview_patch_ref": "patch_1",
                        "mutation_allowed": False,
                    },
                ],
            }
            result = canon_improvement_preview_handler(mock_store, payload)

        assert result["module_id"] == "mod_preview_1"
        assert len(result["preview"]) == 1
        assert result["preview"][0]["mutation_allowed"] is False

    def test_preview_module_id_string_conversion(self):
        """Ensure module_id converted to string."""
        mock_store = MagicMock()
        payload = {"module_id": 999}

        with patch("ai_stack.research_langgraph.preview_canon_improvement") as mock_preview:
            mock_preview.return_value = {"module_id": "999", "preview": []}
            canon_improvement_preview_handler(mock_store, payload)
            mock_preview.assert_called_once_with(store=mock_store, module_id="999")


class TestHandlerDispatchIntegration:
    """Integration tests for handler dispatch patterns."""

    def test_all_handlers_accept_research_store_and_dict_payload(self):
        """All handlers follow same signature pattern."""
        handlers = [
            research_source_inspect_handler,
            research_aspect_extract_handler,
            research_claim_list_handler,
            research_run_get_handler,
            research_exploration_graph_handler,
            canon_issue_inspect_handler,
            research_explore_handler,
            research_validate_handler,
            research_bundle_build_handler,
            canon_improvement_propose_handler,
            canon_improvement_preview_handler,
        ]

        assert len(handlers) == 11
        for handler in handlers:
            assert callable(handler)

    def test_error_propagation_through_handlers(self):
        """Handlers that call other functions propagate errors correctly."""
        mock_store = MagicMock()

        error_cases = [
            (research_source_inspect_handler, {"source_id": "bad"}, "ai_stack.research_langgraph.inspect_source"),
            (research_run_get_handler, {"run_id": "bad"}, "ai_stack.research_langgraph.get_run"),
            (canon_issue_inspect_handler, {"module_id": "bad"}, "ai_stack.research_langgraph.inspect_canon_issue"),
        ]

        for handler, payload, func_path in error_cases:
            with patch(func_path) as mock_func:
                mock_func.return_value = {"error": "test_error"}
                result = handler(mock_store, payload)
                assert result.get("error") == "test_error"
