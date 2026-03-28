"""Reference integrity validation for AI proposals.

Ensures AI decisions may only reference known, valid, context-appropriate module entities.
Denies references to nonexistent characters, relationships, scenes, and triggers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReferencePolicyDecision:
    """Result of evaluating a reference against the reference policy.

    Attributes:
        allowed: Whether the reference is valid and legal
        reason_code: Machine-readable reason code if blocked
        reason_message: Human-readable reason message if blocked
    """

    allowed: bool
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None


class ReferencePolicy:
    """Canonical reference integrity policy for AI proposals.

    Validates that character, relationship, scene, and trigger references
    point to known module entities and are contextually legal.
    """

    @staticmethod
    def evaluate(
        reference_type: str,
        reference_id: str,
        module: any,
        session: any = None,
        current_scene_id: str | None = None,
    ) -> ReferencePolicyDecision:
        """Evaluate whether a reference is valid and legal.

        Args:
            reference_type: One of 'character', 'relationship', 'scene', 'trigger'
            reference_id: The ID/name of the entity being referenced
            module: ContentModule containing canonical entity definitions
            session: SessionState (required for scene/trigger validation)
            current_scene_id: Current scene ID (required for scene/trigger validation)

        Returns:
            ReferencePolicyDecision with allowed flag and reason codes
        """
        # Dispatch to type-specific validator
        if reference_type == "character":
            return ReferencePolicy._validate_character(reference_id, module)
        elif reference_type == "relationship":
            return ReferencePolicy._validate_relationship(reference_id, module)
        elif reference_type == "scene":
            return ReferencePolicy._validate_scene(reference_id, module, session, current_scene_id)
        elif reference_type == "trigger":
            return ReferencePolicy._validate_trigger(reference_id, module, session, current_scene_id)
        else:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="invalid_reference_type",
                reason_message=f"Unknown reference type: {reference_type}"
            )

    @staticmethod
    def _validate_character(character_id: str, module: any) -> ReferencePolicyDecision:
        """Validate character reference (existence only)."""
        if not character_id:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_character",
                reason_message="Character ID cannot be empty"
            )

        if not hasattr(module, "characters") or character_id not in module.characters:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_character",
                reason_message=f"Character '{character_id}' not in module"
            )

        return ReferencePolicyDecision(allowed=True)

    @staticmethod
    def _validate_relationship(relationship_id: str, module: any) -> ReferencePolicyDecision:
        """Validate relationship reference (existence only)."""
        if not relationship_id:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_relationship",
                reason_message="Relationship ID cannot be empty"
            )

        if not hasattr(module, "relationship_axes") or relationship_id not in module.relationship_axes:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_relationship",
                reason_message=f"Relationship '{relationship_id}' not in module"
            )

        return ReferencePolicyDecision(allowed=True)

    @staticmethod
    def _validate_scene(
        scene_id: str,
        module: any,
        session: any,
        current_scene_id: str | None
    ) -> ReferencePolicyDecision:
        """Validate scene reference (existence + context legality)."""
        if not scene_id:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_scene",
                reason_message="Scene ID cannot be empty"
            )

        # Check existence
        if not hasattr(module, "scene_phases") or scene_id not in module.scene_phases:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_scene",
                reason_message=f"Scene '{scene_id}' not in module"
            )

        # Self-reference is always allowed
        if current_scene_id and scene_id == current_scene_id:
            return ReferencePolicyDecision(allowed=True)

        # For other scenes, check reachability
        if not current_scene_id:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="missing_context",
                reason_message="Scene legality check requires current_scene_id"
            )

        # Check if target scene is reachable from current scene
        if not ReferencePolicy._is_scene_reachable(
            current_scene_id, scene_id, module
        ):
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="scene_not_reachable",
                reason_message=f"Scene '{scene_id}' not reachable from current scene '{current_scene_id}'"
            )

        return ReferencePolicyDecision(allowed=True)

    @staticmethod
    def _validate_trigger(
        trigger_id: str,
        module: any,
        session: any,
        current_scene_id: str | None
    ) -> ReferencePolicyDecision:
        """Validate trigger reference (existence + context legality)."""
        if not trigger_id:
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_trigger",
                reason_message="Trigger ID cannot be empty"
            )

        # Check existence in module's canonical trigger space
        if not ReferencePolicy._trigger_exists_in_module(trigger_id, module):
            return ReferencePolicyDecision(
                allowed=False,
                reason_code="unknown_trigger",
                reason_message=f"Trigger '{trigger_id}' not in module"
            )

        # Check applicability in current scene
        if current_scene_id:
            if not ReferencePolicy._trigger_applicable_in_scene(
                trigger_id, current_scene_id, module
            ):
                return ReferencePolicyDecision(
                    allowed=False,
                    reason_code="trigger_not_applicable",
                    reason_message=f"Trigger '{trigger_id}' not applicable in scene '{current_scene_id}'"
                )

        return ReferencePolicyDecision(allowed=True)

    @staticmethod
    def _is_scene_reachable(from_scene: str, to_scene: str, module: any) -> bool:
        """Check if to_scene is reachable from from_scene via phase_transitions."""
        if not hasattr(module, "phase_transitions"):
            return False

        transitions = module.phase_transitions
        if not isinstance(transitions, dict):
            return False

        for transition in transitions.values():
            if hasattr(transition, "from_phase") and hasattr(transition, "to_phase"):
                if transition.from_phase == from_scene and transition.to_phase == to_scene:
                    return True

        return False

    @staticmethod
    def _trigger_exists_in_module(trigger_id: str, module: any) -> bool:
        """Check if trigger exists in module's canonical trigger space."""
        # Check multiple possible locations
        if hasattr(module, "triggers") and trigger_id in module.triggers:
            return True
        if hasattr(module, "assertions") and trigger_id in module.assertions:
            return True
        return False

    @staticmethod
    def _trigger_applicable_in_scene(trigger_id: str, scene_id: str, module: any) -> bool:
        """Check if trigger is applicable in the given scene."""
        # Placeholder: assume all existing triggers are applicable for now
        # This will be refined based on module's actual trigger applicability structure
        return True
