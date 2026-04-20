"""Tests for W2.2.1 — Canonical decision policy and action taxonomy.

Verifies that:
1. The action taxonomy is properly defined
2. Unknown action types are rejected
3. Required fields are enforced per action type
4. Valid actions pass policy validation
"""

from types import SimpleNamespace

import pytest
from app.runtime.decision_policy import AIActionType, AIDecisionPolicy
from app.runtime.validators import validate_action_type, validate_action_structure


class TestActionTypeEnum:
    """Test the AIActionType taxonomy."""

    def test_all_action_types_defined(self):
        """All 6 action types are defined."""
        expected = {
            "state_update",
            "relationship_shift",
            "scene_transition",
            "trigger_assertion",
            "dialogue_impulse",
            "conflict_signal",
        }
        actual = {at.value for at in AIActionType}
        assert actual == expected

    def test_action_type_values_are_lowercase_snake_case(self):
        """Action type values follow naming convention."""
        for action_type in AIActionType:
            assert action_type.value.islower()
            assert "_" in action_type.value or len(action_type.value) <= 12

    def test_no_duplicate_action_types(self):
        """No duplicate values in enum."""
        values = [at.value for at in AIActionType]
        assert len(values) == len(set(values))


class TestActionPolicy:
    """Test AIDecisionPolicy enforcement."""

    def test_allowed_actions_contain_all_types(self):
        """Policy allows all defined action types."""
        for action_type in AIActionType:
            assert action_type in AIDecisionPolicy.ALLOWED_ACTIONS

    def test_is_action_type_allowed_accepts_valid_types(self):
        """Valid action types pass the policy check."""
        for action_type in AIActionType:
            assert AIDecisionPolicy.is_action_type_allowed(action_type.value)

    def test_is_action_type_allowed_rejects_invalid_types(self):
        """Invalid action types are rejected."""
        invalid_types = ["invalid_action", "custom_type", "foo_bar", ""]
        for invalid in invalid_types:
            assert not AIDecisionPolicy.is_action_type_allowed(invalid)


