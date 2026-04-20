"""Explicit bounded social-state projection for planner use (derived only, not world truth)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SocialStateRecord(BaseModel):
    """Consolidates continuity, threads, and scene-pressure signals for the planner."""

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

    def to_runtime_dict(self) -> dict:
        return self.model_dump(mode="json")
