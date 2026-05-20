"""Typed narrative governance contracts shared across services."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.world_engine.narrative_enums import PlayerAffectSignalType, PlayerAffectState


class ValidationViolation(BaseModel):
    """Machine-usable validation violation details."""

    violation_type: str
    specific_issue: str
    rule_violated: str
    suggested_fix: str
    severity: str = "blocking"


class ValidationFeedback(BaseModel):
    """Actionable feedback used for bounded corrective retry orchestration."""

    passed: bool
    violations: list[ValidationViolation] = Field(default_factory=list)
    corrections_needed: list[str] = Field(default_factory=list)
    legal_alternatives: dict[str, list[str]] = Field(default_factory=dict)


class AffectObservation(BaseModel):
    """Single affect signal observation captured from runtime behavior."""

    affect_state: PlayerAffectState
    confidence: float = Field(ge=0.0, le=1.0)
    source_type: PlayerAffectSignalType
    detected_turn: int = Field(ge=0)
    evidence: str = ""


class PlayerAffectAssessment(BaseModel):
    """Bounded affect assessment contract for future adaptation seams."""

    player_id: str
    dominant_affect: PlayerAffectState | None = None
    observations: list[AffectObservation] = Field(default_factory=list)
    preferred_pacing: str | None = None
    comfort_with_intensity: float | None = Field(default=None, ge=0.0, le=1.0)


class CharacterEmotionalState(BaseModel):
    """Optional character-emotion seam for governance-safe extension work."""

    actor_id: str
    current_emotional_state: str
    emotional_intensity: float = Field(ge=0.0, le=1.0)
    emotional_trajectory: str
    transition_cooldown_turns: int = Field(ge=0)
    recent_emotional_beats: list[dict[str, str]] = Field(default_factory=list)
    breaking_point_proximity: float = Field(default=0.0, ge=0.0, le=1.0)


class DraftPatchBundle(BaseModel):
    """Canonical draft patch bundle artifact for review-bound mutation."""

    patch_bundle_id: str
    module_id: str
    draft_workspace_id: str
    revision_ids: list[str]
    target_refs: list[str]
    patch_operations: list[dict[str, object]]
    requires_preview_rebuild: bool = True
    requires_evaluation: bool = True
    finding_ids: list[str] = Field(default_factory=list)
    preview_id: str | None = None
    created_at: str
