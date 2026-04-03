"""Tests for W2.3-R1: SessionState integration with context layers.

Verifies that SessionState can hold W2.3 layers coherently without
regressions to existing session state behavior.
"""

from __future__ import annotations

import pytest

from app.runtime.runtime_models import SessionContextLayers, SessionState, SessionStatus


class TestSessionContextLayersModel:
    """Tests for SessionContextLayers wrapper structure."""

    def test_create_empty_context_layers(self):
        """SessionContextLayers can be created with all None defaults."""
        layers = SessionContextLayers()

        assert layers.short_term_context is None
        assert layers.session_history is None
        assert layers.progression_summary is None
        assert layers.relationship_axis_context is None
        assert layers.lore_direction_context is None

    def test_context_layers_accepts_any_values(self):
        """SessionContextLayers accepts Any type for each field."""
        layers = SessionContextLayers(
            short_term_context={"turn": 1, "scene": "test"},
            session_history=[{"turn": 1}, {"turn": 2}],
            progression_summary={"phase": "early"},
            relationship_axis_context={"axes": []},
            lore_direction_context={"units": []},
        )

        assert layers.short_term_context == {"turn": 1, "scene": "test"}
        assert layers.session_history == [{"turn": 1}, {"turn": 2}]
        assert layers.progression_summary == {"phase": "early"}
        assert layers.relationship_axis_context == {"axes": []}
        assert layers.lore_direction_context == {"units": []}

    def test_context_layers_serializable(self):
        """SessionContextLayers can be serialized to dict."""
        layers = SessionContextLayers(short_term_context={"turn": 1})
        data = layers.model_dump()

        assert data["short_term_context"] == {"turn": 1}
        assert data["session_history"] is None


class TestSessionStateContextIntegration:
    """Tests for SessionState holding W2.3 context layers."""

    def test_session_state_initializes_with_empty_context_layers(self):
        """SessionState creates default empty context_layers on init."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )

        assert session.context_layers is not None
        assert isinstance(session.context_layers, SessionContextLayers)
        assert session.context_layers.short_term_context is None
        assert session.context_layers.session_history is None
        assert session.context_layers.progression_summary is None
        assert session.context_layers.relationship_axis_context is None
        assert session.context_layers.lore_direction_context is None

    def test_session_state_can_receive_context_layers(self):
        """SessionState can be initialized with context_layers data."""
        layers = SessionContextLayers(
            short_term_context={"turn": 1},
            session_history=[],
        )
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
            context_layers=layers,
        )

        assert session.context_layers.short_term_context == {"turn": 1}
        assert session.context_layers.session_history == []

    def test_session_state_context_layers_field_is_accessible(self):
        """SessionState context_layers can be accessed and updated."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )

        # Access and update a layer
        session.context_layers.short_term_context = {"turn": 1, "scene": "scene_1"}

        assert session.context_layers.short_term_context == {"turn": 1, "scene": "scene_1"}

    def test_session_state_with_all_context_layers_populated(self):
        """SessionState can hold all W2.3 layers populated."""
        layers = SessionContextLayers(
            short_term_context={"turn": 5},
            session_history=[{"turn": 1}, {"turn": 2}, {"turn": 5}],
            progression_summary={"phase": "middle", "turns": 5},
            relationship_axis_context={"axes": [("alice", "bob")], "escalation": True},
            lore_direction_context={"units": [{"type": "scene"}], "bounded": True},
        )
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
            context_layers=layers,
        )

        # Verify all layers are accessible
        assert session.context_layers.short_term_context["turn"] == 5
        assert len(session.context_layers.session_history) == 3
        assert session.context_layers.progression_summary["phase"] == "middle"
        assert session.context_layers.relationship_axis_context["escalation"] is True
        assert len(session.context_layers.lore_direction_context["units"]) == 1

    def test_session_state_remains_backward_compatible(self):
        """SessionState without explicit context_layers still works."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
            status=SessionStatus.ACTIVE,
            turn_counter=5,
        )

        # All original fields work
        assert session.module_id == "test_module"
        assert session.status == SessionStatus.ACTIVE
        assert session.turn_counter == 5
        # New context_layers field exists with defaults
        assert session.context_layers is not None


class TestSessionStateStructureMaintenance:
    """Tests that SessionState structure remains maintainable."""

    def test_session_state_serialization_includes_context_layers(self):
        """SessionState serialization includes context_layers."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )
        data = session.model_dump()

        assert "context_layers" in data
        assert data["context_layers"]["short_term_context"] is None

    def test_session_state_json_serialization_works(self):
        """SessionState can be serialized to/from JSON."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )
        json_str = session.model_dump_json()
        restored = SessionState.model_validate_json(json_str)

        assert restored.module_id == session.module_id
        assert restored.context_layers is not None

    def test_session_state_distinct_from_context_layers(self):
        """SessionState and context_layers remain conceptually distinct."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
            turn_counter=10,
        )

        # Core session fields
        assert hasattr(session, "module_id")
        assert hasattr(session, "turn_counter")
        assert hasattr(session, "canonical_state")
        assert hasattr(session, "metadata")

        # Context layers separate
        assert hasattr(session, "context_layers")
        assert isinstance(session.context_layers, SessionContextLayers)

        # Updating context layers doesn't affect core fields
        session.context_layers.short_term_context = {"test": "data"}
        assert session.turn_counter == 10
        assert session.module_id == "test_module"


class TestSessionStateContextLayersClear:
    """Tests for clearing and resetting context layers."""

    def test_context_layers_can_be_reset(self):
        """SessionState can reset context_layers to empty state."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )

        session.context_layers.short_term_context = {"turn": 5}
        assert session.context_layers.short_term_context is not None

        # Reset to new empty instance
        session.context_layers = SessionContextLayers()
        assert session.context_layers.short_term_context is None

    def test_context_layers_independent_updates(self):
        """Each context layer can be updated independently."""
        session = SessionState(
            module_id="test_module",
            module_version="1.0.0",
            current_scene_id="scene_1",
        )

        # Update one layer
        session.context_layers.session_history = [{"turn": 1}]
        assert session.context_layers.session_history == [{"turn": 1}]
        assert session.context_layers.short_term_context is None

        # Update another layer
        session.context_layers.progression_summary = {"phase": "early"}
        assert session.context_layers.progression_summary == {"phase": "early"}
        assert session.context_layers.session_history == [{"turn": 1}]
