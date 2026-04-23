"""
Canonical bounded dramatic-effect evaluation contract (ROADMAP Phase
5–6).

Advisory until validation seam; serializable and inspectable — not a
second truth surface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ai_stack.character_mind_contract import CharacterMindRecord
from ai_stack.scene_plan_contract import ScenePlanRecord
from ai_stack.semantic_move_contract import SemanticMoveRecord
from ai_stack.social_state_contract import SocialStateRecord


class DramaticEffectGateResult(str, Enum):
    """Single source of truth for gate classification.

    On full GoC evaluation paths, ``not_supported`` must never appear.
    Non-GoC evaluators return only ``not_supported``.
    """

    not_supported = "not_supported"
    accepted = "accepted"
    accepted_with_weak_signal = "accepted_with_weak_signal"
    rejected_empty_fluency = "rejected_empty_fluency"
    rejected_character_implausibility = "rejected_character_implausibility"
    rejected_scene_function_mismatch = "rejected_scene_function_mismatch"
    rejected_continuity_pressure = "rejected_continuity_pressure"


class EmptyFluencyRisk(str, Enum):
    """``EmptyFluencyRisk`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    low = "low"
    moderate = "moderate"
    elevated = "elevated"


class CharacterPlausibilityPosture(str, Enum):
    """``CharacterPlausibilityPosture`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    plausible = "plausible"
    uncertain = "uncertain"
    implausible = "implausible"


class ContinuitySupportPosture(str, Enum):
    """``ContinuitySupportPosture`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    none = "none"
    weak = "weak"
    adequate = "adequate"
    strong = "strong"


class PressureContinuationPosture(str, Enum):
    """``PressureContinuationPosture`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    none = "none"
    stabilizes = "stabilizes"
    continues = "continues"
    redirects = "redirects"


class DramaticEffectTraceItem(BaseModel):
    """``DramaticEffectTraceItem`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    model_config = {"extra": "forbid"}

    code: str = Field(..., description="Bounded machine-readable trace step.")
    detail: str = Field(default="", description="Non-narrative hint for operators.")


class DramaticEffectGateOutcome(BaseModel):
    """Bounded dramatic-effect evaluation result — no free prose as hidden
    truth.
    """

    model_config = {"extra": "forbid"}

    gate_result: DramaticEffectGateResult
    rejection_reasons: list[str] = Field(default_factory=list)
    supports_scene_function: bool = False
    continues_or_changes_pressure: bool = False
    character_plausibility_posture: CharacterPlausibilityPosture = CharacterPlausibilityPosture.uncertain
    continuity_support_posture: ContinuitySupportPosture = ContinuitySupportPosture.weak
    empty_fluency_risk: EmptyFluencyRisk = EmptyFluencyRisk.moderate
    effect_rationale_codes: list[str] = Field(default_factory=list)
    legacy_fallback_used: bool = False
    diagnostic_trace: list[DramaticEffectTraceItem] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        """``to_runtime_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        return self.model_dump(mode="json")


class DramaticEffectEvaluationContext(BaseModel):
    """Typed seam input for dramatic-effect evaluation — not a loose dict at
    the validation boundary.
    """

    model_config = {"extra": "forbid"}

    module_id: str
    proposed_narrative: str = ""
    selected_scene_function: str = "establish_pressure"
    pacing_mode: str = "standard"
    silence_brevity_decision: dict[str, Any] = Field(default_factory=dict)
    semantic_move_record: dict[str, Any] | None = None
    social_state_record: dict[str, Any] | None = None
    primary_character_mind: dict[str, Any] | None = None
    scene_plan_record: dict[str, Any] | None = None
    prior_continuity_impacts: list[dict[str, Any]] = Field(default_factory=list)
    actor_lane_summary: dict[str, Any] | None = Field(
        default=None,
        description="Actor-lane health snapshot: {spoken_line_count, action_line_count, initiative_event_count, actor_lane_status}"
    )

    @field_validator("semantic_move_record", "social_state_record", "primary_character_mind", "scene_plan_record", mode="before")
    @classmethod
    def _none_empty_dict(cls, v: Any) -> Any:
        """``_none_empty_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            v: ``v`` (Any); meaning follows the type and call sites.
        
        Returns:
            Any:
                Returns a value of type ``Any``; see the function body for structure, error paths, and sentinels.
        """
        if v is None:
            return None
        return v

    def validated_semantic_move(self) -> SemanticMoveRecord | None:
        """Describe what ``validated_semantic_move`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            SemanticMoveRecord | None:
                Returns a value of type ``SemanticMoveRecord
                | None``; see the function body for structure, error paths, and sentinels.
        """
        raw = self.semantic_move_record
        if not raw:
            return None
        try:
            return SemanticMoveRecord.model_validate(raw)
        except Exception:
            return None

    def validated_social_state(self) -> SocialStateRecord | None:
        """Describe what ``validated_social_state`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            SocialStateRecord | None:
                Returns a value of type ``SocialStateRecord |
                None``; see the function body for structure, error paths, and sentinels.
        """
        raw = self.social_state_record
        if not raw:
            return None
        try:
            return SocialStateRecord.model_validate(raw)
        except Exception:
            return None

    def validated_character_mind(self) -> CharacterMindRecord | None:
        """Describe what ``validated_character_mind`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            CharacterMindRecord | None:
                Returns a value of type ``CharacterMindRecord
                | None``; see the function body for structure, error paths, and sentinels.
        """
        raw = self.primary_character_mind
        if not raw:
            return None
        try:
            return CharacterMindRecord.model_validate(raw)
        except Exception:
            return None

    def validated_scene_plan(self) -> ScenePlanRecord | None:
        """Describe what ``validated_scene_plan`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            ScenePlanRecord | None:
                Returns a value of type ``ScenePlanRecord |
                None``; see the function body for structure, error paths, and sentinels.
        """
        raw = self.scene_plan_record
        if not raw:
            return None
        try:
            return ScenePlanRecord.model_validate(raw)
        except Exception:
            return None


class SemanticPlannerSupportLevel(str, Enum):
    """Capability metadata only — gate truth remains
    ``DramaticEffectGateResult``.
    """

    full_goc = "full_goc"
    non_goc_waived = "non_goc_waived"
    module_unsupported = "module_unsupported"
