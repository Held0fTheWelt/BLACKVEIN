"""
Explicit bounded social-state projection for planner use (derived only,
not world truth).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SocialStateRecord(BaseModel):
    """Consolidates continuity, threads, and scene-pressure signals for the
    planner.
    """

    model_config = {"extra": "forbid"}

    prior_continuity_classes: list[str] = Field(default_factory=list)
    scene_pressure_state: str = Field(default="moderate_tension")
    active_thread_count: int = Field(default=0, ge=0, le=256)
    thread_pressure_summary_present: bool = False
    guidance_phase_key: str | None = None
    responder_asymmetry_code: str = Field(
        default="neutral",
        description="Bounded code derived from continuity + phase (e.g. blame_on_host_spouse).",
    )
    social_risk_band: str = Field(default="moderate", description="low|moderate|high")
    prior_social_state_fingerprint: str | None = Field(
        default=None,
        description="Fingerprint of the previously committed social-state record, if rehydrated.",
    )
    prior_social_risk_band: str | None = Field(
        default=None,
        description="Risk band from the previously committed social-state record, if available.",
    )
    social_continuity_status: str = Field(
        default="initial_social_state",
        description="initial_social_state|stable_prior_social_state|social_state_shifted",
    )
    relationship_pressure_codes: list[str] = Field(
        default_factory=list,
        description="Bounded relationship-pressure codes derived from social state and canonical axes.",
    )
    active_relationship_axis_ids: list[str] = Field(
        default_factory=list,
        description="Canonical relationship axis ids currently implicated by the social-state projection.",
    )
    dominant_relationship_axis_id: str | None = Field(
        default=None,
        description="First active relationship axis id, when any canonical axis is implicated.",
    )

    def to_runtime_dict(self) -> dict:
        """``to_runtime_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict:
                Returns a value of type ``dict``; see the function body for structure, error paths, and sentinels.
        """
        return self.model_dump(mode="json")
