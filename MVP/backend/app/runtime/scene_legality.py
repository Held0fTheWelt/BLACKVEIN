"""Reusable scene transition and ending legality rules for W2 ``SessionState``.

Single implementation shared by ``validators`` and ``next_situation`` for consistent
**in-process** narrative checks. Not “authority” over World Engine live runs — engine
contracts govern production play.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SceneLegalityDecision:
    """Result of evaluating scene or ending legality.

    Attributes:
        allowed: Whether the transition/ending is legally allowed
        reason: Human-readable explanation of why it was allowed/denied
    """

    allowed: bool
    reason: str = ""


class SceneTransitionLegality:
    """Canonical legality rules for scene transitions and endings.

    Ensures validators.py and next_situation.py make identical
    decisions about narrative progression legality.
    """

    @staticmethod
    def check_transition_legal(
        from_scene: str,
        to_scene: str,
        module: any,
        session: any = None,
        detected_triggers: list[str] | None = None,
    ) -> SceneLegalityDecision:
        """Check if a scene transition is legal.

        Verifies:
        1. Target scene exists in module
        2. Self-transitions (staying in current scene) are always allowed
        3. A transition path exists from from_scene to to_scene
        4. If transition has conditions, all are detected (or triggers not available)

        Args:
            from_scene: Current scene ID
            to_scene: Proposed target scene ID
            module: ContentModule with transition definitions
            session: SessionState (optional, for future context checks)
            detected_triggers: Trigger IDs detected in current turn (optional)

        Returns:
            SceneLegalityDecision with allowed flag and reason
        """
        # Step 1: Verify target scene exists
        if not hasattr(module, "scene_phases") or to_scene not in module.scene_phases:
            return SceneLegalityDecision(
                allowed=False,
                reason=f"Scene '{to_scene}' not in module"
            )

        # Step 2: Self-transitions are always allowed (staying in current scene)
        if from_scene == to_scene:
            return SceneLegalityDecision(
                allowed=True,
                reason=f"Self-transition in '{from_scene}' is always allowed"
            )

        # Step 3: Find transition(s) from from_scene to to_scene
        matching_transitions = []
        if hasattr(module, "phase_transitions"):
            for transition in module.phase_transitions.values():
                if (hasattr(transition, "from_phase") and
                    hasattr(transition, "to_phase") and
                    transition.from_phase == from_scene and
                    transition.to_phase == to_scene):
                    matching_transitions.append(transition)

        if not matching_transitions:
            return SceneLegalityDecision(
                allowed=False,
                reason=f"Scene '{to_scene}' not reachable from '{from_scene}'"
            )

        # Step 4: Check conditions on matching transitions
        # If ANY transition has no conditions, it's unconditionally legal
        # If ALL transitions require conditions, check if they're met
        last_rejection_reason = None
        for transition in matching_transitions:
            is_legal, reason = SceneTransitionLegality._check_transition_conditions(
                transition, detected_triggers
            )
            if is_legal:
                return SceneLegalityDecision(
                    allowed=True,
                    reason=f"Transition from '{from_scene}' to '{to_scene}' is legal"
                )
            # Track the rejection reason for final error message
            last_rejection_reason = reason

        # All transitions require conditions that aren't met
        # Use specific rejection reason if available (e.g., "Conditions undefined but detected_triggers not provided")
        if last_rejection_reason:
            return SceneLegalityDecision(
                allowed=False,
                reason=f"Transition from '{from_scene}' to '{to_scene}' cannot proceed: {last_rejection_reason}"
            )
        else:
            return SceneLegalityDecision(
                allowed=False,
                reason=f"All transitions from '{from_scene}' to '{to_scene}' require unmet conditions"
            )

    @staticmethod
    def _check_transition_conditions(transition, detected_triggers: list[str] | None = None) -> tuple[bool, str]:
        """Check if transition conditions are met.

        Args:
            transition: PhaseTransition object
            detected_triggers: Detected trigger IDs in current turn (optional)

        Returns:
            (is_legal, reason) tuple
        """
        # Unconditional transition (no conditions defined) always allowed
        if not transition.trigger_conditions:
            return True, "Unconditional transition"

        # Conditional transition: all conditions must be detected
        if detected_triggers is not None:
            if all(cond in detected_triggers for cond in transition.trigger_conditions):
                return True, f"All conditions {transition.trigger_conditions} detected"
            else:
                missing = [c for c in transition.trigger_conditions if c not in detected_triggers]
                return False, f"Missing conditions: {missing}"

        # Conditions defined but no detected_triggers provided: cannot evaluate
        return False, "Conditions undefined but detected_triggers not provided"

    @staticmethod
    def check_ending_legal(
        module: any,
        session: any = None,
        detected_triggers: list[str] | None = None,
    ) -> tuple[Optional[str], SceneLegalityDecision]:
        """Check if any ending condition is legally triggered.

        Verifies ending conditions in priority order:
        1. If unconditional ending exists, return it
        2. If any conditional ending has all conditions detected, return it
        3. If no ending is legal, return None

        Args:
            module: ContentModule with ending definitions
            session: SessionState (optional)
            detected_triggers: Trigger IDs detected in current turn (optional)

        Returns:
            (ending_id, SceneLegalityDecision) tuple
            ending_id is None if no legal ending exists
        """
        if not hasattr(module, "ending_conditions"):
            return None, SceneLegalityDecision(
                allowed=False,
                reason="Module has no ending conditions defined"
            )

        # Check each ending in order
        for ending_id, ending in module.ending_conditions.items():
            is_legal, reason = SceneTransitionLegality._check_ending_conditions(
                ending, detected_triggers
            )
            if is_legal:
                return ending_id, SceneLegalityDecision(
                    allowed=True,
                    reason=f"Ending '{ending_id}' is legally triggered: {reason}"
                )

        # No legal ending
        return None, SceneLegalityDecision(
            allowed=False,
            reason="No ending conditions are satisfied"
        )

    @staticmethod
    def _check_ending_conditions(ending, detected_triggers: list[str] | None = None) -> tuple[bool, str]:
        """Check if ending conditions are met.

        Args:
            ending: EndingCondition object
            detected_triggers: Detected trigger IDs in current turn (optional)

        Returns:
            (is_legal, reason) tuple
        """
        # Unconditional ending (no conditions defined) always triggers
        if not ending.trigger_conditions:
            return True, "Unconditional ending"

        # Conditional ending: all conditions must be detected
        if detected_triggers is not None:
            if all(cond in detected_triggers for cond in ending.trigger_conditions):
                return True, f"All conditions {ending.trigger_conditions} detected"
            else:
                missing = [c for c in ending.trigger_conditions if c not in detected_triggers]
                return False, f"Missing conditions: {missing}"

        # Conditions defined but no detected_triggers provided: cannot evaluate
        return False, "Conditions undefined but detected_triggers not provided"
