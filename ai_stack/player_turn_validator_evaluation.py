"""Local player-turn validator evaluation for ADR-0041 registry adapters.

Thin, deterministic wrappers over existing intent and action-resolution logic.
Does not mutate runtime state or call LLMs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_stack.player_action_resolution import resolve_player_action
from ai_stack.semantic_move_interpretation_goc import interpret_goc_semantic_move
from ai_stack.semantic_move_contract import SEMANTIC_MOVE_TYPES
from story_runtime_core.player_input_intent_contract import (
    is_known_player_input_kind,
    normalize_player_input_kind,
)

LOCAL_PROOF_LEVEL = "local_only"

_UNRESOLVED_INTENT_KINDS: frozenset[str] = frozenset({"unclear", "ambiguous", ""})
_ACTION_RESOLUTION_PASS_STATUSES: frozenset[str] = frozenset({"allowed", "allowed_offscreen"})
_ACTION_RESOLUTION_FAIL_STATUSES: frozenset[str] = frozenset(
    {"blocked", "unsafe", "unknown_target", "ambiguous"}
)


def _base_result(
    validator_id: str,
    *,
    available: bool,
    passed: bool,
    status: str,
    reason: str | None = None,
    contract_pass: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "validator_id": validator_id,
        "available": available,
        "passed": passed,
        "blocking": True,
        "proof_level": LOCAL_PROOF_LEVEL,
        "live_or_staging_evidence": False,
        "status": status,
        "reason": reason,
    }
    if contract_pass is not None:
        payload["contract_pass"] = contract_pass
    payload.update(extra)
    return payload


def _affordance_resolution_passes(affordance_resolution: dict[str, Any]) -> bool:
    status = str(
        affordance_resolution.get("status")
        or affordance_resolution.get("affordance_status")
        or ""
    ).strip().lower()
    policy = str(affordance_resolution.get("action_commit_policy") or "").strip().lower()
    if status in _ACTION_RESOLUTION_FAIL_STATUSES:
        return False
    if policy == "needs_clarification":
        return False
    if status in _ACTION_RESOLUTION_PASS_STATUSES:
        return True
    if status == "partial":
        return policy not in {"needs_clarification"}
    if status == "skipped" and policy == "no_commit":
        return True
    return False


def evaluate_player_intent_contract(
    *,
    raw_player_input: str | None = None,
    interpreted_input: dict[str, Any] | None = None,
    interpreted_move: dict[str, Any] | None = None,
    module_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate player intent contract using local deterministic rules."""
    if not isinstance(interpreted_input, dict):
        return _base_result(
            "player_intent_contract",
            available=False,
            passed=False,
            status="unavailable",
            reason="missing_required_context",
            contract_pass=False,
        )

    player_input_kind = normalize_player_input_kind(interpreted_input.get("player_input_kind"))
    raw_text = str(raw_player_input or interpreted_input.get("raw_text") or "").strip()
    if not player_input_kind and not raw_text:
        return _base_result(
            "player_intent_contract",
            available=False,
            passed=False,
            status="unavailable",
            reason="missing_required_context",
            contract_pass=False,
        )

    if player_input_kind and not is_known_player_input_kind(player_input_kind):
        return _base_result(
            "player_intent_contract",
            available=True,
            passed=False,
            status="rejected",
            reason="unknown_player_input_kind",
            contract_pass=False,
            failure_codes=["unknown_player_input_kind"],
            player_input_kind=player_input_kind,
        )

    if raw_text and player_input_kind in _UNRESOLVED_INTENT_KINDS:
        return _base_result(
            "player_intent_contract",
            available=True,
            passed=False,
            status="rejected",
            reason="unresolved_player_input_kind",
            contract_pass=False,
            failure_codes=["unresolved_player_input_kind"],
            player_input_kind=player_input_kind or None,
        )

    semantic_move_type: str | None = None
    if raw_text and module_id:
        record = interpret_goc_semantic_move(
            module_id=str(module_id).strip(),
            player_input=raw_text,
            interpreted_input=interpreted_input,
            interpreted_move=interpreted_move if isinstance(interpreted_move, dict) else None,
        )
        semantic_move_type = str(record.move_type or "").strip() or None
        if semantic_move_type and semantic_move_type not in SEMANTIC_MOVE_TYPES:
            return _base_result(
                "player_intent_contract",
                available=True,
                passed=False,
                status="rejected",
                reason="invalid_semantic_move_type",
                contract_pass=False,
                failure_codes=["invalid_semantic_move_type"],
                semantic_move_type=semantic_move_type,
            )

    return _base_result(
        "player_intent_contract",
        available=True,
        passed=True,
        status="approved",
        reason=None,
        contract_pass=True,
        player_input_kind=player_input_kind or None,
        semantic_move_type=semantic_move_type,
    )


def evaluate_action_resolution_contract(
    *,
    raw_player_input: str | None = None,
    raw_text: str | None = None,
    interpreted_input: dict[str, Any] | None = None,
    module_id: str | None = None,
    runtime_projection: dict[str, Any] | None = None,
    player_action_frame: dict[str, Any] | None = None,
    affordance_resolution: dict[str, Any] | None = None,
    content_modules_root: Path | None = None,
    environment_state: dict[str, Any] | None = None,
    environment_model: dict[str, Any] | None = None,
    player_local_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate action resolution contract using local deterministic rules."""
    if isinstance(player_action_frame, dict) and isinstance(affordance_resolution, dict):
        aff = affordance_resolution
    else:
        text = str(raw_text or raw_player_input or "").strip()
        if not text or not isinstance(interpreted_input, dict):
            return _base_result(
                "action_resolution_contract",
                available=False,
                passed=False,
                status="unavailable",
                reason="missing_required_context",
                contract_pass=False,
            )
        module = str(module_id or "").strip()
        projection = runtime_projection if isinstance(runtime_projection, dict) else None
        if not module or projection is None:
            return _base_result(
                "action_resolution_contract",
                available=False,
                passed=False,
                status="unavailable",
                reason="missing_required_context",
                contract_pass=False,
            )
        resolved = resolve_player_action(
            raw_text=text,
            interpreted_input=interpreted_input,
            module_id=module,
            runtime_projection=projection,
            content_modules_root=content_modules_root,
            player_local_context=player_local_context
            if isinstance(player_local_context, dict)
            else None,
            environment_state=environment_state if isinstance(environment_state, dict) else None,
            environment_model=environment_model if isinstance(environment_model, dict) else None,
        )
        aff = resolved.get("affordance_resolution")
        if not isinstance(aff, dict):
            return _base_result(
                "action_resolution_contract",
                available=False,
                passed=False,
                status="unavailable",
                reason="missing_affordance_resolution",
                contract_pass=False,
            )

    passed = _affordance_resolution_passes(aff)
    if passed:
        return _base_result(
            "action_resolution_contract",
            available=True,
            passed=True,
            status="approved",
            reason=None,
            contract_pass=True,
            affordance_status=str(
                aff.get("status") or aff.get("affordance_status") or ""
            ).strip()
            or None,
            action_commit_policy=str(aff.get("action_commit_policy") or "").strip() or None,
        )

    return _base_result(
        "action_resolution_contract",
        available=True,
        passed=False,
        status="rejected",
        reason="action_resolution_not_committable",
        contract_pass=False,
        failure_codes=["action_resolution_not_committable"],
        affordance_status=str(aff.get("status") or aff.get("affordance_status") or "").strip()
        or None,
        action_commit_policy=str(aff.get("action_commit_policy") or "").strip() or None,
    )
