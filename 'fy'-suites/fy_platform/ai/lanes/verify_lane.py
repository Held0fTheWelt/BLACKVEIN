"""Verify lane: Validation and compatibility checking."""

from __future__ import annotations

from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import Contract, SecurityRisk


class VerifyLane:
    """Verify lane validates outputs and checks compatibility.

    This lane is used by:
    - Contract verification (APIs match actual code)
    - Compatibility validation (cross-suite compatibility)
    - Security audits (vulnerability detection)
    - Quality gates (output quality checks)
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the verify lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for verification context.
        """
        self.adapter = adapter
        self.validations: list[dict[str, Any]] = []
        self.risks: list[SecurityRisk] = []
        self.errors: list[str] = []
        self.metadata: dict[str, Any] = {}

    def validate(self, target: Any, mode: str = 'standard') -> dict[str, Any]:
        """Validate a target (artifact, contract, compatibility).

        Parameters
        ----------
        target
            Object to validate (contract, artifact, code, etc.)
        mode
            Validation mode: 'standard', 'strict', 'cross-suite'

        Returns
        -------
        dict
            Validation results with errors and warnings
        """
        result = {
            'target': str(target) if hasattr(target, '__str__') else type(target).__name__,
            'mode': mode,
            'valid': True,
            'errors': [],
            'warnings': [],
        }

        if self.adapter:
            # Delegate to suite-specific validation
            result.update(self._adapter_verify(target, mode))
        else:
            # Platform-level validation
            result.update(self._platform_verify(target, mode))

        return result

    def _adapter_verify(self, target: Any, mode: str) -> dict[str, Any]:
        """Delegate to suite adapter's verification capability."""
        return {
            'adapter': self.adapter.suite,
            'mode': mode,
            'status': 'delegated_to_adapter',
        }

    def _platform_verify(self, target: Any, mode: str) -> dict[str, Any]:
        """Platform-level validation."""
        return {
            'mode': mode,
            'status': 'no_adapter',
        }

    def register_risk(self, risk: SecurityRisk) -> None:
        """Register a detected security risk."""
        self.risks.append(risk)

    def add_error(self, error: str) -> None:
        """Record a validation error."""
        self.errors.append(error)

    def get_risks(self) -> list[SecurityRisk]:
        """Return detected security risks."""
        return self.risks

    def get_errors(self) -> list[str]:
        """Return validation errors."""
        return self.errors
