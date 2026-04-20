"""Planner-canonical scene plan record — advisory until validation/commit; not committed_result."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScenePlanRecord(BaseModel):
    """Canonical planner-facing selection surface for scene function, responder, pacing within the graph."""

    model_config = {"extra": "forbid"}

    planner_schema_version: str = Field(default="goc_semantic_planner_v1")
    selected_scene_function: str
    selected_responder_set: list[dict[str, Any]]
    pacing_mode: str
    silence_brevity_decision: dict[str, Any]
    planner_rationale_codes: list[str] = Field(
        default_factory=list,
        description="Bounded codes explaining selection (no free prose).",
    )
    semantic_move_fingerprint: str = ""
    social_state_fingerprint: str = ""
    selection_source: str = Field(
        default="semantic_pipeline_v1",
        description="semantic_pipeline_v1 | legacy_fallback — compatibility trace only for legacy.",
    )

    def to_runtime_dict(self) -> dict:
        return self.model_dump(mode="json")
