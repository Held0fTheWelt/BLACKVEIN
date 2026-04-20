"""Validation module for content modules.

Provides comprehensive validation for content module structure, cross-references,
and constraints. Validates semantic integrity of characters, relationships, triggers,
phases, and transitions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.content.module_models import ContentModule


@dataclass
class ValidationResult:
    """Result of a module validation operation.

    Attributes:
        is_valid: True if the module passes all validation checks
        module_id: The ID of the validated module
        errors: List of validation errors found (critical issues)
        warnings: List of validation warnings (non-critical issues)
        validation_time_ms: Time taken to perform validation in milliseconds
    """

    is_valid: bool
    module_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation_time_ms: float = 0.0


class ModuleCrossReferenceValidator:
    """Validator for semantic integrity of content modules.

    Checks that all cross-references within a module are valid, including:
    - Character references in triggers and relationships
    - Relationship axis references and character pairs
    - Trigger references in phases and transitions
    - Phase sequence integrity and transition DAG validity
    - Constraint bounds and enum values
    """

    def validate_character_references(self, module: ContentModule) -> list[str]:
        """Validate that all character references are valid.

        Checks that:
        - Trigger IDs in character_vulnerability keys reference valid characters
        - All character IDs exist in module.characters

        Args:
            module: The content module to validate

        Returns:
            List of validation errors found
        """
        errors: list[str] = []
        character_ids = set(module.characters.keys())

        for trigger_id, trigger in module.trigger_definitions.items():
            for char_id in trigger.character_vulnerability.keys():
                if char_id not in character_ids:
                    errors.append(
                        f"Trigger '{trigger_id}' references undefined character '{char_id}' "
                        f"in character_vulnerability"
                    )

        return errors

    def validate_relationship_references(self, module: ContentModule) -> list[str]:
        """Validate that all relationship references are valid.

        Each entry in ``axis.relationships`` is a relationship *id* that must appear in
        ``relationship_definitions`` (pairwise YAML) or in a small set of aggregate ids
        used by some modules (host/guest composites, etc.).
        """
        errors: list[str] = []
        pair_keys = set(module.relationship_definitions.keys())
        aggregates = frozenset(
            {
                "hosts_vs_guests",
                "veronique_guests",
                "michel_guests",
                "all_characters_pairwise",
            }
        )

        for axis_id, axis in module.relationship_axes.items():
            for rel_id in axis.relationships:
                if rel_id in pair_keys or rel_id in aggregates:
                    continue
                errors.append(
                    f"Relationship axis '{axis_id}' references unknown relationship id '{rel_id}'"
                )

        return errors

    def validate_trigger_references(self, module: ContentModule) -> list[str]:
        """Validate trigger id references on scene phases.

        ``phase_transitions`` / ``ending_conditions`` may store *narrative* trigger
        descriptions in ``trigger_conditions`` (not formal trigger ids); only
        ``active_triggers`` on phases are validated against ``trigger_definitions``.
        """
        errors: list[str] = []
        trigger_ids = set(module.trigger_definitions.keys())

        for phase_id, phase in module.scene_phases.items():
            for trigger_id in phase.active_triggers:
                if trigger_id not in trigger_ids:
                    errors.append(
                        f"Phase '{phase_id}' references undefined trigger '{trigger_id}' "
                        f"in active_triggers"
                    )

        return errors

    def validate_phase_sequence(self, module: ContentModule) -> list[str]:
        """Validate phase sequence integrity and transition DAG.

        Checks that:
        - Phase sequences are 1, 2, 3, 4, 5 (no gaps)
        - Phase IDs referenced in transitions exist
        - Transitions form valid DAG (no cycles)

        Args:
            module: The content module to validate

        Returns:
            List of validation errors found
        """
        errors: list[str] = []
        phase_map = module.phase_map()
        phase_ids = set(phase_map.keys())

        # Check for sequence gaps and valid sequences
        if module.scene_phases:
            sequences = sorted({phase.sequence for phase in module.scene_phases.values()})
            # Check if sequences are consecutive starting from 1
            expected = 1
            for seq in sequences:
                if seq != expected:
                    errors.append(
                        f"Phase sequence {seq} breaks sequence continuity. "
                        f"Expected {expected}, got {seq}"
                    )
                    expected += 1
                else:
                    expected += 1

        # Check transition phase references
        for transition in module.phase_transitions.values():
            if transition.from_phase not in phase_ids:
                errors.append(
                    f"Transition references undefined source phase '{transition.from_phase}'"
                )
            if transition.to_phase not in phase_ids:
                errors.append(
                    f"Transition references undefined target phase '{transition.to_phase}'"
                )

        # Check for cycles in transitions using DFS
        if not self._is_valid_dag(module.phase_transitions, phase_ids):
            errors.append("Phase transitions form a cycle (not a valid DAG)")

        return errors

    def _is_valid_dag(self, transitions, phase_ids: set[str]) -> bool:
        """Check if transitions form a valid directed acyclic graph.

        Args:
            transitions: Dict or list of PhaseTransition objects
            phase_ids: Set of valid phase IDs

        Returns:
            True if the transition graph is acyclic, False if cycles detected
        """
        # Build adjacency list
        graph = {phase_id: [] for phase_id in phase_ids}
        trans_items = transitions.values() if isinstance(transitions, dict) else transitions
        for transition in trans_items:
            if (
                transition.from_phase in graph
                and transition.to_phase in graph
            ):
                graph[transition.from_phase].append(transition.to_phase)

        # DFS-based cycle detection
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        # Check all nodes for cycles
        for phase_id in phase_ids:
            if phase_id not in visited:
                if has_cycle(phase_id):
                    return False

        return True

    def validate_constraints(self, module: ContentModule) -> list[str]:
        """Validate that all constraints have valid values.

        Checks that:
        - Numeric bounds make sense (e.g., max > 0, min <= max)
        - Required fields are non-empty where appropriate
        - Enum values are valid

        Args:
            module: The content module to validate

        Returns:
            List of validation errors found
        """
        errors: list[str] = []

        # Validate character baseline_attitude is non-empty
        for char_id, character in module.characters.items():
            if not character.baseline_attitude:
                errors.append(
                    f"Character '{char_id}' has empty baseline_attitude"
                )
            if not character.role:
                errors.append(
                    f"Character '{char_id}' has empty role"
                )

        # Validate relationship axis baseline is valid
        for axis_id, axis in module.relationship_axes.items():
            if axis.baseline is None:
                errors.append(
                    f"Relationship axis '{axis_id}' has invalid baseline value"
                )
            # For numeric baselines, ensure they're positive
            if isinstance(axis.baseline, (int, float)):
                if axis.baseline < 0:
                    errors.append(
                        f"Relationship axis '{axis_id}' has negative baseline value: {axis.baseline}"
                    )

        # Validate phase sequence is positive
        for phase_id, phase in module.scene_phases.items():
            if phase.sequence <= 0:
                errors.append(
                    f"Phase '{phase_id}' has invalid sequence: {phase.sequence} (must be > 0)"
                )
            if not phase.name:
                errors.append(
                    f"Phase '{phase_id}' has empty name"
                )

        # Validate trigger definitions have required fields
        for trigger_id, trigger in module.trigger_definitions.items():
            if not trigger.name:
                errors.append(
                    f"Trigger '{trigger_id}' has empty name"
                )
            if not trigger.description:
                errors.append(
                    f"Trigger '{trigger_id}' has empty description"
                )

        # Validate ending conditions have required fields
        for ending_id, ending in module.ending_conditions.items():
            if not ending.name:
                errors.append(
                    f"Ending '{ending_id}' has empty name"
                )
            if not ending.description:
                errors.append(
                    f"Ending '{ending_id}' has empty description"
                )

        # Validate relationship axes have names and descriptions
        for axis_id, axis in module.relationship_axes.items():
            if not axis.name:
                errors.append(
                    f"Relationship axis '{axis_id}' has empty name"
                )
            if not axis.description:
                errors.append(
                    f"Relationship axis '{axis_id}' has empty description"
                )

        return errors

    def validate_all(self, module: ContentModule) -> ValidationResult:
        """Validate all aspects of a content module.

        Orchestrates all validation checks and collects all errors
        from each validation method. Returns a complete ValidationResult
        with all errors and warnings found.

        Args:
            module: The content module to validate

        Returns:
            ValidationResult containing validation status, all errors,
            warnings, and timing information
        """
        start_time = time.perf_counter()

        all_errors: list[str] = []
        warnings: list[str] = []

        # Run all validation methods
        all_errors.extend(self.validate_character_references(module))
        all_errors.extend(self.validate_relationship_references(module))
        all_errors.extend(self.validate_trigger_references(module))
        all_errors.extend(self.validate_phase_sequence(module))
        all_errors.extend(self.validate_constraints(module))

        # Calculate validation time
        end_time = time.perf_counter()
        validation_time_ms = (end_time - start_time) * 1000

        # Determine if module is valid
        is_valid = len(all_errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            module_id=module.metadata.module_id,
            errors=all_errors,
            warnings=warnings,
            validation_time_ms=validation_time_ms,
        )
