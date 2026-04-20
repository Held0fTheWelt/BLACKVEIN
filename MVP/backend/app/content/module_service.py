"""High-level service for content module orchestration.

Provides a unified interface for loading, validating, and managing content modules.
Coordinates between the module loader, validator, and models to provide
comprehensive module handling with non-fail-fast operations where appropriate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .module_exceptions import (
    ModuleLoadError,
    ModuleNotFoundError,
    ModuleValidationError,
)
from .module_loader import (
    ModuleFileLoader,
    ModuleStructureValidator,
    content_modules_root,
    load_module,
)
from .module_models import ContentModule
from .module_validator import ModuleCrossReferenceValidator, ValidationResult


class ModuleService:
    """High-level orchestration interface for content module operations.

    Provides methods for loading, validating, and querying content modules.
    Handles coordination between file loading, structure validation, and
    cross-reference validation with appropriate error handling and reporting.

    Attributes:
        root_path: Path to the root directory containing module subdirectories.
    """

    def __init__(self, *, root_path: Path | None = None) -> None:
        """Initialize the ModuleService.

        Args:
            root_path: Optional *modules root* (directory containing ``<module_id>/``).
                      If omitted, uses the repository ``content/modules`` next to ``backend/``.
        """
        if root_path is None:
            self.root_path = content_modules_root()
        else:
            # Convert to Path if string, keep as Path if already Path
            self.root_path = Path(root_path) if isinstance(root_path, str) else root_path

    def load_and_validate(self, module_id: str) -> dict[str, Any]:
        """Load and validate a content module.

        Performs a three-phase operation:
        - Phase 1: Load YAML files using ModuleFileLoader
        - Phase 2: Validate structure using ModuleStructureValidator
        - Phase 3: Validate cross-references using ModuleCrossReferenceValidator

        Args:
            module_id: The unique identifier of the module to load and validate.

        Returns:
            Dictionary containing:
            - "module": ContentModule instance (fully validated)
            - "validation": ValidationResult with all validation details

        Raises:
            ModuleNotFoundError: If module directory cannot be found.
            ModuleLoadError: If module files cannot be loaded or parsed.
            ModuleValidationError: If module structure or cross-references are invalid.

        Example:
            >>> result = service.load_and_validate("god_of_carnage")
            >>> module = result["module"]
            >>> validation = result["validation"]
            >>> if validation.is_valid:
            ...     print(f"Module {module.metadata.title} loaded successfully")
        """
        # Phase 1: Load module (this handles file loading and structure validation)
        module = self._load_module_internal(module_id)

        # Phase 2: Validate cross-references
        validator = ModuleCrossReferenceValidator()
        validation_result = validator.validate_all(module)

        # Phase 3: Check validation results - raise if invalid
        if not validation_result.is_valid:
            raise ModuleValidationError(
                message="Module cross-reference validation failed",
                module_id=module_id,
                errors=validation_result.errors,
            )

        return {
            "module": module,
            "validation": validation_result,
        }

    def preflight_check(self, module_id: str) -> ValidationResult:
        """Perform validation without instantiation or raising exceptions.

        Loads the module and runs all validation checks but returns the result
        instead of raising exceptions. This allows for non-blocking validation
        and inspection of issues without halting execution.

        Args:
            module_id: The unique identifier of the module to check.

        Returns:
            ValidationResult containing validation status, errors, warnings,
            and timing information.

        Example:
            >>> result = service.preflight_check("god_of_carnage")
            >>> if not result.is_valid:
            ...     for error in result.errors:
            ...         print(f"Error: {error}")
        """
        try:
            module = self._load_module_internal(module_id)
        except (ModuleLoadError, ModuleValidationError):
            # If loading/validation fails, return invalid result
            return ValidationResult(
                is_valid=False,
                module_id=module_id,
                errors=["Failed to load module"],
                warnings=[],
                validation_time_ms=0.0,
            )

        # Run validation and return result (no exceptions)
        validator = ModuleCrossReferenceValidator()
        return validator.validate_all(module)

    def list_available_modules(self) -> list[str]:
        """List all available module IDs in the module directory.

        Scans the root_path/content/modules/ directory and returns a sorted list
        of subdirectory names, each representing a module ID.

        Returns:
            Sorted list of module IDs (subdirectory names).
            Returns empty list if root directory doesn't exist.

        Example:
            >>> modules = service.list_available_modules()
            >>> print(f"Available modules: {', '.join(modules)}")
        """
        if not self.root_path.exists():
            return []

        try:
            # Get all subdirectories
            subdirs = sorted(
                [d.name for d in self.root_path.iterdir() if d.is_dir()]
            )
            return subdirs
        except (PermissionError, OSError):
            # Non-fail-fast: return empty list on error
            return []

    def get_module_metadata(self, module_id: str) -> dict[str, Any]:
        """Load and return only module metadata without full validation.

        Loads only the module.yaml file and returns metadata fields without
        loading or validating the full module. This is a lightweight operation
        useful for checking module compatibility and basic information.

        Args:
            module_id: The unique identifier of the module.

        Returns:
            Dictionary containing metadata fields:
            - module_id: Module identifier
            - title: Human-readable module title
            - version: Module version (semantic versioning)
            - contract_version: Content module contract version
            - content: Module description (if available)
            - files: Module files mapping (if available)

        Raises:
            ModuleNotFoundError: If module directory cannot be found.
            ModuleLoadError: If module.yaml cannot be loaded or parsed.

        Example:
            >>> metadata = service.get_module_metadata("god_of_carnage")
            >>> print(f"{metadata['title']} v{metadata['version']}")
        """
        module_path = self.root_path / module_id

        if not module_path.exists():
            raise ModuleNotFoundError(
                message="Module not found",
                module_id=module_id,
                file_path=str(module_path),
            )

        # Load only module.yaml
        metadata_path = module_path / "module.yaml"
        if not metadata_path.exists():
            raise ModuleNotFoundError(
                message="Module file not found (module.yaml)",
                module_id=module_id,
                file_path=str(metadata_path),
            )

        loader = ModuleFileLoader()
        metadata_data = loader.load_file(metadata_path)

        # Extract metadata fields
        return {
            "module_id": metadata_data.get("module_id", module_id),
            "title": metadata_data.get("title", ""),
            "version": metadata_data.get("version", ""),
            "contract_version": metadata_data.get("contract_version", ""),
            "content": metadata_data.get("content", ""),
            "files": metadata_data.get("files", {}),
        }

    def _load_module_internal(self, module_id: str) -> ContentModule:
        """Internal helper to load and validate module structure.

        Uses the module_loader.load_module function with the configured root path
        to perform Phase 1 (file loading) and Phase 2 (structure validation).

        Args:
            module_id: The unique identifier of the module.

        Returns:
            ContentModule instance with validated structure.

        Raises:
            ModuleNotFoundError: If module directory cannot be found.
            ModuleLoadError: If module files cannot be loaded or parsed.
            ModuleValidationError: If module structure is invalid.
        """
        return load_module(module_id, root_path=self.root_path)
