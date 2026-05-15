"""ADR-0041 validator dispatch from a local execution plan.

Default mode is ``dry_run``: projection-only evidence with no validator execution.
``plan_enforced`` is opt-in via ``ADR0041_VALIDATOR_DISPATCH_MODE`` or an explicit
test-harness ``mode`` plus a registered local validator registry.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ai_stack.capability_selector import (
    LOCAL_SELECTION_EVIDENCE_SCOPE,
    LOCAL_SELECTION_PROOF_LEVEL,
    validate_semantic_capability_name,
)
from ai_stack.capability_validator_plan import (
    VALIDATOR_EXECUTION_PLAN_SCHEMA_VERSION,
    ValidatorExecutionPlan,
    ValidatorPlanEntry,
    ValidatorPlanMode,
)

ADR0041_VALIDATOR_DISPATCH_MODE_ENV = "ADR0041_VALIDATOR_DISPATCH_MODE"
VALIDATOR_DISPATCH_REPORT_SCHEMA_VERSION = "validator_dispatch_report.v1"
DEFAULT_VALIDATOR_DISPATCH_MODE = "dry_run"
DISPATCH_REPORT_REASON = (
    "ADR-0041 dry-run dispatch projection only; default validator execution unchanged."
)
PLAN_ENFORCED_DISPATCH_REASON = (
    "ADR-0041 plan-enforced local dispatch; explicit opt-in only; not production default."
)

LocalValidatorCallable = Callable[[ValidatorPlanEntry, dict[str, Any]], dict[str, Any] | None]
ValidatorRegistry = Mapping[str, LocalValidatorCallable]


class ValidatorDispatchMode(str, Enum):
    """How dispatch interprets a validator execution plan."""

    DRY_RUN = "dry_run"
    PLAN_ENFORCED = "plan_enforced"


class ValidatorDispatchAction(str, Enum):
    """Planned dispatch action for one validator, diagnostic, or judge ID."""

    RUN = "run"
    OBSERVE = "observe"
    SKIP = "skip"
    DISALLOW_JUDGE = "disallow_judge"


def _coerce_dispatch_mode(value: ValidatorDispatchMode | str | None) -> ValidatorDispatchMode:
    if value is None:
        return ValidatorDispatchMode.DRY_RUN
    if isinstance(value, ValidatorDispatchMode):
        return value
    text = str(value or "").strip()
    for item in ValidatorDispatchMode:
        if item.value == text:
            return item
    allowed = ", ".join(item.value for item in ValidatorDispatchMode)
    raise ValueError(f"Unsupported ValidatorDispatchMode: {text!r}; expected one of {allowed}")


def resolve_validator_dispatch_mode(
    *,
    explicit_mode: ValidatorDispatchMode | str | None = None,
    env_value: str | None = None,
) -> tuple[ValidatorDispatchMode, tuple[str, ...]]:
    """Resolve dispatch mode: explicit override, then env, else dry_run.

    Missing or invalid env values fail closed to ``dry_run`` with a warning.
    """
    warnings: list[str] = []
    if explicit_mode is not None:
        return _coerce_dispatch_mode(explicit_mode), tuple(warnings)

    raw = env_value
    if raw is None:
        raw = os.environ.get(ADR0041_VALIDATOR_DISPATCH_MODE_ENV)
    text = str(raw or "").strip().lower()
    if not text or text == ValidatorDispatchMode.DRY_RUN.value:
        return ValidatorDispatchMode.DRY_RUN, tuple(warnings)
    if text == ValidatorDispatchMode.PLAN_ENFORCED.value:
        return ValidatorDispatchMode.PLAN_ENFORCED, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_VALIDATOR_DISPATCH_MODE_ENV}={raw!r}; "
        f"falling back to {ValidatorDispatchMode.DRY_RUN.value}."
    )
    return ValidatorDispatchMode.DRY_RUN, tuple(warnings)


def _validate_registry(registry: ValidatorRegistry | None) -> dict[str, LocalValidatorCallable]:
    if registry is None:
        return {}
    validated: dict[str, LocalValidatorCallable] = {}
    for key, callable_obj in registry.items():
        validator_id = validate_semantic_capability_name(str(key))
        if not callable(callable_obj):
            raise TypeError(f"validator registry entry {validator_id!r} must be callable")
        validated[validator_id] = callable_obj
    return validated


def _target_id_for_entry(entry: ValidatorPlanEntry) -> str | None:
    return entry.validator_id or entry.diagnostic_id or entry.judge_id or entry.plan_id


def _planned_action_for_mode(mode: ValidatorPlanMode) -> ValidatorDispatchAction:
    if mode is ValidatorPlanMode.RUN_LOCAL_VALIDATOR:
        return ValidatorDispatchAction.RUN
    if mode is ValidatorPlanMode.RUN_OBSERVER_DIAGNOSTIC:
        return ValidatorDispatchAction.OBSERVE
    if mode is ValidatorPlanMode.SKIP_JUDGE_DISALLOWED:
        return ValidatorDispatchAction.DISALLOW_JUDGE
    if mode in {
        ValidatorPlanMode.SKIP_EXCLUDED,
        ValidatorPlanMode.SKIP_BUDGET_DISALLOWED,
        ValidatorPlanMode.RUN_JUDGE,
    }:
        return ValidatorDispatchAction.SKIP
    return ValidatorDispatchAction.SKIP


def _would_execute_for_entry(entry: ValidatorPlanEntry) -> bool:
    return entry.mode in {
        ValidatorPlanMode.RUN_LOCAL_VALIDATOR,
        ValidatorPlanMode.RUN_OBSERVER_DIAGNOSTIC,
    }


def _sanitize_local_execution_evidence(
    *,
    validator_id: str,
    raw: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize local validator returns into a bounded, JSON-safe authority evidence row."""
    vid = validate_semantic_capability_name(str(validator_id or "").strip() or "unknown")
    if not isinstance(raw, dict):
        return {
            "validator_id": vid,
            "passed": False,
            "status": "unknown",
            "blocking": True,
            "available": False,
            "proof_level": LOCAL_SELECTION_PROOF_LEVEL,
            "live_or_staging_evidence": False,
        }
    status = str(raw.get("status") or "").strip().lower()
    passed_raw = raw.get("passed")
    if passed_raw is None:
        passed = status in {"approved", "passed", "local_stub_executed", "local_executed"} and status not in {
            "rejected",
            "failed",
            "error",
            "unavailable",
        }
    else:
        passed = bool(passed_raw)
    failure_codes = raw.get("failure_codes") or []
    codes = (
        [str(x) for x in failure_codes[:16] if str(x).strip()]
        if isinstance(failure_codes, list)
        else []
    )
    return {
        "validator_id": vid,
        "passed": bool(passed),
        "status": status or ("approved" if passed else "rejected"),
        "blocking": bool(raw.get("blocking", True)),
        "available": raw.get("available") is not False,
        "proof_level": LOCAL_SELECTION_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "reason": raw.get("reason"),
        "failure_codes": codes,
    }


