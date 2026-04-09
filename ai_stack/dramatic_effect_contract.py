"""Canonical bounded dramatic-effect evaluation contract (ROADMAP Phase 5–6).

Advisory until validation seam; serializable and inspectable — not a second truth surface.
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
    low = "low"
    moderate = "moderate"
    elevated = "elevated"


class CharacterPlausibilityPosture(str, Enum):
    plausible = "plausible"
    uncertain = "uncertain"
    implausible = "implausible"


class ContinuitySupportPosture(str, Enum):
    none = "none"
    weak = "weak"
    adequate = "adequate"
    strong = "strong"


class PressureContinuationPosture(str, Enum):
    none = "none"
    stabilizes = "stabilizes"
    continues = "continues"
    redirects = "redirects"


class DramaticEffectTraceItem(BaseModel):
    model_config = {"extra": "forbid"}

    code: str = Field(..., description="Bounded machine-readable trace step.")
    detail: str = Field(default="", description="Non-narrative hint for operators.")


class DramaticEffectGateOutcome(BaseModel):
    """Bounded dramatic-effect evaluation result — no free prose as hidden truth."""

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
        return self.model_dump(mode="json")


class DramaticEffectEvaluationContext(BaseModel):
    """Typed seam input for dramatic-effect evaluation — not a loose dict at the validation boundary."""

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

    @field_validator("semantic_move_record", "social_state_record", "primary_character_mind", "scene_plan_record", mode="before")
    @classmethod
    def _none_empty_dict(cls, v: Any) -> Any:
        if v is None:
            return None
        return v

    def validated_semantic_move(self) -> SemanticMoveRecord | None:
        raw = self.semantic_move_record
        if not raw:
            return None
        try:
            return SemanticMoveRecord.model_validate(raw)
        except Exception:
            return None

    def validated_social_state(self) -> SocialStateRecord | None:
        raw = self.social_state_record
        if not raw:
            return None
        try:
            return SocialStateRecord.model_validate(raw)
        except Exception:
            return None

    def validated_character_mind(self) -> CharacterMindRecord | None:
        raw = self.primary_character_mind
        if not raw:
            return None
        try:
            return CharacterMindRecord.model_validate(raw)
        except Exception:
            return None

    def validated_scene_plan(self) -> ScenePlanRecord | None:
        raw = self.scene_plan_record
        if not raw:
            return None
        try:
            return ScenePlanRecord.model_validate(raw)
        except Exception:
            return None


class SemanticPlannerSupportLevel(str, Enum):
    """Capability metadata only — gate truth remains ``DramaticEffectGateResult``."""

    full_goc = "full_goc"
    non_goc_waived = "non_goc_waived"
    module_unsupported = "module_unsupported"
