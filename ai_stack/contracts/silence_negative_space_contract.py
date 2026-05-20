"""Silence / negative-space contract for bounded scene decisions.

The contract extends the existing ``silence_brevity_decision`` payload without
changing its stable ``mode`` field, so older runtime consumers keep working
while tests can assert structured invariants.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_frozen_vocabulary import SILENCE_BREVITY_MODES

SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION = "silence_negative_space.v1"

SILENCE_NEGATIVE_SPACE_SOURCES: frozenset[str] = frozenset(
    {
        "default",
        "non_goc_slice",
        "slice_boundary",
        "raw_text",
        "semantic_move",
        "interpreted_input",
        "sparse_fragment",
        "narrative_thread",
        "player_request",
    }
)

SILENCE_NEGATIVE_SPACE_KINDS: frozenset[str] = frozenset(
    {
        "none",
        "empty_input",
        "non_lexical_input",
        "explicit_silence",
        "withheld_answer",
        "awkward_pause",
        "defensive_pause",
        "discomfort_pause",
        "refusal_pressure",
        "provocation_pause",
        "charged_after_tension",
        "player_requested_brevity",
        "boundary_containment",
        "thread_pressure",
        "thread_interpretation_pressure",
    }
)

SILENCE_NEGATIVE_SPACE_FUNCTIONS: frozenset[str] = frozenset(
    {
        "not_applicable",
        "default_verbal_density",
        "withhold_response",
        "carry_tension",
        "compress_response",
        "maintain_pressure",
        "escalate_pressure",
        "contain_boundary",
    }
)

SILENCE_NEGATIVE_SPACE_DURATION_HINTS: frozenset[str] = frozenset(
    {"none", "beat", "short", "held"}
)


class SilenceNegativeSpaceDecision(BaseModel):
    """Structured silence decision carried inside ``silence_brevity_decision``."""

    model_config = {"extra": "forbid"}

    contract: str = Field(default=SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION)
    mode: str
    reason: str
    source: str = "default"
    silence_kind: str = "none"
    dramatic_function: str = "not_applicable"
    pressure_basis: str | None = None
    duration_hint: str = "none"
    requires_visible_beat: bool = False
    blocks_forced_speech: bool = False
    semantic_move_type: str | None = None
    interpreter_signal: str | None = None

    @field_validator("contract")
    @classmethod
    def _contract_supported(cls, value: str) -> str:
        if value != SILENCE_NEGATIVE_SPACE_CONTRACT_VERSION:
            raise ValueError(f"Unsupported silence negative-space contract: {value!r}")
        return value

    @field_validator("mode")
    @classmethod
    def _mode_in_frozen_vocab(cls, value: str) -> str:
        if value not in SILENCE_BREVITY_MODES:
            raise ValueError(f"Invalid silence_brevity mode: {value!r}")
        return value

    @field_validator("source")
    @classmethod
    def _source_supported(cls, value: str) -> str:
        if value not in SILENCE_NEGATIVE_SPACE_SOURCES:
            raise ValueError(f"Invalid silence source: {value!r}")
        return value

    @field_validator("silence_kind")
    @classmethod
    def _kind_supported(cls, value: str) -> str:
        if value not in SILENCE_NEGATIVE_SPACE_KINDS:
            raise ValueError(f"Invalid silence kind: {value!r}")
        return value

    @field_validator("dramatic_function")
    @classmethod
    def _function_supported(cls, value: str) -> str:
        if value not in SILENCE_NEGATIVE_SPACE_FUNCTIONS:
            raise ValueError(f"Invalid silence dramatic function: {value!r}")
        return value

    @field_validator("duration_hint")
    @classmethod
    def _duration_supported(cls, value: str) -> str:
        if value not in SILENCE_NEGATIVE_SPACE_DURATION_HINTS:
            raise ValueError(f"Invalid silence duration hint: {value!r}")
        return value

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _infer_silence_kind(reason: str, mode: str) -> str:
    reason_l = str(reason or "").strip().lower()
    if reason_l == "slice_boundary_containment_move":
        return "boundary_containment"
    if reason_l in {"thin_edge_plus_withheld", "dramatic_silence_move"}:
        return "explicit_silence"
    if reason_l == "silence_withdrawal":
        return "withheld_answer"
    if reason_l in {
        "thin_edge_withheld_upgraded_by_prior_tension",
        "silence_withdrawal_upgraded_by_prior_tension",
    }:
        return "charged_after_tension"
    if reason_l == "sparse_fragment_refusal_or_provocation_pressure":
        return "refusal_pressure"
    if reason_l == "sparse_fragment_defensive_pause_pressure":
        return "defensive_pause"
    if reason_l == "player_requested_brevity":
        return "player_requested_brevity"
    if reason_l == "narrative_thread_pressure_multi_pressure":
        return "thread_pressure"
    if reason_l == "narrative_thread_interpretation_pressure":
        return "thread_interpretation_pressure"
    if mode == "withheld":
        return "withheld_answer"
    return "none"


def _infer_dramatic_function(reason: str, mode: str, silence_kind: str) -> str:
    if silence_kind in {"refusal_pressure", "provocation_pause"}:
        return "escalate_pressure"
    if silence_kind in {"defensive_pause", "discomfort_pause", "player_requested_brevity"}:
        return "compress_response"
    if silence_kind in {"thread_pressure"}:
        return "maintain_pressure"
    if silence_kind == "boundary_containment":
        return "contain_boundary"
    if silence_kind in {
        "empty_input",
        "non_lexical_input",
        "explicit_silence",
        "withheld_answer",
        "awkward_pause",
        "charged_after_tension",
    }:
        return "withhold_response" if mode == "withheld" else "carry_tension"
    if str(reason or "") == "default_verbal_density":
        return "default_verbal_density"
    return "not_applicable"


def build_silence_negative_space_decision(
    *,
    mode: str,
    reason: str,
    source: str = "default",
    silence_kind: str | None = None,
    dramatic_function: str | None = None,
    pressure_basis: str | None = None,
    duration_hint: str | None = None,
    requires_visible_beat: bool | None = None,
    blocks_forced_speech: bool | None = None,
    semantic_move_type: str | None = None,
    interpreter_signal: str | None = None,
) -> dict[str, Any]:
    """Build a normalized silence-negative-space payload for runtime use."""

    kind = silence_kind or _infer_silence_kind(reason, mode)
    function = dramatic_function or _infer_dramatic_function(reason, mode, kind)
    active_negative_space = kind not in {
        "none",
        "boundary_containment",
        "player_requested_brevity",
    }
    if requires_visible_beat is None:
        requires_visible_beat = active_negative_space and mode in {"withheld", "brief"}
    if blocks_forced_speech is None:
        blocks_forced_speech = kind in {
            "empty_input",
            "non_lexical_input",
            "explicit_silence",
            "withheld_answer",
            "awkward_pause",
            "charged_after_tension",
        }
    if duration_hint is None:
        duration_hint = "held" if mode == "withheld" else "beat" if active_negative_space else "none"

    return SilenceNegativeSpaceDecision(
        mode=mode,
        reason=reason,
        source=source,
        silence_kind=kind,
        dramatic_function=function,
        pressure_basis=pressure_basis,
        duration_hint=duration_hint,
        requires_visible_beat=requires_visible_beat,
        blocks_forced_speech=blocks_forced_speech,
        semantic_move_type=semantic_move_type,
        interpreter_signal=interpreter_signal,
    ).to_runtime_dict()


def coerce_silence_negative_space_decision(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy silence payloads into the silence-negative-space contract."""

    src = payload if isinstance(payload, dict) else {}
    mode = str(src.get("mode") or "normal").strip()
    reason = str(src.get("reason") or "default_verbal_density").strip()
    return build_silence_negative_space_decision(
        mode=mode,
        reason=reason,
        source=str(src.get("source") or "default").strip() or "default",
        silence_kind=str(src.get("silence_kind") or "").strip() or None,
        dramatic_function=str(src.get("dramatic_function") or "").strip() or None,
        pressure_basis=src.get("pressure_basis") if isinstance(src.get("pressure_basis"), str) else None,
        duration_hint=str(src.get("duration_hint") or "").strip() or None,
        requires_visible_beat=src.get("requires_visible_beat")
        if isinstance(src.get("requires_visible_beat"), bool)
        else None,
        blocks_forced_speech=src.get("blocks_forced_speech")
        if isinstance(src.get("blocks_forced_speech"), bool)
        else None,
        semantic_move_type=src.get("semantic_move_type") if isinstance(src.get("semantic_move_type"), str) else None,
        interpreter_signal=src.get("interpreter_signal") if isinstance(src.get("interpreter_signal"), str) else None,
    )
