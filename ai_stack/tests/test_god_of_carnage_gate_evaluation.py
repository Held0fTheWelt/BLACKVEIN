# ai_stack/tests/test_god_of_carnage_gate_evaluation.py
from __future__ import annotations

import pytest

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_gate_evaluation import (
    gate_turn_integrity,
    gate_diagnostic_sufficiency,
    gate_dramatic_quality,
    gate_slice_boundary,
)


class TestGateTurnIntegrity:
    def test_pass_all_required_nodes_present(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": [
                    "goc_resolve_canonical_content",
                    "director_assess_scene",
                    "director_select_dramatic_parameters",
                    "proposal_normalize",
                    "validate_seam",
                    "commit_seam",
                    "render_visible",
                ]
            },
            "validation_outcome": {"status": "approved"},
            "committed_result": {"commit_applied": True},
            "module_id": "god_of_carnage",
        }
        assert gate_turn_integrity(state) == "pass"

    def test_fail_missing_required_node(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": ["goc_resolve_canonical_content"],
            }
        }
        assert gate_turn_integrity(state) == "fail"

    def test_fail_no_graph_diagnostics(self) -> None:
        state = {}
        assert gate_turn_integrity(state) == "fail"

    def test_pass_god_of_carnage_no_commit(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": [
                    "goc_resolve_canonical_content",
                    "director_assess_scene",
                    "director_select_dramatic_parameters",
                    "proposal_normalize",
                    "validate_seam",
                    "commit_seam",
                    "render_visible",
                ]
            },
            "validation_outcome": {"status": "approved"},
            "committed_result": {"commit_applied": False},
            "module_id": "god_of_carnage",
        }
        assert gate_turn_integrity(state) == "pass"


class TestGateDiagnosticSufficiency:
    def test_fail_invalid_repro_type(self) -> None:
        state = {
            "graph_diagnostics": {
                "repro_metadata": "not_a_dict",
            }
        }
        assert gate_diagnostic_sufficiency(state) == "fail"

    def test_conditional_pass_missing_graph_diagnostics(self) -> None:
        state = {}
        assert gate_diagnostic_sufficiency(state) == "conditional_pass"

    def test_pass_repro_metadata_complete(self) -> None:
        state = {
            "graph_diagnostics": {
                "repro_metadata": {
                    "graph_name": "test_graph",
                    "trace_id": "trace_123",
                    "selected_model": "gpt-4",
                    "selected_provider": "openai",
                    "retrieval_domain": "test_domain",
                    "retrieval_profile": "test_profile",
                    "model_attempted": True,
                    "model_success": True,
                    "adapter_invocation_mode": "test_mode",
                    "graph_path_summary": "test_summary",
                }
            }
        }
        assert gate_diagnostic_sufficiency(state) == "pass"


class TestGateDramaticQuality:
    def test_fail_rejected_dramatic_alignment(self) -> None:
        state = {
            "validation_outcome": {
                "status": "rejected",
                "reason": "dramatic_alignment_mismatch",
            }
        }
        assert gate_dramatic_quality(state) == "fail"

    def test_fail_rejected_dramatic_effect(self) -> None:
        state = {
            "validation_outcome": {
                "status": "rejected",
                "reason": "dramatic_effect_insufficient",
            }
        }
        assert gate_dramatic_quality(state) == "fail"

    def test_conditional_pass_not_approved(self) -> None:
        state = {
            "validation_outcome": {
                "status": "pending",
            }
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_pass_with_truth_aligned_marker(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_conditional_pass_short_narration_escalate(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": {"gm_narration": ["x"]},
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_conditional_pass_markers_not_list(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": "not_a_list",
            "experiment_preview": False,
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_pass_experiment_preview_false_no_truth_aligned(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["other_marker"],
            "experiment_preview": False,
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_conditional_pass_short_narration_redirect_blame(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "redirect_blame",
            "visible_output_bundle": {"gm_narration": ["a"]},
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_conditional_pass_short_narration_reveal_surface(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "reveal_surface",
            "visible_output_bundle": {"gm_narration": ["short"]},
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_pass_long_narration_escalate(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": {"gm_narration": ["this is a longer narration"]},
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_pass_non_matching_scene_function(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "other_function",
            "visible_output_bundle": {"gm_narration": ["x"]},
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_pass_no_gm_narration(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": {},
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_pass_empty_gm_narration_list(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": {"gm_narration": []},
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_pass_invalid_output_bundle(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": "not_a_dict",
        }
        assert gate_dramatic_quality(state) == "pass"


class TestGateSliceBoundary:
    def test_pass_no_failure_markers(self) -> None:
        state = {
            "failure_markers": [],
        }
        assert gate_slice_boundary(state) == "pass"

    def test_pass_missing_failure_markers(self) -> None:
        state = {}
        assert gate_slice_boundary(state) == "pass"

    def test_fail_scope_breach_marker(self) -> None:
        state = {
            "failure_markers": [
                {"failure_class": "scope_breach"},
            ]
        }
        assert gate_slice_boundary(state) == "fail"

    def test_pass_other_failure_class(self) -> None:
        state = {
            "failure_markers": [
                {"failure_class": "other_failure"},
            ]
        }
        assert gate_slice_boundary(state) == "pass"

    def test_pass_failure_markers_not_list(self) -> None:
        state = {
            "failure_markers": "not_a_list",
        }
        assert gate_slice_boundary(state) == "pass"

    def test_fail_multiple_markers_with_scope_breach(self) -> None:
        state = {
            "failure_markers": [
                {"failure_class": "other_failure"},
                {"failure_class": "scope_breach"},
            ]
        }
        assert gate_slice_boundary(state) == "fail"
