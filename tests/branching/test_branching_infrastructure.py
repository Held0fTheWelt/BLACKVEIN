"""
Comprehensive tests for Phase 6 branching infrastructure.

Tests decision points, path states, consequence filtering, and outcome divergence.
"""

import pytest
from story_runtime_core.branching import (
    DecisionPoint, DecisionPointType, DecisionOption, DecisionPointRegistry,
    PathState, PathStateManager,
    ConsequenceFilter, ConsequenceFact,
    OutcomeDivergence, DivergenceMetric
)


class TestDecisionPoint:
    """Test decision point definition and validation."""

    def test_create_valid_decision_point(self):
        """Test creating a valid decision point."""
        options = [
            DecisionOption(id="escalate", label="Escalate", description="Push harder"),
            DecisionOption(id="back_off", label="Back Off", description="Seek understanding"),
        ]

        decision = DecisionPoint(
            id="mediation_approach",
            turn_number=5,
            scenario_id="salon_mediation",
            decision_type=DecisionPointType.APPROACH,
            prompt="How do you respond to Annette?",
            options=options,
        )

        assert decision.validate()
        assert decision.id == "mediation_approach"
        assert len(decision.options) == 2

    def test_decision_point_requires_2_plus_options(self):
        """Test that decision points require at least 2 options."""
        single_option = [DecisionOption(id="only", label="Only", description="")]
        decision = DecisionPoint(
            id="bad", turn_number=1, scenario_id="test",
            decision_type=DecisionPointType.APPROACH,
            prompt="Choose",
            options=single_option,
        )
        assert not decision.validate()

    def test_decision_point_option_limit(self):
        """Test that decision points don't exceed 5 options."""
        options = [
            DecisionOption(id=f"opt{i}", label=f"Option {i}", description="")
            for i in range(6)
        ]
        decision = DecisionPoint(
            id="too_many", turn_number=1, scenario_id="test",
            decision_type=DecisionPointType.APPROACH,
            prompt="Choose",
            options=options,
        )
        assert not decision.validate()

    def test_decision_point_serialization(self):
        """Test decision point can be serialized to dict."""
        options = [
            DecisionOption(
                id="esc", label="Escalate", description="Push harder",
                consequence_tags=["escalation_path"],
                pressure_delta={"blame": 2}
            ),
        ]
        decision = DecisionPoint(
            id="choice1", turn_number=5, scenario_id="scenario1",
            decision_type=DecisionPointType.APPROACH,
            prompt="How?", options=options,
        )

        d = decision.to_dict()
        assert d['id'] == "choice1"
        assert d['turn_number'] == 5
        assert d['options'][0]['consequence_tags'] == ["escalation_path"]


class TestDecisionPointRegistry:
    """Test decision point registry."""

    def test_register_and_retrieve(self):
        """Test registering and retrieving decision points."""
        registry = DecisionPointRegistry()

        option = DecisionOption(id="opt1", label="Option 1", description="")
        decision = DecisionPoint(
            id="d1", turn_number=5, scenario_id="s1",
            decision_type=DecisionPointType.APPROACH,
            prompt="Q?", options=[option, option],
        )

        assert registry.register(decision)
        assert registry.get_for_turn("s1", 5) == decision

    def test_get_all_for_scenario(self):
        """Test retrieving all decisions for a scenario."""
        registry = DecisionPointRegistry()
        option = DecisionOption(id="o", label="O", description="")

        d1 = DecisionPoint("d1", 5, "s1", DecisionPointType.APPROACH, "Q", [option, option])
        d2 = DecisionPoint("d2", 10, "s1", DecisionPointType.STRATEGY, "Q", [option, option])

        registry.register(d1)
        registry.register(d2)

        all_d = registry.get_for_scenario("s1")
        assert len(all_d) == 2
        assert d1 in all_d and d2 in all_d

    def test_registry_json_serialization(self):
        """Test registry can be serialized to JSON."""
        registry = DecisionPointRegistry()
        option = DecisionOption(id="o", label="O", description="")
        d = DecisionPoint("d1", 5, "s1", DecisionPointType.APPROACH, "Q", [option, option])
        registry.register(d)

        json_str = registry.to_json()
        assert isinstance(json_str, str)
        assert "d1" in json_str
        assert "s1" in json_str

        restored = DecisionPointRegistry.from_json(json_str)
        assert restored.get_for_turn("s1", 5) is not None


