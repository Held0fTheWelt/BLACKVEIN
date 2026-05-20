"""Build capability-selection aspect records from manager plans."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _state_dict_or_empty

def _infer_realized_manager_capabilities(
    existing: Any,
    manager_caps: list[Any],
    *,
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
) -> list[Any]:
    realized = list(existing) if isinstance(existing, list) else []
    narrator_actual = narrator_authority.get("actual") if isinstance(narrator_authority.get("actual"), dict) else {}
    npc_actual = npc_authority.get("actual") if isinstance(npc_authority.get("actual"), dict) else {}
    narrator_present = bool(narrator_actual.get("narrator_block_present") or narrator_actual.get("consequence_realized"))
    npc_spoken = int(npc_actual.get("spoken_line_count") or 0) > 0
    npc_action = int(npc_actual.get("action_line_count") or 0) > 0
    for cap in manager_caps:
        text = str(cap or "").strip()
        if not text or text in realized:
            continue
        if text.startswith("narrator.") and narrator_present:
            realized.append(text)
        elif text in {"npc.social_reaction.optional", "npc.direct_answer.allowed"} and npc_spoken:
            realized.append(text)
        elif text == "npc.action_gesture.optional" and npc_action:
            realized.append(text)
    return realized
def _capability_status_bits(selection: dict[str, Any]) -> tuple[dict[str, Any], Any, str]:
    violations = selection.get("violations")
    violation = violations[0] if isinstance(violations, list) and violations else {}
    missing = selection.get("missing_required_capabilities")
    missing_first = missing[0] if isinstance(missing, list) and missing else None
    reason = (
        str(violation.get("reason") or violation.get("capability"))
        if isinstance(violation, dict) and violation
        else f"missing_required_capability:{missing_first}"
        if missing_first
        else ""
    )
    return (violation if isinstance(violation, dict) else {}, missing_first, reason)
def _capability_selection_aspect_record(ctx: _RuntimeAspectBuild, cap_reason: str) -> dict[str, Any]:
    status = str(ctx.capability_selection.get("status") or "missing").strip()
    cap_violation = ctx.cap_violation
    cap_missing = ctx.cap_missing_first
    return make_aspect_record(
        applicable=True,
        status=status if status in {"passed", "failed", "partial"} else "missing",
        expected={
            "blocked_capabilities": ctx.capability_selection.get("blocked_capabilities"),
            "required_capabilities": ctx.capability_selection.get("required_capabilities"),
            "selected_capabilities_must_be_realized_or_marked_missing": True,
            "director_capability_manager_plan": ctx.capability_selection.get("director_capability_manager_plan"),
        },
        selected={
            "requested_capabilities": ctx.capability_selection.get("requested_capabilities"),
            "selected_capabilities": ctx.capability_selection.get("selected_capabilities"),
            "blocked_capabilities": ctx.capability_selection.get("blocked_capabilities"),
            "required_capabilities": ctx.capability_selection.get("required_capabilities"),
            "suppressed_capabilities": ctx.capability_selection.get("suppressed_capabilities"),
        },
        actual={
            "realized_capabilities": ctx.capability_selection.get("realized_capabilities"),
            "violated_capabilities": ctx.capability_selection.get("violated_capabilities"),
            "violations": ctx.capability_selection.get("violations"),
            "missing_required_capabilities": ctx.capability_selection.get("missing_required_capabilities"),
            "forbidden_capability_realized": bool(cap_violation),
        },
        reasons=[cap_reason] if cap_reason else [],
        source="runtime",
        failure_class="hard_contract_failure" if cap_violation else "recoverable_contract_gap" if cap_missing else None,
        failure_reason=(
            str(cap_violation.get("reason") or "forbidden_capability_realized")
            if cap_violation
            else "capability_missing_required"
            if cap_missing
            else None
        ),
        offending_actor_id=cap_violation.get("offending_actor_id") if cap_violation else None,
        selected_capability=cap_missing,
        realized_capability=cap_violation.get("capability") if cap_violation else None,
    )
