"""Tests for narrative state transfer DTOs (DS-007 Task 2).

Tests frozen dataclasses, field validation, and successful instantiation
with valid data. Verifies type-safe boundaries between turn_executor and
narrative layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.runtime.narrative_state_transfer_dto import (
    NarrativeCommitEvent,
    ThreadUpdateInput,
    ThreadUpdateResult,
)


class TestNarrativeCommitEvent:
    """Test NarrativeCommitEvent frozen dataclass and validation."""

    def test_instantiate_with_valid_data(self) -> None:
        """Create NarrativeCommitEvent with all valid required fields."""
        now = datetime.utcnow()
        event = NarrativeCommitEvent(
            commit_id="commit_001",
            turn_id="turn_5",
            narrative_id="session_abc",
            user_id="user_123",
            commit_payload={"scene_id": "scene_1", "status": "active"},
            timestamp=now,
        )
        assert event.commit_id == "commit_001"
        assert event.turn_id == "turn_5"
        assert event.narrative_id == "session_abc"
        assert event.user_id == "user_123"
        assert event.commit_payload == {"scene_id": "scene_1", "status": "active"}
        assert event.timestamp == now
        assert event.metadata is None

    def test_instantiate_with_optional_metadata(self) -> None:
        """Create NarrativeCommitEvent with optional metadata dict."""
        now = datetime.utcnow()
        metadata = {"source": "ai_adapter", "priority": 1}
        event = NarrativeCommitEvent(
            commit_id="commit_002",
            turn_id="turn_6",
            narrative_id="session_def",
            user_id="user_456",
            commit_payload={"action": "escalate"},
            timestamp=now,
            metadata=metadata,
        )
        assert event.metadata == metadata
        assert event.metadata["source"] == "ai_adapter"

    def test_frozen_prevents_modification(self) -> None:
        """Frozen dataclass prevents field modification after creation."""
        now = datetime.utcnow()
        event = NarrativeCommitEvent(
            commit_id="commit_003",
            turn_id="turn_7",
            narrative_id="session_ghi",
            user_id="user_789",
            commit_payload={},
            timestamp=now,
        )
        with pytest.raises(AttributeError):
            event.commit_id = "commit_999"  # type: ignore

    def test_missing_commit_id_raises_error(self) -> None:
        """Empty commit_id raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="commit_id is required"):
            NarrativeCommitEvent(
                commit_id="",
                turn_id="turn_8",
                narrative_id="session_jkl",
                user_id="user_101",
                commit_payload={},
                timestamp=now,
            )

    def test_missing_turn_id_raises_error(self) -> None:
        """Empty turn_id raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="turn_id is required"):
            NarrativeCommitEvent(
                commit_id="commit_004",
                turn_id="",
                narrative_id="session_mno",
                user_id="user_202",
                commit_payload={},
                timestamp=now,
            )

    def test_missing_narrative_id_raises_error(self) -> None:
        """Empty narrative_id raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="narrative_id is required"):
            NarrativeCommitEvent(
                commit_id="commit_005",
                turn_id="turn_9",
                narrative_id="",
                user_id="user_303",
                commit_payload={},
                timestamp=now,
            )

    def test_missing_user_id_raises_error(self) -> None:
        """Empty user_id raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="user_id is required"):
            NarrativeCommitEvent(
                commit_id="commit_006",
                turn_id="turn_10",
                narrative_id="session_pqr",
                user_id="",
                commit_payload={},
                timestamp=now,
            )

    def test_invalid_timestamp_type_raises_error(self) -> None:
        """Non-datetime timestamp raises ValueError."""
        with pytest.raises(ValueError, match="timestamp must be a datetime object"):
            NarrativeCommitEvent(
                commit_id="commit_007",
                turn_id="turn_11",
                narrative_id="session_stu",
                user_id="user_404",
                commit_payload={},
                timestamp="2024-01-01",  # type: ignore
            )

    def test_commit_payload_preserves_complex_data(self) -> None:
        """commit_payload correctly preserves nested dict data."""
        now = datetime.utcnow()
        complex_payload = {
            "scene_id": "scene_1",
            "consequences": ["escalation", "new_thread"],
            "deltas": [
                {"target": "chars.npc1.mood", "value": 80},
                {"target": "world.time", "value": "evening"},
            ],
        }
        event = NarrativeCommitEvent(
            commit_id="commit_008",
            turn_id="turn_12",
            narrative_id="session_vwx",
            user_id="user_505",
            commit_payload=complex_payload,
            timestamp=now,
        )
        assert event.commit_payload == complex_payload
        assert len(event.commit_payload["deltas"]) == 2


class TestThreadUpdateResult:
    """Test ThreadUpdateResult frozen dataclass and validation."""

    def test_instantiate_with_valid_data(self) -> None:
        """Create ThreadUpdateResult with all valid required fields."""
        now = datetime.utcnow()
        result = ThreadUpdateResult(
            thread_id="thread_001",
            escalated_count=2,
            resolved_count=1,
            thread_version=5,
            updated_at=now,
        )
        assert result.thread_id == "thread_001"
        assert result.escalated_count == 2
        assert result.resolved_count == 1
        assert result.thread_version == 5
        assert result.updated_at == now
        assert result.metadata is None

    def test_instantiate_with_optional_metadata(self) -> None:
        """Create ThreadUpdateResult with optional metadata."""
        now = datetime.utcnow()
        metadata = {"reason": "escalation_signal", "source_event": "commit_009"}
        result = ThreadUpdateResult(
            thread_id="thread_002",
            escalated_count=1,
            resolved_count=0,
            thread_version=3,
            updated_at=now,
            metadata=metadata,
        )
        assert result.metadata == metadata

    def test_frozen_prevents_modification(self) -> None:
        """Frozen dataclass prevents field modification after creation."""
        now = datetime.utcnow()
        result = ThreadUpdateResult(
            thread_id="thread_003",
            escalated_count=0,
            resolved_count=0,
            thread_version=1,
            updated_at=now,
        )
        with pytest.raises(AttributeError):
            result.escalated_count = 5  # type: ignore

    def test_missing_thread_id_raises_error(self) -> None:
        """Empty thread_id raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="thread_id is required"):
            ThreadUpdateResult(
                thread_id="",
                escalated_count=0,
                resolved_count=0,
                thread_version=1,
                updated_at=now,
            )

    def test_negative_escalated_count_raises_error(self) -> None:
        """Negative escalated_count raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="escalated_count must be non-negative"):
            ThreadUpdateResult(
                thread_id="thread_004",
                escalated_count=-1,
                resolved_count=0,
                thread_version=1,
                updated_at=now,
            )

    def test_negative_resolved_count_raises_error(self) -> None:
        """Negative resolved_count raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="resolved_count must be non-negative"):
            ThreadUpdateResult(
                thread_id="thread_005",
                escalated_count=0,
                resolved_count=-1,
                thread_version=1,
                updated_at=now,
            )

    def test_negative_thread_version_raises_error(self) -> None:
        """Negative thread_version raises ValueError."""
        now = datetime.utcnow()
        with pytest.raises(ValueError, match="thread_version must be non-negative"):
            ThreadUpdateResult(
                thread_id="thread_006",
                escalated_count=0,
                resolved_count=0,
                thread_version=-1,
                updated_at=now,
            )

    def test_invalid_updated_at_type_raises_error(self) -> None:
        """Non-datetime updated_at raises ValueError."""
        with pytest.raises(ValueError, match="updated_at must be a datetime object"):
            ThreadUpdateResult(
                thread_id="thread_007",
                escalated_count=0,
                resolved_count=0,
                thread_version=1,
                updated_at="2024-01-01",  # type: ignore
            )

    def test_zero_counts_valid(self) -> None:
        """Zero counts are valid and meaningful."""
        now = datetime.utcnow()
        result = ThreadUpdateResult(
            thread_id="thread_008",
            escalated_count=0,
            resolved_count=0,
            thread_version=0,
            updated_at=now,
        )
        assert result.escalated_count == 0
        assert result.resolved_count == 0
        assert result.thread_version == 0


