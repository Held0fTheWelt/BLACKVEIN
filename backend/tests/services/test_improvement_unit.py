"""Unit tests for improvement_service pure functions and ImprovementStore."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.improvement_service import (
    ImprovementStore,
    _evaluate_transcript,
    build_comparison_package,
    build_evidence_strength_map,
    build_recommendation_rationale,
    create_variant,
)


class TestImprovementStore:
    """Tests for ImprovementStore class."""

    @pytest.fixture
    def store_root(self, tmp_path: Path):
        """Temporary storage root."""
        return tmp_path / "improvement"

    def test_improvement_store_write_and_read_json(self, store_root: Path):
        """Store persists and retrieves JSON documents."""
        store = ImprovementStore(root=store_root)
        variant_id = f"variant_{uuid4().hex}"
        variant_data = {
            "variant_id": variant_id,
            "baseline_id": "baseline_001",
            "candidate_summary": "Test variant",
            "created_by": "test_actor",
        }

        # Write
        path = store.write_json("variants", variant_id, variant_data)
        assert path.exists()
        assert path.read_text().find(variant_id) >= 0

        # Read back
        retrieved = store.read_json("variants", variant_id)
        assert retrieved["variant_id"] == variant_id
        assert retrieved["baseline_id"] == "baseline_001"

    def test_improvement_store_list_json_empty_folder_returns_empty(
        self, store_root: Path
    ):
        """List on empty folder returns empty list."""
        store = ImprovementStore(root=store_root)
        items = store.list_json("experiments")
        assert items == []

    def test_improvement_store_list_json_with_files(self, store_root: Path):
        """List returns all JSON files in category folder."""
        store = ImprovementStore(root=store_root)
        exp_ids = [f"experiment_{uuid4().hex}" for _ in range(3)]
        for eid in exp_ids:
            store.write_json("experiments", eid, {"experiment_id": eid})

        experiments = store.list_json("experiments")
        assert len(experiments) == 3
        stored_ids = {e["experiment_id"] for e in experiments}
        assert stored_ids == set(exp_ids)


class TestCreateVariant:
    """Tests for create_variant function."""

    @pytest.fixture
    def store_root(self, tmp_path: Path):
        """Temporary storage root."""
        return tmp_path / "improvement"

    def test_create_variant_with_default_mutation_plan(self, store_root: Path):
        """Create variant with no metadata uses default mutation plan."""
        store = ImprovementStore(root=store_root)
        variant = create_variant(
            baseline_id="baseline_001",
            candidate_summary="Test variant with defaults",
            actor_id="test_actor",
            store=store,
        )

        assert variant["variant_id"].startswith("variant_")
        assert variant["baseline_id"] == "baseline_001"
        assert isinstance(variant["mutation_plan"], list)
        assert len(variant["mutation_plan"]) == 2  # default has 2 operations
        assert variant["review_status"] == "pending_review"
        assert variant["lineage"]["lineage_depth"] == 1

    def test_create_variant_with_parent_variant_increments_lineage_depth(
        self, store_root: Path
    ):
        """Create variant with parent_variant_id increments lineage depth."""
        store = ImprovementStore(root=store_root)
        parent = create_variant(
            baseline_id="baseline_001",
            candidate_summary="Parent variant",
            actor_id="actor_1",
            store=store,
        )

        child = create_variant(
            baseline_id="baseline_001",
            candidate_summary="Child variant",
            actor_id="actor_1",
            metadata={
                "parent_variant_id": parent["variant_id"],
                "lineage_depth": 3,
            },
            store=store,
        )

        assert child["lineage"]["parent_variant_id"] == parent["variant_id"]
        assert child["lineage"]["lineage_depth"] == 3

    def test_create_variant_with_mutation_metadata_dict(self, store_root: Path):
        """Create variant preserves mutation_metadata from input."""
        store = ImprovementStore(root=store_root)
        metadata = {
            "mutation_metadata": {
                "source": "human_feedback",
                "intent_tags": ["pacing", "dialogue"],
            }
        }
        variant = create_variant(
            baseline_id="baseline_001",
            candidate_summary="Custom metadata variant",
            actor_id="actor_1",
            metadata=metadata,
            store=store,
        )

        assert variant["mutation_metadata"]["source"] == "human_feedback"
        assert variant["mutation_metadata"]["intent_tags"] == ["pacing", "dialogue"]

    def test_create_variant_invalid_mutation_plan_falls_back_to_default(
        self, store_root: Path
    ):
        """Create variant with invalid mutation_plan falls back to default."""
        store = ImprovementStore(root=store_root)
        variant = create_variant(
            baseline_id="baseline_001",
            candidate_summary="Invalid plan variant",
            actor_id="actor_1",
            metadata={"mutation_plan": "not_a_list"},
            store=store,
        )

        assert isinstance(variant["mutation_plan"], list)
        assert len(variant["mutation_plan"]) == 2  # fell back to default


class TestEvaluateTranscript:
    """Tests for _evaluate_transcript function."""

    def test_evaluate_transcript_counts_kinds_correctly(self):
        """Evaluate counts semantic kinds and metrics correctly."""
        transcript = [
            {
                "turn_number": 1,
                "interpreted_kind": "action",
                "guard_rejected": False,
                "repetition_flag": False,
                "scene_marker": "scene_1",
                "triggered_tags": ["action"],
                "quality_hint": 0.5,
            },
            {
                "turn_number": 2,
                "interpreted_kind": "speech",
                "guard_rejected": False,
                "repetition_flag": False,
                "scene_marker": "scene_1",
                "triggered_tags": ["dialogue"],
                "quality_hint": 0.75,
            },
            {
                "turn_number": 3,
                "interpreted_kind": "action",
                "guard_rejected": False,
                "repetition_flag": False,
                "scene_marker": "scene_2",
                "triggered_tags": ["action"],
                "quality_hint": 0.6,
            },
        ]
        metrics = _evaluate_transcript(transcript)

        # Function rounds to 4 decimals: 2/3 ≈ 0.6667
        assert metrics["semantic_action_rate"] == round(2.0 / 3.0, 4)
        assert metrics["semantic_speech_rate"] == round(1.0 / 3.0, 4)
        assert metrics["scene_marker_coverage"] == 2.0
        assert metrics["guard_reject_rate"] == 0.0
        assert metrics["repetition_signal"] == 0.0

    def test_evaluate_transcript_detects_repetition(self):
        """Evaluate detects repetition flags."""
        transcript = [
            {
                "turn_number": 1,
                "interpreted_kind": "speech",
                "guard_rejected": False,
                "repetition_flag": True,
                "scene_marker": "scene_1",
                "triggered_tags": [],
                "quality_hint": 0.0,
            },
            {
                "turn_number": 2,
                "interpreted_kind": "speech",
                "guard_rejected": False,
                "repetition_flag": True,
                "scene_marker": "scene_1",
                "triggered_tags": [],
                "quality_hint": 0.0,
            },
        ]
        metrics = _evaluate_transcript(transcript)

        assert metrics["repetition_signal"] == 1.0

    def test_evaluate_transcript_empty_transcript_returns_zero_counts(self):
        """Empty transcript returns metrics with zero values."""
        metrics = _evaluate_transcript([])

        assert metrics["guard_reject_rate"] == 0.0
        assert metrics["repetition_signal"] == 0.0
        assert metrics["trigger_coverage"] == 0.0


class TestBuildComparisonPackage:
    """Tests for build_comparison_package function."""

    def test_build_comparison_package_structure(self):
        """Build comparison package structures dimensions correctly."""
        evaluation = {
            "experiment_id": "exp_123",
            "variant_id": "var_123",
            "baseline_id": "base_123",
            "generated_at": "2026-04-05T00:00:00",
            "metrics": {
                "guard_reject_rate": 0.2,
                "repetition_signal": 0.1,
                "structure_flow_health": 0.8,
                "transcript_quality_heuristic": 0.7,
                "semantic_speech_rate": 0.4,
                "semantic_action_rate": 0.6,
            },
            "baseline_metrics": {
                "guard_reject_rate": 0.3,
                "repetition_signal": 0.2,
                "structure_flow_health": 0.7,
                "transcript_quality_heuristic": 0.6,
                "semantic_speech_rate": 0.3,
                "semantic_action_rate": 0.7,
            },
            "comparison": {
                "guard_reject_rate_delta": -0.1,
                "repetition_signal_delta": -0.1,
                "structure_flow_health_delta": 0.1,
                "quality_heuristic_delta": 0.1,
            },
            "notable_failures": ["none"],
        }
        package = build_comparison_package(evaluation)

        assert package["experiment_id"] == "exp_123"
        assert len(package["dimensions"]) == 4
        assert package["dimensions"][0]["metric"] == "guard_reject_rate"
        assert package["semantic_delta"]["semantic_speech_rate_delta"] == 0.1
        assert package["semantic_delta"]["semantic_action_rate_delta"] == -0.1


class TestBuildEvidenceStrengthMap:
    """Tests for build_evidence_strength_map function."""

    def test_evidence_strength_map_all_true(self):
        """All evidence sources present returns moderate/primary strength."""
        evaluation = {"metrics": {}}
        evidence = build_evidence_strength_map(
            evaluation=evaluation,
            retrieval_hit_count=5,
            transcript_tool_ok=True,
            governance_bundle_attached=True,
        )

        assert evidence["sandbox_candidate_metrics"] == "primary"
        assert evidence["baseline_control_transcript"] == "primary"
        assert evidence["retrieval_context"] == "moderate"
        assert evidence["transcript_tool_readback"] == "moderate"
        assert evidence["governance_review_bundle"] == "moderate"

    def test_evidence_strength_map_all_false(self):
        """No evidence sources returns none/low strength."""
        evaluation = {"metrics": {}}
        evidence = build_evidence_strength_map(
            evaluation=evaluation,
            retrieval_hit_count=0,
            transcript_tool_ok=False,
            governance_bundle_attached=False,
        )

        assert evidence["retrieval_context"] == "none"
        assert evidence["transcript_tool_readback"] == "low"
        assert evidence["governance_review_bundle"] == "pending_until_route"

    def test_evidence_strength_map_mixed(self):
        """Mixed evidence presence returns mixed strength."""
        evaluation = {"metrics": {}}
        evidence = build_evidence_strength_map(
            evaluation=evaluation,
            retrieval_hit_count=3,
            transcript_tool_ok=False,
            governance_bundle_attached=True,
        )

        assert evidence["retrieval_context"] == "moderate"
        assert evidence["transcript_tool_readback"] == "low"
        assert evidence["governance_review_bundle"] == "moderate"


class TestBuildRecommendationRationale:
    """Tests for build_recommendation_rationale function."""

    def test_recommendation_rationale_guard_driver_above_threshold(self):
        """Guard reject rate > 0.4 triggers guard driver."""
        evaluation = {
            "metrics": {
                "guard_reject_rate": 0.5,
                "repetition_signal": 0.1,
            },
            "comparison": {
                "structure_flow_health_delta": 0.1,
                "quality_heuristic_delta": 0.1,
            },
        }
        rationale = build_recommendation_rationale(
            evaluation=evaluation,
            recommendation_summary="Guard-related revision needed",
        )

        drivers = rationale.get("drivers", [])
        guard_drivers = [d for d in drivers if d.get("metric") == "guard_reject_rate"]
        assert len(guard_drivers) > 0
        assert guard_drivers[0]["observed"] == 0.5

    def test_recommendation_rationale_repetition_driver_above_threshold(self):
        """Repetition signal > 0.5 triggers repetition driver."""
        evaluation = {
            "metrics": {
                "guard_reject_rate": 0.1,
                "repetition_signal": 0.6,
            },
            "comparison": {
                "structure_flow_health_delta": 0.1,
                "quality_heuristic_delta": 0.1,
            },
        }
        rationale = build_recommendation_rationale(
            evaluation=evaluation,
            recommendation_summary="Repetition-related revision",
        )

        drivers = rationale.get("drivers", [])
        rep_drivers = [d for d in drivers if d.get("metric") == "repetition_signal"]
        assert len(rep_drivers) > 0

    def test_recommendation_rationale_retrieval_driver_with_paths(self):
        """Retrieval context with hit_count and paths adds driver."""
        evaluation = {
            "metrics": {
                "guard_reject_rate": 0.1,
                "repetition_signal": 0.1,
            },
            "comparison": {
                "structure_flow_health_delta": 0.1,
                "quality_heuristic_delta": 0.1,
            },
        }
        rationale = build_recommendation_rationale(
            evaluation=evaluation,
            recommendation_summary="Evidence-grounded review",
            retrieval_hit_count=3,
            retrieval_source_paths=["docs/scene1.md", "docs/scene2.md"],
        )

        drivers = rationale.get("drivers", [])
        retrieval_drivers = [d for d in drivers if d.get("category") == "retrieval_context"]
        assert len(retrieval_drivers) > 0
        assert retrieval_drivers[0]["hit_count"] == 3

    def test_recommendation_rationale_baseline_pass_fallback(self):
        """Metrics all below threshold produces drivers list (may be empty or contain structure/quality deltas)."""
        evaluation = {
            "metrics": {
                "guard_reject_rate": 0.1,
                "repetition_signal": 0.1,
            },
            "comparison": {
                "structure_flow_health_delta": 0.1,
                "quality_heuristic_delta": 0.1,
            },
        }
        rationale = build_recommendation_rationale(
            evaluation=evaluation,
            recommendation_summary="No issues detected",
        )

        # Should have drivers key, which may be empty or contain structure/quality positive deltas
        assert "drivers" in rationale
        assert isinstance(rationale["drivers"], list)
