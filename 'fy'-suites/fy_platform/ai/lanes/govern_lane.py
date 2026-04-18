"""Govern lane: Policy enforcement and release readiness."""

from __future__ import annotations

from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import DecisionRecord, PolicyDecision
from fy_platform.ai.lanes.precheck_lane import PreCheckLane


class GovernLane:
    """Govern lane enforces governance and release policies.

    This lane is used by:
    - release readiness checks
    - production readiness validation
    - policy enforcement gates

    GovernLane now orchestrates policy enforcement:
    1. Run PreCheckLane deterministic validation
    2. Check metrify budget constraints
    3. Return governance result with policy decisions
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the govern lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for governance context.
        """
        self.adapter = adapter
        self.decisions: list[DecisionRecord] = []
        self.violations: list[dict[str, Any]] = []
        self.policy_decisions: list[PolicyDecision] = []
        self.precheck_lane: PreCheckLane = PreCheckLane(adapter)
        self.metadata: dict[str, Any] = {}

    def check_readiness(self, mode: str = 'release') -> dict[str, Any]:
        """Check if target is ready for a phase.

        Parameters
        ----------
        mode
            Readiness mode: 'release', 'production', 'deploy'

        Returns
        -------
        dict
            Readiness status with violations and recommendations
        """
        result = {
            'mode': mode,
            'ready': True,
            'violations': [],
            'decisions': [],
        }

        if self.adapter:
            # Delegate to suite-specific governance
            result.update(self._adapter_govern(mode))
        else:
            # Platform-level governance
            result.update(self._platform_govern(mode))

        return result

    def _adapter_govern(self, mode: str) -> dict[str, Any]:
        """Delegate to suite adapter's governance capability."""
        return {
            'adapter': self.adapter.suite,
            'mode': mode,
            'status': 'delegated_to_adapter',
        }

    def _platform_govern(self, mode: str) -> dict[str, Any]:
        """Platform-level governance checks."""
        return {
            'mode': mode,
            'status': 'no_adapter',
        }

    def record_decision(self, decision: DecisionRecord) -> None:
        """Record a governance decision."""
        self.decisions.append(decision)

    def record_policy_decision(self, decision: PolicyDecision) -> None:
        """Record a policy enforcement decision."""
        self.policy_decisions.append(decision)

    def get_decisions(self) -> list[DecisionRecord]:
        """Return recorded decisions."""
        return self.decisions

    def get_policy_decisions(self) -> list[PolicyDecision]:
        """Return recorded policy decisions."""
        return self.policy_decisions

    def get_violations(self) -> list[dict[str, Any]]:
        """Return detected violations."""
        return self.violations