class TestThreadUpdateInput:
    """Test ThreadUpdateInput frozen dataclass and validation."""

    @pytest.fixture
    def valid_commit_event(self) -> NarrativeCommitEvent:
        """Create a valid NarrativeCommitEvent for use in tests."""
        return NarrativeCommitEvent(
            commit_id="commit_010",
            turn_id="turn_15",
            narrative_id="session_xyz",
            user_id="user_606",
            commit_payload={"status": "active"},
            timestamp=datetime.utcnow(),
        )

    def test_instantiate_with_valid_data(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Create ThreadUpdateInput with all valid required fields."""
        history = [{"turn": 1}, {"turn": 2}]
        progression = {"momentum": "active", "stalled_turns": 0}
        relationship = {"escalation_markers": False}

        input_obj = ThreadUpdateInput(
            history=history,
            progression=progression,
            relationship=relationship,
            commit_event=valid_commit_event,
        )
        assert input_obj.history == history
        assert input_obj.progression == progression
        assert input_obj.relationship == relationship
        assert input_obj.commit_event == valid_commit_event

    def test_frozen_prevents_modification(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Frozen dataclass prevents field modification after creation."""
        input_obj = ThreadUpdateInput(
            history=[],
            progression={},
            relationship={},
            commit_event=valid_commit_event,
        )
        with pytest.raises(AttributeError):
            input_obj.history = [{"turn": 1}]  # type: ignore

    def test_empty_history_valid(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Empty history list is valid."""
        input_obj = ThreadUpdateInput(
            history=[],
            progression={},
            relationship={},
            commit_event=valid_commit_event,
        )
        assert input_obj.history == []

    def test_empty_progression_valid(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Empty progression dict is valid."""
        input_obj = ThreadUpdateInput(
            history=[],
            progression={},
            relationship={},
            commit_event=valid_commit_event,
        )
        assert input_obj.progression == {}

    def test_empty_relationship_valid(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Empty relationship dict is valid."""
        input_obj = ThreadUpdateInput(
            history=[],
            progression={},
            relationship={},
            commit_event=valid_commit_event,
        )
        assert input_obj.relationship == {}

    def test_complex_history_data(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Complex nested history data is preserved."""
        complex_history = [
            {
                "turn": 1,
                "threads": [{"id": "t1", "status": "active"}],
                "state": {"chars": {"npc1": {"mood": 50}}},
            },
            {
                "turn": 2,
                "threads": [{"id": "t1", "status": "escalating"}],
                "state": {"chars": {"npc1": {"mood": 70}}},
            },
        ]
        input_obj = ThreadUpdateInput(
            history=complex_history,
            progression={},
            relationship={},
            commit_event=valid_commit_event,
        )
        assert len(input_obj.history) == 2
        assert input_obj.history[0]["turn"] == 1
        assert input_obj.history[1]["threads"][0]["status"] == "escalating"

    def test_invalid_history_type_raises_error(self, valid_commit_event: NarrativeCommitEvent) -> None:
        """Non-list history raises ValueError."""
        with pytest.raises(ValueError, match="history must be a list"):
            ThreadUpdateInput(
                history={"turn": 1},  # type: ignore
                progression={},
                relationship={},
                commit_event=valid_commit_event,
            )

    def test_invalid_progression_type_raises_error(
        self, valid_commit_event: NarrativeCommitEvent
    ) -> None:
        """Non-dict progression raises ValueError."""
        with pytest.raises(ValueError, match="progression must be a dict"):
            ThreadUpdateInput(
                history=[],
                progression=[],  # type: ignore
                relationship={},
                commit_event=valid_commit_event,
            )

    def test_invalid_relationship_type_raises_error(
        self, valid_commit_event: NarrativeCommitEvent
    ) -> None:
        """Non-dict relationship raises ValueError."""
        with pytest.raises(ValueError, match="relationship must be a dict"):
            ThreadUpdateInput(
                history=[],
                progression={},
                relationship="escalated",  # type: ignore
                commit_event=valid_commit_event,
            )

    def test_invalid_commit_event_type_raises_error(self) -> None:
        """Non-NarrativeCommitEvent commit_event raises ValueError."""
        with pytest.raises(ValueError, match="commit_event must be a NarrativeCommitEvent"):
            ThreadUpdateInput(
                history=[],
                progression={},
                relationship={},
                commit_event={"commit_id": "123"},  # type: ignore
            )

    def test_integration_all_dtypes_together(
        self, valid_commit_event: NarrativeCommitEvent
    ) -> None:
        """Comprehensive integration test with all DTO types."""
        # Create a complete scenario
        event = NarrativeCommitEvent(
            commit_id="commit_full",
            turn_id="turn_20",
            narrative_id="session_full",
            user_id="user_999",
            commit_payload={
                "scene_id": "forest",
                "consequences": ["escalation_signal"],
                "triggers": ["conflict"],
            },
            timestamp=datetime.utcnow(),
            metadata={"source": "ai_executor"},
        )

        result = ThreadUpdateResult(
            thread_id="thread_interpersonal",
            escalated_count=3,
            resolved_count=0,
            thread_version=7,
            updated_at=datetime.utcnow(),
            metadata={"reason": "character_conflict"},
        )

        input_obj = ThreadUpdateInput(
            history=[
                {"turn": 18, "active_threads": 2},
                {"turn": 19, "active_threads": 2},
            ],
            progression={"momentum": "stalled", "stalled_turns": 2},
            relationship={"escalation_markers": True, "tension_level": 8},
            commit_event=event,
        )

        # Verify all components are preserved
        assert event.commit_payload["scene_id"] == "forest"
        assert result.escalated_count == 3
        assert len(input_obj.history) == 2
        assert input_obj.progression["stalled_turns"] == 2
