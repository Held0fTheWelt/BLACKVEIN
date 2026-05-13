from __future__ import annotations

from pathlib import Path

from app.content.module_loader import load_module
from app.content.module_models import ContentModule

from .models import CanonicalCompileOutput, RetrievalChunk, RetrievalCorpusSeed, ReviewExportSeed, RuntimeProjection


def _resolve_start_scene_id(module: ContentModule) -> str:
    if not module.scene_phases:
        raise ValueError(f"Module '{module.metadata.module_id}' has no scene phases.")
    return min(module.scene_phases.items(), key=lambda kv: kv[1].sequence)[0]


def _build_runtime_projection(module: ContentModule) -> RuntimeProjection:
    scenes: list[dict] = []
    for scene_id, phase in sorted(module.scene_phases.items(), key=lambda item: item[1].sequence):
        scenes.append(
            {
                "id": scene_id,
                "scene_id": scene_id,
                "name": phase.name,
                "sequence": phase.sequence,
                "description": phase.description,
                "content_focus": list(phase.content_focus),
                "engine_tasks": list(phase.engine_tasks),
                "active_triggers": list(phase.active_triggers),
                "enforced_constraints": list(phase.enforced_constraints or []),
                "turn_estimate": phase.turn_estimate,
                "exit_condition": phase.exit_condition,
            }
        )

    triggers: list[dict] = []
    for trigger_id, trigger in sorted(module.trigger_definitions.items()):
        triggers.append(
            {
                "trigger_id": trigger_id,
                "name": trigger.name,
                "active_in_phases": list(trigger.active_in_phases),
                "recognition_markers": list(trigger.recognition_markers),
                "character_vulnerability": dict(trigger.character_vulnerability),
                "escalation_impact": dict(trigger.escalation_impact),
            }
        )

    endings: list[dict] = []
    for ending_id, ending in sorted(module.ending_conditions.items()):
        endings.append(
            {
                "ending_id": ending_id,
                "title": ending.name,
                "description": ending.description,
                "conditions": ending.trigger_conditions,
                "outcome": dict(ending.outcome),
                "closure_action": list(ending.closure_action or []),
            }
        )

    relationship_axes: list[dict] = []
    for axis_id, axis in sorted(module.relationship_axes.items()):
        relationship_axes.append(
            {
                "axis_id": axis_id,
                "id": axis.id,
                "name": axis.name,
                "description": axis.description,
                "relationships": list(axis.relationships),
                "baseline": dict(axis.baseline),
                "escalation": dict(axis.escalation),
            }
        )

    relationships: list[dict] = []
    for rel_id, rel in sorted(module.relationship_definitions.items()):
        if isinstance(rel, dict):
            relationships.append({"relationship_id": rel_id, **rel})
        else:
            relationships.append({"relationship_id": rel_id, "value": rel})

    characters: list[dict] = []
    for character_id, character in sorted(module.characters.items()):
        characters.append(
            {
                "character_id": character_id,
                "id": character.id,
                "name": character.name,
                "role": character.role,
                "baseline_attitude": character.baseline_attitude,
                "extras": dict(character.extras),
            }
        )

    return RuntimeProjection(
        module_id=module.metadata.module_id,
        module_version=module.metadata.version,
        start_scene_id=_resolve_start_scene_id(module),
        scenes=scenes,
        triggers=triggers,
        endings=endings,
        relationship_axes=relationship_axes,
        relationships=relationships,
        escalation_axes=dict(module.escalation_axes),
        opening_scene_sequence=dict(module.opening_scene_sequence),
        hard_forbidden_rules=dict(module.hard_forbidden_rules),
        character_ids=sorted(module.characters.keys()),
        characters=characters,
        transition_hints=[
            {
                "from": transition.from_phase,
                "to": transition.to_phase,
                "trigger_conditions": list(transition.trigger_conditions),
                "engine_checks": list(transition.engine_checks),
                "transition_action": transition.transition_action,
            }
            for _, transition in sorted(module.phase_transitions.items())
        ],
    )


def _build_retrieval_seed(module: ContentModule) -> RetrievalCorpusSeed:
    chunks: list[RetrievalChunk] = []
    for scene_id, phase in sorted(module.scene_phases.items(), key=lambda item: item[1].sequence):
        chunks.append(
            RetrievalChunk(
                chunk_id=f"scene:{scene_id}",
                kind="scene",
                text=f"{phase.name}: {phase.description}",
                metadata={"scene_id": scene_id, "sequence": phase.sequence},
            )
        )
    for trigger_id, trigger in sorted(module.trigger_definitions.items()):
        chunks.append(
            RetrievalChunk(
                chunk_id=f"trigger:{trigger_id}",
                kind="trigger",
                text=f"{trigger.name}: {trigger.description}",
                metadata={"trigger_id": trigger_id, "active_in_phases": list(trigger.active_in_phases)},
            )
        )
    for ending_id, ending in sorted(module.ending_conditions.items()):
        chunks.append(
            RetrievalChunk(
                chunk_id=f"ending:{ending_id}",
                kind="ending",
                text=f"{ending.name}: {ending.description}",
                metadata={"ending_id": ending_id},
            )
        )
    return RetrievalCorpusSeed(
        module_id=module.metadata.module_id,
        module_version=module.metadata.version,
        chunks=chunks,
    )


def _build_review_export_seed(module: ContentModule, runtime_projection: RuntimeProjection) -> ReviewExportSeed:
    return ReviewExportSeed(
        module_id=module.metadata.module_id,
        module_version=module.metadata.version,
        summary={
            "title": module.metadata.title,
            "description": module.metadata.description,
            "character_count": len(module.characters),
            "scene_count": len(runtime_projection.scenes),
            "trigger_count": len(runtime_projection.triggers),
            "ending_count": len(runtime_projection.endings),
        },
        scenes=runtime_projection.scenes,
        triggers=runtime_projection.triggers,
        endings=runtime_projection.endings,
    )


def compile_loaded_module(module: ContentModule) -> CanonicalCompileOutput:
    runtime_projection = _build_runtime_projection(module)
    retrieval_corpus_seed = _build_retrieval_seed(module)
    review_export_seed = _build_review_export_seed(module, runtime_projection)
    return CanonicalCompileOutput(
        runtime_projection=runtime_projection,
        retrieval_corpus_seed=retrieval_corpus_seed,
        review_export_seed=review_export_seed,
    )


def compile_module(module_id: str, *, root_path: Path | None = None) -> CanonicalCompileOutput:
    module = load_module(module_id, root_path=root_path)
    return compile_loaded_module(module)
