"""Capture foundational dramatic validations for the runtime ledger."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _record_validation

def _capture_scene_energy(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "scene_energy_target")
    transition = _state_dict(ctx, "scene_energy_transition")
    validation = validate_scene_energy_realization(
        scene_energy_target=target,
        scene_energy_transition=transition,
        structured_output=ctx.structured_output,
        scene_plan_record=_state_dict(ctx, "scene_plan_record"),
    )
    _record_validation(
        ctx,
        "scene_energy",
        ASPECT_SCENE_ENERGY,
        validation,
        ctx.hooks.scene_energy_aspect_record(target=target, transition=transition, validation=validation),
    )
def _capture_pacing_rhythm(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "pacing_rhythm_state")
    target = _state_dict(ctx, "pacing_rhythm_target")
    validation = validate_pacing_rhythm_realization(
        pacing_rhythm_target=target,
        pacing_rhythm_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "pacing_rhythm",
        ASPECT_PACING_RHYTHM,
        validation,
        ctx.hooks.pacing_rhythm_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )
def _capture_temporal_control(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "temporal_control_target")
    state_record = _state_dict(ctx, "temporal_control_state")
    validation = validate_temporal_control_realization(
        temporal_control_target=target,
        temporal_control_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "temporal_control",
        ASPECT_TEMPORAL_CONTROL,
        validation,
        build_temporal_control_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )
def _capture_improvisational_coherence(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "improvisational_coherence_target")
    validation = validate_improvisational_coherence_realization(
        improvisational_coherence_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "improvisational_coherence",
        ASPECT_IMPROVISATIONAL_COHERENCE,
        validation,
        build_improvisational_coherence_aspect_record(
            target=target,
            validation=validation,
            source="validator",
        ),
    )
