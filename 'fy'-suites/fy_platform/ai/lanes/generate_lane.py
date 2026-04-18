"""Generate lane: Artifact and plan creation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import Contract, TestObligation, DocumentationObligation


class GenerateLane:
    """Generate lane creates artifacts, contracts, and plans.

    This lane is used by:
    - contractify: Emit OpenAPI and interface contracts
    - documentify: Generate multi-track documentation
    - testify: Plan test consolidation
    - despaghettify: Emit wave plans
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the generate lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for generation context.
        """
        self.adapter = adapter
        self.artifacts: list[dict[str, Any]] = []
        self.contracts: list[Contract] = []
        self.obligations: list[TestObligation | DocumentationObligation] = []
        self.metadata: dict[str, Any] = {}

    def generate(self, source: Path, mode: str = 'standard') -> dict[str, Any]:
        """Generate artifacts from analysis.

        Parameters
        ----------
        source
            Source analysis or target repository
        mode
            Generation mode: 'standard', 'draft', 'strict'

        Returns
        -------
        dict
            Generated artifacts and metadata
        """
        result = {
            'source': str(source),
            'mode': mode,
            'artifacts': [],
            'contracts': [],
            'obligations': [],
        }

        if self.adapter:
            # Delegate to suite-specific generation
            result.update(self._adapter_generate(source, mode))
        else:
            # Platform-level generation
            result.update(self._platform_generate(source, mode))

        return result

    def _adapter_generate(self, source: Path, mode: str) -> dict[str, Any]:
        """Delegate to suite adapter's generation capability."""
        return {
            'adapter': self.adapter.suite,
            'mode': mode,
            'status': 'delegated_to_adapter',
        }

    def _platform_generate(self, source: Path, mode: str) -> dict[str, Any]:
        """Platform-level artifact generation."""
        return {
            'mode': mode,
            'status': 'no_adapter',
        }

    def register_contract(self, contract: Contract) -> None:
        """Register a discovered or generated contract."""
        self.contracts.append(contract)

    def register_obligation(self, obligation: TestObligation | DocumentationObligation) -> None:
        """Register a test or documentation obligation."""
        self.obligations.append(obligation)

    def get_contracts(self) -> list[Contract]:
        """Return generated contracts."""
        return self.contracts

    def get_obligations(self) -> list[TestObligation | DocumentationObligation]:
        """Return generated obligations."""
        return self.obligations

    def get_artifacts(self) -> list[dict[str, Any]]:
        """Return generated artifacts."""
        return self.artifacts
