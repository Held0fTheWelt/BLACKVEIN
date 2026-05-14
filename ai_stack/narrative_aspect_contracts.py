"""Generic narrative aspect contracts for content-driven runtime themes.

Narrative aspects are policy-defined runtime themes/signals. The engine knows
how to select, evidence, and validate aspect contracts; content modules own the
concrete aspect ids and their authored meaning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


NARRATIVE_ASPECT_SCHEMA_VERSION = "narrative_aspect_policy.v1"
NARRATIVE_ASPECT_RECORD_VERSION = "narrative_aspect_record.v1"

COMMIT_IMPACTS: frozenset[str] = frozenset({"diagnostic", "recover", "reject"})
EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "state_path_present",
        "state_path_equals",
        "visible_origin_present",
        "visible_capability_present",
        "ledger_aspect_status",
    }
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _get_path(root: dict[str, Any], path: str | None) -> Any:
    current: Any = root
    for part in [p for p in _text(path).split(".") if p]:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current.get(part)
    return current


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


@dataclass(frozen=True)
class NarrativeAspectEvidenceRule:
    kind: str
    id: str | None = None
    required: bool = True
    path: str | None = None
    value: Any = None
    origin_aspect: str | None = None
    origin_capability: str | None = None
    ledger_aspect: str | None = None
    status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeAspectPolicy:
    id: str
    enabled: bool = True
    selection_source: str = "module_policy"
    activation: dict[str, Any] = field(default_factory=dict)
    evidence: list[NarrativeAspectEvidenceRule] = field(default_factory=list)
    commit_impact: str = "diagnostic"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeAspectSelection:
    schema_version: str = NARRATIVE_ASPECT_RECORD_VERSION
    selected_aspects: list[str] = field(default_factory=list)
    candidate_aspects: list[str] = field(default_factory=list)
    selection_source: str = "module_policy"

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeAspectEvidence:
    aspect_id: str
    rule_id: str | None
    kind: str
    required: bool
    present: bool
    source: str = "runtime"
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeAspectValidation:
    status: str
    policy_present: bool
    schema_version: str = NARRATIVE_ASPECT_RECORD_VERSION
    selected_aspects: list[str] = field(default_factory=list)
    realized_aspects: list[str] = field(default_factory=list)
    missing_required_evidence: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    failure_reason: str | None = None
    commit_impact: str = "diagnostic"

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def _normalize_evidence_rule(raw: dict[str, Any]) -> NarrativeAspectEvidenceRule | None:
    kind = _text(raw.get("kind") or raw.get("type"))
    if kind not in EVIDENCE_KINDS:
        return None
    return NarrativeAspectEvidenceRule(
        kind=kind,
        id=_text(raw.get("id")) or None,
        required=bool(raw.get("required", True)),
        path=_text(raw.get("path")) or None,
        value=raw.get("value"),
        origin_aspect=_text(raw.get("origin_aspect")) or None,
        origin_capability=_text(raw.get("origin_capability")) or None,
        ledger_aspect=_text(raw.get("ledger_aspect")) or None,
        status=_text(raw.get("status")) or None,
    )


def normalize_narrative_aspect_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe, module-neutral narrative aspect policy."""
    src = policy if isinstance(policy, dict) else {}
    raw_aspects = src.get("aspects") if isinstance(src.get("aspects"), list) else []
    aspects: list[dict[str, Any]] = []
    for raw in raw_aspects:
        if not isinstance(raw, dict):
            continue
        aspect_id = _text(raw.get("id"))
        if not aspect_id:
            continue
        evidence = [
            rule.to_dict()
            for rule in (
                _normalize_evidence_rule(item)
                for item in _as_list(raw.get("evidence") or raw.get("required_evidence"))
                if isinstance(item, dict)
            )
            if rule is not None
        ]
        commit_impact = _text(raw.get("commit_impact") or src.get("default_commit_impact") or "diagnostic")
        if commit_impact not in COMMIT_IMPACTS:
            commit_impact = "diagnostic"
        aspects.append(
            NarrativeAspectPolicy(
                id=aspect_id,
                enabled=bool(raw.get("enabled", True)),
                selection_source=_text(raw.get("selection_source") or "module_policy"),
                activation=raw.get("activation") if isinstance(raw.get("activation"), dict) else {},
                evidence=[
                    NarrativeAspectEvidenceRule(**rule)
                    for rule in evidence
                    if isinstance(rule, dict)
                ],
                commit_impact=commit_impact,
                metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
            ).to_dict()
        )
    return {
        "schema_version": _text(src.get("schema_version")) or NARRATIVE_ASPECT_SCHEMA_VERSION,
        "default_commit_impact": _text(src.get("default_commit_impact") or "diagnostic"),
        "aspects": aspects,
    }


def _activation_selected(activation: dict[str, Any], context: dict[str, Any]) -> bool:
    if activation.get("always") is True or not activation:
        return True
    any_paths = [_text(item) for item in _as_list(activation.get("state_paths_any")) if _text(item)]
    if any_paths and any(_value_present(_get_path(context, path)) for path in any_paths):
        return True
    all_paths = [_text(item) for item in _as_list(activation.get("state_paths_all")) if _text(item)]
    if all_paths and all(_value_present(_get_path(context, path)) for path in all_paths):
        return True
    input_kinds = {_text(item).lower() for item in _as_list(activation.get("input_kinds")) if _text(item)}
    if input_kinds and _text(_get_path(context, "input.kind")).lower() in input_kinds:
        return True
    return False