class TestPathState:
    """Test path state tracking."""

    def test_create_path_state(self):
        """Test creating a path state."""
        path = PathState(session_id="sess1", scenario_id="scenario1")
        assert path.session_id == "sess1"
        assert len(path.path_nodes) == 0

    def test_add_decision_to_path(self):
        """Test adding decisions to a path."""
        path = PathState(session_id="sess1", scenario_id="scenario1")

        path.add_decision(turn=5, decision_id="d1", option_id="escalate", consequence_tags=["escalation_path"])
        path.add_decision(turn=10, decision_id="d2", option_id="push_harder", consequence_tags=["escalation_path"])

        assert len(path.path_nodes) == 2
        assert path.get_decision_at_turn(5) is not None
        assert path.get_decision_at_turn(5).chosen_option_id == "escalate"

    def test_path_consequence_tags(self):
        """Test consequence tag accumulation in path."""
        path = PathState(session_id="sess1", scenario_id="scenario1")

        path.add_decision(5, "d1", "opt1", ["tag_a", "tag_b"])
        path.add_decision(10, "d2", "opt2", ["tag_b", "tag_c"])

        assert path.is_on_path("tag_a")
        assert path.is_on_path("tag_b")
        assert path.is_on_path("tag_c")
        assert not path.is_on_path("tag_d")

    def test_path_signature(self):
        """Test path signature generation (for divergence comparison)."""
        path_a = PathState(session_id="s1", scenario_id="scenario1")
        path_a.add_decision(5, "d1", "escalate", [])
        path_a.add_decision(10, "d2", "push", [])

        path_b = PathState(session_id="s2", scenario_id="scenario1")
        path_b.add_decision(5, "d1", "escalate", [])
        path_b.add_decision(10, "d2", "push", [])

        path_c = PathState(session_id="s3", scenario_id="scenario1")
        path_c.add_decision(5, "d1", "back_off", [])
        path_c.add_decision(10, "d2", "push", [])

        # Identical paths should have same signature
        assert path_a.get_path_signature() == path_b.get_path_signature()
        # Different paths should have different signatures
        assert path_a.get_path_signature() != path_c.get_path_signature()

    def test_path_json_serialization(self):
        """Test path state JSON serialization."""
        path = PathState(session_id="sess1", scenario_id="scenario1")
        path.add_decision(5, "d1", "escalate", ["tag_a"])

        json_str = path.to_json()
        restored = PathState.from_json(json_str)

        assert restored.session_id == "sess1"
        assert restored.get_decision_at_turn(5).chosen_option_id == "escalate"
        assert "tag_a" in restored.active_consequence_tags


class TestPathStateManager:
    """Test path state management for multiple sessions."""

    def test_create_and_track_multiple_paths(self):
        """Test managing multiple session paths."""
        manager = PathStateManager()

        path1 = manager.create_path("session1", "scenario1")
        path2 = manager.create_path("session2", "scenario1")

        path1.add_decision(5, "d1", "escalate", ["esc"])
        path2.add_decision(5, "d1", "back_off", ["resolution"])

        assert manager.is_consequence_active("session1", "esc")
        assert not manager.is_consequence_active("session1", "resolution")
        assert manager.is_consequence_active("session2", "resolution")
        assert not manager.is_consequence_active("session2", "esc")

    def test_compare_paths(self):
        """Test path comparison."""
        manager = PathStateManager()

        path1 = manager.create_path("s1", "scenario")
        path1.add_decision(5, "d1", "escalate", ["esc"])
        path1.add_decision(10, "d2", "push", ["esc"])

        path2 = manager.create_path("s2", "scenario")
        path2.add_decision(5, "d1", "back_off", ["res"])
        path2.add_decision(10, "d2", "push", ["res"])

        comparison = manager.compare_paths("s1", "s2")
        assert comparison['total_divergence'] == 1  # Only first decision differs


