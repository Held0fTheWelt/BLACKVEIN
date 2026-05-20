"""
Planner-canonical scene plan record — advisory until validation/commit;
not committed_result.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import TRANSITION_PATTERNS


class ScenePlanRecord(BaseModel):
    """Canonical planner-facing selection surface for scene function,
    responder, pacing within the graph.
    """

    model_config = {"extra": "forbid"}

    planner_schema_version: str = Field(default="goc_semantic_planner_v1")
    selected_scene_function: str
    selected_responder_set: list[dict[str, Any]]
    pacing_mode: str
    silence_brevity_decision: dict[str, Any]
    narrative_scene_function: str = Field(
        default="",
        description="Richer narrative function selected by the scene director; advisory realization intent.",
    )
    realization_mode: str = Field(
        default="",
        description="Bounded realization channel such as narration, npc action, dialogue, or mixed setup.",
    )
    pressure_function: str = Field(
        default="",
        description="Optional pressure-specific function; may be none when the scene target is non-pressure.",
    )
    scene_target: dict[str, Any] = Field(
        default_factory=dict,
        description="General director target for the turn; replaces pressure_target as the broad concept.",
    )
    pressure_target: dict[str, Any] = Field(
        default_factory=dict,
        description="Compatibility alias for pressure-oriented target data; advisory until validation/commit.",
    )
    target_obligations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Director obligations that make the target playable and validation-safe.",
    )
    actor_directives: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Bounded NPC/director directives such as stage presence, force reaction, or hold silence.",
    )
    dramatic_beats: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Bounded immediate beat objects selected for realization; no prose oracle.",
    )
    handover_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="How the director returns control or affordance to the player after the planned beats.",
    )
    content_frame: dict[str, Any] = Field(
        default_factory=dict,
        description="Canonical content slice selected for this turn: path step, scene node, objects, location, quote anchors, and access decisions.",
    )
    speech_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Director decision for whether NPC speech is required, recommended, or suppressed for the selected content frame.",
    )
    quote_moment_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Moment-locked quote policy; exact quote anchors are rare and must satisfy the listed requirements.",
    )
    dialogue_plan: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered content-guided NPC speech beats selected by the director.",
    )
    capability_manager_plan: dict[str, Any] = Field(
        default_factory=dict,
        description="Director-selected capability gate: which runtime dramatic capabilities should run for this turn.",
    )
    continuity_obligation: dict[str, Any] = Field(
        default_factory=dict,
        description="Planner-facing continuity carry obligation; does not commit world truth.",
    )
    expected_transition_pattern: str = Field(
        default="soft",
        description="Expected transition pattern from the canonical GoC transition vocabulary.",
    )
    planner_rationale_codes: list[str] = Field(
        default_factory=list,
        description="Bounded codes explaining selection (no free prose).",
    )
    semantic_move_fingerprint: str = ""
    social_state_fingerprint: str = ""
    semantic_scene_planner_version: str = ""
    selection_source: str = Field(
        default="semantic_pipeline_v1",
        description="semantic_pipeline_v1 | structural_fallback — diagnostic trace only.",
    )

    @field_validator("expected_transition_pattern")
    @classmethod
    def _expected_transition_pattern_in_contract(cls, value: str) -> str:
        if value not in TRANSITION_PATTERNS:
            raise ValueError(f"Invalid expected_transition_pattern: {value!r}")
        return value

    def to_runtime_dict(self) -> dict:
        """``to_runtime_dict`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            dict:
                Returns a value of type ``dict``; see the function body for structure, error paths, and sentinels.
        """
        return self.model_dump(mode="json")
