from __future__ import annotations

from pathlib import Path

from app.content.module_loader import load_module
from app.content.module_models import ContentModule

from .models import CanonicalCompileOutput, RetrievalChunk, RetrievalCorpusSeed, ReviewExportSeed, RuntimeProjection


def _resolve_start_scene_id(module: ContentModule) -> str:
    scene_graph = module.scene_graph if isinstance(module.scene_graph, dict) else {}
    graph_start = str(scene_graph.get("default_start_node_id") or "").strip()
    if graph_start:
        return graph_start
    if not module.scene_phases:
        raise ValueError(f"Module '{module.metadata.module_id}' has no scene phases.")
    return min(module.scene_phases.items(), key=lambda kv: kv[1].sequence)[0]


def _build_runtime_projection(module: ContentModule) -> RuntimeProjection:
    scenes: list[dict] = []
    scene_graph = module.scene_graph if isinstance(module.scene_graph, dict) else {}
    graph_nodes = scene_graph.get("nodes") if isinstance(scene_graph.get("nodes"), list) else []
    if graph_nodes:
        phase_by_id = module.scene_phases
        sorted_nodes = sorted(
            [row for row in graph_nodes if isinstance(row, dict)],
            key=lambda row: int(row.get("sequence") or 0),
        )
        for node in sorted_nodes:
            scene_id = str(node.get("id") or "").strip()
            if not scene_id:
                continue
            phase_id = str(node.get("phase_id") or "").strip()
            phase = phase_by_id.get(phase_id)
            scenes.append(
                {
                    "id": scene_id,
                    "scene_id": scene_id,
                    "name": str(node.get("title") or scene_id),
                    "sequence": int(node.get("sequence") or len(scenes) + 1),
                    "description": str(node.get("summary") or ""),
                    "phase_id": phase_id or None,
                    "location_id": node.get("location_id"),
                    "scene_function": node.get("scene_function"),
                    "visibility": node.get("visibility"),
                    "required_event_ids": list(node.get("required_event_ids") or []),
                    "content_focus": list(phase.content_focus) if phase else [],
                    "engine_tasks": [str(node.get("scene_function") or "scene_node")] + (list(phase.engine_tasks) if phase else []),
                    "active_triggers": list(phase.active_triggers) if phase else [],
                    "enforced_constraints": list(phase.enforced_constraints or []) if phase else [],
                    "turn_estimate": phase.turn_estimate if phase else None,
                    "exit_condition": phase.exit_condition if phase else None,
                }
            )
    else:
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
                "actor_id": character.actor_id or character.runtime_actor_id or character.id,
                "runtime_actor_id": character.runtime_actor_id or character.actor_id or character.id,
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
        opening_quote_anchors=dict(module.opening_quote_anchors),
        hard_forbidden_rules=dict(module.hard_forbidden_rules),
        canonical_path=dict(module.canonical_path),
        modularity_policy=dict(module.modularity_policy),
        scene_graph=dict(module.scene_graph),
        locations=dict(module.locations),
        objects=dict(module.objects),
        content_access_policy=dict(module.content_access_policy),
        character_ids=sorted(module.characters.keys()),
        characters=characters,
        character_documents=dict(module.character_documents),
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


