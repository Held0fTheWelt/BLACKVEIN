"""Capture dramatic arc validations for irony, expectation, and momentum."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _record_validation, _state_dict

def _capture_dramatic_irony(ctx: _RuntimeAspectBuild) -> None:
    record = _state_dict(ctx, "dramatic_irony_record")
    validation = validate_dramatic_irony_realization(
        record=record,
        generation=ctx.generation,
        proposed_state_effects=ctx.proposed_state_effects,
    )
    _record_validation(
        ctx,
        "dramatic_irony",
        ASPECT_DRAMATIC_IRONY,
        validation,
        build_dramatic_irony_aspect_record(
            record=record,
            validation=validation,
            source="validator",
        ),
    )
def _capture_expectation_variation(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "expectation_variation_target")
    state_record = _state_dict(ctx, "expectation_variation_state")
    validation = validate_expectation_variation_realization(
        expectation_variation_target=target,
        expectation_variation_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "expectation_variation",
        ASPECT_EXPECTATION_VARIATION,
        validation,
        build_expectation_variation_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )
def _capture_narrative_momentum(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "narrative_momentum_target")
    state_record = _state_dict(ctx, "narrative_momentum_state")
    validation = validate_narrative_momentum_realization(
        narrative_momentum_target=target,
        narrative_momentum_state=state_record,
        structured_output=ctx.structured_output,
        module_runtime_policy=_state_dict(ctx, "module_runtime_policy"),
    )
    policy = ctx.hooks.runtime_governance_section(ctx.state, "narrative_momentum")
    _record_validation(
        ctx,
        "narrative_momentum",
        ASPECT_NARRATIVE_MOMENTUM,
        validation,
        build_narrative_momentum_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            policy=policy,
            source="validator",
        ),
    )
