"""W2.2.1 — Canonical Decision Policy and Action Taxonomy

Defines the explicit taxonomy of allowed AI decision actions.
All AI proposals must conform to one of these action types.
"""

from enum import Enum


class AIActionType(str, Enum):
    """Canonical taxonomy of allowed AI decision actions.

    Each action type has specific validation rules and expected structure.
    """

    STATE_UPDATE = "state_update"
    """Update a character, relationship, or scene property.

    Requires: target_path, next_value
    Examples: character emotional_state, relationship affinity, scene_metadata
    """

    RELATIONSHIP_SHIFT = "relationship_shift"
    """Propose a change in relationship between entities.

    Requires: target_path (relationship path), next_value
    Examples: trust level change, affection shift
    """

    SCENE_TRANSITION = "scene_transition"
    """Propose transition to a different scene or phase.

    Requires: proposed_scene_id in decision
    Examples: move to next scene, return to previous location
    """

    TRIGGER_ASSERTION = "trigger_assertion"
    """Assert that a game trigger has been detected or should fire.

    Requires: trigger ID in detected_triggers list
    Examples: conflict escalation trigger, reconciliation moment
    """

    DIALOGUE_IMPULSE = "dialogue_impulse"
    """Character wants to say or do something (narrative action).

    Requires: character_id, impulse_text, intensity
    Examples: character dialogue, character action beat
    """

    CONFLICT_SIGNAL = "conflict_signal"
    """Signal current narrative conflict state and intensity.

    Requires: primary_axis, intensity
    Examples: trust conflict intensifying, guilt emerging
    """


class AIDecisionPolicy:
    """Canonical policy for AI decision validation.

    Enforces allowed action types and their validation rules.
    """

    ALLOWED_ACTIONS = frozenset(AIActionType)

    @staticmethod
    def is_action_type_allowed(action_type: str) -> bool:
        """Check if an action type is in the allowed taxonomy.

        Args:
            action_type: The proposed action type string

        Returns:
            True if action_type is a valid AIActionType value
        """
        try:
            AIActionType(action_type)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_action_description(action_type: str) -> str:
        """Get human-readable description of an action type.

        Args:
            action_type: The action type string

        Returns:
            Description of what this action type is for
        """
        try:
            action = AIActionType(action_type)
            return action.__doc__ or f"Action type: {action.value}"
        except ValueError:
            return f"Unknown action type: {action_type}"
