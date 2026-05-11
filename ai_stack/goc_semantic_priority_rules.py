"""
GoC semantic move priority stack — table-driven rules (first match
wins).

Extracted from semantic_move_interpretation_goc to keep the main
interpreter flat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ai_stack.semantic_move_contract import InterpretationTraceItem

# Predicate receives: features dict, combined normalized text, intent_s, interpreted_move dict
RulePredicate = Callable[[dict[str, Any], str, str, dict[str, Any]], bool]


@dataclass(frozen=True)
class SemanticPriorityRule:
    """``SemanticPriorityRule`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    rule_id: str
    trace_detail: str  # e.g. rule:accusation_synset — stable contract for logs/tests
    predicate: RulePredicate
    move_type: str
    family: str
    direct: str
    tactic: str | None
    risk: str


def _off_scope(combined: str) -> bool:
    """Describe what ``_off_scope`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        combined: ``combined`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
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
    """``_pred_off_scope`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        _f: ``_f`` (dict[str, Any]); meaning follows the type and call sites.
        combined: ``combined`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return _off_scope(combined)


def _pred_silence_pause(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_silence_pause`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_pause"] or (f["syn_silence"] and not f["syn_repair"]))


def _pred_alliance(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_alliance`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_alliance"])


def _pred_expose(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_expose`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_expose"])


def _pred_repair_reveal(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_repair_reveal`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_repair"] and f["syn_reveal"])


def _pred_repair_probe(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_repair_probe`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_repair"] and f["syn_probe"])


def _pred_repair(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_repair`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_repair"])


def _pred_deflect(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_deflect`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_deflect"])


def _pred_accusation(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_accusation`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_accusation"])


def _pred_reveal(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_reveal`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_reveal"])


def _pred_escalate(f: dict[str, Any], _c: str, _i: str, _mv: dict[str, Any]) -> bool:
    """``_pred_escalate`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return bool(f["syn_escalate"])


def _pred_probe_or_question(
    f: dict[str, Any], _c: str, _i: str, mv: dict[str, Any]
) -> bool:
    """``_pred_probe_or_question`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        f: ``f`` (dict[str, Any]); meaning follows the type and call sites.
        _c: ``_c`` (str); meaning follows the type and call sites.
        _i: ``_i`` (str); meaning follows the type and call sites.
        mv: ``mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    # PLAYER-ACTION-INTENT-01: physical moves/perception questions should not default
    # to probe_inquiry / NPC-answer demand.
    if bool(f.get("player_input_kind_is_action")) or bool(f.get("player_input_kind_is_perception")):
        return False
    return bool(
        f["syn_probe"] or f["question_end"] or "question" in str(mv.get("move_class", "")).lower()
    )


def _pred_provocation(_f: dict[str, Any], combined: str, intent_s: str, _mv: dict[str, Any]) -> bool:
    """``_pred_provocation`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        _f: ``_f`` (dict[str, Any]); meaning follows the type and call sites.
        combined: ``combined`` (str); meaning follows the type and call sites.
        intent_s: ``intent_s`` (str); meaning follows the type and call sites.
        _mv: ``_mv`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    if bool(_f.get("player_input_kind_is_action")) or bool(_f.get("player_input_kind_is_perception")):
        return False
    return "cynic" in intent_s or "provok" in combined


# (rule_id, trace_detail, predicate, move_type, family, direct, tactic, risk) — first match wins.
_RULE_SPEC_ROWS: tuple[tuple[str, str, RulePredicate, str, str, str, str | None, str], ...] = (
    (
        "off_scope_containment",
        "rule:off_scope_containment",
        _pred_off_scope,
        "off_scope_containment",
        "neutral",
        "ambiguous",
        "slice_boundary",
        "low",
    ),
    (
        "silence_withdrawal",
        "rule:silence_or_pause",
        _pred_silence_pause,
        "silence_withdrawal",
        "withdraw",
        "ambiguous",
        "withhold_response",
        "moderate",
    ),
    (
        "alliance_reposition",
        "rule:alliance_synset",
        _pred_alliance,
        "alliance_reposition",
        "alliance",
        "",
        "faction_shift",
        "high",
    ),
    (
        "humiliating_exposure",
        "rule:exposure_synset",
        _pred_expose,
        "humiliating_exposure",
        "expose",
        "",
        "dignity_strike",
        "high",
    ),
    (
        "competing_repair_and_reveal",
        "rule:repair_reveal_compete",
        _pred_repair_reveal,
        "competing_repair_and_reveal",
        "repair",
        "ambiguous",
        "repair_truth_compete",
        "high",
    ),
    (
        "repair_attempt_probe",
        "rule:repair_plus_probe",
        _pred_repair_probe,
        "repair_attempt",
        "repair",
        "ambiguous",
        "repair_under_inquiry",
        "moderate",
    ),
    (
        "repair_attempt",
        "rule:repair_synset",
        _pred_repair,
        "repair_attempt",
        "repair",
        "direct",
        "stabilize",
        "moderate",
    ),
    (
        "evasive_deflection",
        "rule:deflect_synset",
        _pred_deflect,
        "evasive_deflection",
        "deflect",
        "indirect",
        "avoid_accountability",
        "moderate",
    ),
    (
        "direct_accusation",
        "rule:accusation_synset",
        _pred_accusation,
        "direct_accusation",
        "attack",
        "direct",
        "blame_assignment",
        "high",
    ),
    (
        "reveal_surface",
        "rule:reveal_synset",
        _pred_reveal,
        "reveal_surface",
        "reveal",
        "direct",
        "truth_surface",
        "high",
    ),
    (
        "escalation_threat",
        "rule:escalate_synset",
        _pred_escalate,
        "escalation_threat",
        "escalate",
        "direct",
        "heat_increase",
        "high",
    ),
    (
        "probe_inquiry",
        "rule:probe_or_question_shape",
        _pred_probe_or_question,
        "probe_inquiry",
        "probe",
        "indirect",
        "motive_inquiry",
        "moderate",
    ),
    (
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

_GOC_PRIORITY_RULES: tuple[SemanticPriorityRule, ...] = tuple(
    SemanticPriorityRule(*row) for row in _RULE_SPEC_ROWS
)


def build_goc_priority_rules() -> tuple[SemanticPriorityRule, ...]:
    """Ordered stack: first matching rule wins (after non-GoC handled
    upstream).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        tuple[SemanticPriorityRule, ...]:
            Returns a value of type ``tuple[SemanticPriorityRule, ...]``; see the function body for structure, error paths, and sentinels.
    """
    return _GOC_PRIORITY_RULES


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


def _rule_directness(rule: SemanticPriorityRule, *, features: dict[str, Any]) -> str:
    """Resolve per-rule directness adjustments used by both ranked and primary paths."""
    direct = rule.direct
    if rule.rule_id == "alliance_reposition":
        direct = "direct" if features.get("question_end") else "indirect"
    elif rule.rule_id == "humiliating_exposure":
        direct = "direct" if features.get("syn_accusation") else "indirect"
    return direct


def rank_goc_move_candidates(
    *,
    features: dict[str, Any],
    combined: str,
    intent_s: str,
    interpreted_move: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return deterministic, primary-first ranked semantic move candidates."""
    ranked: list[dict[str, Any]] = []
    rules = _GOC_PRIORITY_RULES
    max_rank = max(len(rules), 1)
    for idx, rule in enumerate(rules):
        if not rule.predicate(features, combined, intent_s, interpreted_move):
            continue
        confidence = max(0.05, round((max_rank - idx) / max_rank, 4))
        ranked.append(
            {
                "move_type": rule.move_type,
                "social_move_family": rule.family,
                "directness": _rule_directness(rule, features=features),
                "pressure_tactic": rule.tactic,
                "scene_risk_band": rule.risk,
                "rank": idx + 1,
                "confidence": confidence,
                "trace_detail": rule.trace_detail,
            }
        )

    if not ranked:
        ranked.append(
            {
                "move_type": _DEFAULT_RULE.move_type,
                "social_move_family": _DEFAULT_RULE.family,
                "directness": _DEFAULT_RULE.direct,
                "pressure_tactic": _DEFAULT_RULE.tactic,
                "scene_risk_band": _DEFAULT_RULE.risk,
                "rank": max_rank + 1,
                "confidence": 0.05,
                "trace_detail": _DEFAULT_RULE.trace_detail,
            }
        )

    for order, row in enumerate(ranked, start=1):
        row["rank"] = order
    return ranked


def resolve_goc_move_from_rules(
    *,
    features: dict[str, Any],
    combined: str,
    intent_s: str,
    interpreted_move: dict[str, Any],
    trace: list[InterpretationTraceItem],
) -> tuple[str, str, str, str | None, str]:
    """Apply priority stack; mutates trace with the winning rule id.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        features: ``features`` (dict[str, Any]); meaning follows the type and call sites.
        combined: ``combined`` (str); meaning follows the type and call sites.
        intent_s: ``intent_s`` (str); meaning follows the type and call sites.
        interpreted_move: ``interpreted_move`` (dict[str,
            Any]); meaning follows the type and call sites.
        trace: ``trace`` (list[InterpretationTraceItem]); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str, str, str | None, str]:
            Returns a value of type ``tuple[str, str, str, str | None, str]``; see the function body for structure, error paths, and sentinels.
    """
    rules = _GOC_PRIORITY_RULES
    for rule in rules:
        if not rule.predicate(features, combined, intent_s, interpreted_move):
            continue
        direct = _rule_directness(rule, features=features)
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