class TestActionTypeValidation:
    """Test validate_action_type() function."""

    def test_valid_action_types_pass(self):
        """Valid action types pass validation."""
        for action_type in AIActionType:
            is_valid, error = validate_action_type(action_type.value)
            assert is_valid
            assert error is None

    def test_invalid_action_type_fails(self):
        """Unknown action types are rejected."""
        is_valid, error = validate_action_type("unknown_action")
        assert not is_valid
        assert "Unknown action type" in error
        assert "unknown_action" in error

    def test_empty_action_type_fails(self):
        """Empty action type is rejected."""
        is_valid, error = validate_action_type("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_error_message_lists_allowed_types(self):
        """Error message includes list of allowed types."""
        is_valid, error = validate_action_type("invalid")
        assert "state_update" in error
        assert "conflict_signal" in error


class TestActionStructureValidation:
    """Test validate_action_structure() function."""

    def test_state_update_requires_target_path(self):
        """STATE_UPDATE requires target_path."""
        is_valid, errors = validate_action_structure(
            "state_update",
            {"next_value": 50}  # Missing target_path
        )
        assert not is_valid
        assert any("target_path" in e for e in errors)

    def test_state_update_requires_next_value(self):
        """STATE_UPDATE requires next_value."""
        is_valid, errors = validate_action_structure(
            "state_update",
            {"target_path": "characters.test.state"}  # Missing next_value
        )
        assert not is_valid
        assert any("next_value" in e for e in errors)

    def test_state_update_accepts_valid_structure(self):
        """STATE_UPDATE accepts valid fields."""
        is_valid, errors = validate_action_structure(
            "state_update",
            {
                "target_path": "characters.test.state",
                "next_value": 50,
                "rationale": "test update"
            }
        )
        assert is_valid
        assert len(errors) == 0

    def test_relationship_shift_requires_target_path_and_value(self):
        """RELATIONSHIP_SHIFT requires both fields."""
        is_valid, errors = validate_action_structure(
            "relationship_shift",
            {"target_path": "relationships.test"}  # Missing next_value
        )
        assert not is_valid

    def test_scene_transition_requires_scene_id(self):
        """SCENE_TRANSITION requires scene_id."""
        is_valid, errors = validate_action_structure(
            "scene_transition",
            {"other_field": "value"}
        )
        assert not is_valid
        assert any("scene_id" in e for e in errors)

    def test_trigger_assertion_requires_trigger_ids(self):
        """TRIGGER_ASSERTION requires trigger_ids."""
        is_valid, errors = validate_action_structure(
            "trigger_assertion",
            {}
        )
        assert not is_valid
        assert any("trigger_ids" in e for e in errors)

    def test_dialogue_impulse_requires_fields(self):
        """DIALOGUE_IMPULSE requires character_id and impulse_text."""
        is_valid, errors = validate_action_structure(
            "dialogue_impulse",
            {"character_id": "character1"}  # Missing impulse_text
        )
        assert not is_valid
        assert any("impulse_text" in e for e in errors)

    def test_conflict_signal_requires_intensity(self):
        """CONFLICT_SIGNAL requires intensity."""
        is_valid, errors = validate_action_structure(
            "conflict_signal",
            {"primary_axis": "trust"}  # Missing intensity
        )
        assert not is_valid
        assert any("intensity" in e for e in errors)

    def test_conflict_signal_accepts_intensity_zero(self):
        """CONFLICT_SIGNAL accepts intensity of 0.0."""
        is_valid, errors = validate_action_structure(
            "conflict_signal",
            {"primary_axis": "trust", "intensity": 0.0}
        )
        assert is_valid


class TestValidateActionStructureExtraBranches:
    """Branches in validate_action_structure (invalid enum, module-backed checks)."""

    def test_invalid_action_type_string(self):
        is_valid, errors = validate_action_structure("not_a_valid_action_type", {})
        assert not is_valid
        assert errors and "Invalid action type" in errors[0]

    def test_relationship_shift_missing_target_path(self):
        is_valid, errors = validate_action_structure(
            "relationship_shift",
            {"next_value": 1},
        )
        assert not is_valid
        assert any("target_path" in e for e in errors)

    def test_trigger_assertion_passes_with_triggers_on_stub_module(self):
        mod = SimpleNamespace(triggers={"known_trigger": True}, assertions={})
        sess = SimpleNamespace(current_scene_id="scene_a")
        is_valid, errors = validate_action_structure(
            "trigger_assertion",
            {"trigger_ids": ["known_trigger"]},
            module=mod,
            session=sess,
        )
        assert is_valid
        assert errors == []

    def test_dialogue_impulse_valid_with_god_of_carnage_module(self, god_of_carnage_module):
        is_valid, errors = validate_action_structure(
            "dialogue_impulse",
            {"character_id": "veronique", "impulse_text": "A line."},
            module=god_of_carnage_module,
        )
        assert is_valid
        assert not errors

    def test_dialogue_impulse_missing_impulse_text_after_character_ok(self, god_of_carnage_module):
        is_valid, errors = validate_action_structure(
            "dialogue_impulse",
            {"character_id": "veronique"},
            module=god_of_carnage_module,
        )
        assert not is_valid
        assert any("impulse_text" in e for e in errors)

    def test_trigger_assertion_one_invalid_among_ids(self):
        mod = SimpleNamespace(triggers={"good_t": True}, assertions={})
        sess = SimpleNamespace(current_scene_id="scene_a")
        is_valid, errors = validate_action_structure(
            "trigger_assertion",
            {"trigger_ids": ["good_t", "bad_t"]},
            module=mod,
            session=sess,
        )
        assert not is_valid
        assert errors

class TestGetActionDescription:
    def test_unknown_action_type_message(self):
        from app.runtime.decision_policy import AIDecisionPolicy
        assert "Unknown" in AIDecisionPolicy.get_action_description("not_a_real_type")

    def test_known_type_uses_doc_or_fallback(self):
        from app.runtime.decision_policy import AIDecisionPolicy, AIActionType
        for at in AIActionType:
            desc = AIDecisionPolicy.get_action_description(at.value)
            assert desc
            assert at.value in desc or (at.__doc__ and at.__doc__.strip() in desc)
