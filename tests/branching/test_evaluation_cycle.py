"""
Integration tests for Phase 6 evaluation cycle.

Tests the full flow: decision definitions -> evaluation sessions -> divergence measurement.
"""

import pytest
from datetime import datetime, timezone

from story_runtime_core.branching import (
    DecisionPointRegistry, PathStateManager, ConsequenceFilter, ConsequenceFact
)
from story_runtime_core.branching.phase5_scenario_definitions import (
    build_scenario_c_registry, get_scenario_paths
)
import importlib.util
from pathlib import Path

# Load from world-engine by file path to avoid namespace collision with backend/app.
_BTE_PATH = Path(__file__).resolve().parent.parent.parent / "world-engine" / "app" / "runtime" / "branching_turn_executor.py"
_bte_spec = importlib.util.spec_from_file_location("_we_branching_turn_executor", _BTE_PATH)
_bte_mod = importlib.util.module_from_spec(_bte_spec)
_bte_spec.loader.exec_module(_bte_mod)
BranchingTurnExecutor = _bte_mod.BranchingTurnExecutor
BranchingTurnResult = _bte_mod.BranchingTurnResult
from tests.branching.evaluation_framework import (
    EvaluationProtocol, SessionTranscript, EvaluatorFeedback, DivergenceAnalysis,
    ReplayabilityEvaluator, DeterminismVerifier, EvaluationReport, EvaluationMetric
)


class MockSession:
    """Mock session for testing."""
    def __init__(self, session_id, scenario_id, turn_number=0):
        self.session_id = session_id
        self.scenario_id = scenario_id
        self.turn_number = turn_number
        self.players = {"player1"}
        self.history = []


class MockSessionManager:
    """Mock session manager for testing."""
    def __init__(self):
        self.sessions = {}

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def create_session(self, session_id, scenario_id):
        session = MockSession(session_id, scenario_id)
        self.sessions[session_id] = session
        return session


class TestEvaluationFramework:
    """Test the evaluation framework components."""

    def test_session_transcript_creation(self):
        """Test creating a session transcript."""
        transcript = SessionTranscript(
            session_id="sess1",
            scenario_id="salon_mediation",
            evaluator_id="eval1",
            approach_name="A1: Escalation",
            path_signature="escalation_hold_firm_learned",
        )

        assert transcript.session_id == "sess1"
        assert transcript.scenario_id == "salon_mediation"
        assert transcript.evaluator_id == "eval1"
        assert len(transcript.turns) == 0
        assert len(transcript.consequence_tags) == 0

    def test_evaluator_feedback_creation(self):
        """Test creating evaluator feedback."""
        feedback = EvaluatorFeedback(
            evaluator_id="eval1",
            session_id="sess1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            arc_satisfaction=8,
            character_consistency=7,
            player_agency=9,
            pressure_coherence=7,
            consequence_visibility=8,
            engagement=9,
            branch_intentionality=8,
            what_felt_real=["character voice", "pressure building"],
            what_felt_fake=["convenience ending"],
            would_replay=True,
            replay_reason="Different approach would feel totally different"
        )

        assert feedback.arc_satisfaction == 8
        assert feedback.player_agency == 9
        assert feedback.would_replay is True

    def test_divergence_analysis_calculation(self):
        """Test divergence analysis with weighted metrics."""
        analysis = DivergenceAnalysis(
            path_a_signature="escalation",
            path_b_signature="understanding",
            approach_a="A1: Escalation",
            approach_b="C1: Understanding",
            decision_divergence_percentage=100.0,  # All 3 decisions different
            consequence_divergence_percentage=85.0,  # 85% of facts differ
            pressure_divergence_percentage=70.0,  # Pressure curves 70% different
            dialogue_divergence_percentage=60.0,  # 60% of dialogue different
            ending_divergence_percentage=90.0,  # Final states very different
            overall_divergence_percentage=0.0,  # Will be calculated
        )

        overall = EvaluationProtocol.calculate_overall_divergence(analysis)
        # (100*0.25 + 85*0.35 + 70*0.15 + 60*0.15 + 90*0.10)
        # = 25 + 29.75 + 10.5 + 9 + 9 = 83.25
        assert 82 < overall < 84

    def test_divergence_quality_assessment(self):
        """Test qualitative assessment of divergence."""
        assert "minimal" in EvaluationProtocol.assess_divergence_quality(15)
        assert "low" in EvaluationProtocol.assess_divergence_quality(35)
        assert "moderate" in EvaluationProtocol.assess_divergence_quality(55)
        assert "high" in EvaluationProtocol.assess_divergence_quality(75)
        assert "very_high" in EvaluationProtocol.assess_divergence_quality(95)

    def test_evaluation_protocol_checkpoint_questions(self):
        """Test evaluation checkpoint protocol."""
        protocol = EvaluationProtocol.create_checkpoint_protocol()

        assert protocol["frequency"] == 5
        assert len(protocol["questions"]) >= 5
        assert "drama" in protocol["questions"][0].lower()
        assert "character" in protocol["questions"][1].lower()
        assert "choice" in protocol["questions"][2].lower()


class TestEvaluationWithScenarioC:
    """Test full evaluation flow with Scenario C."""

    def test_scenario_c_decision_definitions(self):
        """Test that Scenario C decision points are properly defined."""
        registry = build_scenario_c_registry()

        # Should have 6 decision points total
        # (3 opening + 3 path-specific pressure responses + 3 path-specific closures)
        all_decisions = registry.get_all_decisions()
        assert len(all_decisions) >= 6

        # Opening posture should be there
        opening = registry.get_by_id("opening_posture")
        assert opening is not None
        assert len(opening.options) == 3

    def test_scenario_c_paths_defined(self):
        """Test that three canonical paths are defined."""
        paths = get_scenario_paths()

        assert "path_A_escalation" in paths
        assert "path_B_divide" in paths
        assert "path_C_understanding" in paths

        # Each path has 3 decisions
        for path_name, decisions in paths.items():
            assert len(decisions) == 3

    def test_simulate_evaluation_session_path_a(self):
        """Simulate running one evaluation session on Path A."""
        registry = build_scenario_c_registry()
        session_mgr = MockSessionManager()
        session_mgr.create_session("eval_sess_a", "salon_mediation")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Simulate Path A: Escalation -> Hold Firm -> Learned Respect
        path_a = get_scenario_paths()["path_A_escalation"]

        # Turn 2: Opening posture (escalate)
        decision_id, option_id = path_a[0]
        result = executor.execute_turn(
            "eval_sess_a", "player1",
            {"type": "decide", "decision_option_id": option_id}
        )
        assert result.success
        assert result.chosen_option_id == "escalate"
        assert "escalation_path" in result.consequence_tags

        # Verify decision was recorded
        path = executor.path_manager.get_path("eval_sess_a")
        assert len(path.path_nodes) == 1

    def test_simulate_evaluation_session_path_c(self):
        """Simulate running one evaluation session on Path C."""
        registry = build_scenario_c_registry()
        session_mgr = MockSessionManager()
        session_mgr.create_session("eval_sess_c", "salon_mediation")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Simulate Path C: Understanding -> Deepen -> Connected
        path_c = get_scenario_paths()["path_C_understanding"]

        # Turn 2: Opening posture (understand)
        _, option_id = path_c[0]
        result = executor.execute_turn(
            "eval_sess_c", "player1",
            {"type": "decide", "decision_option_id": option_id}
        )
        assert result.success
        assert result.chosen_option_id == "understand"
        assert "understanding_path" in result.consequence_tags
        assert "relational_style" in result.consequence_tags


class TestReplayabilityMeasurement:
    """Test replayability evaluation."""

    def test_replayability_evaluator_tracks_pairs(self):
        """Test that replayability evaluator tracks replay pairs."""
        evaluator = ReplayabilityEvaluator()

        # Create two transcripts
        t1 = SessionTranscript(
            session_id="run1", scenario_id="salon_mediation",
            evaluator_id="eval1", approach_name="Path A",
            path_signature="path_a_sig"
        )
        t2 = SessionTranscript(
            session_id="run2", scenario_id="salon_mediation",
            evaluator_id="eval1", approach_name="Path C",
            path_signature="path_c_sig"
        )

        feedback = EvaluatorFeedback(
            evaluator_id="eval1", session_id="run2",
            timestamp=datetime.now(timezone.utc).isoformat(),
            arc_satisfaction=8, character_consistency=7,
            player_agency=9, pressure_coherence=8,
            consequence_visibility=8, engagement=9,
            branch_intentionality=8,
            would_replay=True,
            replay_reason="Totally different approach"
        )

        evaluator.register_replay_pair("eval1", t1, t2, feedback)

        # Verify registered
        assert "eval1" in evaluator.replay_sessions
        assert len(evaluator.replay_sessions["eval1"]) == 2
        assert len(evaluator.replay_feedback["eval1"]) == 1

    def test_replayability_percentage_calculation(self):
        """Test calculating replayability percentage."""
        evaluator = ReplayabilityEvaluator()

        # Create 3 evaluators, 2 want to replay
        for i in range(3):
            t1 = SessionTranscript(
                session_id=f"r1_{i}", scenario_id="salon_mediation",
                evaluator_id=f"eval{i}", approach_name=f"Path {i}",
                path_signature=f"sig_{i}"
            )
            t2 = SessionTranscript(
                session_id=f"r2_{i}", scenario_id="salon_mediation",
                evaluator_id=f"eval{i}", approach_name=f"Path {i+1}",
                path_signature=f"sig_{i+1}"
            )

            feedback = EvaluatorFeedback(
                evaluator_id=f"eval{i}",
                session_id=f"r2_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                arc_satisfaction=8, character_consistency=7,
                player_agency=9, pressure_coherence=8,
                consequence_visibility=8, engagement=9,
                branch_intentionality=8,
                would_replay=(i < 2),  # First 2 want to replay
            )

            evaluator.register_replay_pair(f"eval{i}", t1, t2, feedback)

        # 2 out of 3 evaluators would replay = 66.67%
        replayability = evaluator.calculate_replayability_likelihood()
        assert 66 < replayability < 67


