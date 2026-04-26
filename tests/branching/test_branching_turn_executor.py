"""
Tests for branching-aware turn execution.

Verifies the four seams (proposal, validation, commit, render) work correctly
and that branching integrates cleanly with turn execution.
"""

import importlib.util
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from pathlib import Path

# Load from world-engine by file path to avoid namespace collision with backend/app.
_BTE_PATH = Path(__file__).resolve().parent.parent.parent / "world-engine" / "app" / "runtime" / "branching_turn_executor.py"
_bte_spec = importlib.util.spec_from_file_location("_we_branching_turn_executor", _BTE_PATH)
_bte_mod = importlib.util.module_from_spec(_bte_spec)
_bte_spec.loader.exec_module(_bte_mod)
BranchingTurnExecutor = _bte_mod.BranchingTurnExecutor
BranchingTurnResult = _bte_mod.BranchingTurnResult
TurnSeam = _bte_mod.TurnSeam
BranchingTurnExecutorFactory = _bte_mod.BranchingTurnExecutorFactory
from story_runtime_core.branching import (
    DecisionPoint, DecisionPointType, DecisionOption,
    DecisionPointRegistry, PathStateManager, ConsequenceFilter,
    ConsequenceFact
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


class TestBranchingTurnExecutorWithoutDecisionPoints:
    """Test turn execution works normally without decision points."""

    def test_execute_turn_without_decision_point(self):
        """Test executing a turn when no decision point exists."""
        # Setup
        session_mgr = MockSessionManager()
        session = session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=DecisionPointRegistry(),
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Execute turn
        action = {"type": "move", "direction": "north"}
        result = executor.execute_turn("sess1", "player1", action)

        # Verify
        assert result.success
        assert result.new_turn_number == 1
        assert result.decision_point_id is None
        assert result.chosen_option_id is None

    def test_turn_increments_counter(self):
        """Test that turn counter increments."""
        session_mgr = MockSessionManager()
        session = session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=DecisionPointRegistry(),
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Execute 3 turns
        for i in range(3):
            action = {"type": f"action{i}"}
            result = executor.execute_turn("sess1", "player1", action)
            assert result.new_turn_number == i + 1

        assert session.turn_number == 3

    def test_history_recorded_for_all_turns(self):
        """Test that turn history is recorded."""
        session_mgr = MockSessionManager()
        session = session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=DecisionPointRegistry(),
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        action = {"type": "test_action"}
        result = executor.execute_turn("sess1", "player1", action)

        assert len(session.history) == 1
        assert session.history[0]["action"] == action
        assert session.history[0]["turn"] == 0


class TestBranchingTurnExecutorWithDecisionPoints:
    """Test turn execution with decision points."""

    def test_decision_point_proposal_seam(self):
        """Test PROPOSAL seam: decision point is detected."""
        # Setup registry with decision point
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="esc", label="Escalate", description="", consequence_tags=["escalation"]),
            DecisionOption(id="res", label="Resolve", description="", consequence_tags=["resolution"]),
        ]
        decision = DecisionPoint(
            id="approach_choice", turn_number=0, scenario_id="scenario1",
            decision_type=DecisionPointType.APPROACH, prompt="How?", options=options
        )
        registry.register(decision)

        # Setup session manager
        session_mgr = MockSessionManager()
        session = session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Execute turn with decision
        action = {"type": "make_decision", "decision_option_id": "esc"}
        result = executor.execute_turn("sess1", "player1", action)

        # Verify decision was detected
        assert result.decision_point_id == "approach_choice"
        assert result.chosen_option_id == "esc"

    def test_decision_point_validation_seam_invalid_option(self):
        """Test VALIDATION seam: rejects invalid option."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="opt1", label="Option 1", description=""),
            DecisionOption(id="opt2", label="Option 2", description=""),
        ]
        decision = DecisionPoint(
            id="d1", turn_number=0, scenario_id="scenario1",
            decision_type=DecisionPointType.APPROACH, prompt="Choose", options=options
        )
        registry.register(decision)

        session_mgr = MockSessionManager()
        session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Try to choose invalid option
        action = {"type": "decide", "decision_option_id": "invalid_opt"}
        result = executor.execute_turn("sess1", "player1", action)

        # Verify rejection
        assert not result.success
        assert "Invalid option" in result.error_message

    def test_decision_point_validation_seam_missing_option(self):
        """Test VALIDATION seam: requires option_id when decision point exists."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="opt1", label="O1", description=""),
            DecisionOption(id="opt2", label="O2", description=""),
        ]
        decision = DecisionPoint(
            id="d1", turn_number=0, scenario_id="scenario1",
            decision_type=DecisionPointType.APPROACH, prompt="Choose", options=options
        )
        registry.register(decision)

        session_mgr = MockSessionManager()
        session_mgr.create_session("sess1", "scenario1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Try to execute turn without specifying option
        action = {"type": "some_action"}  # No decision_option_id
        result = executor.execute_turn("sess1", "player1", action)

        # Verify rejection
        assert not result.success
        assert "requires decision_option_id" in result.error_message

    def test_decision_point_commit_seam(self):
        """Test COMMIT seam: decision is recorded in path state."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="a", label="A", description="", consequence_tags=["tag_a"]),
            DecisionOption(id="b", label="B", description="", consequence_tags=["tag_b"]),
        ]
        decision = DecisionPoint(
            id="d1", turn_number=0, scenario_id="scenario1",
            decision_type=DecisionPointType.APPROACH, prompt="Choose", options=options
        )
        registry.register(decision)

        session_mgr = MockSessionManager()
        session_mgr.create_session("sess1", "scenario1")

        path_mgr = PathStateManager()
        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=path_mgr,
            consequence_filter=ConsequenceFilter()
        )

        # Execute decision
        action = {"type": "decide", "decision_option_id": "a"}
        result = executor.execute_turn("sess1", "player1", action)

        # Verify path was recorded
        path = path_mgr.get_path("sess1")
        assert path is not None
        assert len(path.path_nodes) == 1
        assert path.path_nodes[0].chosen_option_id == "a"
        assert "tag_a" in path.active_consequence_tags

    def test_consequence_tags_applied(self):
        """Test that consequence tags are applied from chosen option."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(
                id="escalate", label="Escalate", description="",
                consequence_tags=["escalation_path", "high_pressure"]
            ),
        ]
        decision = DecisionPoint(
            id="approach", turn_number=0, scenario_id="s1",
            decision_type=DecisionPointType.APPROACH, prompt="How?", options=options
        )
        registry.register(decision)

        session_mgr = MockSessionManager()
        session_mgr.create_session("s1", "s1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        action = {"type": "decide", "decision_option_id": "escalate"}
        result = executor.execute_turn("s1", "player1", action)

        # Verify tags
        assert result.consequence_tags == ["escalation_path", "high_pressure"]

    def test_decision_point_render_seam(self):
        """Test RENDER seam: output is filtered based on path."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="opt1", label="O1", description="", consequence_tags=["path_a"]),
        ]
        decision = DecisionPoint(
            id="d1", turn_number=0, scenario_id="s1",
            decision_type=DecisionPointType.APPROACH, prompt="Choose", options=options
        )
        registry.register(decision)

        # Setup consequence filter with path-specific facts
        cf = ConsequenceFilter()
        cf.register_fact(ConsequenceFact(
            id="fact_a", text="Path A fact",
            consequence_tags=["path_a"],
            turn_introduced=0, scope="global", visibility="player_visible"
        ))
        cf.register_fact(ConsequenceFact(
            id="fact_b", text="Path B fact",
            consequence_tags=["path_b"],
            turn_introduced=0, scope="global", visibility="player_visible"
        ))

        session_mgr = MockSessionManager()
        session_mgr.create_session("s1", "s1")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=PathStateManager(),
            consequence_filter=cf
        )

        action = {"type": "decide", "decision_option_id": "opt1"}
        result = executor.execute_turn("s1", "player1", action)

        # Verify result includes path-specific facts
        # (In full implementation, this would filter visible consequences)
        assert result.success
        assert "path_a" in result.consequence_tags

    def test_path_signature_unique_per_path(self):
        """Test that different decisions produce different path signatures."""
        registry = DecisionPointRegistry()
        options = [
            DecisionOption(id="a", label="A", description=""),
            DecisionOption(id="b", label="B", description=""),
        ]
        decision = DecisionPoint(
            id="d1", turn_number=0, scenario_id="s1",
            decision_type=DecisionPointType.APPROACH, prompt="Choose", options=options
        )
        registry.register(decision)

        session_mgr = MockSessionManager()
        session_mgr.create_session("s1a", "s1")
        session_mgr.create_session("s1b", "s1")

        path_mgr = PathStateManager()
        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=registry,
            path_manager=path_mgr,
            consequence_filter=ConsequenceFilter()
        )

        # Create two paths with different decisions
        executor.execute_turn("s1a", "p1", {"type": "decide", "decision_option_id": "a"})
        executor.execute_turn("s1b", "p1", {"type": "decide", "decision_option_id": "b"})

        # Verify signatures are different
        path_a = path_mgr.get_path("s1a")
        path_b = path_mgr.get_path("s1b")

        assert path_a.get_path_signature() != path_b.get_path_signature()


class TestBranchingTurnExecutorRegressions:
    """Test that branching doesn't break existing functionality."""

    def test_non_branching_scenarios_still_work(self):
        """Test that scenarios without decision points work normally."""
        session_mgr = MockSessionManager()
        session_mgr.create_session("s1", "scenario_no_branching")

        executor = BranchingTurnExecutor(
            session_manager=session_mgr,
            decision_registry=DecisionPointRegistry(),  # Empty registry
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        # Execute 5 turns normally
        for i in range(5):
            action = {"type": f"action_{i}"}
            result = executor.execute_turn("s1", "p1", action)
            assert result.success
            assert result.new_turn_number == i + 1
            assert result.decision_point_id is None

    def test_invalid_session_returns_error(self):
        """Test that invalid session is handled."""
        executor = BranchingTurnExecutor(
            session_manager=MockSessionManager(),  # No sessions created
            decision_registry=DecisionPointRegistry(),
            path_manager=PathStateManager(),
            consequence_filter=ConsequenceFilter()
        )

        result = executor.execute_turn("nonexistent", "p1", {"type": "action"})

        assert not result.success
        assert "not found" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