def select_narrative_aspects(
    *,
    narrative_aspect_policy: dict[str, Any] | None,
    runtime_context: dict[str, Any] | None = None,
) -> NarrativeAspectSelection:
    """Select enabled aspect ids from policy using generic activation rules."""
    policy = normalize_narrative_aspect_policy(narrative_aspect_policy)
    context = runtime_context if isinstance(runtime_context, dict) else {}
    candidates: list[str] = []
    selected: list[str] = []
    for aspect in policy.get("aspects") or []:
        if not isinstance(aspect, dict) or not aspect.get("enabled", True):
            continue
        aspect_id = _text(aspect.get("id"))
        if not aspect_id:
            continue
        candidates.append(aspect_id)
        activation = aspect.get("activation") if isinstance(aspect.get("activation"), dict) else {}
        if _activation_selected(activation, context):
            selected.append(aspect_id)
    return NarrativeAspectSelection(
        selected_aspects=selected,
        candidate_aspects=candidates,
        selection_source="module_policy" if candidates else "not_applicable",
    )


def _visible_blocks(context: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = context.get("visible_blocks") or context.get("scene_blocks") or []
    return [block for block in blocks if isinstance(block, dict)] if isinstance(blocks, list) else []


def _ledger_aspects(context: dict[str, Any]) -> dict[str, Any]:
    ledger = context.get("ledger") if isinstance(context.get("ledger"), dict) else {}
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    return aspects if isinstance(aspects, dict) else {}


def _evaluate_rule(
    *,
    aspect_id: str,
    rule: dict[str, Any],
    context: dict[str, Any],
) -> NarrativeAspectEvidence:
    kind = _text(rule.get("kind"))
    present = False
    detail: dict[str, Any] = {}
    if kind == "state_path_present":
        value = _get_path(context, _text(rule.get("path")))
        present = _value_present(value)
        detail = {"path": rule.get("path")}
    elif kind == "state_path_equals":
        value = _get_path(context, _text(rule.get("path")))
        present = value == rule.get("value")
        detail = {"path": rule.get("path"), "expected_value": rule.get("value"), "actual_value": value}
    elif kind == "visible_origin_present":
        expected_origin = _text(rule.get("origin_aspect")) or "narrative_aspect"
        matches = [
            block.get("id") or block.get("block_id")
            for block in _visible_blocks(context)
            if _text(block.get("origin_aspect")) == expected_origin
            and (
                not _text(block.get("origin_aspect_id"))
                or _text(block.get("origin_aspect_id")) == aspect_id
            )
        ]
        present = bool(matches)
        detail = {"origin_aspect": expected_origin, "evidence_blocks": matches}
    elif kind == "visible_capability_present":
        expected_capability = _text(rule.get("origin_capability"))
        matches = [
            block.get("id") or block.get("block_id")
            for block in _visible_blocks(context)
            if expected_capability and _text(block.get("origin_capability")) == expected_capability
        ]
        present = bool(matches)
        detail = {"origin_capability": expected_capability, "evidence_blocks": matches}
    elif kind == "ledger_aspect_status":
        ledger_aspect = _text(rule.get("ledger_aspect"))
        expected_status = _text(rule.get("status"))
        record = _ledger_aspects(context).get(ledger_aspect)
        actual_status = record.get("status") if isinstance(record, dict) else None
        present = bool(ledger_aspect) and (not expected_status or _text(actual_status) == expected_status)
        detail = {"ledger_aspect": ledger_aspect, "expected_status": expected_status, "actual_status": actual_status}
    return NarrativeAspectEvidence(
        aspect_id=aspect_id,
        rule_id=_text(rule.get("id")) or None,
        kind=kind,
        required=bool(rule.get("required", True)),
        present=present,
        detail=detail,
    )


def validate_narrative_aspects(
    *,
    narrative_aspect_policy: dict[str, Any] | None,
    runtime_context: dict[str, Any] | None = None,
) -> NarrativeAspectValidation:
    """Validate selected narrative aspects against generic evidence rules."""
    policy = normalize_narrative_aspect_policy(narrative_aspect_policy)
    context = runtime_context if isinstance(runtime_context, dict) else {}
    selection = select_narrative_aspects(
        narrative_aspect_policy=policy,
        runtime_context=context,
    )
    selected_ids = set(selection.selected_aspects)
    evidence: list[dict[str, Any]] = []
    missing_required: list[dict[str, Any]] = []
    realized: list[str] = []
    max_impact = "diagnostic"
    for aspect in policy.get("aspects") or []:
        if not isinstance(aspect, dict):
            continue
        aspect_id = _text(aspect.get("id"))
        if not aspect_id or aspect_id not in selected_ids:
            continue
        impact = _text(aspect.get("commit_impact") or "diagnostic")
        if impact == "reject":
            max_impact = "reject"
        elif impact == "recover" and max_impact != "reject":
            max_impact = "recover"
        rules = [rule for rule in aspect.get("evidence") or [] if isinstance(rule, dict)]
        evaluated = [
            _evaluate_rule(aspect_id=aspect_id, rule=rule, context=context)
            for rule in rules
        ]
        evidence.extend(item.to_dict() for item in evaluated)
        missing_for_aspect = [
            item.to_dict()
            for item in evaluated
            if item.required and not item.present
        ]
        missing_required.extend(missing_for_aspect)
        if not missing_for_aspect:
            realized.append(aspect_id)
    policy_present = bool(policy.get("aspects"))
    if not policy_present:
        status = "not_applicable"
    elif missing_required:
        status = "failed" if max_impact in {"recover", "reject"} else "partial"
    elif selected_ids:
        status = "passed"
    else:
        status = "not_applicable"
    failure_reason = "missing_required_narrative_aspect_evidence" if missing_required else None
    return NarrativeAspectValidation(
        status=status,
        policy_present=policy_present,
        selected_aspects=selection.selected_aspects,
        realized_aspects=realized,
        missing_required_evidence=missing_required,
        evidence=evidence,
        failure_reason=failure_reason,
        commit_impact=max_impact,
    )