class TestDeterminismVerification:
    """Test determinism verification."""

    def test_determinism_verifier_tracks_tests(self):
        """Test that determinism verifier tracks test runs."""
        verifier = DeterminismVerifier()

        t1 = SessionTranscript(
            session_id="det1", scenario_id="test",
            evaluator_id="det", approach_name="Path A",
            path_signature="sig_abc123"
        )
        t1.turns = [{"turn": 1}, {"turn": 2}]
        t1.consequence_tags = {"tag1", "tag2"}

        t2 = SessionTranscript(
            session_id="det2", scenario_id="test",
            evaluator_id="det", approach_name="Path A",
            path_signature="sig_abc123"
        )
        t2.turns = [{"turn": 1}, {"turn": 2}]
        t2.consequence_tags = {"tag1", "tag2"}

        sequence = ["decision1", "decision2"]
        verifier.register_test("test", sequence, t1, t2)

        report = verifier.get_determinism_report()
        assert report["determinism_verified"] is True
        assert report["pass_rate"] == 100.0

    def test_determinism_failure_detection(self):
        """Test that determinism verifier catches failures."""
        verifier = DeterminismVerifier()

        t1 = SessionTranscript(
            session_id="det1", scenario_id="test",
            evaluator_id="det", approach_name="Path A",
            path_signature="sig_abc123"
        )
        t1.consequence_tags = {"tag1"}

        t2 = SessionTranscript(
            session_id="det2", scenario_id="test",
            evaluator_id="det", approach_name="Path A",
            path_signature="sig_different"  # Different!
        )
        t2.consequence_tags = {"tag2"}

        verifier.register_test("test", ["d1", "d2"], t1, t2)

        report = verifier.get_determinism_report()
        assert report["determinism_verified"] is False
        assert len(report["failures"]) == 1


class TestEvaluationReport:
    """Test evaluation report generation."""

    def test_evaluation_report_creation(self):
        """Test creating an evaluation report."""
        report = EvaluationReport("salon_mediation")

        assert report.scenario_id == "salon_mediation"
        assert len(report.session_transcripts) == 0

    def test_evaluation_report_summary(self):
        """Test generating report summary."""
        report = EvaluationReport("salon_mediation")

        # Add a mock session
        transcript = SessionTranscript(
            session_id="s1", scenario_id="salon_mediation",
            evaluator_id="eval1", approach_name="Path A",
            path_signature="sig_a"
        )

        feedback = EvaluatorFeedback(
            evaluator_id="eval1", session_id="s1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            arc_satisfaction=8, character_consistency=8,
            player_agency=9, pressure_coherence=8,
            consequence_visibility=8, engagement=9,
            branch_intentionality=8
        )

        report.add_session(transcript, feedback)

        summary = report.get_summary()
        assert summary["scenario"] == "salon_mediation"
        assert summary["sessions_completed"] == 1
        assert summary["evaluators"] == 1

    def test_evaluation_report_with_divergence(self):
        """Test report with divergence analysis."""
        report = EvaluationReport("salon_mediation")

        analysis = DivergenceAnalysis(
            path_a_signature="path_a",
            path_b_signature="path_c",
            approach_a="Escalation",
            approach_b="Understanding",
            decision_divergence_percentage=100.0,
            consequence_divergence_percentage=80.0,
            pressure_divergence_percentage=75.0,
            dialogue_divergence_percentage=65.0,
            ending_divergence_percentage=85.0,
            overall_divergence_percentage=0.0,
        )

        report.add_divergence(analysis)

        summary = report.get_summary()
        assert summary["outcome_divergence"]["analyses"] == 1
        overall = summary["outcome_divergence"]["average_divergence"]
        assert 78 < overall < 82  # Weighted average around 80


class TestEvaluationScenarioConstants:
    """Test Phase 6 evaluation targets."""

    def test_phase6_success_criteria(self):
        """Test Phase 6 success criteria."""
        # Phase 6 targets:
        # 1. Outcome divergence >= 60%
        # 2. Replayability >= 70%
        # 3. Determinism = 100%

        target_divergence = 60.0
        target_replayability = 70.0
        target_determinism = 100.0

        # Create sample analysis
        analysis = DivergenceAnalysis(
            path_a_signature="a", path_b_signature="b",
            approach_a="A", approach_b="B",
            decision_divergence_percentage=100.0,
            consequence_divergence_percentage=75.0,
            pressure_divergence_percentage=70.0,
            dialogue_divergence_percentage=65.0,
            ending_divergence_percentage=85.0,
            overall_divergence_percentage=0.0,
        )

        overall = EvaluationProtocol.calculate_overall_divergence(analysis)
        assert overall >= target_divergence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