@dataclass(frozen=True)
class ValidatorDispatchDecision:
    """Dispatch decision for one planned validator, diagnostic, or judge entry."""

    capability: str
    planned_mode: ValidatorPlanMode | str
    dispatch_action: ValidatorDispatchAction | str
    validator_id: str | None = None
    would_execute: bool = False
    actually_executed: bool = False
    unavailable: bool = False
    reason: str = DISPATCH_REPORT_REASON
    local_execution_evidence: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability",
            validate_semantic_capability_name(self.capability),
        )
        mode = self.planned_mode
        if not isinstance(mode, ValidatorPlanMode):
            mode = ValidatorPlanMode(str(mode))
        object.__setattr__(self, "planned_mode", mode)
        action = self.dispatch_action
        if not isinstance(action, ValidatorDispatchAction):
            action = ValidatorDispatchAction(str(action))
        object.__setattr__(self, "dispatch_action", action)
        object.__setattr__(
            self,
            "validator_id",
            validate_semantic_capability_name(self.validator_id)
            if self.validator_id
            else None,
        )
        object.__setattr__(self, "would_execute", bool(self.would_execute))
        object.__setattr__(self, "actually_executed", bool(self.actually_executed))
        object.__setattr__(self, "unavailable", bool(self.unavailable))
        evidence = self.local_execution_evidence
        if evidence is not None and not isinstance(evidence, dict):
            raise TypeError("local_execution_evidence must be a dict or None")
        object.__setattr__(
            self,
            "local_execution_evidence",
            dict(evidence) if isinstance(evidence, dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["planned_mode"] = self.planned_mode.value
        payload["dispatch_action"] = self.dispatch_action.value
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class ValidatorDispatchEntry:
    """One dispatch report row tied to a plan entry."""

    capability: str
    planned_mode: ValidatorPlanMode | str
    dispatch_action: ValidatorDispatchAction | str
    validator_id: str | None = None
    would_execute: bool = False
    actually_executed: bool = False
    unavailable: bool = False
    reason: str = DISPATCH_REPORT_REASON
    local_execution_evidence: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        decision = ValidatorDispatchDecision(
            capability=self.capability,
            planned_mode=self.planned_mode,
            dispatch_action=self.dispatch_action,
            validator_id=self.validator_id,
            would_execute=self.would_execute,
            actually_executed=self.actually_executed,
            unavailable=self.unavailable,
            reason=self.reason,
            local_execution_evidence=self.local_execution_evidence,
        )
        object.__setattr__(self, "capability", decision.capability)
        object.__setattr__(self, "planned_mode", decision.planned_mode)
        object.__setattr__(self, "dispatch_action", decision.dispatch_action)
        object.__setattr__(self, "validator_id", decision.validator_id)
        object.__setattr__(self, "would_execute", decision.would_execute)
        object.__setattr__(self, "actually_executed", decision.actually_executed)
        object.__setattr__(self, "unavailable", decision.unavailable)
        object.__setattr__(self, "reason", decision.reason)
        object.__setattr__(self, "local_execution_evidence", decision.local_execution_evidence)

    def to_dict(self) -> dict[str, Any]:
        return ValidatorDispatchDecision(
            capability=self.capability,
            planned_mode=self.planned_mode,
            dispatch_action=self.dispatch_action,
            validator_id=self.validator_id,
            would_execute=self.would_execute,
            actually_executed=self.actually_executed,
            unavailable=self.unavailable,
            reason=self.reason,
            local_execution_evidence=self.local_execution_evidence,
        ).to_dict()


@dataclass(frozen=True)
class ValidatorDispatchReport:
    """Local-only dispatch report derived from one validator execution plan."""

    mode: ValidatorDispatchMode | str = ValidatorDispatchMode.DRY_RUN
    entries: tuple[ValidatorDispatchEntry, ...] = field(default_factory=tuple)
    validators_would_run: tuple[str, ...] = field(default_factory=tuple)
    diagnostics_would_run: tuple[str, ...] = field(default_factory=tuple)
    validators_would_skip: tuple[str, ...] = field(default_factory=tuple)
    judges_would_be_disallowed: tuple[str, ...] = field(default_factory=tuple)
    validators_unavailable: tuple[str, ...] = field(default_factory=tuple)
    actually_executed: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    reason: str = DISPATCH_REPORT_REASON
    proof_level: str = LOCAL_SELECTION_PROOF_LEVEL
    evidence_scope: str = LOCAL_SELECTION_EVIDENCE_SCOPE
    live_or_staging_evidence: bool = False
    execution_changed: bool = False
    implementation_proof: bool = False
    feature_flag_enabled: bool = False
    commit_gate_changed: bool = False
    readiness_gate_changed: bool = False
    judge_execution_changed: bool = False
    schema_version: str = VALIDATOR_DISPATCH_REPORT_SCHEMA_VERSION
    plan_schema_version: str = VALIDATOR_EXECUTION_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _coerce_dispatch_mode(self.mode))
        object.__setattr__(
            self,
            "entries",
            tuple(
                entry
                if isinstance(entry, ValidatorDispatchEntry)
                else ValidatorDispatchEntry(**entry)
                for entry in self.entries
            ),
        )
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings if str(item).strip()))
        object.__setattr__(self, "proof_level", LOCAL_SELECTION_PROOF_LEVEL)
        object.__setattr__(self, "evidence_scope", LOCAL_SELECTION_EVIDENCE_SCOPE)
        object.__setattr__(self, "live_or_staging_evidence", False)
        object.__setattr__(self, "implementation_proof", False)
        object.__setattr__(self, "feature_flag_enabled", bool(self.feature_flag_enabled))
        object.__setattr__(self, "commit_gate_changed", False)
        object.__setattr__(self, "readiness_gate_changed", False)
        object.__setattr__(self, "judge_execution_changed", False)
        if self.mode is ValidatorDispatchMode.DRY_RUN:
            object.__setattr__(self, "execution_changed", False)
            object.__setattr__(self, "actually_executed", tuple())
            object.__setattr__(self, "feature_flag_enabled", False)

    def to_runtime_projection(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "plan_schema_version": self.plan_schema_version,
            "mode": self.mode.value,
            "proof_level": self.proof_level,
            "evidence_scope": self.evidence_scope,
            "live_or_staging_evidence": self.live_or_staging_evidence,
            "execution_changed": self.execution_changed,
            "implementation_proof": self.implementation_proof,
            "implemented_by_runtime": False,
            "live_verified": False,
            "staging_verified": False,
            "provider_verified": False,
            "capability_promoted": False,
            "feature_flag_enabled": self.feature_flag_enabled,
            "commit_gate_changed": self.commit_gate_changed,
            "readiness_gate_changed": self.readiness_gate_changed,
            "judge_execution_changed": self.judge_execution_changed,
            "validators_would_run": list(self.validators_would_run),
            "diagnostics_would_run": list(self.diagnostics_would_run),
            "validators_would_skip": list(self.validators_would_skip),
            "judges_would_be_disallowed": list(self.judges_would_be_disallowed),
            "validators_unavailable": list(self.validators_unavailable),
            "actually_executed": list(self.actually_executed),
            "entries": [entry.to_dict() for entry in self.entries],
            "reason": self.reason,
            "warnings": list(self.warnings),
        }
        return {"validator_dispatch_report": payload}

    def to_ledger_payload(self) -> dict[str, Any]:
        return self.to_runtime_projection()

    def to_runtime_intelligence_projection(self) -> dict[str, Any]:
        return self.to_runtime_projection()


