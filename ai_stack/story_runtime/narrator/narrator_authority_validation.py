"""Local narrator-authority contract evaluation for ADR-0041 registry adapters.

Extracts the narrator presence/required check used by runtime aspect assembly
into a deterministic, side-effect-free helper. Does not mutate runtime state.
"""

from __future__ import annotations

from typing import Any

from ai_stack.god_of_carnage_dramatic_alignment import extract_proposed_narrative_text
from ai_stack.opening_shape_normalizer import narration_summary_to_plain_str
from story_runtime_core.player_input_intent_contract import (
    is_mixed_player_input_kind,
    is_narrator_only_player_input_kind,
)

LOCAL_PROOF_LEVEL = "local_only"


def _narrative_text(
    *,
    structured_output: dict[str, Any] | None,
    proposed_state_effects: list[dict[str, Any]] | None,
) -> str:
    structured = structured_output if isinstance(structured_output, dict) else {}
    return "\n".join(
        part
        for part in (
            narration_summary_to_plain_str(structured.get("narration_summary")),
            str(structured.get("narrative_response") or "").strip(),
            extract_proposed_narrative_text(proposed_state_effects or []),
        )
        if str(part or "").strip()
    ).strip()


def evaluate_narrator_authority_contract(
    *,
    structured_output: dict[str, Any] | None,
    turn_number: int | None = None,
    narrator_required: bool | None = None,
    player_input_kind: str | None = None,
    affordance_requires_narrator: bool | None = None,
    narrator_response_expected: bool | None = None,
    proposed_state_effects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate narrator authority contract using local deterministic rules."""
    if structured_output is None and proposed_state_effects is None:
        return {
            "validator_id": "narrator_authority_contract",
            "available": False,
            "passed": False,
            "blocking": True,
            "proof_level": LOCAL_PROOF_LEVEL,
            "live_or_staging_evidence": False,
            "status": "unavailable",
            "reason": "missing_required_context",
        }

    turn = int(turn_number or 0)
    pik = str(player_input_kind or "").strip().lower()
    required = bool(narrator_required)
    if narrator_response_expected is not None:
        required = required or bool(narrator_response_expected)
    if is_narrator_only_player_input_kind(pik) or is_mixed_player_input_kind(pik):
        required = True
    if affordance_requires_narrator is True:
        required = True

    narrative_text = _narrative_text(
        structured_output=structured_output,
        proposed_state_effects=proposed_state_effects,
    )
    narrator_present = bool(narrative_text)
    if turn <= 0 and narrator_present:
        required = True

    if required and not narrator_present:
        return {
            "validator_id": "narrator_authority_contract",
            "available": True,
            "passed": False,
            "blocking": True,
            "proof_level": LOCAL_PROOF_LEVEL,
            "live_or_staging_evidence": False,
            "status": "rejected",
            "contract_pass": False,
            "reason": "narrator_required_missing",
            "failure_codes": ["narrator_required_missing"],
        }

    applicable = bool(required or narrator_present)
    if not applicable:
        return {
            "validator_id": "narrator_authority_contract",
            "available": True,
            "passed": True,
            "blocking": True,
            "proof_level": LOCAL_PROOF_LEVEL,
            "live_or_staging_evidence": False,
            "status": "not_applicable",
            "contract_pass": True,
            "reason": "narrator_authority_not_applicable",
        }

    return {
        "validator_id": "narrator_authority_contract",
        "available": True,
        "passed": True,
        "blocking": True,
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": "approved",
        "contract_pass": True,
        "reason": None,
        "narrator_required": required,
        "narrator_present": narrator_present,
    }
