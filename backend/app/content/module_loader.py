"""
Module loader for content modules.

Handles loading, parsing, and validating content modules from YAML files
in a structured module directory. Provides non-fail-fast validation that
collects all errors before raising exceptions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .module_exceptions import (
    ModuleFileReadError,
    ModuleNotFoundError,
    ModuleParseError,
    ModuleStructureError,
)
from .module_models import ContentModule


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _derive_scene_phases_from_phase_beat_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Project phase_beat_policy into scene_phases for runtime consumers."""
    phases = policy.get("phases") if isinstance(policy, dict) else None
    if not isinstance(phases, dict):
        return {}
    derived: dict[str, Any] = {}
    for fallback_sequence, (phase_id, block) in enumerate(phases.items(), start=1):
        if not isinstance(block, dict):
            continue
        phase_key = str(block.get("id") or phase_id)
        sequence = block.get("sequence")
        if not isinstance(sequence, int):
            digits = "".join(ch for ch in phase_key if ch.isdigit())
            sequence = int(digits) if digits else fallback_sequence
        derived[phase_key] = {
            "id": phase_key,
            "name": str(block.get("name") or phase_key.replace("_", " ").title()),
            "sequence": sequence,
            "description": str(block.get("description") or block.get("pacing_note") or phase_key),
            "content_focus": _as_string_list(
                block.get("content_focus")
                or block.get("allowed_narrator_beats")
                or block.get("allowed_scene_functions")
                or []
            ),
            "engine_tasks": _as_string_list(
                block.get("engine_tasks")
                or block.get("allowed_scene_functions")
                or block.get("allowed_narrator_beats")
                or []
            ),
            "active_triggers": _as_string_list(block.get("active_triggers") or []),
            "enforced_constraints": _as_string_list(block.get("enforced_constraints") or []),
            "turn_estimate": str(block.get("turn_estimate") or ""),
            "exit_condition": str(block.get("exit_condition") or ""),
        }
    return derived


