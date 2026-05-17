"""Entity-level retrieval chunk builders (one chunk per authoritative unit)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.content.module_models import ContentModule
from story_runtime_core.director_surface_hints import load_module_director_surface_hints

from .models import RetrievalChunk
from . import retrieval_text


def _unwrap_root(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        inner = payload.get(key)
        if isinstance(inner, dict):
            return inner
    return payload


def _locations_inner(module: ContentModule) -> dict[str, Any]:
    loc = module.locations if isinstance(module.locations, dict) else {}
    return _unwrap_root(loc, "locations")


def _objects_inner(module: ContentModule) -> dict[str, Any]:
    objects = module.objects if isinstance(module.objects, dict) else {}
    return _unwrap_root(objects, "objects")


def _canonical_path_inner(module: ContentModule) -> dict[str, Any]:
    canonical = module.canonical_path if isinstance(module.canonical_path, dict) else {}
    return _unwrap_root(canonical, "canonical_path")


def _apartment_layout_inner(module: ContentModule) -> dict[str, Any]:
    layout = module.apartment_layout if isinstance(module.apartment_layout, dict) else {}
    return _unwrap_root(layout, "apartment_layout")


def _place_source_path_map(module: ContentModule, module_id: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    inner = _locations_inner(module)
    prefix = f"content/modules/{module_id}/"
    for rel in inner.get("place_files") or []:
        rel_path = str(rel).strip().replace("\\", "/")
        if not rel_path:
            continue
        place_id = Path(rel_path).stem
        mapping[place_id] = prefix + rel_path.lstrip("/")
    layout = _apartment_layout_inner(module)
    room_files = layout.get("room_location_files")
    if isinstance(room_files, dict):
        for room_id, rel in room_files.items():
            rel_path = str(rel).strip().replace("\\", "/")
            if rel_path:
                mapping.setdefault(str(room_id).strip(), prefix + rel_path.lstrip("/"))
    return mapping


def _base_metadata(
    module_id: str,
    *,
    content_kind: str,
    source_path: str,
    use_for: tuple[str, ...],
    entity_id: str | None = None,
    runtime_language_adapter_available: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "module_id": module_id,
        "authority": "module_canonical",
        "language": "en",
        "content_kind": content_kind,
        "source_path": source_path,
        "use_for": list(use_for),
        "runtime_language_adapter_available": runtime_language_adapter_available,
    }
    if entity_id:
        metadata["entity_id"] = entity_id
    metadata.update(extra)
    return metadata


def _make_chunk(
    *,
    kind: str,
    chunk_id: str,
    text: str,
    metadata: dict[str, Any],
) -> RetrievalChunk | None:
    if not text.strip():
        return None
    return RetrievalChunk(chunk_id=chunk_id, kind=kind, text=text, metadata=metadata)


def chunks_from_places(module: ContentModule) -> list[RetrievalChunk]:
    module_id = module.metadata.module_id
    source_paths = _place_source_path_map(module, module_id)
    chunks: list[RetrievalChunk] = []
    places = _locations_inner(module).get("places")
    if not isinstance(places, list):
        return chunks
    for place in sorted(
        [row for row in places if isinstance(row, dict)],
        key=lambda row: str(row.get("id") or ""),
    ):
        place_id = str(place.get("id") or "").strip()
        if not place_id:
            continue
        source_path = source_paths.get(place_id) or f"content/modules/{module_id}/locations/{place_id}.yaml"
        text = retrieval_text.format_location(place)
        chunk = _make_chunk(
            kind="location",
            chunk_id=f"location:{place_id}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="location",
                source_path=source_path,
                entity_id=place_id,
                use_for=("affordance_resolution", "scene_director_navigation", "player_local_context"),
                runtime_language_adapter_available=True,
                playable_access=place.get("playable_access"),
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def chunks_from_apartment_topology(module: ContentModule) -> list[RetrievalChunk]:
    module_id = module.metadata.module_id
    layout = _apartment_layout_inner(module)
    source_path = f"content/modules/{module_id}/locations/appartment_vallon/apartment_layout.yaml"
    rooms = layout.get("rooms")
    if not isinstance(rooms, list):
        return []
    chunks: list[RetrievalChunk] = []
    for room in sorted(
        [row for row in rooms if isinstance(row, dict)],
        key=lambda row: str(row.get("id") or ""),
    ):
        room_id = str(room.get("id") or "").strip()
        if not room_id:
            continue
        text = retrieval_text.format_location_topology(room)
        chunk = _make_chunk(
            kind="location_topology",
            chunk_id=f"location_topology:{room_id}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="location_topology",
                source_path=source_path,
                entity_id=room_id,
                use_for=("affordance_resolution", "player_local_context"),
                runtime_language_adapter_available=True,
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def chunks_from_object_documents(module: ContentModule) -> list[RetrievalChunk]:
    module_id = module.metadata.module_id
    documents = _objects_inner(module).get("object_documents")
    if not isinstance(documents, dict):
        return []
    chunks: list[RetrievalChunk] = []
    for object_id, obj in sorted(documents.items(), key=lambda item: str(item[0])):
        if not isinstance(obj, dict):
            continue
        entity_id = str(obj.get("id") or object_id).strip()
        if not entity_id:
            continue
        source_ref = str(obj.get("source_ref") or "").strip().replace("\\", "/")
        source_path = (
            f"content/modules/{module_id}/{source_ref}"
            if source_ref
            else f"content/modules/{module_id}/objects/{entity_id}.yaml"
        )
        text = retrieval_text.format_object(obj)
        chunk = _make_chunk(
            kind="object",
            chunk_id=f"object:{entity_id}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="object",
                source_path=source_path,
                entity_id=entity_id,
                use_for=("object_authority", "symbolic_object_resonance", "narrator_packet"),
                runtime_language_adapter_available=True,
                placement_location_id=obj.get("placement_location_id"),
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def chunks_from_character_documents(module: ContentModule) -> list[RetrievalChunk]:
    module_id = module.metadata.module_id
    chunks: list[RetrievalChunk] = []
    for char_id, doc in sorted(module.character_documents.items(), key=lambda item: str(item[0])):
        if not isinstance(doc, dict):
            continue
        entity_id = str(doc.get("canonical_id") or doc.get("id") or char_id).strip()
        if not entity_id:
            continue
        source_path = f"content/modules/{module_id}/characters/definitions/{char_id}.yaml"
        text = retrieval_text.format_character(doc)
        chunk = _make_chunk(
            kind="character",
            chunk_id=f"character:{entity_id}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="character",
                source_path=source_path,
                entity_id=entity_id,
                use_for=("character_mind", "character_voice", "scene_director_responder_selection"),
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def _canonical_step_source_path(module_root: Path, module_id: str, step_id: str) -> str:
    cp_dir = module_root / "canonical_path"
    if cp_dir.is_dir():
        for yaml_file in sorted(cp_dir.glob("*.yaml")):
            if yaml_file.stem == "index":
                continue
            stem = yaml_file.stem
            if step_id == stem or step_id.endswith(stem) or stem in step_id:
                return f"content/modules/{module_id}/canonical_path/{yaml_file.name}"
    return f"content/modules/{module_id}/canonical_path/{step_id}.yaml"


def chunks_from_canonical_steps(module: ContentModule, *, module_root: Path) -> list[RetrievalChunk]:
    module_id = module.metadata.module_id
    steps = _canonical_path_inner(module).get("steps")
    if not isinstance(steps, list):
        return []
    chunks: list[RetrievalChunk] = []
    for step in sorted(
        [row for row in steps if isinstance(row, dict)],
        key=lambda row: int(row.get("sequence") or 0),
    ):
        step_id = str(step.get("id") or "").strip()
        if not step_id:
            continue
        sequence = step.get("sequence")
        location_ref = step.get("location_ref")
        location_id = ""
        if isinstance(location_ref, dict):
            location_id = str(location_ref.get("location_id") or "").strip()
        source_path = _canonical_step_source_path(module_root, module_id, step_id)
        text = retrieval_text.format_canonical_step(step)
        chunk = _make_chunk(
            kind="canonical_step",
            chunk_id=f"canonical_step:{step_id}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="canonical_step",
                source_path=source_path,
                entity_id=step_id,
                use_for=("opening_realization", "story_direction", "narrator_packet"),
                sequence=sequence,
                location_id=location_id or None,
                path_id=step.get("path_id"),
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def chunks_from_director_hints(module_root: Path, module_id: str) -> list[RetrievalChunk]:
    hints = load_module_director_surface_hints(module_root)
    chunks: list[RetrievalChunk] = []
    for index, record in enumerate(hints):
        if not isinstance(record, dict):
            continue
        hint_id = str(record.get("hint_id") or "").strip()
        source = str(record.get("source") or "").strip().replace("\\", "/")
        slug = hint_id or Path(source).stem or f"hint_{index}"
        source_path = (
            source
            if source.startswith("content/modules/")
            else f"content/modules/{module_id}/{source.lstrip('/')}"
        )
        text = retrieval_text.format_director_hint(record)
        chunk = _make_chunk(
            kind="director_hint",
            chunk_id=f"director_hint:{slug}",
            text=text,
            metadata=_base_metadata(
                module_id,
                content_kind="director_hint",
                source_path=source_path,
                entity_id=hint_id or slug,
                use_for=("scene_director_dramatic_parameters", "render_support"),
                player_visible=False,
                hint_type=record.get("hint_type"),
            ),
        )
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def build_entity_retrieval_chunks(module: ContentModule, *, module_root: Path) -> list[RetrievalChunk]:
    """Emit one retrieval chunk per authoritative location/object/character/step/hint unit."""
    module_id = module.metadata.module_id
    chunks: list[RetrievalChunk] = []
    chunks.extend(chunks_from_places(module))
    chunks.extend(chunks_from_apartment_topology(module))
    chunks.extend(chunks_from_object_documents(module))
    chunks.extend(chunks_from_character_documents(module))
    chunks.extend(chunks_from_canonical_steps(module, module_root=module_root))
    chunks.extend(chunks_from_director_hints(module_root, module_id))
    return chunks