def _unique_ids(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = validate_semantic_capability_name(item)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return tuple(ordered)


def _decision_for_entry(
    entry: ValidatorPlanEntry,
    *,
    mode: ValidatorDispatchMode,
) -> ValidatorDispatchDecision:
    dispatch_action = _planned_action_for_mode(entry.mode)
    would_execute = _would_execute_for_entry(entry)
    target_id = _target_id_for_entry(entry)
    return ValidatorDispatchDecision(
        capability=entry.capability,
        planned_mode=entry.mode,
        dispatch_action=dispatch_action,
        validator_id=target_id,
        would_execute=would_execute,
        actually_executed=False,
        unavailable=False,
        reason=entry.reason,
    )


def _invoke_registered_local_validator(
    *,
    validator_id: str,
    entry: ValidatorPlanEntry,
    registry: dict[str, LocalValidatorCallable],
    dispatch_context: dict[str, Any],
) -> tuple[bool, bool, str, dict[str, Any] | None]:
    """Return (executed, unavailable, reason, local_execution_evidence)."""
    vid = validate_semantic_capability_name(str(validator_id or "").strip())
    callable_obj = registry.get(vid)
    if callable_obj is None:
        msg = f"{vid} is not registered for local plan-enforced dispatch."
        return (
            False,
            True,
            msg,
            _sanitize_local_execution_evidence(
                validator_id=vid,
                raw={"status": "unavailable", "passed": False, "available": False, "reason": msg},
            ),
        )
    try:
        result = callable_obj(entry, dispatch_context)
    except Exception as exc:  # noqa: BLE001 - surface local stub failures without false-green pass
        msg = f"{vid} local dispatch failed: {exc}"
        return (
            False,
            True,
            msg,
            _sanitize_local_execution_evidence(
                validator_id=vid,
                raw={"status": "error", "passed": False, "available": False, "reason": msg},
            ),
        )
    if not isinstance(result, dict):
        msg = f"{vid} local dispatch returned non-dict evidence."
        return (
            False,
            True,
            msg,
            _sanitize_local_execution_evidence(
                validator_id=vid,
                raw={"status": "error", "passed": False, "available": False, "reason": msg},
            ),
        )
    if result.get("available") is False:
        reason = str(result.get("reason") or "validator_not_registered").strip()
        msg = f"{vid} unavailable: {reason}."
        return (
            False,
            True,
            msg,
            _sanitize_local_execution_evidence(
                validator_id=vid,
                raw={"status": "unavailable", "passed": False, "available": False, "reason": reason},
            ),
        )
    status = str(result.get("status") or "").strip().lower()
    if status in {"unavailable", "failed", "error"}:
        msg = f"{vid} reported status={status or 'unknown'}."
        return (
            False,
            True,
            msg,
            _sanitize_local_execution_evidence(
                validator_id=vid,
                raw={
                    "status": status or "unavailable",
                    "passed": False,
                    "available": True,
                    "reason": msg,
                },
            ),
        )
    evidence = _sanitize_local_execution_evidence(validator_id=vid, raw=result)
    return True, False, f"{vid} executed via registered local validator.", evidence


def build_validator_dispatch_report(
    execution_plan: ValidatorExecutionPlan,
    *,
    mode: ValidatorDispatchMode | str | None = None,
    validator_registry: ValidatorRegistry | None = None,
    dispatch_context: dict[str, Any] | None = None,
    feature_flag_enabled: bool | None = None,
) -> ValidatorDispatchReport:
    """Build a local dispatch report from one validator execution plan."""
    if not isinstance(execution_plan, ValidatorExecutionPlan):
        raise TypeError("execution_plan must be a ValidatorExecutionPlan")

    dispatch_mode = _coerce_dispatch_mode(mode)
    registry = _validate_registry(validator_registry)
    context = dict(dispatch_context or {})
    context.setdefault("proof_level", LOCAL_SELECTION_PROOF_LEVEL)
    context.setdefault("live_or_staging_evidence", False)

    decisions: list[ValidatorDispatchDecision] = []
    validators_would_run: list[str] = []
    diagnostics_would_run: list[str] = []
    validators_would_skip: list[str] = []
    judges_would_be_disallowed: list[str] = []
    validators_unavailable: list[str] = []
    actually_executed: list[str] = []
    report_warnings = list(execution_plan.warnings)

    for entry in execution_plan.entries:
        decision = _decision_for_entry(entry, mode=dispatch_mode)
        target_id = decision.validator_id
        executed = False
        unavailable = False
        reason = decision.reason
        local_evidence: dict[str, Any] | None = None

        if decision.dispatch_action is ValidatorDispatchAction.RUN and decision.would_execute:
            if target_id:
                validators_would_run.append(target_id)
            if dispatch_mode is ValidatorDispatchMode.PLAN_ENFORCED and target_id:
                executed, unavailable, reason, local_evidence = _invoke_registered_local_validator(
                    validator_id=target_id,
                    entry=entry,
                    registry=registry,
                    dispatch_context=context,
                )
        elif (
            decision.dispatch_action is ValidatorDispatchAction.OBSERVE
            and decision.would_execute
            and target_id
        ):
            diagnostics_would_run.append(target_id)
        elif decision.dispatch_action is ValidatorDispatchAction.SKIP and target_id:
            validators_would_skip.append(target_id)
        elif decision.dispatch_action is ValidatorDispatchAction.DISALLOW_JUDGE and target_id:
            judges_would_be_disallowed.append(target_id)

        if unavailable and target_id:
            validators_unavailable.append(target_id)
        if executed and target_id:
            actually_executed.append(target_id)

        decisions.append(
            ValidatorDispatchDecision(
                capability=decision.capability,
                planned_mode=decision.planned_mode,
                dispatch_action=decision.dispatch_action,
                validator_id=target_id,
                would_execute=decision.would_execute,
                actually_executed=executed,
                unavailable=unavailable,
                reason=reason,
                local_execution_evidence=local_evidence,
            )
        )

    execution_changed = (
        dispatch_mode is ValidatorDispatchMode.PLAN_ENFORCED and bool(actually_executed)
    )
    flag_enabled = (
        bool(feature_flag_enabled)
        if feature_flag_enabled is not None
        else dispatch_mode is ValidatorDispatchMode.PLAN_ENFORCED
    )
    reason = (
        DISPATCH_REPORT_REASON
        if dispatch_mode is ValidatorDispatchMode.DRY_RUN
        else PLAN_ENFORCED_DISPATCH_REASON
    )

    entries = tuple(
        ValidatorDispatchEntry(
            capability=decision.capability,
            planned_mode=decision.planned_mode,
            dispatch_action=decision.dispatch_action,
            validator_id=decision.validator_id,
            would_execute=decision.would_execute,
            actually_executed=decision.actually_executed,
            unavailable=decision.unavailable,
            reason=decision.reason,
            local_execution_evidence=decision.local_execution_evidence,
        )
        for decision in decisions
    )

    return ValidatorDispatchReport(
        mode=dispatch_mode,
        entries=entries,
        validators_would_run=_unique_ids(validators_would_run),
        diagnostics_would_run=_unique_ids(diagnostics_would_run),
        validators_would_skip=_unique_ids(validators_would_skip),
        judges_would_be_disallowed=_unique_ids(judges_would_be_disallowed),
        validators_unavailable=_unique_ids(validators_unavailable),
        actually_executed=_unique_ids(actually_executed),
        warnings=tuple(report_warnings),
        execution_changed=execution_changed,
        feature_flag_enabled=flag_enabled,
        reason=reason,
    )
