"""Typed package and packet contracts for narrative governance runtime."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NarrativePackageManifest(BaseModel):
    """Immutable package metadata loaded by world-engine."""

    module_id: str
    package_version: str
    source_revision: str
    build_created_at: str
    build_id: str
    policy_profile: str
    included_scenes: list[str] = Field(default_factory=list)
    included_actors: list[str] = Field(default_factory=list)
    trigger_map_version: str
    legality_table_version: str
    package_schema_version: str
    build_status: str
    validation_status: str


class SceneFallbackBundle(BaseModel):
    """Explicit fallback notices for blocked live turns."""

    safe_reactions: dict[str, str] = Field(default_factory=dict)
    stall_phrases: list[str] = Field(default_factory=list)
    redirect_phrases: list[str] = Field(default_factory=list)
    generic_safe_line: str = "Fallback: turn generation was blocked; no substitute narration was committed."


class NarrativePackage(BaseModel):
    """Compiled package payload consumed at runtime."""

    manifest: NarrativePackageManifest
    system_directive: str
    scene_constraints: dict[str, dict[str, object]] = Field(default_factory=dict)
    scene_guidance: dict[str, dict[str, object]] = Field(default_factory=dict)
    actor_minds: dict[str, dict[str, object]] = Field(default_factory=dict)
    voice_rules: dict[str, dict[str, object]] = Field(default_factory=dict)
    trigger_map: dict[str, list[str]] = Field(default_factory=dict)
    legality_tables: dict[str, dict[str, object]] = Field(default_factory=dict)
    policy_layers: dict[str, dict[str, object]] = Field(default_factory=dict)
    scene_fallbacks: dict[str, SceneFallbackBundle] = Field(default_factory=dict)


class NarrativeDirectorScenePacket(BaseModel):
    """Typed packet contract passed into turn generation."""

    module_id: str
    package_version: str
    scene_id: str
    phase_id: str
    turn_number: int
    player_input: str
    selected_scene_function: str
    pacing_mode: str
    responder_set: list[dict[str, object]] = Field(default_factory=list)
    active_threads: list[dict[str, object]] = Field(default_factory=list)
    scene_constraints: dict[str, object] = Field(default_factory=dict)
    scene_guidance: dict[str, object] = Field(default_factory=dict)
    actor_minds: dict[str, dict[str, object]] = Field(default_factory=dict)
    voice_rules: dict[str, dict[str, object]] = Field(default_factory=dict)
    legality_table: dict[str, object] = Field(default_factory=dict)
    effective_policy: dict[str, object] = Field(default_factory=dict)
    output_schema_version: str = "runtime_turn_v2"
