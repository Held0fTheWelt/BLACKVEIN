"""Local ADR-0041 validator planning from semantic capability selection.

The planner is intentionally declarative and side-effect free. It produces a
local evidence plan for which validator or diagnostic IDs would be considered
for the selected capabilities. It does not execute validators, change runtime
gates, run judges, or make live/staging claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ai_stack.capability_selector import (
    CAP_ACTION_RESOLUTION,
    CAP_CALLBACK_WEB,
    CAP_CONSEQUENCE_CASCADE,
    CAP_DRAMATIC_IRONY,
    CAP_ENVIRONMENT_STATE,
    CAP_INFORMATION_DISCLOSURE,
    CAP_LONG_HORIZON_FORECAST,
    CAP_NARRATOR_AUTHORITY,
    CAP_NPC_AGENCY,
    CAP_PLAYER_INTENT_INFERENCE,
    CAP_SCENE_ENERGY,
    CAP_SENSORY_CONTEXT,
    CAP_SILENCE_NEGATIVE_SPACE,
    CAP_THEMATIC_TRACKING,
    CAP_VOICE_CONSISTENCY,
    CapabilitySelectionResult,
    INITIAL_CAPABILITIES,
    LOCAL_SELECTION_EVIDENCE_SCOPE,
    LOCAL_SELECTION_PROOF_LEVEL,
    validate_semantic_capability_name,
)


VALIDATOR_EXECUTION_PLAN_SCHEMA_VERSION = "validator_execution_plan.v1"
VALIDATOR_PLAN_REASON = "planned from ADR-0041 capability selection; not executed yet"

GOC_SEAM_MIRROR_SUITE_CAPABILITY = "goc_seam_mirror_suite"


class ValidatorPlanMode(str, Enum):
    """Planning mode for a validator, diagnostic, or judge ID."""

    RUN_LOCAL_VALIDATOR = "run_local_validator"
    RUN_OBSERVER_DIAGNOSTIC = "run_observer_diagnostic"
    RUN_JUDGE = "run_judge"
    SKIP_EXCLUDED = "skip_excluded"
    SKIP_BUDGET_DISALLOWED = "skip_budget_disallowed"
    SKIP_JUDGE_DISALLOWED = "skip_judge_disallowed"


LOCAL_VALIDATORS: dict[str, str] = {
    CAP_NARRATOR_AUTHORITY: "narrator_authority_contract",
    CAP_SCENE_ENERGY: "scene_energy_contract",
    CAP_ENVIRONMENT_STATE: "environment_state_contract",
    CAP_INFORMATION_DISCLOSURE: "information_disclosure_contract",
    CAP_VOICE_CONSISTENCY: "voice_consistency_contract",
    CAP_NPC_AGENCY: "npc_agency_contract",
    CAP_PLAYER_INTENT_INFERENCE: "player_intent_contract",
    CAP_ACTION_RESOLUTION: "action_resolution_contract",
    CAP_CONSEQUENCE_CASCADE: "consequence_cascade_contract",
    CAP_LONG_HORIZON_FORECAST: "forecast_contract",
    CAP_SILENCE_NEGATIVE_SPACE: "silence_negative_space_contract",
    CAP_DRAMATIC_IRONY: "dramatic_irony_contract",
}

OBSERVER_DIAGNOSTICS: dict[str, str] = {
    CAP_THEMATIC_TRACKING: "thematic_tracking_diagnostic",
    CAP_CALLBACK_WEB: "callback_web_diagnostic",
    CAP_SENSORY_CONTEXT: "sensory_context_diagnostic",
}

JUDGE_VALIDATORS: dict[str, str] = {
    capability: f"{capability}_judge" for capability in INITIAL_CAPABILITIES
}


def _coerce_mode(value: ValidatorPlanMode | str) -> ValidatorPlanMode:
    if isinstance(value, ValidatorPlanMode):
        return value
    text = str(value or "").strip()
    for item in ValidatorPlanMode:
        if item.value == text:
            return item
    allowed = ", ".join(item.value for item in ValidatorPlanMode)
    raise ValueError(f"Unsupported ValidatorPlanMode: {text!r}; expected one of {allowed}")


def _validate_plan_id(value: str | None) -> str | None:
    if value is None:
        return None
    return validate_semantic_capability_name(value)


def _unique(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = validate_semantic_capability_name(item)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return tuple(ordered)


@dataclass(frozen=True)
class ValidatorPlanEntry:
    """One planned validator, diagnostic, judge, or skip decision."""

    capability: str
    mode: ValidatorPlanMode | str
    plan_id: str
    validator_id: str | None = None
    diagnostic_id: str | None = None
    judge_id: str | None = None
    blocking: bool = False
    planned_only: bool = True
    reason: str = VALIDATOR_PLAN_REASON

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability",
            validate_semantic_capability_name(self.capability),
        )
        object.__setattr__(self, "mode", _coerce_mode(self.mode))
        object.__setattr__(self, "plan_id", validate_semantic_capability_name(self.plan_id))
        object.__setattr__(self, "validator_id", _validate_plan_id(self.validator_id))
        object.__setattr__(self, "diagnostic_id", _validate_plan_id(self.diagnostic_id))
        object.__setattr__(self, "judge_id", _validate_plan_id(self.judge_id))
        object.__setattr__(self, "blocking", bool(self.blocking))
        object.__setattr__(self, "planned_only", True)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class ValidatorExecutionPlan:
    """Local-only validator execution plan derived from one selection result."""

    selection_result: CapabilitySelectionResult
    entries: tuple[ValidatorPlanEntry, ...] = field(default_factory=tuple)
    reason: str = VALIDATOR_PLAN_REASON
    warnings: tuple[str, ...] = field(default_factory=tuple)
    proof_level: str = LOCAL_SELECTION_PROOF_LEVEL
    evidence_scope: str = LOCAL_SELECTION_EVIDENCE_SCOPE
    live_or_staging_evidence: bool = False
    execution_changed: bool = False
    implementation_proof: bool = False
    schema_version: str = VALIDATOR_EXECUTION_PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entries",
            tuple(
                entry
                if isinstance(entry, ValidatorPlanEntry)
                else ValidatorPlanEntry(**entry)
                for entry in self.entries
            ),
        )
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings if str(item).strip()))
        object.__setattr__(self, "proof_level", LOCAL_SELECTION_PROOF_LEVEL)
        object.__setattr__(self, "evidence_scope", LOCAL_SELECTION_EVIDENCE_SCOPE)
        object.__setattr__(self, "live_or_staging_evidence", False)
        object.__setattr__(self, "execution_changed", False)
        object.__setattr__(self, "implementation_proof", False)

    def _ids_for_mode(self, mode: ValidatorPlanMode, id_key: str) -> list[str]:
        values: list[str] = []
        for entry in self.entries:
            if entry.mode is mode:
                value = getattr(entry, id_key)
                if value:
                    values.append(value)
        return list(_unique(tuple(values)))

    @property
    def validators_to_run(self) -> list[str]:
        return self._ids_for_mode(ValidatorPlanMode.RUN_LOCAL_VALIDATOR, "validator_id")

    @property
    def observer_diagnostics(self) -> list[str]:
        return self._ids_for_mode(ValidatorPlanMode.RUN_OBSERVER_DIAGNOSTIC, "diagnostic_id")

    @property
    def validators_skipped(self) -> list[str]:
        return [
            entry.plan_id
            for entry in self.entries
            if entry.mode
            in {
                ValidatorPlanMode.SKIP_EXCLUDED,
                ValidatorPlanMode.SKIP_BUDGET_DISALLOWED,
            }
        ]

    @property
    def judges_to_run(self) -> list[str]:
        return self._ids_for_mode(ValidatorPlanMode.RUN_JUDGE, "judge_id")

    @property
    def judges_disallowed(self) -> list[str]:
        return self._ids_for_mode(ValidatorPlanMode.SKIP_JUDGE_DISALLOWED, "judge_id")

    def to_runtime_projection(self) -> dict[str, Any]:
        """Return a local RuntimeAspectLedger projection payload."""
        return {
            "validator_execution_plan": {
                "schema_version": self.schema_version,
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
                "validators_to_run": self.validators_to_run,
                "observer_diagnostics": self.observer_diagnostics,
                "validators_skipped": self.validators_skipped,
                "judges_to_run": self.judges_to_run,
                "judges_disallowed": self.judges_disallowed,
                "entries": [entry.to_dict() for entry in self.entries],
                "reason": self.reason,
                "warnings": list(self.warnings),
            }
        }

    def to_ledger_payload(self) -> dict[str, Any]:
        return self.to_runtime_projection()

    def to_runtime_intelligence_projection(self) -> dict[str, Any]:
        return self.to_runtime_projection()


def _local_validator_id(capability: str) -> str:
    return LOCAL_VALIDATORS.get(capability) or f"{capability}_contract"


def _observer_diagnostic_id(capability: str) -> str:
    return OBSERVER_DIAGNOSTICS.get(capability) or f"{capability}_diagnostic"


def _skip_plan_id(capability: str) -> str:
    return LOCAL_VALIDATORS.get(capability) or OBSERVER_DIAGNOSTICS.get(capability) or f"{capability}_contract"


def build_validator_execution_plan(
    selection_result: CapabilitySelectionResult,
) -> ValidatorExecutionPlan:
    """Build a local-only validator plan from one ADR-0041 selector result."""
    if not isinstance(selection_result, CapabilitySelectionResult):
        raise TypeError("selection_result must be a CapabilitySelectionResult")

    entries: list[ValidatorPlanEntry] = []
    for capability in selection_result.enforced:
        validator_id = _local_validator_id(capability)
        entries.append(
            ValidatorPlanEntry(
                capability=capability,
                mode=ValidatorPlanMode.RUN_LOCAL_VALIDATOR,
                plan_id=validator_id,
                validator_id=validator_id,
                blocking=True,
                reason=f"{capability} is enforced by semantic capability selection.",
            )
        )

    for capability in selection_result.observed:
        diagnostic_id = _observer_diagnostic_id(capability)
        entries.append(
            ValidatorPlanEntry(
                capability=capability,
                mode=ValidatorPlanMode.RUN_OBSERVER_DIAGNOSTIC,
                plan_id=diagnostic_id,
                diagnostic_id=diagnostic_id,
                blocking=False,
                reason=f"{capability} is observe-only; diagnostic is non-blocking.",
            )
        )

    for capability in selection_result.excluded:
        plan_id = _skip_plan_id(capability)
        entries.append(
            ValidatorPlanEntry(
                capability=capability,
                mode=ValidatorPlanMode.SKIP_EXCLUDED,
                plan_id=plan_id,
                validator_id=plan_id if plan_id.endswith("_contract") else None,
                diagnostic_id=plan_id if plan_id.endswith("_diagnostic") else None,
                blocking=False,
                reason=f"{capability} is excluded for this turn.",
            )
        )

    if selection_result.budget.allow_llm_judges:
        for capability in selection_result.judged:
            judge_id = JUDGE_VALIDATORS[capability]
            entries.append(
                ValidatorPlanEntry(
                    capability=capability,
                    mode=ValidatorPlanMode.RUN_JUDGE,
                    plan_id=judge_id,
                    judge_id=judge_id,
                    blocking=False,
                    reason=f"{capability} is judge-selected and budget allows judges.",
                )
            )
    else:
        for capability in INITIAL_CAPABILITIES:
            judge_id = JUDGE_VALIDATORS[capability]
            entries.append(
                ValidatorPlanEntry(
                    capability=capability,
                    mode=ValidatorPlanMode.SKIP_JUDGE_DISALLOWED,
                    plan_id=judge_id,
                    judge_id=judge_id,
                    blocking=False,
                    reason="LLM-as-a-Judge is disallowed by this turn budget.",
                )
            )

    return ValidatorExecutionPlan(
        selection_result=selection_result,
        entries=tuple(entries),
        warnings=selection_result.warnings,
    )


def prepend_goc_seam_mirror_plan_entries(
    plan: ValidatorExecutionPlan,
    *,
    seam_mirror_validator_ids: tuple[str, ...],
) -> ValidatorExecutionPlan:
    """Prepend deterministic GOC seam-mirror validators (plan_enforced graph path only)."""
    if not seam_mirror_validator_ids:
        return plan
    extra: list[ValidatorPlanEntry] = []
    for validator_id in seam_mirror_validator_ids:
        vid = validate_semantic_capability_name(str(validator_id))
        extra.append(
            ValidatorPlanEntry(
                capability=GOC_SEAM_MIRROR_SUITE_CAPABILITY,
                mode=ValidatorPlanMode.RUN_LOCAL_VALIDATOR,
                plan_id=vid,
                validator_id=vid,
                blocking=True,
                reason=(
                    "ADR-0041 GOC seam mirror: deterministic local check shared with "
                    "run_validation_seam helpers; non-commit."
                ),
            )
        )
    return ValidatorExecutionPlan(
        selection_result=plan.selection_result,
        entries=tuple(extra) + plan.entries,
        warnings=plan.warnings,
    )
