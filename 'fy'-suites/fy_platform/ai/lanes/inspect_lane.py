"""Inspect lane: Read-only structure and behavior analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import Contract, StructureFinding


class InspectLane:
    """Inspect lane provides read-only analysis of repository structure.

    This lane is used by:
    - contractify: Discover and audit API contracts
    - docify: Analyze docstring coverage
    - despaghettify: Detect structural issues
    - testify: Analyze test coverage
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the inspect lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for suite-specific inspection logic.
            If None, lane operates in platform mode.
        """
        self.adapter = adapter
        self.findings: list[Any] = []
        self.contracts: list[Contract] = []
        self.metadata: dict[str, Any] = {}

    def analyze(self, target: Path, mode: str = 'standard') -> dict[str, Any]:
        """Run analysis on a target repository.

        Parameters
        ----------
        target
            Path to repository or artifact to inspect
        mode
            Inspection mode: 'standard', 'deep', 'cross-suite'

        Returns
        -------
        dict
            Analysis results with findings and contracts
        """
        if self.adapter:
            # Delegate to suite-specific adapter
            result = self._adapter_inspect(target, mode)
        else:
            # Platform-level inspection
            result = self._platform_inspect(target, mode)

        self.metadata['target'] = str(target)
        self.metadata['mode'] = mode

        return result

    def _adapter_inspect(self, target: Path, mode: str) -> dict[str, Any]:
        """Delegate to suite adapter's inspect capability."""
        return {
            'adapter': self.adapter.suite,
            'target': str(target),
            'mode': mode,
            'status': 'delegated_to_adapter',
        }

    def _platform_inspect(self, target: Path, mode: str) -> dict[str, Any]:
        """Platform-level inspection (basic structure analysis)."""
        return {
            'target': str(target),
            'mode': mode,
            'findings': [],
            'contracts': [],
            'status': 'no_adapter',
        }

    def get_findings(self) -> list[Any]:
        """Return collected findings."""
        return self.findings

    def get_contracts(self) -> list[Contract]:
        """Return discovered contracts."""
        return self.contracts
