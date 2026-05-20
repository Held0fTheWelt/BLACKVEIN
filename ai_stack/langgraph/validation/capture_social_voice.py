"""Capture social, tone, and relationship runtime validations."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _record_validation, _state_dict

def _capture_social_pressure(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "social_pressure_state")
    target = _state_dict(ctx, "social_pressure_target")
    validation = validate_social_pressure_metric(
        social_pressure_target=target,
        social_pressure_state=state_record,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    policy = ctx.hooks.runtime_governance_section(ctx.state, "social_pressure")
    _record_validation(
        ctx,
        "social_pressure",
        ASPECT_SOCIAL_PRESSURE,
        validation,
        ctx.hooks.social_pressure_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
            policy=policy,
        ),
    )
def _capture_tonal_consistency(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "tonal_consistency_target")
    policy = ctx.hooks.runtime_governance_section(ctx.state, "tonal_consistency")
    validation = validate_tonal_consistency_realization(
        tonal_consistency_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "tonal_consistency",
        ASPECT_TONAL_CONSISTENCY,
        validation,
        build_tonal_consistency_aspect_record(
            target=target,
            validation=validation,
            policy=policy,
            source="validator",
        ),
    )
def _capture_relationship_state(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "relationship_state_record")
    target = _state_dict(ctx, "relationship_dynamics_target")
    validation = validate_relationship_state_realization(
        relationship_state_record=state_record,
        relationship_dynamics_target=target,
        structured_output=ctx.structured_output,
        actor_lane_context=_state_dict(ctx, "actor_lane_context"),
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    _record_validation(
        ctx,
        "relationship_state",
        ASPECT_RELATIONSHIP_STATE,
        validation,
        build_relationship_state_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )
