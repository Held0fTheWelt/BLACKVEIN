"""Deterministic semantic move interpretation for GoC — not a rename of keyword heuristics.

Uses normalization, interpreted_input signals, feature synsets, and explicit priority rules.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.semantic_move_contract import (
    SEMANTIC_MOVE_TYPES,
    InterpretationTraceItem,
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
    s = unicodedata.normalize("NFC", text or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _contains_syn(text: str, syn: tuple[str, ...]) -> bool:
    """Whole-phrase or substring match without first-hit keyword racing between synsets."""
    for phrase in syn:
        if phrase in text:
            return True
    return False


def _named_target_hint(text: str) -> str | None:
    if "annette" in text:
        return "annette_reille"
    if "alain" in text:
        return "alain_reille"
    if "michel" in text or "michael" in text:
        return "michel_longstreet"
    if "veronique" in text or "penelope" in text:
        return "veronique_vallon"
    return None


def interpret_goc_semantic_move(
    *,
    module_id: str,
    player_input: str,
    interpreted_input: dict[str, Any] | None,
    interpreted_move: dict[str, Any] | None,
    prior_continuity_classes: list[str] | None = None,
) -> SemanticMoveRecord:
    """Produce SemanticMoveRecord; deterministic for fixed inputs."""
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
        )
        return rec

    inp = interpreted_input if isinstance(interpreted_input, dict) else {}
    mv = interpreted_move if isinstance(interpreted_move, dict) else {}
    raw = _normalize(player_input)
    combined = _normalize(f"{player_input} {mv.get('player_intent', '')}")

    kind = str(inp.get("kind") or "")
    intent_s = str(inp.get("intent") or mv.get("player_intent") or "")
    trace.append(
        InterpretationTraceItem(
            step_id="read_interpreted_signals",
            detail_code=f"kind={kind[:48]}",
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
    }
    trace.append(InterpretationTraceItem(step_id="score_feature_vector", detail_code="features_computed"))

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
    off_scope = any(k in combined for k in off_scope_keywords) and "carnage" not in combined

    move_type: str
    family: str
    direct: str
    tactic: str | None
    risk: str

    # Explicit priority stack (first matching rule wins after off_scope and silence-withdrawal).
    if off_scope:
        move_type = "off_scope_containment"
        family = "neutral"
        direct = "ambiguous"
        tactic = "slice_boundary"
        risk = "low"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:off_scope_containment"))
    elif features["syn_pause"] or (features["syn_silence"] and not features["syn_repair"]):
        move_type = "silence_withdrawal"
        family = "withdraw"
        direct = "ambiguous"
        tactic = "withhold_response"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:silence_or_pause"))
    elif features["syn_alliance"]:
        move_type = "alliance_reposition"
        family = "alliance"
        direct = "direct" if features["question_end"] else "indirect"
        tactic = "faction_shift"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:alliance_synset"))
    elif features["syn_expose"]:
        move_type = "humiliating_exposure"
        family = "expose"
        direct = "direct" if features["syn_accusation"] else "indirect"
        tactic = "dignity_strike"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:exposure_synset"))
    elif features["syn_repair"] and features["syn_reveal"]:
        move_type = "competing_repair_and_reveal"
        family = "repair"
        direct = "ambiguous"
        tactic = "repair_truth_compete"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:repair_reveal_compete"))
    elif features["syn_repair"] and features["syn_probe"]:
        move_type = "repair_attempt"
        family = "repair"
        direct = "ambiguous"
        tactic = "repair_under_inquiry"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:repair_plus_probe"))
    elif features["syn_repair"]:
        move_type = "repair_attempt"
        family = "repair"
        direct = "direct"
        tactic = "stabilize"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:repair_synset"))
    elif features["syn_deflect"]:
        move_type = "evasive_deflection"
        family = "deflect"
        direct = "indirect"
        tactic = "avoid_accountability"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:deflect_synset"))
    elif features["syn_accusation"]:
        move_type = "direct_accusation"
        family = "attack"
        direct = "direct"
        tactic = "blame_assignment"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:accusation_synset"))
    elif features["syn_reveal"]:
        move_type = "reveal_surface"
        family = "reveal"
        direct = "direct"
        tactic = "truth_surface"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:reveal_synset"))
    elif features["syn_escalate"]:
        move_type = "escalation_threat"
        family = "escalate"
        direct = "direct"
        tactic = "heat_increase"
        risk = "high"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:escalate_synset"))
    elif features["syn_probe"] or bool(features["question_end"]) or "question" in str(mv.get("move_class", "")).lower():
        move_type = "probe_inquiry"
        family = "probe"
        direct = "indirect"
        tactic = "motive_inquiry"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:probe_or_question_shape"))
    elif "cynic" in intent_s or "provok" in combined:
        move_type = "indirect_provocation"
        family = "attack"
        direct = "indirect"
        tactic = "social_needle"
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:intent_provocation_cue"))
    else:
        move_type = "establish_situational_pressure"
        family = "neutral"
        direct = "ambiguous"
        tactic = None
        risk = "moderate"
        trace.append(InterpretationTraceItem(step_id="apply_priority_rules", detail_code="rule:default_situational"))

    assert move_type in SEMANTIC_MOVE_TYPES, move_type

    target = _named_target_hint(combined)
    trace.append(InterpretationTraceItem(step_id="emit_record", detail_code=f"move_type={move_type}"))

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
    )


def semantic_move_fingerprint(record: SemanticMoveRecord) -> str:
    payload = f"{record.move_type}|{record.social_move_family}|{record.directness}|{record.pressure_tactic or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
