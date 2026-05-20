"""
Canonical YAML authority for God of Carnage
(VERTICAL_SLICE_CONTRACT_GOC.md §6.1).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import unicodedata

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import GOC_MODULE_ID
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_scene_identity import (
    GOC_SCENE_ID_TO_GUIDANCE_PHASE,
    GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY,
    guidance_phase_key_for_scene_id,
)
from story_runtime_core.director_surface_hints import (
    load_module_director_surface_hints,
    select_director_surface_hints,
)
from ai_stack.language_io.language_adapter import build_interaction_surface

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _repo_root() -> Path:
    """Describe what ``_repo_root`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        Path:
            Returns a value of type ``Path``; see the function body for structure, error paths, and sentinels.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "content" / "modules").is_dir():
            return parent
    return here.parents[3]


def goc_module_yaml_dir() -> Path:
    """``goc_module_yaml_dir`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        Path:
            Returns a value of type ``Path``; see the function body for structure, error paths, and sentinels.
    """
    return _repo_root() / "content" / "modules" / GOC_MODULE_ID


def goc_knowledge_yaml_dir() -> Path:
    """Directory for English-authored structured knowledge YAML (``knowledge/*.yaml``)."""
    return goc_module_yaml_dir() / "knowledge"


def goc_characters_yaml_dir() -> Path:
    """Directory for character, relationship, and voice authority YAML."""
    return goc_module_yaml_dir() / "characters"


def goc_locations_yaml_dir() -> Path:
    """Directory for location authority YAML."""
    return goc_module_yaml_dir() / "locations"


def goc_objects_yaml_dir() -> Path:
    """Directory for object authority YAML."""
    return goc_module_yaml_dir() / "objects"


def goc_canonical_path_yaml_dir() -> Path:
    """Directory for numbered canonical path YAML."""
    return goc_module_yaml_dir() / "canonical_path"


def goc_beat_library_yaml_dir() -> Path:
    """Directory for reusable scene-direction beat pattern YAML."""
    return goc_module_yaml_dir() / "direction" / "beat_library"


def load_goc_canonical_module_yaml() -> dict[str, Any]:
    """Load authoritative module.yaml for god_of_carnage from the
    repository tree.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load canonical GoC module YAML.")
    path = goc_module_yaml_dir() / "module.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Canonical GoC module.yaml not found at {path}")
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("module.yaml must parse to a mapping.")
    mid = data.get("module_id")
    if mid != GOC_MODULE_ID:
        raise ValueError(f"module.yaml module_id mismatch: expected {GOC_MODULE_ID!r}, got {mid!r}")
    return data


@lru_cache(maxsize=1)
def cached_goc_yaml_title() -> str:
    """``cached_goc_yaml_title`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    mod = load_goc_canonical_module_yaml()
    title = mod.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Canonical module.yaml must define a non-empty string title.")
    return title.strip()


def _safe_load_yaml_mapping(path: Path) -> dict[str, Any]:
    """``_safe_load_yaml_mapping`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        path: ``path`` (Path); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load canonical GoC module YAML.")
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    merged: dict[str, Any] = {}
    for doc in yaml.safe_load_all(raw):
        if isinstance(doc, dict):
            merged.update(doc)
    return merged


def _safe_load_first_yaml_mapping(paths: list[Path]) -> dict[str, Any]:
    for path in paths:
        data = _safe_load_yaml_mapping(path)
        if data:
            return data
    return {}


def load_goc_characters_yaml() -> dict[str, Any]:
    """Load the compact canonical character roster or derive it from documents.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    data = _safe_load_first_yaml_mapping(
        [
            goc_characters_yaml_dir() / "index.yaml",
            goc_module_yaml_dir() / "characters.yaml",
        ]
    )
    ch = data.get("characters")
    if isinstance(ch, dict) and ch:
        return ch
    docs = load_goc_character_documents_yaml()
    return {
        char_id: {
            "id": str(doc.get("canonical_id") or doc.get("id") or char_id),
            "name": str(doc.get("name") or char_id),
            "role": str(doc.get("role") or ""),
            "baseline_attitude": str(
                doc.get("baseline_attitude")
                or doc.get("baseline_posture")
                or doc.get("public_identity")
                or ""
            ),
            **({"actor_id": doc.get("actor_id") or doc.get("runtime_actor_id")} if (doc.get("actor_id") or doc.get("runtime_actor_id")) else {}),
            **({"runtime_actor_id": doc.get("runtime_actor_id") or doc.get("actor_id")} if (doc.get("runtime_actor_id") or doc.get("actor_id")) else {}),
            **({"playable_status": doc.get("playable_status")} if doc.get("playable_status") else {}),
        }
        for char_id, doc in docs.items()
        if isinstance(doc, dict)
    }


def load_goc_character_voice_yaml() -> dict[str, Any]:
    """Load character voice guidance.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    data = _safe_load_first_yaml_mapping(
        [
            goc_characters_yaml_dir() / "character_voice.yaml",
            goc_module_yaml_dir() / "direction" / "character_voice.yaml",
        ]
    )
    ch = data.get("characters")
    if isinstance(ch, dict):
        return ch

    voices_dir = goc_characters_yaml_dir() / "voices"
    if not voices_dir.is_dir():
        return {}
    voices: dict[str, Any] = {}
    for path in sorted(voices_dir.glob("character_voice_*.yaml")):
        data = _safe_load_yaml_mapping(path)
        if not data:
            continue
        char_id = path.stem.removeprefix("character_voice_")
        voices[char_id] = data
    return voices


def load_goc_voice_consistency_yaml() -> dict[str, Any]:
    """Load the global voice consistency policy from character_voice.yaml."""
    data = _safe_load_first_yaml_mapping(
        [
            goc_characters_yaml_dir() / "character_voice.yaml",
            goc_characters_yaml_dir() / "voices" / "voice_consistency.yaml",
            goc_module_yaml_dir() / "direction" / "character_voice.yaml",
        ]
    )
    policy = data.get("voice_consistency")
    return policy if isinstance(policy, dict) else {}


@lru_cache(maxsize=1)
def load_goc_director_surface_hints_yaml() -> list[dict[str, Any]]:
    """Load authored director_surface_hint records from content/modules/.../hints/."""
    return load_module_director_surface_hints(goc_module_yaml_dir())


def select_goc_director_surface_hints_for_turn(
    *,
    scene_id: str,
    pacing_mode: str,
) -> list[dict[str, str | bool]]:
    """Filter module hints for the current scene phase and pacing."""
    phase_key = guidance_phase_key_for_scene_id(scene_id)
    return select_director_surface_hints(
        load_goc_director_surface_hints_yaml(),
        scene_id=scene_id,
        pacing_mode=pacing_mode,
        guidance_phase_key=phase_key,
    )


def load_goc_scene_guidance_yaml() -> dict[str, Any]:
    """Project phase_beat_policy into the scene-guidance runtime shape.

    The authored per-scene guidance file was removed to avoid a second
    phase-description database. Runtime seams still consume the derived mapping
    keys, so this function derives those short hints from the single phase
    authority instead.
    """
    policy = load_goc_phase_beat_policy_yaml()
    phases = policy.get("phases") if isinstance(policy.get("phases"), dict) else {}
    guidance: dict[str, Any] = {}

    for guidance_key, phase_id in GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY.items():
        block = phases.get(phase_id) if isinstance(phases, dict) else None
        if not isinstance(block, dict):
            continue

        name = str(block.get("name") or phase_id.replace("_", " ").title())
        description = str(block.get("description") or block.get("pacing_note") or "").strip()
        pacing_note = str(block.get("pacing_note") or "").strip()
        allowed_beats = [str(item) for item in list(block.get("allowed_narrator_beats") or [])]
        pressure_markers = [str(item) for item in list(block.get("pressure_markers") or [])]

        constraints: dict[str, Any] = {}
        for item in list(block.get("enforced_constraints") or []):
            if isinstance(item, dict):
                constraints.update(item)
            elif isinstance(item, str) and item.strip():
                constraints[item.strip()] = True

        ai_guidance: list[str] = []
        if pacing_note:
            ai_guidance.append(pacing_note)
        if allowed_beats:
            ai_guidance.append("Allowed narrator beats: " + ", ".join(allowed_beats[:6]))

        guidance[guidance_key] = {
            "title": name,
            "duration": str(block.get("turn_estimate") or ""),
            "phase_policy_ref": f"phase_beat_policy.yaml#phase_beat_policy.phases.{phase_id}",
            "narrative_context": f"{name}: {description}",
            "ai_guidance": ai_guidance,
            "pressure_watch": pressure_markers,
            "constraint_enforcement": constraints,
            "exit_signal": str(block.get("exit_condition") or ""),
        }

    return guidance


def load_goc_opening_sequence_yaml() -> dict[str, Any]:
    """Load direction/opening_sequence.yaml (session opening narrator path, ADR-0035)."""
    path = goc_module_yaml_dir() / "direction" / "opening_sequence.yaml"
    return _safe_load_yaml_mapping(path)


def load_goc_opening_document_text() -> str:
    """Load the human-editable opening document for authoring/review context."""
    path = goc_module_yaml_dir() / "direction" / "opening.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def load_goc_scene_phases_yaml() -> dict[str, Any]:
    """Project phase_beat_policy phases into the scene_phases runtime shape."""
    policy = load_goc_phase_beat_policy_yaml()
    phases = policy.get("phases") if isinstance(policy.get("phases"), dict) else {}
    out: dict[str, Any] = {}
    for fallback_sequence, (phase_id, block) in enumerate(phases.items(), start=1):
        if not isinstance(block, dict):
            continue
        key = str(block.get("id") or phase_id)
        sequence = block.get("sequence")
        if not isinstance(sequence, int):
            digits = "".join(ch for ch in key if ch.isdigit())
            sequence = int(digits) if digits else fallback_sequence
        out[key] = {
            "id": key,
            "name": str(block.get("name") or key.replace("_", " ").title()),
            "sequence": sequence,
            "description": str(block.get("description") or block.get("pacing_note") or key),
            "content_focus": list(block.get("content_focus") or block.get("allowed_narrator_beats") or []),
            "engine_tasks": list(block.get("engine_tasks") or block.get("allowed_narrator_beats") or []),
            "active_triggers": list(block.get("active_triggers") or []),
            "enforced_constraints": [str(item) for item in list(block.get("enforced_constraints") or [])],
            "turn_estimate": str(block.get("turn_estimate") or ""),
            "exit_condition": str(block.get("exit_condition") or ""),
        }
    return out


def load_goc_scene_graph_yaml() -> dict[str, Any]:
    """Load scene_graph.yaml as the authored scene-node graph."""
    path = goc_module_yaml_dir() / "scene_graph.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "scene_graph")


def load_goc_canonical_path_yaml() -> dict[str, Any]:
    """Load numbered canonical path steps from canonical_path/."""
    path_dir = goc_canonical_path_yaml_dir()
    data = _safe_load_yaml_mapping(path_dir / "index.yaml")
    canonical_path = _unwrap_top_level_mapping(data, "canonical_path")
    if not canonical_path:
        return {}

    steps: list[dict[str, Any]] = []
    for path in sorted(path_dir.glob("*.yaml")):
        if path.name == "index.yaml":
            continue
        payload = _safe_load_yaml_mapping(path)
        step = payload.get("canonical_path_step") or payload.get("step")
        if isinstance(step, dict):
            steps.append(step)

    if steps:
        canonical_path = dict(canonical_path)
        canonical_path["steps"] = sorted(steps, key=lambda row: int(row.get("sequence") or 0))
    return canonical_path


def load_goc_modularity_policy_yaml() -> dict[str, Any]:
    """Load content authority-boundary policy."""
    path = goc_knowledge_yaml_dir() / "modularity_policy.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "modularity_policy")


def load_goc_beat_library_yaml() -> dict[str, Any]:
    """Load reusable scene-direction beat patterns from direction/beat_library/."""
    beat_dir = goc_beat_library_yaml_dir()
    if not beat_dir.is_dir():
        return {}

    index = _safe_load_yaml_mapping(beat_dir / "_index.yaml")
    library = _unwrap_top_level_mapping(index, "beat_library_index") or index
    patterns: dict[str, Any] = {}
    pattern_files: dict[str, str] = {}
    for path in sorted(beat_dir.glob("*.yaml")):
        if path.name == "_index.yaml":
            continue
        payload = _safe_load_yaml_mapping(path)
        pattern = payload.get("beat_pattern") if isinstance(payload, dict) else None
        if not isinstance(pattern, dict):
            continue
        pattern_id = str(pattern.get("id") or path.stem).strip()
        if not pattern_id:
            continue
        pattern = dict(pattern)
        pattern.setdefault("source_ref", path.relative_to(goc_module_yaml_dir()).as_posix())
        patterns[pattern_id] = pattern
        pattern_files[pattern_id] = path.relative_to(goc_module_yaml_dir()).as_posix()

    out = dict(library) if isinstance(library, dict) else {}
    out["patterns"] = patterns
    out["pattern_files"] = pattern_files
    return out


def load_goc_locations_yaml() -> dict[str, Any]:
    """Load authored location/accessibility surface from index plus location files."""
    data = _safe_load_first_yaml_mapping(
        [
            goc_locations_yaml_dir() / "index.yaml",
            goc_locations_yaml_dir() / "locations.yaml",
            goc_module_yaml_dir() / "locations.yaml",
        ]
    )
    locations = _unwrap_top_level_mapping(data, "locations")
    if not locations:
        return {}

    existing_places = locations.get("places") if isinstance(locations.get("places"), list) else []
    merged: dict[str, Any] = {}
    for place in existing_places:
        if not isinstance(place, dict):
            continue
        place_id = str(place.get("id") or "").strip()
        if place_id:
            merged[place_id] = place

    for place_id, place in _load_goc_location_documents_yaml().items():
        merged[place_id] = place

    if merged:
        locations = dict(locations)
        locations["places"] = list(merged.values())
    return locations


def load_goc_character_documents_yaml() -> dict[str, Any]:
    """Load per-character authoring documents from characters/*.yaml."""
    char_dir = goc_characters_yaml_dir()
    if not char_dir.is_dir():
        return {}
    docs: dict[str, Any] = {}
    for path in sorted(char_dir.rglob("*.yaml")):
        data = _safe_load_yaml_mapping(path)
        inner = data.get("character_document") or data.get("character")
        if not isinstance(inner, dict):
            continue
        char_id = str(inner.get("id") or inner.get("canonical_id") or path.stem).strip()
        if char_id:
            docs[char_id] = inner
    return docs


def goc_actor_identity_index(yaml_slice: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    """Return actor identity records derived from content character documents."""
    docs = (
        yaml_slice.get("character_documents")
        if isinstance(yaml_slice, dict) and isinstance(yaml_slice.get("character_documents"), dict)
        else None
    )
    if not isinstance(docs, dict) or not docs:
        docs = (
            yaml_slice.get("characters")
            if isinstance(yaml_slice, dict) and isinstance(yaml_slice.get("characters"), dict)
            else None
        )
    if not isinstance(docs, dict) or not docs:
        docs = load_goc_character_documents_yaml()
    out: dict[str, dict[str, str]] = {}
    for key, row in docs.items():
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or row.get("runtime_actor_id") or "").strip()
        if not actor_id:
            continue
        character_key = str(row.get("id") or row.get("canonical_id") or key or "").strip()
        name = str(row.get("name") or character_key or actor_id).strip()
        first_name = name.split()[0] if name else actor_id.replace("_", " ").title()
        out[actor_id] = {
            "actor_id": actor_id,
            "character_key": character_key,
            "name": name,
            "first_name": first_name,
            "playable_status": str(row.get("playable_status") or "").strip(),
            "household_side": str(row.get("household_side") or "").strip(),
            "role": str(row.get("role") or "").strip(),
        }
    return out


def goc_actor_identity(
    actor_id_or_ref: str | None,
    *,
    yaml_slice: dict[str, Any] | None = None,
) -> dict[str, str]:
    ref = str(actor_id_or_ref or "").strip()
    ref_low = ref.lower()
    ref_folded = "".join(
        ch for ch in unicodedata.normalize("NFKD", ref_low)
        if not unicodedata.combining(ch)
    )
    index = goc_actor_identity_index(yaml_slice)
    if ref in index:
        return dict(index[ref])
    for row in index.values():
        aliases = {
            str(row.get("actor_id") or "").strip(),
            str(row.get("character_key") or "").strip(),
            str(row.get("name") or "").strip(),
            str(row.get("first_name") or "").strip(),
        }
        alias_lows = {alias.lower() for alias in aliases if alias}
        alias_folded = {
            "".join(
                ch for ch in unicodedata.normalize("NFKD", alias.lower())
                if not unicodedata.combining(ch)
            )
            for alias in aliases
            if alias
        }
        if ref and (ref in aliases or ref_low in alias_lows or ref_folded in alias_folded):
            return dict(row)
    return {}


def goc_actor_display_name(
    actor_id_or_ref: str | None,
    *,
    yaml_slice: dict[str, Any] | None = None,
    first_name: bool = False,
) -> str:
    ident = goc_actor_identity(actor_id_or_ref, yaml_slice=yaml_slice)
    if ident:
        return ident.get("first_name" if first_name else "name") or ident.get("actor_id") or "Actor"
    raw = str(actor_id_or_ref or "").strip()
    return raw.replace("_", " ").title() if raw else "Actor"


def goc_character_key_for_actor_id(
    actor_id_or_ref: str | None,
    *,
    yaml_slice: dict[str, Any] | None = None,
) -> str:
    return goc_actor_identity(actor_id_or_ref, yaml_slice=yaml_slice).get("character_key", "")


def goc_actor_ids_from_content(yaml_slice: dict[str, Any] | None = None) -> list[str]:
    return list(goc_actor_identity_index(yaml_slice).keys())


def _load_goc_location_documents_yaml() -> dict[str, Any]:
    loc_dir = goc_locations_yaml_dir()
    if not loc_dir.is_dir():
        return {}
    docs: dict[str, Any] = {}
    reserved = {"index.yaml", "locations.yaml", "apartment_layout.yaml"}
    for path in sorted(loc_dir.rglob("*.yaml")):
        if path.name in reserved:
            continue
        data = _safe_load_yaml_mapping(path)
        inner = data.get("location") or data.get("place")
        if not isinstance(inner, dict):
            continue
        place_id = str(inner.get("id") or path.stem).strip()
        if place_id:
            docs[place_id] = inner
    return docs


def _load_goc_object_documents_yaml() -> dict[str, Any]:
    obj_dir = goc_objects_yaml_dir()
    if not obj_dir.is_dir():
        return {}
    docs: dict[str, Any] = {}
    reserved = {"index.yaml", "objects.yaml"}
    for path in sorted(obj_dir.rglob("*.yaml")):
        if path.name in reserved:
            continue
        data = _safe_load_yaml_mapping(path)
        inner = data.get("object") or data.get("object_document")
        if not isinstance(inner, dict):
            continue
        object_id = str(inner.get("id") or path.stem).strip()
        if object_id:
            object_doc = dict(inner)
            object_doc.setdefault("source_ref", path.relative_to(goc_module_yaml_dir()).as_posix())
            docs[object_id] = object_doc
    return docs


def load_goc_objects_yaml() -> dict[str, Any]:
    data = _safe_load_first_yaml_mapping(
        [
            goc_objects_yaml_dir() / "index.yaml",
            goc_objects_yaml_dir() / "objects.yaml",
            goc_module_yaml_dir() / "objects.yaml",
        ]
    )
    objects = _unwrap_top_level_mapping(data, "objects")
    object_documents = _load_goc_object_documents_yaml()
    if object_documents:
        objects = dict(objects)
        objects["object_documents"] = object_documents
    return objects


def load_goc_relationships_yaml() -> dict[str, Any]:
    """Load relationship authority without dropping pairwise relationship data."""
    data = _safe_load_first_yaml_mapping(
        [
            goc_characters_yaml_dir() / "details" / "relationships.yaml",
            goc_characters_yaml_dir() / "relationships.yaml",
            goc_module_yaml_dir() / "relationships.yaml",
        ]
    )
    return {
        "relationship_axes": data.get("relationship_axes") if isinstance(data.get("relationship_axes"), dict) else {},
        "relationships": data.get("relationships") if isinstance(data.get("relationships"), dict) else {},
        "stability_constraints": data.get("stability_constraints")
        if isinstance(data.get("stability_constraints"), dict)
        else {},
    }


def load_goc_triggers_yaml() -> dict[str, Any]:
    """Load trigger definitions and recognition strategy."""
    path = goc_module_yaml_dir() / "triggers.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "trigger_types": data.get("trigger_types") if isinstance(data.get("trigger_types"), dict) else {},
        "trigger_recognition": data.get("trigger_recognition")
        if isinstance(data.get("trigger_recognition"), dict)
        else {},
        "trigger_state": data.get("trigger_state") if isinstance(data.get("trigger_state"), dict) else {},
    }


def load_goc_transitions_yaml() -> dict[str, Any]:
    """Load phase transition rules and safeguards."""
    path = goc_module_yaml_dir() / "transitions.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "phase_transitions": data.get("phase_transitions")
        if isinstance(data.get("phase_transitions"), dict)
        else {},
        "transition_mechanics": data.get("transition_mechanics")
        if isinstance(data.get("transition_mechanics"), dict)
        else {},
        "state_on_transition": data.get("state_on_transition")
        if isinstance(data.get("state_on_transition"), dict)
        else {},
        "transition_safeguards": data.get("transition_safeguards")
        if isinstance(data.get("transition_safeguards"), dict)
        else {},
    }


def load_goc_endings_yaml() -> dict[str, Any]:
    """Load ending definitions."""
    path = goc_module_yaml_dir() / "endings.yaml"
    data = _safe_load_yaml_mapping(path)
    endings = data.get("ending_types")
    return endings if isinstance(endings, dict) else {}


def load_goc_escalation_axes_yaml() -> dict[str, Any]:
    """Load escalation axes and interaction model."""
    path = goc_module_yaml_dir() / "escalation_axes.yaml"
    data = _safe_load_yaml_mapping(path)
    return {
        "escalation_axes": data.get("escalation_axes") if isinstance(data.get("escalation_axes"), dict) else {},
        "interaction_model": data.get("interaction_model") if isinstance(data.get("interaction_model"), dict) else {},
    }


def load_goc_system_prompt_text() -> str:
    """Load the authored GoC system prompt text for bounded excerpts."""
    path = goc_module_yaml_dir() / "direction" / "system_prompt.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _unwrap_top_level_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    inner = data.get(key)
    return inner if isinstance(inner, dict) else {}


def load_goc_scene_affordances_yaml_inner() -> dict[str, Any]:
    """Return the runtime interaction surface derived from locations and objects."""
    return build_interaction_surface(GOC_MODULE_ID, content_modules_root=goc_module_yaml_dir().parent)


def load_goc_scene_affordances_block() -> dict[str, Any]:
    """Wrap scene affordances for narrator consequence contracts (expects ``scene_affordances`` key)."""
    inner = load_goc_scene_affordances_yaml_inner()
    return {"scene_affordances": inner} if inner else {}


def load_goc_apartment_layout_yaml() -> dict[str, Any]:
    data = _safe_load_first_yaml_mapping(
        [
            goc_locations_yaml_dir() / "appartment_vallon" / "apartment_layout.yaml",
            goc_locations_yaml_dir() / "appartment" / "apartment_layout.yaml",
            goc_locations_yaml_dir() / "apartment" / "apartment_layout.yaml",
            goc_locations_yaml_dir() / "apartment_layout.yaml",
            goc_module_yaml_dir() / "apartment_layout.yaml",
        ]
    )
    return _unwrap_top_level_mapping(data, "apartment_layout")


def load_goc_premise_and_backstory_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "premise_and_backstory.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "premise_and_backstory")


def load_goc_actor_pressure_profiles_yaml() -> dict[str, Any]:
    data = _safe_load_first_yaml_mapping(
        [
            goc_characters_yaml_dir() / "details" / "actor_pressure_profiles.yaml",
            goc_characters_yaml_dir() / "actor_pressure_profiles.yaml",
            goc_module_yaml_dir() / "actor_pressure_profiles.yaml",
        ]
    )
    return _unwrap_top_level_mapping(data, "actor_pressure_profiles")


def load_goc_phase_beat_policy_yaml() -> dict[str, Any]:
    path = goc_module_yaml_dir() / "phase_beat_policy.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "phase_beat_policy")


def load_goc_narrator_sensory_palette_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "narrator_sensory_palette.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "narrator_sensory_palette")


def load_goc_opening_scene_sequence_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "opening_scene_sequence.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "opening_scene_sequence")


def load_goc_opening_quote_anchors_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "opening_quote_anchors.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "opening_quote_anchors")


def load_goc_hard_forbidden_rules_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "hard_forbidden_rules.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "hard_forbidden_rules")


def load_goc_content_access_policy_yaml() -> dict[str, Any]:
    path = goc_knowledge_yaml_dir() / "content_access_policy.yaml"
    return _unwrap_top_level_mapping(_safe_load_yaml_mapping(path), "content_access_policy")


@lru_cache(maxsize=1)
def load_goc_yaml_slice_bundle() -> dict[str, Any]:
    """Bundle of YAML-backed slice surfaces used by the director
    (VERTICAL_SLICE_CONTRACT_GOC.md §6).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    relationships = load_goc_relationships_yaml()
    triggers = load_goc_triggers_yaml()
    transitions = load_goc_transitions_yaml()
    escalation = load_goc_escalation_axes_yaml()
    scene_aff = load_goc_scene_affordances_yaml_inner()
    return {
        "characters": load_goc_characters_yaml(),
        "character_voice": load_goc_character_voice_yaml(),
        "character_documents": load_goc_character_documents_yaml(),
        "voice_consistency": load_goc_voice_consistency_yaml(),
        "scene_guidance": load_goc_scene_guidance_yaml(),
        "opening_sequence": load_goc_opening_sequence_yaml(),
        "opening_document_excerpt": load_goc_opening_document_text()[:2400],
        "scene_phases": load_goc_scene_phases_yaml(),
        "scene_graph": load_goc_scene_graph_yaml(),
        "canonical_path": load_goc_canonical_path_yaml(),
        "modularity_policy": load_goc_modularity_policy_yaml(),
        "beat_library": load_goc_beat_library_yaml(),
        "director_surface_hints": load_goc_director_surface_hints_yaml(),
        "relationship_axes": relationships["relationship_axes"],
        "relationships": relationships["relationships"],
        "stability_constraints": relationships["stability_constraints"],
        "trigger_types": triggers["trigger_types"],
        "trigger_recognition": triggers["trigger_recognition"],
        "trigger_state": triggers["trigger_state"],
        "phase_transitions": transitions["phase_transitions"],
        "transition_mechanics": transitions["transition_mechanics"],
        "state_on_transition": transitions["state_on_transition"],
        "transition_safeguards": transitions["transition_safeguards"],
        "ending_types": load_goc_endings_yaml(),
        "escalation_axes": escalation["escalation_axes"],
        "escalation_interaction_model": escalation["interaction_model"],
        "system_prompt_excerpt": load_goc_system_prompt_text()[:2400],
        "scene_affordances": scene_aff,
        "locations": load_goc_locations_yaml(),
        "objects": load_goc_objects_yaml(),
        "apartment_layout": load_goc_apartment_layout_yaml(),
        "premise_and_backstory": load_goc_premise_and_backstory_yaml(),
        "actor_pressure_profiles": load_goc_actor_pressure_profiles_yaml(),
        "phase_beat_policy": load_goc_phase_beat_policy_yaml(),
        "narrator_sensory_palette": load_goc_narrator_sensory_palette_yaml(),
        "opening_scene_sequence": load_goc_opening_scene_sequence_yaml(),
        "opening_quote_anchors": load_goc_opening_quote_anchors_yaml(),
        "hard_forbidden_rules": load_goc_hard_forbidden_rules_yaml(),
        "content_access_policy": load_goc_content_access_policy_yaml(),
    }


def clear_goc_yaml_slice_cache() -> None:
    """Describe what ``clear_goc_yaml_slice_cache`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    """
    load_goc_yaml_slice_bundle.cache_clear()


def thin_edge_staging_line_from_guidance(*, scene_guidance: dict[str, Any], scene_id: str) -> str:
    """First line from YAML narrative_context for bounded non-factual
    staging (truth-safe supplement).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return ""
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return ""
    nc = block.get("narrative_context")
    if not isinstance(nc, str) or not nc.strip():
        return ""
    first_line = nc.strip().split("\n")[0].strip()
    return first_line[:280]


def scene_assessment_phase_hints(*, scene_guidance: dict[str, Any], scene_id: str) -> dict[str, Any]:
    """Read-only hints from YAML for scene_assessment (not a second truth
    surface).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return {}
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return {"guidance_phase_key": phase}
    title = block.get("title")
    ce = block.get("constraint_enforcement")
    civ = None
    if isinstance(ce, dict):
        civ = ce.get("civility_required")
    return {
        "guidance_phase_key": phase,
        "guidance_phase_title": title if isinstance(title, str) else None,
        "guidance_civility_required": civ,
    }


def scene_guidance_snippets(*, scene_guidance: dict[str, Any], scene_id: str) -> dict[str, str]:
    """Read short operator/render snippets from scene_guidance without
    creating new truth.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        scene_guidance: ``scene_guidance`` (dict[str,
            Any]); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if not scene_guidance:
        return {}
    phase = guidance_phase_key_for_scene_id(scene_id)
    block = scene_guidance.get(phase)
    if not isinstance(block, dict):
        return {"guidance_phase_key": phase}
    out: dict[str, str] = {"guidance_phase_key": phase}
    exit_signal = block.get("exit_signal")
    if isinstance(exit_signal, str) and exit_signal.strip():
        out["exit_signal"] = exit_signal.strip()[:220]
    ai_guidance = block.get("ai_guidance")
    if isinstance(ai_guidance, list):
        for item in ai_guidance:
            if isinstance(item, str) and item.strip():
                out["ai_guidance_hint"] = item.strip()[:220]
                break
    return out


def goc_character_profile_snippet(
    *,
    actor_id: str,
    yaml_slice: dict[str, Any] | None,
    scene_id: str = "",
) -> dict[str, str]:
    """Return short YAML-backed role/voice snippets for responder-specific
    rendering.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        actor_id: ``actor_id`` (str); meaning follows the type and call sites.
        yaml_slice: ``yaml_slice`` (dict[str, Any] |
            None); meaning follows the type and call sites.
        scene_id: ``scene_id`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, str]:
            Returns a value of type ``dict[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(yaml_slice, dict):
        return {}
    chars = yaml_slice.get("characters") if isinstance(yaml_slice.get("characters"), dict) else {}
    voice = yaml_slice.get("character_voice") if isinstance(yaml_slice.get("character_voice"), dict) else {}
    key = ""
    for raw_key, row in chars.items():
        if not isinstance(row, dict):
            continue
        row_actor_id = str(row.get("actor_id") or row.get("runtime_actor_id") or "").strip()
        if row_actor_id == actor_id:
            key = str(raw_key or "").strip()
            break
    if not key:
        return {}
    cblock = chars.get(key) if isinstance(chars.get(key), dict) else {}
    vblock = voice.get(key) if isinstance(voice.get(key), dict) else {}
    out: dict[str, str] = {"character_key": key}
    role = cblock.get("role")
    if isinstance(role, str) and role.strip():
        out["role"] = role.strip()[:120]
    baseline = cblock.get("baseline_attitude")
    if isinstance(baseline, str) and baseline.strip():
        out["baseline_attitude"] = baseline.strip()[:180]
    formal_role = vblock.get("formal_role")
    if isinstance(formal_role, str) and formal_role.strip():
        out["formal_role"] = formal_role.strip()[:140]
    baseline_tone = vblock.get("baseline_tone")
    if isinstance(baseline_tone, str) and baseline_tone.strip():
        out["baseline_tone"] = baseline_tone.strip()[:140]
    if scene_id.strip():
        phase_key = guidance_phase_key_for_scene_id(scene_id)
        arc = vblock.get("escalation_arc")
        if isinstance(arc, dict):
            phase_arc_key = GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY.get(phase_key)
            if phase_arc_key:
                arc_text = arc.get(phase_arc_key)
                if isinstance(arc_text, str) and arc_text.strip():
                    out["phase_arc_hint"] = arc_text.strip()[:180]
    return out


def detect_builtin_yaml_title_conflict(
    *,
    host_template_id: str | None,
    host_template_title: str | None,
) -> dict[str, Any] | None:
    """If a secondary builtin template contradicts YAML title, return a
    failure marker payload.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        host_template_id: ``host_template_id`` (str |
            None); meaning follows the type and call sites.
        host_template_title: ``host_template_title`` (str
            | None); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    if not host_template_id or host_template_id != "god_of_carnage_solo":
        return None
    if not host_template_title:
        return None
    canonical = cached_goc_yaml_title()
    if host_template_title.strip() == canonical:
        return None
    return {
        "failure_class": "scope_breach",
        "note": "builtins_yaml_title_mismatch",
        "canonical_yaml_title": canonical,
        "host_template_title": host_template_title.strip(),
    }
