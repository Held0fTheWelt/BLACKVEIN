"""Semantic move interpretation from AI-provided semantics and runtime signals.

This module intentionally contains no phrase synsets, keyword tables, or
priority-rule stacks. The AI layer may provide a bounded ``semantic_move``
payload; the engine validates that payload against the public contract and
falls back only to neutral or explicit silence signals.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_subtext_policy import build_subtext_record_from_policy
from ai_stack.semantic_move_contract import (
    SEMANTIC_MOVE_TYPES,
    InterpretationTraceItem,
    RankedMoveCandidate,
    SemanticMoveRecord,
)
from story_runtime_core.player_input_intent_contract import (
    is_action_like_player_input_kind,
    is_mixed_player_input_kind,
    is_perception_like_player_input_kind,
    is_question_punctuation_probe_guarded,
    player_input_kind_family,
    question_shape_may_probe,
)


_SOCIAL_MOVE_FAMILIES = {
    "attack",
    "repair",
    "probe",
    "deflect",
    "expose",
    "withdraw",
    "alliance",
    "escalate",
    "reveal",
    "neutral",
}
_DIRECTNESS_VALUES = {"direct", "indirect", "ambiguous"}
_RISK_VALUES = {"low", "moderate", "high"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _semantic_payload(*, interpreted_input: dict[str, Any], interpreted_move: dict[str, Any]) -> dict[str, Any]:
    for container in (interpreted_input, interpreted_move):
        for key in ("semantic_move", "ai_semantic_move", "semantic_move_resolution"):
            value = container.get(key)
            if isinstance(value, dict) and value:
                return value
    return {}


def _first_allowed(value: Any, allowed: set[str] | frozenset[str], fallback: str) -> str:
    text = _clean(value).lower()
    return text if text in allowed else fallback


def _candidate_from_payload(payload: dict[str, Any], *, rank: int, fallback_trace: str) -> RankedMoveCandidate | None:
    if not isinstance(payload, dict):
        return None
    move_type = _first_allowed(payload.get("move_type"), SEMANTIC_MOVE_TYPES, "")
    if not move_type:
        return None
    return RankedMoveCandidate(
        move_type=move_type,
        social_move_family=_first_allowed(payload.get("social_move_family"), _SOCIAL_MOVE_FAMILIES, "neutral"),  # type: ignore[arg-type]
        directness=_first_allowed(payload.get("directness"), _DIRECTNESS_VALUES, "ambiguous"),  # type: ignore[arg-type]
        pressure_tactic=_clean(payload.get("pressure_tactic")) or None,
        scene_risk_band=_first_allowed(payload.get("scene_risk_band"), _RISK_VALUES, "moderate"),  # type: ignore[arg-type]
        rank=rank,
        confidence=max(0.0, min(1.0, float(payload.get("confidence") or 0.75))),
        trace_detail=_clean(payload.get("trace_detail")) or fallback_trace,
    )


def _ranked_candidates(payload: dict[str, Any], primary: RankedMoveCandidate) -> list[RankedMoveCandidate]:
    rows = payload.get("ranked_move_candidates")
    out: list[RankedMoveCandidate] = [primary]
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            cand = _candidate_from_payload(row, rank=len(out) + 1, fallback_trace="ai_semantic_move_candidate")
            if cand and cand.move_type not in {c.move_type for c in out}:
                out.append(cand)
            if len(out) >= 4:
                break
    for idx, cand in enumerate(out, start=1):
        cand.rank = idx
    return out


def _explicit_silence_signal(
    *,
    player_input: str,
    interpreted_input: dict[str, Any],
    interpreted_move: dict[str, Any],
    player_input_kind: str,
) -> tuple[bool, bool]:
    ambiguity = _clean(interpreted_input.get("ambiguity")).lower()
    intent = _clean(interpreted_input.get("intent") or interpreted_move.get("player_intent")).lower()
    non_lexical = (
        not _clean(player_input)
        or ambiguity in {"empty_input", "no_lexical_tokens", "punctuation_only"}
        or player_input_kind == "wait_or_observe"
    )
    interpreted = (
        "withheld_response_or_silence" in intent
        or "silence" in intent
        or bool(interpreted_input.get("silence_negative_space_signal"))
        or non_lexical
    )
    return interpreted, non_lexical


def interpret_goc_semantic_move(
    *,
    module_id: str,
    player_input: str,
    interpreted_input: dict[str, Any] | None,
    interpreted_move: dict[str, Any] | None,
    prior_continuity_classes: list[str] | None = None,
) -> SemanticMoveRecord:
    """Produce a bounded semantic move from AI semantics or explicit silence state."""
    del prior_continuity_classes
    trace: list[InterpretationTraceItem] = [
        InterpretationTraceItem(step_id="normalize_input", detail_code="start")
    ]
    inp = interpreted_input if isinstance(interpreted_input, dict) else {}
    mv = interpreted_move if isinstance(interpreted_move, dict) else {}
    kind = _clean(inp.get("kind"))
    player_input_kind = _clean(inp.get("player_input_kind")).lower()
    player_action_committed = bool(inp.get("player_action_committed"))
    player_speech_committed = bool(inp.get("player_speech_committed"))
    interpreted_silence_signal, non_lexical_silence = _explicit_silence_signal(
        player_input=player_input,
        interpreted_input=inp,
        interpreted_move=mv,
        player_input_kind=player_input_kind,
    )
    trace.append(
        InterpretationTraceItem(
            step_id="read_interpreted_signals",
            detail_code=f"kind={kind[:48]}|player_input_kind={player_input_kind[:48]}",
        )
    )

    payload = _semantic_payload(interpreted_input=inp, interpreted_move=mv)
    trace.append(
        InterpretationTraceItem(
            step_id="read_ai_semantic_move",
            detail_code="present" if payload else "missing",
        )
    )
    feature_snapshot: dict[str, bool | int | str] = {
        "semantic_move_ai_present": bool(payload),
        "semantic_move_ai_required": not bool(payload),
        "interpreted_silence_signal": interpreted_silence_signal,
        "non_lexical_silence_signal": non_lexical_silence,
        "player_input_kind": player_input_kind,
        "player_input_kind_family": player_input_kind_family(player_input_kind),
        "player_input_kind_is_action": is_action_like_player_input_kind(player_input_kind),
        "player_input_kind_is_perception": is_perception_like_player_input_kind(player_input_kind),
        "player_input_kind_is_speech": player_input_kind == "speech",
        "player_input_kind_is_mixed": is_mixed_player_input_kind(player_input_kind),
        "player_input_kind_question_shape_may_probe": question_shape_may_probe(player_input_kind),
        "player_input_kind_question_shape_guarded": is_question_punctuation_probe_guarded(player_input_kind),
        "player_action_committed": player_action_committed,
        "player_speech_committed": player_speech_committed,
        "non_goc": module_id != GOC_MODULE_ID,
    }

    if payload:
        primary = _candidate_from_payload(payload, rank=1, fallback_trace="ai_semantic_move")
    elif interpreted_silence_signal:
        primary = RankedMoveCandidate(
            move_type="silence_withdrawal",
            social_move_family="withdraw",
            directness="ambiguous",
            pressure_tactic=None,
            scene_risk_band="moderate",
            rank=1,
            confidence=0.85,
            trace_detail="runtime_signal:silence_negative_space",
        )
    else:
        primary = RankedMoveCandidate(
            move_type="establish_situational_pressure",
            social_move_family="neutral",
            directness="ambiguous",
            pressure_tactic=None,
            scene_risk_band="low",
            rank=1,
            confidence=0.5,
            trace_detail="semantic_move_ai_required",
        )
    if primary is None:
        primary = RankedMoveCandidate(
            move_type="establish_situational_pressure",
            social_move_family="neutral",
            directness="ambiguous",
            pressure_tactic=None,
            scene_risk_band="low",
            rank=1,
            confidence=0.5,
            trace_detail="invalid_ai_semantic_move_fallback",
        )

    ranked_candidates = _ranked_candidates(payload, primary) if payload else [primary]
    secondary_move_type = ranked_candidates[1].move_type if len(ranked_candidates) > 1 else None
    secondary_features = [f"secondary_move:{secondary_move_type}"] if secondary_move_type else []
    target_actor_hint = (
        _clean(payload.get("target_actor_hint"))
        or _clean(payload.get("target_actor_id"))
        or _clean(payload.get("resolved_target_id"))
        or None
    )
    trace.append(InterpretationTraceItem(step_id="emit_record", detail_code=f"move_type={primary.move_type}"))
    evidence_codes = [
        primary.trace_detail,
        f"move_type:{primary.move_type}",
        f"directness:{primary.directness}",
        f"risk:{primary.scene_risk_band}",
    ]
    for key, value in sorted(feature_snapshot.items()):
        if isinstance(value, bool) and value:
            evidence_codes.append(f"feature:{key}")
    subtext = build_subtext_record_from_policy(
        move_type=primary.move_type,
        explicit_intent=_clean(inp.get("intent") or mv.get("player_intent")) or None,
        trace_detail=primary.trace_detail,
        evidence_codes=evidence_codes,
    )

    return SemanticMoveRecord(
        move_type=primary.move_type,
        social_move_family=primary.social_move_family,
        target_actor_hint=target_actor_hint,
        directness=primary.directness,
        pressure_tactic=primary.pressure_tactic,
        scene_risk_band=primary.scene_risk_band,
        interpretation_trace=trace,
        interpreter_kind=kind or None,
        feature_snapshot=feature_snapshot,
        ranked_move_candidates=ranked_candidates,
        secondary_move_type=secondary_move_type,
        secondary_dramatic_features=secondary_features,
        subtext=subtext,
    )


def semantic_move_fingerprint(record: SemanticMoveRecord) -> str:
    payload = f"{record.move_type}|{record.social_move_family}|{record.directness}|{record.pressure_tactic or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
