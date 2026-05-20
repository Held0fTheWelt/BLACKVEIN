"""Capture meta-narrative and NPC-agency validations."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _record_validation, _state_dict, _state_dict_or_empty

def _capture_meta_narrative(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "meta_narrative_awareness_target")
    validation = validate_meta_narrative_awareness_realization(
        meta_narrative_awareness_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "meta_narrative_awareness",
        ASPECT_META_NARRATIVE_AWARENESS,
        validation,
        build_meta_narrative_awareness_aspect_record(
            target=target,
            validation=validation,
            source="validator",
        ),
    )
def _capture_npc_agency(ctx: _RuntimeAspectBuild) -> None:
    plan = ctx.hooks.npc_agency_plan_from_state(ctx.state)
    actor_lane_context = _state_dict(ctx, "actor_lane_context")
    validation = (
        validate_npc_initiative_realization(
            plan,
            ctx.structured_output,
            actor_lane_context=actor_lane_context,
            strict_required=True,
        )
        if isinstance(plan, dict)
        else None
    )
    ctx.validations["npc_initiative"] = validation
    ctx.ledger = set_aspect_record(
        ctx.ledger,
        ASPECT_NPC_AGENCY,
        ctx.hooks.npc_agency_aspect_record(validation),
    )
    if isinstance(validation, dict):
        ctx.outcome = {**ctx.outcome, "npc_initiative_validation": validation}
