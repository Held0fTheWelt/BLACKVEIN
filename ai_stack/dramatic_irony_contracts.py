"""Bounded Pi16 dramatic-irony contracts.

These contracts describe audience/actor knowledge asymmetry without making
hidden intent directly narratable. Runtime builders may select an opportunity,
but validation still controls whether a visible realization obeys the surface
policy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


DRAMATIC_IRONY_SCHEMA_VERSION = "dramatic_irony.v1"
DRAMATIC_IRONY_ASPECT_VERSION = "dramatic_irony_aspect.v1"

DRAMATIC_IRONY_STATUS_NOT_APPLICABLE = "not_applicable"
DRAMATIC_IRONY_STATUS_NO_OPPORTUNITY = "no_opportunity"
DRAMATIC_IRONY_STATUS_SELECTED = "selected"

DRAMATIC_IRONY_REALIZATION_NOT_EVALUATED = "not_evaluated"
DRAMATIC_IRONY_REALIZATION_SELECTED_ONLY = "selected_only"
DRAMATIC_IRONY_REALIZATION_REALIZED = "realized"
DRAMATIC_IRONY_REALIZATION_REJECTED = "rejected"

DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED = "npc_private_plan_selected"

DRAMATIC_IRONY_SURFACE_BEHAVIORAL_ECHO = "behavioral_echo"
DRAMATIC_IRONY_SURFACE_MISREAD_REACTION = "misread_reaction"
DRAMATIC_IRONY_SURFACE_WITHHELD_CONTEXT = "withheld_context"
DRAMATIC_IRONY_SURFACE_SUBTEXT_PRESSURE = "subtext_pressure"
DRAMATIC_IRONY_SURFACE_DIRECT_REVEAL = "direct_hidden_intent_reveal"
DRAMATIC_IRONY_SURFACE_OMNISCIENT_REVEAL = "omniscient_reveal"

DRAMATIC_IRONY_CONTEXT_VISIBILITY_BOUNDED_SURFACE_ONLY = "bounded_surface_only"
DRAMATIC_IRONY_RECOVERY_BEHAVIOR_RECOVER = "recover"
DRAMATIC_IRONY_RECOVERY_BEHAVIOR_REJECT = "reject"

DRAMATIC_IRONY_VIOLATION_FORBIDDEN_SURFACE_MODE = "dramatic_irony_forbidden_surface_mode"
DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO = "dramatic_irony_hidden_fact_echo"

DEFAULT_DRAMATIC_IRONY_ALLOWED_SOURCES: tuple[str, ...] = (
    DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
)
DEFAULT_DRAMATIC_IRONY_ALLOWED_SURFACE_MODES: tuple[str, ...] = (
    DRAMATIC_IRONY_SURFACE_BEHAVIORAL_ECHO,
    DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
    DRAMATIC_IRONY_SURFACE_WITHHELD_CONTEXT,
    DRAMATIC_IRONY_SURFACE_SUBTEXT_PRESSURE,
)
DEFAULT_DRAMATIC_IRONY_FORBIDDEN_SURFACE_MODES: tuple[str, ...] = (
    DRAMATIC_IRONY_SURFACE_DIRECT_REVEAL,
    DRAMATIC_IRONY_SURFACE_OMNISCIENT_REVEAL,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: Any) -> list[str]:
    raw = values if isinstance(values, (list, tuple, set)) else [values]
    out: list[str] = []
    for value in raw:
        text = _clean_text(value)
        if text and text not in out:
            out.append(text)
    return out


def default_dramatic_irony_policy() -> dict[str, Any]:
    """Return the neutral default Pi16 surface policy."""
    return {
        "schema_version": DRAMATIC_IRONY_SCHEMA_VERSION,
        "enabled": True,
        "allowed_sources": list(DEFAULT_DRAMATIC_IRONY_ALLOWED_SOURCES),
        "allowed_surface_modes": list(DEFAULT_DRAMATIC_IRONY_ALLOWED_SURFACE_MODES),
        "forbidden_surface_modes": list(DEFAULT_DRAMATIC_IRONY_FORBIDDEN_SURFACE_MODES),
        "max_opportunities": 3,
        "direct_reveal_allowed": False,
        "model_context_visibility": DRAMATIC_IRONY_CONTEXT_VISIBILITY_BOUNDED_SURFACE_ONLY,
        "require_structured_realization": True,
        "recovery_behavior": DRAMATIC_IRONY_RECOVERY_BEHAVIOR_RECOVER,
        "hidden_fact_echo_check": True,
    }


def normalize_dramatic_irony_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe shape."""
    raw = policy if isinstance(policy, dict) else {}
    default = default_dramatic_irony_policy()
    allowed_sources = _dedupe_strings(raw.get("allowed_sources")) or list(
        DEFAULT_DRAMATIC_IRONY_ALLOWED_SOURCES
    )
    allowed_surface_modes = _dedupe_strings(raw.get("allowed_surface_modes")) or list(
        DEFAULT_DRAMATIC_IRONY_ALLOWED_SURFACE_MODES
    )
    forbidden_surface_modes = _dedupe_strings(raw.get("forbidden_surface_modes")) or list(
        DEFAULT_DRAMATIC_IRONY_FORBIDDEN_SURFACE_MODES
    )
    try:
        max_opportunities = int(raw.get("max_opportunities", default["max_opportunities"]))
    except (TypeError, ValueError):
        max_opportunities = int(default["max_opportunities"])
    max_opportunities = max(1, min(max_opportunities, 8))
    return {
        "schema_version": _clean_text(raw.get("schema_version"))
        or DRAMATIC_IRONY_SCHEMA_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "allowed_sources": allowed_sources,
        "allowed_surface_modes": [
            mode
            for mode in allowed_surface_modes
            if mode not in set(forbidden_surface_modes)
        ],
        "forbidden_surface_modes": forbidden_surface_modes,
        "max_opportunities": max_opportunities,
        "direct_reveal_allowed": bool(raw.get("direct_reveal_allowed", False)),
        "model_context_visibility": _clean_text(raw.get("model_context_visibility"))
        or DRAMATIC_IRONY_CONTEXT_VISIBILITY_BOUNDED_SURFACE_ONLY,
        "require_structured_realization": bool(
            raw.get("require_structured_realization", True)
        ),
        "recovery_behavior": _clean_text(raw.get("recovery_behavior"))
        or DRAMATIC_IRONY_RECOVERY_BEHAVIOR_RECOVER,
        "hidden_fact_echo_check": bool(raw.get("hidden_fact_echo_check", True)),
    }