_KNOWLEDGE_CHUNK_PROFILES: tuple[dict[str, object], ...] = (
    {
        "field": "opening_scene_sequence",
        "source_path": "content/modules/{module_id}/knowledge/opening_scene_sequence.yaml",
        "content_kind": "opening_scene_sequence",
        "authority": "module_canonical",
        "use_for": ("opening_realization", "narrator_packet", "opening_event_coverage_gate"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "opening_quote_anchors",
        "source_path": "content/modules/{module_id}/knowledge/opening_quote_anchors.yaml",
        "content_kind": "opening_quote_anchors",
        "authority": "module_canonical",
        "use_for": ("opening_realization", "quote_anchor_policy", "scene_director_dramatic_parameters"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "hard_forbidden_rules",
        "source_path": "content/modules/{module_id}/knowledge/hard_forbidden_rules.yaml",
        "content_kind": "hard_forbidden_rules",
        "authority": "module_canonical",
        "use_for": ("hard_forbidden_gate", "narrator_packet", "validation_seam"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "premise_and_backstory",
        "source_path": "content/modules/{module_id}/knowledge/premise_and_backstory.yaml",
        "content_kind": "premise_and_backstory",
        "authority": "module_canonical",
        "use_for": ("opening_realization", "narrator_packet"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "narrator_sensory_palette",
        "source_path": "content/modules/{module_id}/knowledge/narrator_sensory_palette.yaml",
        "content_kind": "narrator_sensory_palette",
        "authority": "module_canonical",
        "use_for": ("narrator_packet", "scene_director_dramatic_parameters"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "apartment_layout",
        "source_path": "content/modules/{module_id}/locations/appartment_vallon/apartment_layout.yaml",
        "content_kind": "apartment_layout",
        "authority": "module_canonical",
        "use_for": ("affordance_resolution", "player_local_context"),
        "language": "en",
        "runtime_locale_available": True,
    },
    {
        "field": "actor_pressure_profiles",
        "source_path": "content/modules/{module_id}/characters/actor_pressure_profiles.yaml",
        "content_kind": "actor_pressure_profiles",
        "authority": "module_canonical",
        "use_for": ("scene_director_responder_selection", "narrator_packet"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "phase_beat_policy",
        "source_path": "content/modules/{module_id}/phase_beat_policy.yaml",
        "content_kind": "phase_beat_policy",
        "authority": "module_canonical",
        "use_for": ("scene_director_dramatic_parameters", "pacing_gate"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "canonical_path",
        "source_path": "content/modules/{module_id}/canonical_path/index.yaml",
        "content_kind": "canonical_path",
        "authority": "module_canonical",
        "use_for": ("opening_realization", "story_direction", "narrator_packet"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "modularity_policy",
        "source_path": "content/modules/{module_id}/knowledge/modularity_policy.yaml",
        "content_kind": "modularity_policy",
        "authority": "module_canonical",
        "use_for": ("content_authority_boundaries", "reference_integrity", "authoring_audit"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "scene_graph",
        "source_path": "content/modules/{module_id}/scene_graph.yaml",
        "content_kind": "scene_graph",
        "authority": "module_canonical",
        "use_for": ("scene_director_navigation", "retrieval_scene_context", "runtime_projection"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "locations",
        "source_path": "content/modules/{module_id}/locations/index.yaml",
        "content_kind": "locations",
        "authority": "module_canonical",
        "use_for": ("affordance_resolution", "scene_director_navigation", "player_local_context"),
        "language": "en",
        "runtime_locale_available": True,
    },
    {
        "field": "objects",
        "source_path": "content/modules/{module_id}/objects/index.yaml",
        "content_kind": "objects",
        "authority": "module_canonical",
        "use_for": ("object_authority", "symbolic_object_resonance", "narrator_packet"),
        "language": "en",
        "runtime_locale_available": True,
    },
    {
        "field": "content_access_policy",
        "source_path": "content/modules/{module_id}/knowledge/content_access_policy.yaml",
        "content_kind": "content_access_policy",
        "authority": "module_canonical",
        "use_for": ("hard_forbidden_gate", "affordance_resolution", "scene_director_navigation"),
        "language": "en",
        "runtime_locale_available": False,
    },
    {
        "field": "character_documents",
        "source_path": "content/modules/{module_id}/characters/*.yaml",
        "content_kind": "character_documents",
        "authority": "module_canonical",
        "use_for": ("character_mind", "character_voice", "scene_director_responder_selection"),
        "language": "en",
        "runtime_locale_available": False,
    },
)


def _knowledge_text_excerpt(field: str, payload: dict) -> str:
    """Produce a deterministic, bounded text excerpt for RAG indexing.

    The excerpt favours top-level mapping keys so retrieval can match by
    structural label without leaking full YAML into prompts.
    """
    if not isinstance(payload, dict) or not payload:
        return ""
    head_lines: list[str] = [f"{field}: structured runtime knowledge."]
    for key in list(payload.keys())[:12]:
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool)):
            head_lines.append(f"- {key}: {str(value)[:160]}")
        elif isinstance(value, list):
            head_lines.append(f"- {key}: list[{len(value)}]")
        elif isinstance(value, dict):
            inner_keys = ", ".join(list(value.keys())[:8])
            head_lines.append(f"- {key}: keys[{inner_keys}]")
    return "\n".join(head_lines)[:1200]


def _build_retrieval_seed(module: ContentModule) -> RetrievalCorpusSeed:
    chunks: list[RetrievalChunk] = []
    module_id = module.metadata.module_id
    scene_nodes = (
        module.scene_graph.get("nodes")
        if isinstance(module.scene_graph, dict) and isinstance(module.scene_graph.get("nodes"), list)
        else []
    )
    if scene_nodes:
        for node in sorted(
            [row for row in scene_nodes if isinstance(row, dict)],
            key=lambda row: int(row.get("sequence") or 0),
        ):
            scene_id = str(node.get("id") or "").strip()
            if not scene_id:
                continue
            chunks.append(
                RetrievalChunk(
                    chunk_id=f"scene_node:{scene_id}",
                    kind="scene",
                    text=f"{node.get('title') or scene_id}: {node.get('summary') or ''}",
                    metadata={
                        "scene_id": scene_id,
                        "sequence": node.get("sequence"),
                        "phase_id": node.get("phase_id"),
                        "location_id": node.get("location_id"),
                        "scene_function": node.get("scene_function"),
                        "source_path": f"content/modules/{module_id}/scene_graph.yaml",
                    },
                )
            )
    else:
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
    # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.3: index authored structured knowledge so
    # runtime, writers-room, and improvement retrievers can cite the canonical
    # source rather than rediscovering it through ad-hoc text matches.
    for profile in _KNOWLEDGE_CHUNK_PROFILES:
        field = str(profile["field"])
        payload = getattr(module, field, None)
        if not isinstance(payload, dict) or not payload:
            continue
        text = _knowledge_text_excerpt(field, payload)
        if not text:
            continue
        chunks.append(
            RetrievalChunk(
                chunk_id=f"knowledge:{field}",
                kind="knowledge",
                text=text,
                metadata={
                    "source_path": str(profile["source_path"]).format(module_id=module_id),
                    "content_kind": profile["content_kind"],
                    "authority": profile["authority"],
                    "use_for": list(profile["use_for"]),
                    "module_id": module_id,
                    "language": profile["language"],
                    "runtime_locale_available": bool(profile["runtime_locale_available"]),
                },
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
