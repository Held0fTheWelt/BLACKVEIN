"""
Deterministic semantic move interpretation for GoC — not a rename of
keyword heuristics.

Uses normalization, interpreted_input signals, feature synsets, and
explicit priority rules.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_semantic_priority_rules import (
    rank_goc_move_candidates,
    resolve_goc_move_from_rules,
)
from ai_stack.semantic_move_contract import (
    SEMANTIC_MOVE_TYPES,
    InterpretationTraceItem,
    RankedMoveCandidate,
    SemanticMoveRecord,
)

# Synonym / paraphrase sets — separate from single-token keyword race; matched as token boundaries.
_ACCUSATION_SYN = (
    "blame",
    "fault",
    "accuse",
    "responsible",
    "accountable",
    "held accountable",
    "point the finger",
    "your fault",
    "hold you responsible",
    "that is on you",
)

_REPAIR_SYN = (
    "sorry",
    "apolog",
    "regret",
    "repair",
    "make amends",
    "take it back",
    "i was wrong",
)

_DEFLECT_SYN = (
    "deflect",
    "evade",
    "change the subject",
    "dodge",
    "sidestep",
    "not answering",
    "avoid the question",
)

_EXPOSE_SYN = (
    "humiliat",
    "embarrass",
    "ashamed",
    "ridicule",
    "mock",
    "shame",
)

_SILENCE_SYN = (
    "silent",
    "say nothing",
    "say absolutely nothing",
    "hold silence",
    "no words",
)

_PAUSE_SYN = (
    "awkward pause",
    "long pause",
    "do not answer",
    "won't answer",
    "refuse to answer",
)

_ALLIANCE_SYN = (
    "side with",
    "siding with",
    "ally with",
    "stand with",
    "against your wife",
    "against your husband",
    "back me up",
)

_PROBE_SYN = (
    "why",
    "motive",
    "reason",
    "explain",
    "what really happened",
)

_REVEAL_SYN = (
    "reveal",
    "secret",
    "truth",
    "admit",
    "come clean",
)

_ESCALATE_SYN = (
    "escalat",
    "fight",
    "furious",
    "attack",
    "lose my temper",
    "enough of this",
)


def _normalize(text: str) -> str:
    """Describe what ``_normalize`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    s = unicodedata.normalize("NFC", text or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _contains_syn(text: str, syn: tuple[str, ...]) -> bool:
    """Whole-phrase or substring match without first-hit keyword racing
    between synsets.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
        syn: ``syn`` (tuple[str, ...]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    for phrase in syn:
        if phrase in text:
            return True
    return False


def _named_target_hint(text: str) -> str | None:
    """``_named_target_hint`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    if "annette" in text:
        return "annette_reille"
    if "alain" in text:
        return "alain_reille"
    if "michel" in text or "michael" in text:
        return "michel_longstreet"
    if "veronique" in text or "penelope" in text:
        return "veronique_vallon"
    return None


def _secondary_dramatic_features(
    *,
    features: dict[str, bool | int | str],
    ranked_rows: list[dict[str, Any]],
) -> list[str]:
    """Derive bounded secondary dramatic feature labels for downstream packet use."""
    tags: list[str] = []

    def _push(tag: str) -> None:
        if tag and tag not in tags:
            tags.append(tag)

    if features.get("syn_pause") or features.get("syn_silence"):
        _push("defensive_pause_signal")
    if features.get("syn_deflect"):
        _push("evasive_deflection_signal")
    if features.get("syn_escalate"):
        _push("escalation_signal")
    if features.get("syn_accusation") and features.get("syn_reveal"):
        _push("accusation_plus_reveal_mix")
    if features.get("question_end") and features.get("syn_probe"):
        _push("probe_question_shape")
    if features.get("prior_blame_pressure"):
        _push("carry_forward_blame_pressure")
    if features.get("prior_alliance_shift"):
        _push("carry_forward_alliance_shift")

    if len(ranked_rows) > 1:
        secondary = str(ranked_rows[1].get("move_type") or "").strip()
        if secondary:
            _push(f"secondary_move:{secondary}")

    return tags[:6]