def content_modules_root() -> Path:
    """Absolute path to the directory that contains module folders (e.g. ``god_of_carnage/``).

    Resolution order:
    1. ``WOS_CONTENT_MODULES_ROOT`` — absolute path to the ``modules`` directory.
    2. ``WOS_REPO_ROOT`` — repository root; uses ``<root>/content/modules``.
    3. Packaged layout (Docker image): this file at ``.../app/content/module_loader.py``
       with modules copied to ``<app-root>/content/modules`` (three parents up from
       ``content/`` → install root, e.g. ``/app/content/modules``).
    4. Heuristic: four parents up, then ``content/modules`` (dev checkout:
       ``.../repo/backend/app/content/module_loader.py``).

    Override env vars when the layout does not match any automatic path.
    """
    explicit = (os.environ.get("WOS_CONTENT_MODULES_ROOT") or "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    repo_root = (os.environ.get("WOS_REPO_ROOT") or "").strip()
    if repo_root:
        return Path(repo_root).expanduser().resolve() / "content" / "modules"
    here = Path(__file__).resolve()
    packaged = here.parent.parent.parent / "content" / "modules"
    if packaged.is_dir():
        return packaged.resolve()
    # Dev checkout: backend/app/content/module_loader.py → repo root
    return here.parent.parent.parent.parent / "content" / "modules"


# Game experience template IDs that map to a different ``content/modules/<dir>`` folder name.
_CONTENT_MODULE_DIRECTORY_ALIASES: dict[str, str] = {
    "god_of_carnage_solo": "god_of_carnage",
}


def resolve_content_module_directory_id(module_id: str) -> str:
    """Return the filesystem directory name under ``content/modules/`` for a requested id.

    Template ids (e.g. ``god_of_carnage_solo``) may differ from the canonical YAML module
    folder (e.g. ``god_of_carnage``).
    """
    key = (module_id or "").strip()
    return _CONTENT_MODULE_DIRECTORY_ALIASES.get(key, key)


class ModuleFileLoader:
    """Handles reading and parsing YAML files from module directories.

    This loader is responsible for reading individual YAML files and loading
    all YAML files from a module directory structure. It handles YAML parsing
    errors and file I/O errors with appropriate exception context.
    """

    def load_file(self, path: Path) -> dict[str, Any]:
        """Load a single YAML file and return its contents.

        Args:
            path: Path to the YAML file to load.

        Returns:
            Dictionary containing the parsed YAML content.

        Raises:
            ModuleParseError: If the file contains invalid YAML.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                # safe_load returns None for empty files, convert to empty dict
                return content if content is not None else {}
        except OSError as e:
            raise ModuleFileReadError(
                message="Failed to read YAML file",
                module_id="unknown",
                file_path=str(path),
                errors=[str(e)],
            ) from e
        except yaml.YAMLError as e:
            raise ModuleParseError(
                message="Failed to parse YAML file",
                module_id="unknown",
                file_path=str(path),
                errors=[str(e)],
            )

    def load_all_module_files(self, module_root: Path) -> dict[str, dict]:
        """Load all YAML files from a module directory.

        Scans the module root directory for all .yaml files and loads each one,
        returning a dictionary mapping filenames (without extension) to their
        parsed contents.

        Args:
            module_root: Path to the root directory of the module.

        Returns:
            Dictionary mapping filename (without .yaml) to parsed content.

        Raises:
            ModuleFileReadError: If the directory doesn't exist or cannot be read.
            ModuleParseError: If any YAML file fails to parse.
        """
        if not module_root.exists():
            raise ModuleFileReadError(
                message=f"Module directory does not exist",
                module_id="unknown",
                file_path=str(module_root),
            )

        if not module_root.is_dir():
            raise ModuleFileReadError(
                message=f"Module path is not a directory",
                module_id="unknown",
                file_path=str(module_root),
            )

        try:
            yaml_files = sorted(module_root.glob("*.yaml"))
        except (PermissionError, OSError) as e:
            raise ModuleFileReadError(
                message=f"Failed to read module directory",
                module_id="unknown",
                file_path=str(module_root),
                errors=[str(e)],
            )

        result: dict[str, Any] = {}
        for yaml_file in yaml_files:
            filename = yaml_file.stem  # filename without .yaml extension
            result[filename] = self.load_file(yaml_file)

        knowledge_dir = module_root / "knowledge"
        if knowledge_dir.is_dir():
            try:
                knowledge_files = sorted(knowledge_dir.glob("*.yaml"))
            except (PermissionError, OSError) as e:
                raise ModuleFileReadError(
                    message="Failed to read module knowledge directory",
                    module_id="unknown",
                    file_path=str(knowledge_dir),
                    errors=[str(e)],
                )
            for yaml_file in knowledge_files:
                result[yaml_file.stem] = self.load_file(yaml_file)

        character_dir = module_root / "characters"
        if character_dir.is_dir():
            try:
                character_files = sorted(character_dir.rglob("*.yaml"))
            except (PermissionError, OSError) as e:
                raise ModuleFileReadError(
                    message="Failed to read module characters directory",
                    module_id="unknown",
                    file_path=str(character_dir),
                    errors=[str(e)],
                )
            character_documents: dict[str, Any] = {}
            for yaml_file in character_files:
                payload = self.load_file(yaml_file)
                if not isinstance(payload, dict):
                    continue
                if "relationship_axes" in payload or yaml_file.stem == "relationships":
                    result["relationships"] = payload
                    continue
                if "actor_pressure_profiles" in payload:
                    result["actor_pressure_profiles"] = payload
                    continue
                if yaml_file.stem == "character_voice":
                    continue
                if "characters" in payload:
                    result["characters"] = payload
                    continue
                if "characters_index" in payload:
                    continue
                inner = payload.get("character_document") or payload.get("character")
                if isinstance(inner, dict):
                    char_id = str(inner.get("id") or inner.get("canonical_id") or yaml_file.stem).strip()
                    if char_id:
                        character_documents[char_id] = inner
            if character_documents:
                result["character_documents"] = character_documents
                result["characters"] = {
                    char_id: {
                        "id": str(doc.get("canonical_id") or doc.get("id") or char_id),
                        "name": str(doc.get("name") or char_id),
                        "role": str(doc.get("role") or doc.get("dramatic_role") or ""),
                        "actor_id": str(doc.get("actor_id") or doc.get("runtime_actor_id") or ""),
                        "runtime_actor_id": str(doc.get("runtime_actor_id") or doc.get("actor_id") or ""),
                        "baseline_attitude": str(
                            doc.get("baseline_attitude")
                            or doc.get("baseline_posture")
                            or doc.get("public_identity")
                            or ""
                        ),
                        "extras": dict(doc),
                    }
                    for char_id, doc in character_documents.items()
                    if isinstance(doc, dict)
                }

        locations_dir = module_root / "locations"
        if locations_dir.is_dir():
            try:
                location_files = sorted(locations_dir.rglob("*.yaml"))
            except (PermissionError, OSError) as e:
                raise ModuleFileReadError(
                    message="Failed to read module locations directory",
                    module_id="unknown",
                    file_path=str(locations_dir),
                    errors=[str(e)],
                )
            location_documents: dict[str, Any] = {}
            for yaml_file in location_files:
                payload = self.load_file(yaml_file)
                if not isinstance(payload, dict):
                    continue
                if yaml_file.parent == locations_dir and yaml_file.stem in {"index", "locations"}:
                    result["locations"] = payload
                    continue
                if yaml_file.stem == "apartment_layout":
                    result["apartment_layout"] = payload
                    continue
                inner = payload.get("location") or payload.get("place")
                if isinstance(inner, dict):
                    place_id = str(inner.get("id") or yaml_file.stem).strip()
                    if place_id:
                        location_documents[place_id] = inner
            if location_documents:
                locations_payload = result.get("locations") if isinstance(result.get("locations"), dict) else {}
                locations_inner = (
                    locations_payload.get("locations")
                    if isinstance(locations_payload.get("locations"), dict)
                    else locations_payload
                )
                locations_inner = dict(locations_inner) if isinstance(locations_inner, dict) else {}
                merged_places: dict[str, Any] = {}
                for row in locations_inner.get("places") if isinstance(locations_inner.get("places"), list) else []:
                    if not isinstance(row, dict):
                        continue
                    place_id = str(row.get("id") or "").strip()
                    if place_id:
                        merged_places[place_id] = row
                merged_places.update(location_documents)
                locations_inner["places"] = list(merged_places.values())
                result["locations"] = {"locations": locations_inner}

        objects_dir = module_root / "objects"
        if objects_dir.is_dir():
            try:
                object_files = sorted(objects_dir.rglob("*.yaml"))
            except (PermissionError, OSError) as e:
                raise ModuleFileReadError(
                    message="Failed to read module objects directory",
                    module_id="unknown",
                    file_path=str(objects_dir),
                    errors=[str(e)],
                )
            object_documents: dict[str, Any] = {}
            for yaml_file in object_files:
                payload = self.load_file(yaml_file)
                if not isinstance(payload, dict):
                    continue
                if yaml_file.parent == objects_dir and yaml_file.stem in {"index", "objects"}:
                    result["objects"] = payload
                    continue
                inner = payload.get("object") or payload.get("object_document")
                if isinstance(inner, dict):
                    object_id = str(inner.get("id") or yaml_file.stem).strip()
                    if object_id:
                        object_doc = dict(inner)
                        object_doc.setdefault(
                            "source_ref",
                            yaml_file.relative_to(module_root).as_posix(),
                        )
                        object_documents[object_id] = object_doc
            if object_documents:
                objects_payload = result.get("objects") if isinstance(result.get("objects"), dict) else {}
                objects_inner = (
                    objects_payload.get("objects")
                    if isinstance(objects_payload.get("objects"), dict)
                    else objects_payload
                )
                objects_inner = dict(objects_inner) if isinstance(objects_inner, dict) else {}
                objects_inner["object_documents"] = object_documents
                result["objects"] = {"objects": objects_inner}

        canonical_path_dir = module_root / "canonical_path"
        if canonical_path_dir.is_dir():
            try:
                canonical_path_files = sorted(canonical_path_dir.glob("*.yaml"))
            except (PermissionError, OSError) as e:
                raise ModuleFileReadError(
                    message="Failed to read module canonical_path directory",
                    module_id="unknown",
                    file_path=str(canonical_path_dir),
                    errors=[str(e)],
                )
            canonical_path_payload: dict[str, Any] = {}
            canonical_path_steps: list[dict[str, Any]] = []
            for yaml_file in canonical_path_files:
                payload = self.load_file(yaml_file)
                if not isinstance(payload, dict):
                    continue
                if yaml_file.stem == "index":
                    canonical_path_payload = payload
                    continue
                step = payload.get("canonical_path_step") or payload.get("step")
                if isinstance(step, dict):
                    canonical_path_steps.append(step)
            if canonical_path_payload or canonical_path_steps:
                inner = (
                    canonical_path_payload.get("canonical_path")
                    if isinstance(canonical_path_payload.get("canonical_path"), dict)
                    else canonical_path_payload
                )
                inner = dict(inner) if isinstance(inner, dict) else {}
                if canonical_path_steps:
                    inner["steps"] = sorted(
                        canonical_path_steps,
                        key=lambda row: int(row.get("sequence") or 0),
                    )
                result["canonical_path"] = {"canonical_path": inner}

        # Unwrap nested dictionaries where YAML files wrap content under a root key.
        #
        # Most YAML files are structured as:
        #   characters.yaml:
        #     characters:
        #       veronique: {...}
        #   relationships.yaml:
        #     relationship_axes:
        #       axis_1: {...}
        #   phase file:
        #     scene_phases:
        #       phase_1: {...}
        #
        # The loader initially stores these with the filename as key and the entire
        # parsed YAML as content:
        #   raw_data['characters'] = {'characters': {...}}
        #   raw_data['relationships'] = {'relationship_axes': {...}}
        #   raw_data['scenes'] = {'scene_phases': {...}}
        #
        # We need to unwrap to get just the content under the root key, while
        # preserving filenames for test assertions and downstream mapping.
        #
        # Special cases:
        # - 'module' is NOT wrapped and should not be unwrapped
        # - Filenames are preserved, but content is unwrapped

        # Mapping of filename stems to their internal wrapping keys
        unwrap_mapping = {
            "characters": "characters",
            "relationships": "relationship_axes",
            "scenes": "scene_phases",
            "triggers": "trigger_types",
            "endings": "ending_types",
            "transitions": "phase_transitions",
            "escalation_axes": "escalation_axes",
            "apartment_layout": "apartment_layout",
            "premise_and_backstory": "premise_and_backstory",
            "actor_pressure_profiles": "actor_pressure_profiles",
            "phase_beat_policy": "phase_beat_policy",
            "narrator_sensory_palette": "narrator_sensory_palette",
            "opening_scene_sequence": "opening_scene_sequence",
            "opening_quote_anchors": "opening_quote_anchors",
            "hard_forbidden_rules": "hard_forbidden_rules",
            "modularity_policy": "modularity_policy",
            "scene_graph": "scene_graph",
            "canonical_path": "canonical_path",
            "locations": "locations",
            "objects": "objects",
            "content_access_policy": "content_access_policy",
        }

        # Iterate over a copy of items to avoid "dictionary keys changed during iteration" error
        for filename, content in list(result.items()):
            if filename != "module" and isinstance(content, dict):
                # relationships.yaml may contain both relationship_axes and pairwise relationships;
                # keep both so structure validation can map them into ContentModule.
                if filename == "relationships" and "relationship_axes" in content:
                    result[filename] = {
                        "relationship_axes": content["relationship_axes"],
                        "relationship_pair_definitions": content.get("relationships", {}),
                        "stability_constraints": content.get("stability_constraints", {}),
                    }
                    continue
                # Check if this filename has a known unwrap mapping
                if filename in unwrap_mapping:
                    wrapping_key = unwrap_mapping[filename]
                    # If content has the wrapping key, unwrap it
                    if wrapping_key in content:
                        # Extract the content under the wrapping key
                        result[filename] = content[wrapping_key]

        return result


class ModuleStructureValidator:
    """Validates module structure against Pydantic models.

    This validator performs non-fail-fast validation, collecting all Pydantic
    validation errors before raising a ModuleStructureError with complete
    error information.
    """

    def validate_structure(self, raw_data: dict[str, dict]) -> ContentModule:
        """Validate and construct a ContentModule from raw parsed data.

        Takes a dictionary of parsed YAML files and attempts to construct a
        ContentModule instance. All Pydantic validation errors are collected
        and included in the exception if validation fails.

        Assembly pipeline:
        1. Load all YAML files into raw_data dict
        2. Map field names (trigger_types → trigger_definitions, etc.)
        3. Extract 'module' key and move to 'metadata'
        4. Validate with Pydantic (which converts dicts to model instances)

        Args:
            raw_data: Dictionary mapping file identifiers to parsed YAML content.
                     Expected keys typically include 'module', 'characters',
                     'relationship_axes', 'trigger_types', 'scene_phases',
                     'phase_transitions', and 'ending_types'.

        Returns:
            A validated ContentModule instance.

        Raises:
            ModuleStructureError: If validation fails, containing all validation errors.
        """
        # Step 1: Map filename keys to proper ContentModule field names
        # After unwrapping in the loader, we have filename stems as keys (triggers, endings,
        # scenes, transitions, relationships) with their unwrapped content. We need to map
        # these to the ContentModule field names.

        # Map triggers or trigger_types -> trigger_definitions
        if "triggers" in raw_data:
            raw_data["trigger_definitions"] = raw_data.pop("triggers")
        elif "trigger_types" in raw_data:
            raw_data["trigger_definitions"] = raw_data.pop("trigger_types")

        # Map endings or ending_types -> ending_conditions
        if "endings" in raw_data:
            raw_data["ending_conditions"] = raw_data.pop("endings")
        elif "ending_types" in raw_data:
            raw_data["ending_conditions"] = raw_data.pop("ending_types")

        # Legacy support: old phase files -> scene_phases. New modules should use
        # phase_beat_policy.yaml as the coarse phase authority.
        if "scenes" in raw_data:
            raw_data["scene_phases"] = raw_data.pop("scenes")
        elif "scene_phases" not in raw_data:
            raw_data["scene_phases"] = _derive_scene_phases_from_phase_beat_policy(
                raw_data.get("phase_beat_policy") if isinstance(raw_data.get("phase_beat_policy"), dict) else {}
            )

        # Map transitions -> phase_transitions
        if "transitions" in raw_data:
            raw_data["phase_transitions"] = raw_data.pop("transitions")

        # Map relationships (file) -> relationship_axes (+ optional pairwise definitions)
        if "relationships" in raw_data:
            relationships_content = raw_data.pop("relationships")
            if isinstance(relationships_content, list):
                relationships_dict = {
                    rel.get("id", f"rel_{i}"): rel for i, rel in enumerate(relationships_content)
                }
                raw_data["relationship_axes"] = relationships_dict
            elif isinstance(relationships_content, dict) and "relationship_axes" in relationships_content:
                raw_data["relationship_axes"] = relationships_content["relationship_axes"]
                pairs = relationships_content.get("relationship_pair_definitions", {})
                if isinstance(pairs, dict):
                    raw_data["relationship_definitions"] = pairs
            elif isinstance(relationships_content, dict):
                raw_data["relationship_axes"] = relationships_content

        # Ensure escalation_axes is passed through correctly
        if "escalation_axes" in raw_data and not isinstance(raw_data["escalation_axes"], dict):
            # If it's not already a dict, wrap it or convert as needed
            if raw_data["escalation_axes"] is None:
                raw_data["escalation_axes"] = {}

        # Step 2: Extract 'module' key and move to 'metadata'
        # The module.yaml file contains module_id, title, version, etc. in the 'module' key
        # but ContentModule expects these in the 'metadata' field as a ModuleMetadata object
        if "module" in raw_data:
            raw_data["metadata"] = raw_data.pop("module")

        try:
            return ContentModule(**raw_data)
        except ValidationError as e:
            # Collect all validation errors with descriptive messages
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"{loc}: {msg}")

            # Extract module_id from metadata if available
            module_id = "unknown"
            if "metadata" in raw_data and isinstance(raw_data["metadata"], dict):
                module_id = raw_data["metadata"].get("module_id", "unknown")

            raise ModuleStructureError(
                message="Content module structure validation failed",
                module_id=module_id,
                errors=error_messages,
            )


def load_module(
    module_id: str,
    *,
    root_path: Path | None = None,
) -> ContentModule:
    """Load and validate a content module.

    Loads all YAML files from a module directory, validates the structure,
    and returns a fully constructed ContentModule instance.

    Args:
        module_id: The unique identifier of the module to load.
        root_path: Optional *modules root* (parent of ``<module_id>/``). If omitted,
                  uses the repository ``content/modules`` directory (next to ``backend/``).

    Returns:
        A validated ContentModule instance.

    Raises:
        ModuleNotFoundError: If the module directory cannot be found.
        ModuleFileReadError: If module files cannot be read.
        ModuleParseError: If any YAML file fails to parse.
        ModuleStructureError: If the module structure is invalid.

    Example:
        >>> module = load_module("god_of_carnage")
        >>> print(module.metadata.title)
    """
    if root_path is None:
        modules_root = content_modules_root()
    else:
        modules_root = Path(root_path) if isinstance(root_path, str) else root_path

    requested_id = (module_id or "").strip()
    directory_id = resolve_content_module_directory_id(requested_id)
    module_root = modules_root / directory_id

    # Check if module directory exists before attempting to load
    if not module_root.exists():
        raise ModuleNotFoundError(
            message=f"Module not found",
            module_id=requested_id,
            file_path=str(module_root),
        )

    # Load all YAML files from the module directory
    loader = ModuleFileLoader()
    try:
        raw_data = loader.load_all_module_files(module_root)
    except (ModuleFileReadError, ModuleParseError):
        # Re-raise with proper module_id context
        raise

    # Validate and construct the ContentModule
    validator = ModuleStructureValidator()
    module = validator.validate_structure(raw_data)

    return module