class TestConsequenceFilter:
    """Test consequence filtering."""

    def test_register_and_filter_facts(self):
        """Test registering facts and filtering by tags."""
        cf = ConsequenceFilter()

        fact1 = ConsequenceFact(
            id="affair", text="Vanya had affair", consequence_tags=["escalation_path"],
            turn_introduced=3, scope="global", visibility="player_visible"
        )
        fact2 = ConsequenceFact(
            id="apology", text="Vanya apologized", consequence_tags=["resolution_path"],
            turn_introduced=5, scope="global", visibility="player_visible"
        )

        cf.register_fact(fact1)
        cf.register_fact(fact2)

        # Path with escalation tag should see fact1 but not fact2
        visible_escalation = cf.get_visible_facts({"escalation_path"})
        assert len(visible_escalation) == 1
        assert visible_escalation[0].id == "affair"

        # Path with resolution tag should see fact2 but not fact1
        visible_resolution = cf.get_visible_facts({"resolution_path"})
        assert len(visible_resolution) == 1
        assert visible_resolution[0].id == "apology"

    def test_divergent_facts(self):
        """Test finding facts that differ between paths."""
        cf = ConsequenceFilter()

        fact1 = ConsequenceFact("f1", "Text 1", ["tag_a"], 1, "global", "player_visible")
        fact2 = ConsequenceFact("f2", "Text 2", ["tag_b"], 1, "global", "player_visible")
        fact_common = ConsequenceFact("f_c", "Common", [], 1, "global", "player_visible")

        cf.register_fact(fact1)
        cf.register_fact(fact2)
        cf.register_fact(fact_common)

        divergence = cf.get_path_divergent_facts({"tag_a"}, {"tag_b"})
        assert len(divergence['unique_to_a']) == 1
        assert len(divergence['unique_to_b']) == 1
        assert len(divergence['shared']) >= 1  # Common fact


class TestOutcomeDivergence:
    """Test outcome divergence measurement."""

    def test_measure_decision_divergence(self):
        """Test measuring divergence in decision sequences."""
        od = OutcomeDivergence()

        decisions_a = ["d1:escalate", "d2:push", "d3:attack"]
        decisions_b = ["d1:escalate", "d2:listen", "d3:listen"]

        score = od.measure_decision_divergence(decisions_a, decisions_b)
        assert score.metric == DivergenceMetric.DECISION_POINTS
        assert score.percentage > 0  # Some divergence
        assert score.percentage < 100  # Not complete divergence

    def test_measure_consequence_divergence(self):
        """Test measuring divergence in facts."""
        od = OutcomeDivergence()

        facts_a = {"affair", "denial", "conflict"}
        facts_b = {"affair", "apology", "reconciliation"}

        score = od.measure_consequence_divergence(facts_a, facts_b)
        assert score.metric == DivergenceMetric.CONSEQUENCE_FACTS
        assert score.percentage > 0
        assert score.detail['shared_facts'] == 1  # "affair" shared

    def test_overall_divergence_calculation(self):
        """Test calculating overall weighted divergence."""
        od = OutcomeDivergence()

        scores = [
            OutcomeDivergence().measure_decision_divergence(
                ["d1:a", "d2:b"], ["d1:a", "d2:c"]
            ),
            OutcomeDivergence().measure_consequence_divergence(
                {"f1", "f2", "f3"}, {"f1", "f4", "f5"}
            ),
        ]

        overall = od.calculate_overall_divergence(scores)
        assert 0 <= overall <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
