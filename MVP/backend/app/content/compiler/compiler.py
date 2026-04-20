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
                "scene_id": scene_id,
                "name": phase.name,
                "sequence": phase.sequence,
                "description": phase.description,
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
            }
        )

    return RuntimeProjection(
        module_id=module.metadata.module_id,
        module_version=module.metadata.version,
        start_scene_id=_resolve_start_scene_id(module),
        scenes=scenes,
        triggers=triggers,
        endings=endings,
        character_ids=sorted(module.characters.keys()),
        transition_hints=[
            {"from": transition.from_phase, "to": transition.to_phase}
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