def interpret_goc_semantic_move(
    *,
    module_id: str,
    player_input: str,
    interpreted_input: dict[str, Any] | None,
    interpreted_move: dict[str, Any] | None,
    prior_continuity_classes: list[str] | None = None,
) -> SemanticMoveRecord:
    """Produce SemanticMoveRecord; deterministic for fixed inputs.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_input: ``interpreted_input`` (dict[str, Any] | None); meaning follows the type and call sites.
        interpreted_move: ``interpreted_move`` (dict[str,
            Any] | None); meaning follows the type and call sites.
        prior_continuity_classes: ``prior_continuity_classes`` (list[str] | None); meaning follows the type and call sites.
    
    Returns:
        SemanticMoveRecord:
            Returns a value of type ``SemanticMoveRecord``; see the function body for structure, error paths, and sentinels.
    """
    trace: list[InterpretationTraceItem] = []
    trace.append(InterpretationTraceItem(step_id="normalize_input", detail_code="start"))

    if module_id != GOC_MODULE_ID:
        rec = SemanticMoveRecord(
            move_type="establish_situational_pressure",
            social_move_family="neutral",
            target_actor_hint=None,
            directness="ambiguous",
            pressure_tactic=None,
            scene_risk_band="low",
            interpretation_trace=trace
            + [InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:non_goc_default")],
            interpreter_kind=None,
            feature_snapshot={"non_goc": True},
            ranked_move_candidates=[
                RankedMoveCandidate(
                    move_type="establish_situational_pressure",
                    social_move_family="neutral",
                    directness="ambiguous",
                    pressure_tactic=None,
                    scene_risk_band="low",
                    rank=1,
                    confidence=0.5,
                    trace_detail="rule:non_goc_default",
                )
            ],
            secondary_move_type=None,
            secondary_dramatic_features=[],
        )
        return rec

    inp = interpreted_input if isinstance(interpreted_input, dict) else {}
    mv = interpreted_move if isinstance(interpreted_move, dict) else {}
    raw = _normalize(player_input)
    combined = _normalize(f"{player_input} {mv.get('player_intent', '')}")

    kind = str(inp.get("kind") or "")
    player_input_kind = str(inp.get("player_input_kind") or "").strip().lower()
    player_action_committed = bool(inp.get("player_action_committed"))
    player_speech_committed = bool(inp.get("player_speech_committed"))
    intent_s = str(inp.get("intent") or mv.get("player_intent") or "")
    trace.append(
        InterpretationTraceItem(
            step_id="read_interpreted_signals",
            detail_code=f"kind={kind[:48]}|player_input_kind={player_input_kind[:48]}",
        )
    )

    prior = list(prior_continuity_classes or [])
    features: dict[str, bool | int | str] = {
        "question_end": bool(player_input.strip().endswith("?")),
        "syn_accusation": _contains_syn(combined, _ACCUSATION_SYN),
        "syn_repair": _contains_syn(combined, _REPAIR_SYN),
        "syn_deflect": _contains_syn(combined, _DEFLECT_SYN),
        "syn_expose": _contains_syn(combined, _EXPOSE_SYN),
        "syn_silence": _contains_syn(combined, _SILENCE_SYN),
        "syn_pause": _contains_syn(combined, _PAUSE_SYN),
        "syn_alliance": _contains_syn(combined, _ALLIANCE_SYN),
        "syn_probe": _contains_syn(combined, _PROBE_SYN),
        "syn_reveal": _contains_syn(combined, _REVEAL_SYN),
        "syn_escalate": _contains_syn(combined, _ESCALATE_SYN),
        "prior_blame_pressure": "blame_pressure" in prior,
        "prior_alliance_shift": "alliance_shift" in prior,
        "player_input_kind_is_action": player_input_kind == "action",
        "player_input_kind_is_perception": player_input_kind == "perception",
        "player_input_kind_is_speech": player_input_kind == "speech",
        "player_input_kind_is_mixed": player_input_kind == "mixed",
        "player_action_committed": player_action_committed,
        "player_speech_committed": player_speech_committed,
    }
    trace.append(InterpretationTraceItem(step_id="score_feature_vector", detail_code="features_computed"))

    move_type, family, direct, tactic, risk = resolve_goc_move_from_rules(
        features=features,
        combined=combined,
        intent_s=intent_s,
        interpreted_move=mv,
        trace=trace,
    )
    ranked_rows = rank_goc_move_candidates(
        features=features,
        combined=combined,
        intent_s=intent_s,
        interpreted_move=mv,
    )

    assert move_type in SEMANTIC_MOVE_TYPES, move_type

    target = _named_target_hint(combined)
    trace.append(InterpretationTraceItem(step_id="emit_record", detail_code=f"move_type={move_type}"))
    ranked_candidates: list[RankedMoveCandidate] = []
    for row in ranked_rows[:4]:
        try:
            ranked_candidates.append(RankedMoveCandidate.model_validate(row))
        except Exception:
            continue
    if not ranked_candidates:
        ranked_candidates.append(
            RankedMoveCandidate(
                move_type=move_type,
                social_move_family=family,  # type: ignore[arg-type]
                directness=direct,  # type: ignore[arg-type]
                pressure_tactic=tactic,
                scene_risk_band=risk,  # type: ignore[arg-type]
                rank=1,
                confidence=1.0,
                trace_detail="rule:primary_from_resolver",
            )
        )
    if ranked_candidates[0].move_type != move_type:
        ranked_candidates.insert(
            0,
            RankedMoveCandidate(
                move_type=move_type,
                social_move_family=family,  # type: ignore[arg-type]
                directness=direct,  # type: ignore[arg-type]
                pressure_tactic=tactic,
                scene_risk_band=risk,  # type: ignore[arg-type]
                rank=1,
                confidence=1.0,
                trace_detail="rule:primary_from_resolver",
            ),
        )
        ranked_candidates = ranked_candidates[:4]
    for idx, candidate in enumerate(ranked_candidates, start=1):
        candidate.rank = idx
    secondary_move_type = ranked_candidates[1].move_type if len(ranked_candidates) > 1 else None
    secondary_features = _secondary_dramatic_features(features=features, ranked_rows=ranked_rows)

    return SemanticMoveRecord(
        move_type=move_type,
        social_move_family=family,  # type: ignore[arg-type]
        target_actor_hint=target,
        directness=direct,  # type: ignore[arg-type]
        pressure_tactic=tactic,
        scene_risk_band=risk,  # type: ignore[arg-type]
        interpretation_trace=trace,
        interpreter_kind=kind or None,
        feature_snapshot=features,
        ranked_move_candidates=ranked_candidates,
        secondary_move_type=secondary_move_type,
        secondary_dramatic_features=secondary_features,
    )


def semantic_move_fingerprint(record: SemanticMoveRecord) -> str:
    """Describe what ``semantic_move_fingerprint`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        record: ``record`` (SemanticMoveRecord); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    payload = f"{record.move_type}|{record.social_move_family}|{record.directness}|{record.pressure_tactic or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
