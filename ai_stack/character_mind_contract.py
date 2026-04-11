"""Canonical CharacterMind tactical identity records with explicit provenance (GoC planner)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FieldProvenanceSource = Literal["authored", "authored_derived", "fallback_default"]


class FieldProvenance(BaseModel):
    model_config = {"extra": "forbid"}

    source: FieldProvenanceSource
    derivation_key: str | None = Field(
        default=None,
        description="When authored_derived: stable key for the derivation rule.",
    )


class CharacterMindRecord(BaseModel):
    """Tactical identity for one character — no LLM-invented psychology."""

    model_config = {"extra": "forbid"}

    character_key: str = Field(..., description="Slice key: veronique, michel, annette, alain.")
    runtime_actor_id: str = Field(
        ...,
        description="Engine actor id e.g. veronique_vallon.",
    )
    formal_role_label: str = Field(default="")
    tactical_posture: str = Field(
        default="",
        description="Bounded tactical label derived from authored slice.",
    )
    pressure_response_bias: str = Field(
        default="",
        description="Bounded bias label for responder selection under pressure.",
    )
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)

    def to_runtime_dict(self) -> dict:
        return self.model_dump(mode="json")
