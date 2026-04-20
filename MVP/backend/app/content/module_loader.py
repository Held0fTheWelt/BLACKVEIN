"""
Module loader for content modules.

Handles loading, parsing, and validating content modules from YAML files
in a structured module directory. Provides non-fail-fast validation that
collects all errors before raising exceptions.
"""

from __future__ import annotations

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


def content_modules_root() -> Path:
    """Absolute path to ``content/modules`` at the repository root (sibling of ``backend/``)."""
    # This file: backend/app/content/module_loader.py
    return Path(__file__).resolve().parent.parent.parent.parent / "content" / "modules"


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

        result = {}
        for yaml_file in yaml_files:
            filename = yaml_file.stem  # filename without .yaml extension
            result[filename] = self.load_file(yaml_file)

        # Unwrap nested dictionaries where YAML files wrap content under a root key.
        #
        # Most YAML files are structured as:
        #   characters.yaml:
        #     characters:
        #       veronique: {...}
        #   relationships.yaml:
        #     relationship_axes:
        #       axis_1: {...}
        #   scenes.yaml:
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

        # Map scenes -> scene_phases
        if "scenes" in raw_data:
            raw_data["scene_phases"] = raw_data.pop("scenes")

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

    module_root = modules_root / module_id

    # Check if module directory exists before attempting to load
    if not module_root.exists():
        raise ModuleNotFoundError(
            message=f"Module not found",
            module_id=module_id,
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
