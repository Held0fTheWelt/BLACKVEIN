"""
Canonical CharacterMind tactical identity records with explicit
provenance (GoC planner).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FieldProvenanceSource = Literal["authored", "authored_derived", "fallback_default"]


class FieldProvenance(BaseModel):
    """``FieldProvenance`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    model_config = {"extra": "forbid"}

    source: FieldProvenanceSource
    derivation_key: str | None = Field(
        default=None,
        description="When authored_derived: stable key for the derivation rule.",
    )


class CharacterMindRecord(BaseModel):
    """Tactical identity for one character — no LLM-invented psychology."""

    model_config = {"extra": "forbid"}

    character_key: str = Field(..., description="Module-defined character slice key.")
    runtime_actor_id: str = Field(
        ...,
        description="Engine actor id resolved from module policy.",
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
        """``to_runtime_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict:
                Returns a value of type ``dict``; see the function body for structure, error paths, and sentinels.
        """
        return self.model_dump(mode="json")
