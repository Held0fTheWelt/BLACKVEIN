"""Derive and apply runtime capability-selection evidence."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .capability_status import _capability_selection_aspect_record

def _capture_capability_selection(ctx: _RuntimeAspectBuild) -> None:
    selection = build_capability_selection_record(
        interpreted_input=_state_dict_or_empty(ctx, "interpreted_input"),
        player_action_frame=_state_dict_or_empty(ctx, "player_action_frame"),
        affordance_resolution=_state_dict_or_empty(ctx, "affordance_resolution"),
        narrator_authority=ctx.narrator_authority,
        npc_authority=ctx.npc_authority,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    scene_plan = _state_dict_or_empty(ctx, "scene_plan_record")
    manager_plan = scene_plan.get("capability_manager_plan")
    if isinstance(manager_plan, dict) and manager_plan.get("run_only_selected_capabilities"):
        _apply_director_capability_plan(
            selection,
            manager_plan,
            narrator_authority=ctx.narrator_authority,
            npc_authority=ctx.npc_authority,
        )
    ctx.capability_selection = selection
    ctx.cap_violation, ctx.cap_missing_first, cap_reason = _capability_status_bits(selection)
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_CAPABILITY_SELECTION,
        _capability_selection_aspect_record(ctx, cap_reason),
    )
def _apply_director_capability_plan(
    selection: dict[str, Any],
    manager_plan: dict[str, Any],
    *,
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
) -> None:
    manager_caps = list(executable_capabilities_from_manager_plan(manager_plan))
    for key in ("requested_capabilities", "selected_capabilities"):
        selection[key] = _append_unique_text(selection.get(key), manager_caps)
    required = _append_required_manager_caps(
        selection.get("required_capabilities"),
        manager_plan.get("required_capabilities"),
        manager_caps,
    )
    selection["required_capabilities"] = required
    selection["director_capability_manager_plan"] = manager_plan
    selection["director_capability_dispatch_audit"] = manager_plan.get("capability_dispatch_audit")
    selection["suppressed_capabilities"] = _clean_text_list(manager_plan.get("suppressed_capabilities"))
    realized = _infer_realized_manager_capabilities(
        selection.get("realized_capabilities"),
        manager_caps,
        narrator_authority=narrator_authority,
        npc_authority=npc_authority,
    )
    selection["realized_capabilities"] = realized
    missing_required = [cap for cap in required if cap not in set(realized)]
    selection["missing_required_capabilities"] = missing_required
    if selection.get("violations"):
        selection["status"] = "failed"
    elif missing_required:
        selection["status"] = "partial"
    else:
        selection["status"] = "passed"
def _append_unique_text(existing: Any, values: list[Any]) -> list[Any]:
    out = list(existing) if isinstance(existing, list) else []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out
def _append_required_manager_caps(existing: Any, requested: Any, manager_caps: list[Any]) -> list[Any]:
    out = list(existing) if isinstance(existing, list) else []
    for value in requested or []:
        text = str(value or "").strip()
        if text and text in manager_caps and text not in out:
            out.append(text)
    return out
def _clean_text_list(values: Any) -> list[str]:
    return [text for text in (str(value or "").strip() for value in values or []) if text]