class KnowledgeFact(BaseModel):
    """Bounded fact known to the player/audience and not every actor."""

    model_config = {"extra": "forbid"}

    fact_id: str
    summary: str
    source: str
    truth_status: str = "bounded_runtime"
    visible_to_player: bool = False
    known_by_actor_ids: list[str] = Field(default_factory=list)
    unknown_to_actor_ids: list[str] = Field(default_factory=list)
    relevance_tags: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("known_by_actor_ids", "unknown_to_actor_ids", "relevance_tags", mode="before")
    @classmethod
    def _dedupe_list(cls, value: Any) -> list[str]:
        return _dedupe_strings(value)


class DramaticIronyOpportunity(BaseModel):
    """One permitted use of knowledge asymmetry for a future visible beat."""

    model_config = {"extra": "forbid"}

    opportunity_id: str
    fact_id: str
    ignorant_actor_id: str
    scene_relevance: str = "moderate"
    risk_band: str = "moderate"
    allowed_surface_mode: str = DRAMATIC_IRONY_SURFACE_MISREAD_REACTION
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    @field_validator("rationale_codes", mode="before")
    @classmethod
    def _dedupe_codes(cls, value: Any) -> list[str]:
        return _dedupe_strings(value)


class DramaticIronyRealization(BaseModel):
    """Validation result for the model's visible use of selected opportunities."""

    model_config = {"extra": "forbid"}

    status: str = DRAMATIC_IRONY_REALIZATION_NOT_EVALUATED
    selected_opportunity_id: str | None = None
    realized_opportunity_ids: list[str] = Field(default_factory=list)
    surface_mode: str | None = None
    visible_text_refs: list[str] = Field(default_factory=list)
    visible_anchor_refs: list[str] = Field(default_factory=list)
    violation_codes: list[str] = Field(default_factory=list)
    leak_blocked: bool = False
    contract_pass: bool = True
    surface_mode_contract_pass: bool = True
    hidden_fact_echo_absent: bool = True
    unused_selected_opportunity_ids: list[str] = Field(default_factory=list)

    @field_validator(
        "realized_opportunity_ids",
        "visible_text_refs",
        "visible_anchor_refs",
        "violation_codes",
        "unused_selected_opportunity_ids",
        mode="before",
    )
    @classmethod
    def _dedupe_values(cls, value: Any) -> list[str]:
        return _dedupe_strings(value)


class DramaticIronyRecord(BaseModel):
    """Planner-owned Pi16 record for one turn."""

    model_config = {"extra": "forbid"}

    schema_version: str = DRAMATIC_IRONY_SCHEMA_VERSION
    aspect_version: str = DRAMATIC_IRONY_ASPECT_VERSION
    policy: dict[str, Any] = Field(default_factory=default_dramatic_irony_policy)
    facts: list[KnowledgeFact] = Field(default_factory=list)
    opportunities: list[DramaticIronyOpportunity] = Field(default_factory=list)
    selected_opportunity_ids: list[str] = Field(default_factory=list)
    realization: DramaticIronyRealization = Field(default_factory=DramaticIronyRealization)
    status: str = DRAMATIC_IRONY_STATUS_NOT_APPLICABLE
    rationale_codes: list[str] = Field(default_factory=list)

    @field_validator("selected_opportunity_ids", "rationale_codes", mode="before")
    @classmethod
    def _dedupe_runtime_values(cls, value: Any) -> list[str]:
        return _dedupe_strings(value)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
