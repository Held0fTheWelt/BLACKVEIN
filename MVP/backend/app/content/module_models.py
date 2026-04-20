"""
Pydantic models for content module structure.

These models define the schema for content modules like "God of Carnage",
providing structure for characters, relationships, triggers, scene phases,
and narrative flow.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModuleMetadata(BaseModel):
    """Metadata about a content module.

    Attributes:
        module_id: Unique identifier for the module
        title: Human-readable title of the module
        version: Module version (semantic versioning)
        contract_version: Version of the content module contract/schema
        description: Human-readable description of the module
        content: Structured content metadata (dict)
        files: List of file references/paths in the module
    """

    module_id: str = Field(..., description="Unique module identifier")
    title: str = Field(..., description="Module title")
    version: str = Field(..., description="Module version (e.g., 1.0.0)")
    contract_version: str = Field(..., description="Content module contract version")
    description: str | None = Field(default=None, description="Module description")
    content: dict[str, Any] = Field(default_factory=dict, description="Structured content metadata")
    files: list[str] = Field(default_factory=list, description="Module file references/paths")


class CharacterDefinition(BaseModel):
    """Definition of a character in a module.

    Attributes:
        id: Unique identifier for the character
        name: Character name
        role: Character's role in the module (e.g., "protagonist", "antagonist")
        baseline_attitude: Initial attitude/demeanor
        extras: Module-specific character attributes (flexible)
    """

    id: str = Field(..., description="Character identifier")
    name: str = Field(..., description="Character name")
    role: str = Field(..., description="Character role in module")
    baseline_attitude: str = Field(..., description="Initial character attitude")
    extras: dict[str, Any] = Field(default_factory=dict, description="Module-specific attributes")


class RelationshipAxis(BaseModel):
    """Definition of a relationship axis between characters.

    Attributes:
        id: Unique identifier for the axis
        name: Axis name (e.g., "dominance", "affection")
        description: Description of what this axis represents
        relationships: Mapping of character pair to relationship state
        baseline: Initial state of the axis
        escalation: How the axis escalates under tension
    """

    id: str = Field(..., description="Axis identifier")
    name: str = Field(..., description="Axis name")
    description: str = Field(..., description="Axis description")
    relationships: list[str] = Field(default_factory=list, description="Character relationship states")
    baseline: dict[str, Any] = Field(..., description="Baseline axis state")
    escalation: dict[str, Any] = Field(default_factory=dict, description="Escalation rules")


class TriggerDefinition(BaseModel):
    """Definition of a trigger event in a module.

    Attributes:
        id: Unique identifier for the trigger
        name: Trigger name
        description: What activates this trigger
        recognition_markers: Signs that indicate trigger activation
        escalation_impact: How this trigger escalates conflict
        active_in_phases: Which scene phases this trigger is active
        character_vulnerability: Character vulnerabilities to this trigger
    """

    id: str = Field(..., description="Trigger identifier")
    name: str = Field(..., description="Trigger name")
    description: str = Field(..., description="Trigger description")
    recognition_markers: list[str] = Field(default_factory=list, description="Markers for trigger recognition")
    escalation_impact: dict[str, Any] = Field(default_factory=dict, description="How this escalates conflict")
    active_in_phases: list[str] = Field(default_factory=list, description="Phase IDs where trigger is active")
    character_vulnerability: dict[str, Any] = Field(default_factory=dict, description="Character vulnerabilities")


class ScenePhase(BaseModel):
    """Definition of a scene phase in module progression.

    Attributes:
        id: Unique identifier for the phase
        name: Phase name
        sequence: Order in which phase occurs (must be positive)
        description: Phase description
        content_focus: What aspects are focused on in this phase
        engine_tasks: Tasks for the narrative engine
        active_triggers: Trigger IDs active in this phase
        enforced_constraints: Constraints active in this phase
    """

    id: str = Field(..., description="Phase identifier")
    name: str = Field(..., description="Phase name")
    sequence: int = Field(..., description="Phase sequence order", gt=0)
    description: str = Field(..., description="Phase description")
    content_focus: list[str] = Field(default_factory=list, description="Content focus for this phase")
    engine_tasks: list[str] = Field(default_factory=list, description="Engine tasks to execute")
    active_triggers: list[str] = Field(default_factory=list, description="Active trigger IDs")
    enforced_constraints: list[str] | None = Field(default=None, description="Phase constraints")

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, v: int) -> int:
        """Ensure sequence is a positive integer."""
        if v <= 0:
            raise ValueError("sequence must be a positive integer")
        return v


class PhaseTransition(BaseModel):
    """Definition of transitions between scene phases.

    Attributes:
        from_phase: Source phase ID
        to_phase: Target phase ID
        trigger_conditions: Conditions that allow transition
        engine_checks: Engine validation before transition
        transition_action: Action to perform during transition
    """

    from_phase: str = Field(..., description="Source phase ID")
    to_phase: str = Field(..., description="Target phase ID")
    trigger_conditions: list[str] = Field(default_factory=list, description="Transition trigger conditions")
    engine_checks: list[str] = Field(default_factory=list, description="Engine validation checks")
    transition_action: str | None = Field(default=None, description="Transition action details")


class EndingCondition(BaseModel):
    """Definition of an ending condition for the module.

    Attributes:
        id: Unique identifier for the ending
        name: Ending name
        description: Description of this ending
        trigger_conditions: Conditions that trigger this ending
        outcome: The outcome of reaching this ending
        closure_action: Action to perform for closure
    """

    id: str = Field(..., description="Ending identifier")
    name: str = Field(..., description="Ending name")
    description: str = Field(..., description="Ending description")
    trigger_conditions: list[str] = Field(default_factory=list, description="Conditions for this ending")
    outcome: dict[str, Any] = Field(..., description="Outcome of this ending")
    closure_action: list[str] | None = Field(default=None, description="Closure action details")


class ContentModule(BaseModel):
    """Aggregated content module structure.

    Contains all components of a content module including metadata, characters,
    relationships, triggers, scene phases, phase transitions, and ending conditions.

    Attributes:
        metadata: Module metadata
        characters: Dictionary of character definitions keyed by character ID
        relationship_axes: Dictionary of relationship axes keyed by axis ID
        trigger_definitions: Dictionary of trigger definitions keyed by trigger ID
        scene_phases: Dictionary of scene phases keyed by phase ID
        phase_transitions: Dictionary of phase transitions keyed by transition ID
        ending_conditions: Dictionary of ending conditions keyed by ending ID
        escalation_axes: Escalation axes data structure
    """

    metadata: ModuleMetadata = Field(..., description="Module metadata")
    characters: dict[str, CharacterDefinition] = Field(default_factory=dict, description="Character definitions by ID")
    relationship_axes: dict[str, RelationshipAxis] = Field(default_factory=dict, description="Relationship axes by ID")
    relationship_definitions: dict[str, Any] = Field(
        default_factory=dict,
        description="Pairwise relationship definitions keyed by relationship id (from relationships.yaml)",
    )
    trigger_definitions: dict[str, TriggerDefinition] = Field(default_factory=dict, description="Trigger definitions by ID")
    scene_phases: dict[str, ScenePhase] = Field(default_factory=dict, description="Scene phases by ID")
    phase_transitions: dict[str, PhaseTransition] = Field(default_factory=dict, description="Phase transitions")
    ending_conditions: dict[str, EndingCondition] = Field(default_factory=dict, description="Ending conditions by ID")
    escalation_axes: dict[str, Any] = Field(default_factory=dict, description="Escalation axes data structure")

    def character_map(self) -> dict[str, CharacterDefinition]:
        """Return the character definitions dictionary."""
        return self.characters

    def phase_map(self) -> dict[str, ScenePhase]:
        """Return the scene phases dictionary."""
        return self.scene_phases

    def trigger_map(self) -> dict[str, TriggerDefinition]:
        """Return the trigger definitions dictionary."""
        return self.trigger_definitions

    def ending_map(self) -> dict[str, EndingCondition]:
        """Return the ending conditions dictionary."""
        return self.ending_conditions

    def relationship_axes_map(self) -> dict[str, RelationshipAxis]:
        """Return the relationship axes dictionary."""
        return self.relationship_axes

    def phase_transitions_map(self) -> dict[str, PhaseTransition]:
        """Return the phase transitions dictionary."""
        return self.phase_transitions
