"""PreCheck lane: Deterministic validation before model work."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.contracts import PolicyDecision, PreCheckResult


class PreCheckLane:
    """PreCheck lane provides deterministic validation and policy enforcement.

    Rules are registered via register_rule() and checked via validate().
    This lane prevents bad inputs and runaway costs before model work begins.

    Used by:
    - Platform CLI (fy govern --mode policy-check, fy govern --mode cost-check)
    - GovernLane (as prerequisite before GenerateLane)
    """

    def __init__(self, adapter: BaseSuiteAdapter | None = None) -> None:
        """Initialize the precheck lane.

        Parameters
        ----------
        adapter
            Optional suite adapter for suite-specific validation rules.
        """
        self.adapter = adapter
        self.rules: dict[str, Callable[[Path, str], PolicyDecision | None]] = {}
        self.violations: list[PolicyDecision] = []
        self.metadata: dict[str, Any] = {}

    def register_rule(
        self,
        rule_name: str,
        checker: Callable[[Path, str], PolicyDecision | None],
    ) -> None:
        """Register a validation rule.

        Parameters
        ----------
        rule_name
            Unique identifier for this rule (e.g., 'file_size_limit').
        checker
            Callable that takes (target: Path, mode: str) and returns
            PolicyDecision if violated, or None if valid.
        """
        self.rules[rule_name] = checker

    def validate(self, target: Path, mode: str = 'policy-check') -> PreCheckResult:
        """Run validation on a target.

        Parameters
        ----------
        target
            Path to repository or artifact to validate.
        mode
            Validation mode: 'policy-check', 'cost-check', 'full'.

        Returns
        -------
        PreCheckResult
            Result with violations and is_valid flag.
        """
        self.violations = []

        # Run built-in rules
        if mode in ('policy-check', 'full'):
            self._run_builtin_rules(target, mode)

        # Run registered rules
        for rule_name, checker in self.rules.items():
            try:
                violation = checker(target, mode)
                if violation:
                    self.violations.append(violation)
            except Exception as exc:
                # Record rule errors as violations
                error_decision = PolicyDecision(
                    policy_id=f'policy-{rule_name}-error',
                    rule_name=rule_name,
                    decision='escalate',
                    evidence=f'Rule check failed: {str(exc)}',
                )
                self.violations.append(error_decision)

        result = PreCheckResult(
            target=str(target),
            mode=mode,
            is_valid=len(self.violations) == 0,
            violations=self.violations,
        )
        return result

    def _run_builtin_rules(self, target: Path, mode: str) -> None:
        """Run built-in validation rules."""
        # File existence check
        if not target.exists():
            violation = PolicyDecision(
                policy_id='policy-target-exists',
                rule_name='target_exists',
                decision='deny',
                evidence=f'Target does not exist: {target}',
            )
            self.violations.append(violation)
            return  # No point checking other rules if target is missing

        # File size limit (10GB for archives, 1GB for directories)
        if target.is_file():
            size_bytes = target.stat().st_size
            limit_bytes = 10 * 1024 * 1024 * 1024  # 10GB
            if size_bytes > limit_bytes:
                violation = PolicyDecision(
                    policy_id='policy-file-size-limit',
                    rule_name='file_size_limit',
                    decision='deny',
                    evidence=f'File {target.name} exceeds limit: {size_bytes} > {limit_bytes} bytes',
                    metadata={
                        'limit_bytes': limit_bytes,
                        'actual_bytes': size_bytes,
                        'file_path': str(target),
                    },
                )
                self.violations.append(violation)

    def get_violations(self) -> list[PolicyDecision]:
        """Return detected violations."""
        return self.violations
