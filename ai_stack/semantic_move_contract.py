"""
Canonical serializable contract for bounded semantic move interpretation
(planner-facing).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

InterpretationTraceStep = Literal[
    "normalize_input",
    "read_interpreted_signals",
    "read_ai_semantic_move",
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

SUBTEXT_SURFACE_MODES: frozenset[str] = frozenset(
    {
        "accusation",
        "apology",
        "alliance_bid",
        "courtesy",
        "deflection",
        "escalation",
        "exposure",
        "neutral",
        "off_scope",
        "question",
        "reveal",
        "silence",
    }
)

SUBTEXT_HIDDEN_INTENT_HYPOTHESES: frozenset[str] = frozenset(
    {
        "avoid_accountability",
        "force_accountability",
        "force_admission",
        "humiliate_or_expose",
        "preserve_relationship",
        "raise_pressure",
        "seek_alliance",
        "seek_repair",
        "slice_boundary",
        "test_boundary",
        "test_motive",
        "unknown",
    }
)

SUBTEXT_FUNCTIONS: frozenset[str] = frozenset(
    {
        "contain_off_scope",
        "deflect_accountability",
        "expose_truth",
        "force_accountability",
        "preserve_dignity",
        "preserve_relationship",
        "probe_motive",
        "raise_pressure",
        "reveal_under_repair",
        "shift_alliance",
        "test_boundary",
        "unset",
    }
)

SincerityBand = Literal["high", "low", "mixed", "unknown"]


def _require_member(value: str, allowed: frozenset[str], field_name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
    return value


class SubtextRecord(BaseModel):
    """Bounded Pi19 surface-vs-intent projection; diagnostic, not truth."""

    model_config = {"extra": "forbid"}

    contract: str = "subtext_interpretation.v1"
    surface_mode: str
    explicit_intent: str | None = None
    hidden_intent_hypothesis: str
    subtext_function: str
    sincerity_band: SincerityBand = "unknown"
    evidence_codes: list[str] = Field(
        default_factory=list,
        description="Bounded semantic evidence codes; no prose oracle.",
    )
    policy_source: str = ""
    policy_rule_id: str = ""

    @field_validator("surface_mode")
    @classmethod
    def _surface_mode_in_contract(cls, value: str) -> str:
        return _require_member(value, SUBTEXT_SURFACE_MODES, "surface_mode")

    @field_validator("hidden_intent_hypothesis")
    @classmethod
    def _hidden_intent_in_contract(cls, value: str) -> str:
        return _require_member(
            value,
            SUBTEXT_HIDDEN_INTENT_HYPOTHESES,
            "hidden_intent_hypothesis",
        )

    @field_validator("subtext_function")
    @classmethod
    def _subtext_function_in_contract(cls, value: str) -> str:
        return _require_member(value, SUBTEXT_FUNCTIONS, "subtext_function")


class InterpretationTraceItem(BaseModel):
    """Structured trace step — no free-form narrative truth."""

    step_id: InterpretationTraceStep
    detail_code: str = Field(
        ...,
        description="Bounded machine-readable code for semantic payload/runtime-signal audit.",
    )


class RankedMoveCandidate(BaseModel):
    """Bounded ranked candidate emitted by semantic interpretation."""

    move_type: str
    social_move_family: SocialMoveFamily
    directness: Directness
    pressure_tactic: str | None = None
    scene_risk_band: SceneRiskBand
    rank: int
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI-provided or runtime fallback confidence-like ordering score for audit and packet handoff.",
    )
    trace_detail: str

    @field_validator("move_type")
    @classmethod
    def _move_type_in_contract(cls, value: str) -> str:
        if value not in SEMANTIC_MOVE_TYPES:
            raise ValueError(f"Invalid semantic move type: {value!r}")
        return value


class SemanticMoveRecord(BaseModel):
    """Planner-facing semantic move from bounded AI semantics and runtime signals."""

    model_config = {"extra": "forbid"}

    move_type: str = Field(..., description="Semantic move label; must be in SEMANTIC_MOVE_TYPES.")
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
        description="Bounded semantic adapter flags and runtime signals.",
    )
    ranked_move_candidates: list[RankedMoveCandidate] = Field(
        default_factory=list,
        description="Primary-first ranked interpretation candidates from AI semantic resolution.",
    )
    secondary_move_type: str | None = Field(
        default=None,
        description="Optional secondary move candidate preserved for downstream dramatic generation.",
    )
    secondary_dramatic_features: list[str] = Field(
        default_factory=list,
        description="Bounded secondary dramatic feature labels derived from sparse/evasive/provocation signals.",
    )
    subtext: SubtextRecord | None = Field(
        default=None,
        description="Bounded surface-vs-intent diagnostic projection for Pi19.",
    )

    @field_validator("move_type")
    @classmethod
    def _move_type_in_contract(cls, value: str) -> str:
        if value not in SEMANTIC_MOVE_TYPES:
            raise ValueError(f"Invalid semantic move type: {value!r}")
        return value

    @field_validator("secondary_move_type")
    @classmethod
    def _secondary_move_type_in_contract(cls, value: str | None) -> str | None:
        if value is not None and value not in SEMANTIC_MOVE_TYPES:
            raise ValueError(f"Invalid secondary semantic move type: {value!r}")
        return value

    def to_runtime_dict(self) -> dict:
        """``to_runtime_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict:
                Returns a value of type ``dict``; see the function body for structure, error paths, and sentinels.
        """
        return self.model_dump(mode="json")
