"""Canonical character voice records and runtime validation payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_stack.story_runtime.npc_agency.character.character_mind_contract import FieldProvenance

VoiceValidationMode = Literal["schema_only", "schema_plus_semantic", "strict_rule_engine"]
VoiceValidationStatus = Literal["approved", "rejected", "not_applicable"]
VoiceFindingSeverity = Literal["info", "warning", "failure"]


class VoiceSemanticLineClassification(BaseModel):
    """One structured semantic voice classification for a spoken line."""

    model_config = {"extra": "forbid"}

    classifier_version: str = "profile_semantic_overlap_v1"
    speaker_id: str
    expected_profile_actor_id: str | None = None
    best_matching_actor_id: str | None = None
    runner_up_actor_id: str | None = None
    expected_profile_alignment: float = 0.0
    best_profile_alignment: float = 0.0
    runner_up_profile_alignment: float = 0.0
    cross_actor_confusion_margin: float = 0.0
    confidence: float = 0.0
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    best_dimension_scores: dict[str, float] = Field(default_factory=dict)
    profile_alignments: dict[str, float] = Field(default_factory=dict)
    dimension_best_matching_actor_ids: dict[str, str] = Field(default_factory=dict)
    classification_status: str = "pass"
    finding_codes: list[str] = Field(default_factory=list)
    policy_sources: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CharacterVoiceProfileRecord(BaseModel):
    """Content-derived voice profile for one runtime actor."""

    model_config = {"extra": "forbid"}

    character_key: str = Field(..., description="Module-defined character key.")
    runtime_actor_id: str = Field(..., description="Canonical runtime actor id.")
    formal_role_label: str = Field(default="")
    baseline_tone: str = Field(default="")
    core_worldview: str = Field(default="")
    speech_patterns: dict[str, str] = Field(default_factory=dict)
    escalation_arc: dict[str, str] = Field(default_factory=dict)
    current_phase_voice_hint: str = Field(default="")
    signature_moments: list[str] = Field(default_factory=list)
    vulnerability: str = Field(default="")
    semantic_profile: dict[str, str] = Field(default_factory=dict)
    semantic_policy: dict[str, Any] = Field(default_factory=dict)
    forbidden_language_markers: dict[str, list[str]] = Field(default_factory=dict)
    dialogue_examples: list[str] = Field(default_factory=list)
    consistency_rules: list[str] = Field(default_factory=list)
    pitfalls_to_avoid: list[str] = Field(default_factory=list)
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"dialogue_examples"})


class VoiceDriftFinding(BaseModel):
    """One content-derived voice consistency finding."""

    model_config = {"extra": "forbid"}

    drift_class: str
    severity: VoiceFindingSeverity
    speaker_id: str
    character_key: str | None = None
    policy_source: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    expected_profile_actor_id: str | None = None
    actual_source_actor_id: str | None = None


class VoiceConsistencyValidationResult(BaseModel):
    """Runtime voice validation result consumed before commit."""

    model_config = {"extra": "forbid"}

    contract: str = "voice_consistency_validation.v1"
    status: VoiceValidationStatus
    reason: str
    validation_mode: VoiceValidationMode
    profiles_checked: int = 0
    spoken_line_count: int = 0
    findings: list[VoiceDriftFinding] = Field(default_factory=list)
    blocking_findings: list[VoiceDriftFinding] = Field(default_factory=list)
    semantic_classifications: list[VoiceSemanticLineClassification] = Field(default_factory=list)
    policy_sources: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
