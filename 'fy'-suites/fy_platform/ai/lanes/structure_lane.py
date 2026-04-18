"""Structure lane: Refactoring and organizational changes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import StructureFinding, DecisionRecord


class StructureLane:
    """Structure lane guides refactoring and codebase organization.

    This lane is used by:
    - despaghettify: Plan and guide refactoring (spike extraction)
    - base_adapter thinning: Extract mechanical responsibilities
    - cross-suite consolidation: Unify related functionality
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the structure lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for structure context.
        """
        self.adapter = adapter
        self.findings: list[StructureFinding] = []
        self.plans: list[dict[str, Any]] = []
        self.decisions: list[DecisionRecord] = []
        self.metadata: dict[str, Any] = {}

    def analyze(self, target: Path, mode: str = 'standard') -> dict[str, Any]:
        """Analyze structure and plan refactoring.

        Parameters
        ----------
        target
            Path to codebase or module to analyze
        mode
            Analysis mode: 'standard', 'platform', 'wave-plan'

        Returns
        -------
        dict
            Structural findings and refactoring plan
        """
        result = {
            'target': str(target),
            'mode': mode,
            'findings': [],
            'plans': [],
            'decisions': [],
        }

        if self.adapter:
            # Delegate to suite-specific analysis
            result.update(self._adapter_analyze(target, mode))
        else:
            # Platform-level structure analysis
            result.update(self._platform_analyze(target, mode))

        return result

    def _adapter_analyze(self, target: Path, mode: str) -> dict[str, Any]:
        """Delegate to suite adapter's structure analysis."""
        return {
            'adapter': self.adapter.suite,
            'mode': mode,
            'status': 'delegated_to_adapter',
        }

    def _platform_analyze(self, target: Path, mode: str) -> dict[str, Any]:
        """Platform-level structure analysis."""
        return {
            'mode': mode,
            'status': 'no_adapter',
        }

    def register_finding(self, finding: StructureFinding) -> None:
        """Register a structural finding."""
        self.findings.append(finding)

    def add_plan(self, plan: dict[str, Any]) -> None:
        """Add a refactoring plan."""
        self.plans.append(plan)

    def record_decision(self, decision: DecisionRecord) -> None:
        """Record a structural decision."""
        self.decisions.append(decision)

    def get_findings(self) -> list[StructureFinding]:
        """Return structural findings."""
        return self.findings

    def get_plans(self) -> list[dict[str, Any]]:
        """Return refactoring plans."""
        return self.plans

    def get_decisions(self) -> list[DecisionRecord]:
        """Return recorded decisions."""
        return self.decisions
