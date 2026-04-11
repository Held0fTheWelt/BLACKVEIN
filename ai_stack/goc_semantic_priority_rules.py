"""GoC semantic move priority stack — table-driven rules (first match wins).

Extracted from semantic_move_interpretation_goc to keep the main interpreter flat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ai_stack.semantic_move_contract import InterpretationTraceItem

# Predicate receives: features dict, combined normalized text, intent_s, interpreted_move dict
RulePredicate = Callable[[dict[str, Any], str, str, dict[str, Any]], bool]


@dataclass(frozen=True)
class SemanticPriorityRule:
    rule_id: str
    trace_detail: str  # e.g. rule:accusation_synset — stable contract for logs/tests
    predicate: RulePredicate
    move_type: str
    family: str
    direct: str
    tactic: str | None
    risk: str


def _off_scope(combined: str) -> bool:
    off_scope_keywords = (
        "mars",
        "spaceship",
        "lighthouse",
        "dragon",
        "bitcoin",
        "stock market",
        "weather forecast",
        "football match",
        "tax return",
        "election campaign",
        "recipe blog",
    )
    return any(k in combined for k in off_scope_keywords) and "carnage" not in combined


def _pred_off_scope(_f: dict[str, Any], combined: str, _i: str, _mv: dict[str, Any]) -> bool:
    return _off_scope(combined)


def _pred_silence_pause(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_pause"] or (f["syn_silence"] and not f["syn_repair"]))


def _pred_alliance(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_alliance"])


def _pred_expose(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_expose"])


def _pred_repair_reveal(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_repair"] and f["syn_reveal"])


def _pred_repair_probe(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_repair"] and f["syn_probe"])


def _pred_repair(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_repair"])


def _pred_deflect(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_deflect"])


def _pred_accusation(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_accusation"])


def _pred_reveal(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_reveal"])


def _pred_escalate(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    return bool(f["syn_escalate"])


def _pred_probe_or_question(
    f: dict[str, Any], _c: str, _i: str, mv: dict[str, Any]
) -> bool:
    return bool(
        f["syn_probe"] or f["question_end"] or "question" in str(mv.get("move_class", "")).lower()
    )


def _pred_provocation(_f: dict[str, Any], combined: str, intent_s: str, _mv: dict[str, Any]) -> bool:
    return "cynic" in intent_s or "provok" in combined


def build_goc_priority_rules() -> tuple[SemanticPriorityRule, ...]:
    """Ordered stack: first matching rule wins (after non-GoC handled upstream)."""

    return (
        SemanticPriorityRule(
            "off_scope_containment",
            "rule:off_scope_containment",
            _pred_off_scope,
            "off_scope_containment",
            "neutral",
            "ambiguous",
            "slice_boundary",
            "low",
        ),
        SemanticPriorityRule(
            "silence_withdrawal",
            "rule:silence_or_pause",
            _pred_silence_pause,
            "silence_withdrawal",
            "withdraw",
            "ambiguous",
            "withhold_response",
            "moderate",
        ),
        SemanticPriorityRule(
            "alliance_reposition",
            "rule:alliance_synset",
            _pred_alliance,
            "alliance_reposition",
            "alliance",
            "",  # filled from question_end
            "faction_shift",
            "high",
        ),
        SemanticPriorityRule(
            "humiliating_exposure",
            "rule:exposure_synset",
            _pred_expose,
            "humiliating_exposure",
            "expose",
            "",  # from syn_accusation
            "dignity_strike",
            "high",
        ),
        SemanticPriorityRule(
            "competing_repair_and_reveal",
            "rule:repair_reveal_compete",
            _pred_repair_reveal,
            "competing_repair_and_reveal",
            "repair",
            "ambiguous",
            "repair_truth_compete",
            "high",
        ),
        SemanticPriorityRule(
            "repair_attempt_probe",
            "rule:repair_plus_probe",
            _pred_repair_probe,
            "repair_attempt",
            "repair",
            "ambiguous",
            "repair_under_inquiry",
            "moderate",
        ),
        SemanticPriorityRule(
            "repair_attempt",
            "rule:repair_synset",
            _pred_repair,
            "repair_attempt",
            "repair",
            "direct",
            "stabilize",
            "moderate",
        ),
        SemanticPriorityRule(
            "evasive_deflection",
            "rule:deflect_synset",
            _pred_deflect,
            "evasive_deflection",
            "deflect",
            "indirect",
            "avoid_accountability",
            "moderate",
        ),
        SemanticPriorityRule(
            "direct_accusation",
            "rule:accusation_synset",
            _pred_accusation,
            "direct_accusation",
            "attack",
            "direct",
            "blame_assignment",
            "high",
        ),
        SemanticPriorityRule(
            "reveal_surface",
            "rule:reveal_synset",
            _pred_reveal,
            "reveal_surface",
            "reveal",
            "direct",
            "truth_surface",
            "high",
        ),
        SemanticPriorityRule(
            "escalation_threat",
            "rule:escalate_synset",
            _pred_escalate,
            "escalation_threat",
            "escalate",
            "direct",
            "heat_increase",
            "high",
        ),
        SemanticPriorityRule(
            "probe_inquiry",
            "rule:probe_or_question_shape",
            _pred_probe_or_question,
            "probe_inquiry",
            "probe",
            "indirect",
            "motive_inquiry",
            "moderate",
        ),
        SemanticPriorityRule(
            "indirect_provocation",
            "rule:intent_provocation_cue",
            _pred_provocation,
            "indirect_provocation",
            "attack",
            "indirect",
            "social_needle",
            "moderate",
        ),
    )


_DEFAULT_RULE = SemanticPriorityRule(
    "default_situational",
    "rule:default_situational",
    lambda *_: True,
    "establish_situational_pressure",
    "neutral",
    "ambiguous",
    None,
    "moderate",
)


def resolve_goc_move_from_rules(
    *,
    features: dict[str, Any],
    combined: str,
    intent_s: str,
    interpreted_move: dict[str, Any],
    trace: list[InterpretationTraceItem],
) -> tuple[str, str, str, str | None, str]:
    """Apply priority stack; mutates trace with the winning rule id."""
    rules = build_goc_priority_rules()
    for rule in rules:
        if not rule.predicate(features, combined, intent_s, interpreted_move):
            continue
        direct = rule.direct
        if rule.rule_id == "alliance_reposition":
            direct = "direct" if features["question_end"] else "indirect"
        elif rule.rule_id == "humiliating_exposure":
            direct = "direct" if features["syn_accusation"] else "indirect"
        trace.append(
            InterpretationTraceItem(
                step_id="apply_priority_rules",
                detail_code=rule.trace_detail,
            )
        )
        return rule.move_type, rule.family, direct, rule.tactic, rule.risk

    rule = _DEFAULT_RULE
    trace.append(
        InterpretationTraceItem(
            step_id="apply_priority_rules",
            detail_code=rule.trace_detail,
        )
    )
    return rule.move_type, rule.family, rule.direct, rule.tactic, rule.risk
