"""Canonical serializable contract for bounded semantic move interpretation (GoC planner)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

InterpretationTraceStep = Literal[
    "normalize_input",
    "read_interpreted_signals",
    "score_feature_vector",
    "apply_priority_rules",
    "emit_record",
]

SEMANTIC_MOVE_TYPES: frozenset[str] = frozenset(
    {
        "off_scope_containment",
        "silence_withdrawal",
        "repair_attempt",
        "direct_accusation",
        "indirect_provocation",
        "evasive_deflection",
        "humiliating_exposure",
        "alliance_reposition",
        "probe_inquiry",
        "escalation_threat",
        "reveal_surface",
        "establish_situational_pressure",
        "competing_repair_and_reveal",
    }
)

SocialMoveFamily = Literal[
    "attack",
    "repair",
    "probe",
    "deflect",
    "expose",
    "withdraw",
    "alliance",
    "escalate",
    "reveal",
    "neutral",
]

Directness = Literal["direct", "indirect", "ambiguous"]

SceneRiskBand = Literal["low", "moderate", "high"]


class InterpretationTraceItem(BaseModel):
    """Structured trace step — no free-form narrative truth."""

    step_id: InterpretationTraceStep
    detail_code: str = Field(
        ...,
        description="Bounded machine-readable code (e.g. rule:direct_accusation_synset_hit).",
    )


class SemanticMoveRecord(BaseModel):
    """Planner-facing semantic move — deterministic for fixed inputs on the GoC path."""

    model_config = {"extra": "forbid"}

    move_type: str = Field(..., description="Semantic move label; must be in SEMANTIC_MOVE_TYPES for GoC.")
    social_move_family: SocialMoveFamily
    target_actor_hint: str | None = Field(
        default=None,
        description="Optional addressee hint from named entities or structural cues; not engine truth.",
    )
    directness: Directness
    pressure_tactic: str | None = Field(
        default=None,
        description="Bounded tactic label (e.g. dignity_strike, civility_challenge).",
    )
    scene_risk_band: SceneRiskBand
    interpretation_trace: list[InterpretationTraceItem] = Field(default_factory=list)
    interpreter_kind: str | None = Field(default=None, description="Echo of interpreted_input.kind for audit.")
    feature_snapshot: dict[str, bool | int | str] = Field(
        default_factory=dict,
        description="Deterministic feature flags used by priority rules (bounded keys).",
    )

    def to_runtime_dict(self) -> dict:
        return self.model_dump(mode="json")
