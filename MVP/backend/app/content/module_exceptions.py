"""
Exception hierarchy for content module operations.

Provides structured exceptions for module loading, validation, and processing
with support for detailed error reporting including module IDs, file paths,
and lists of validation errors.
"""

from __future__ import annotations


class ModuleLoadError(RuntimeError):
    """Base exception for module loading failures.

    Attributes:
        message: Error message
        module_id: ID of the module that failed to load
        file_path: Optional path to the file that caused the error
        errors: Optional list of detailed errors
    """

    def __init__(
        self,
        message: str,
        module_id: str,
        file_path: str | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize ModuleLoadError.

        Args:
            message: Error message describing what went wrong
            module_id: ID of the module involved
            file_path: Optional path to the file involved
            errors: Optional list of detailed error messages
        """
        self.message = message
        self.module_id = module_id
        self.file_path = file_path
        self.errors = errors or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format a detailed error message."""
        lines = [f"Module Load Error [{self.module_id}]: {self.message}"]
        if self.file_path:
            lines.append(f"  File: {self.file_path}")
        if self.errors:
            lines.append("  Details:")
            for error in self.errors:
                lines.append(f"    - {error}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


class ModuleNotFoundError(ModuleLoadError):
    """Exception raised when a module cannot be found."""

    pass


class ModuleFileReadError(ModuleLoadError):
    """Exception raised when a module file cannot be read."""

    pass


class ModuleParseError(ModuleLoadError):
    """Exception raised when a module file cannot be parsed."""

    pass


class ModuleValidationError(RuntimeError):
    """Base exception for module validation failures.

    Attributes:
        message: Error message
        module_id: ID of the module that failed validation
        file_path: Optional path to the file that caused the error
        errors: Optional list of detailed validation errors
    """

    def __init__(
        self,
        message: str,
        module_id: str,
        file_path: str | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize ModuleValidationError.

        Args:
            message: Error message describing what went wrong
            module_id: ID of the module involved
            file_path: Optional path to the file involved
            errors: Optional list of detailed error messages
        """
        self.message = message
        self.module_id = module_id
        self.file_path = file_path
        self.errors = errors or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format a detailed error message."""
        lines = [f"Module Validation Error [{self.module_id}]: {self.message}"]
        if self.file_path:
            lines.append(f"  File: {self.file_path}")
        if self.errors:
            lines.append("  Issues:")
            for error in self.errors:
                lines.append(f"    - {error}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


class ModuleStructureError(ModuleValidationError):
    """Exception raised when module structure is invalid."""

    pass


class ModuleCrossReferenceError(ModuleValidationError):
    """Exception raised when module cross-references are invalid."""

    pass


class ModuleConstraintError(ModuleValidationError):
    """Exception raised when module constraints are violated."""

    pass
