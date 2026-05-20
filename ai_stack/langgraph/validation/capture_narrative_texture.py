"""Capture genre, symbol, sensory, and disclosure validations."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .dependencies import *
from .state_access import _record_validation, _state_dict_or_empty

def _capture_genre_awareness(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "genre_awareness_target")
    state_record = _state_dict(ctx, "genre_awareness_state")
    validation = validate_genre_awareness_realization(
        genre_awareness_target=target,
        genre_awareness_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "genre_awareness",
        ASPECT_GENRE_AWARENESS,
        validation,
        build_genre_awareness_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )
def _capture_symbolic_object(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "symbolic_object_resonance_target")
    state_record = _state_dict(ctx, "symbolic_object_resonance_state")
    validation = validate_symbolic_object_resonance_realization(
        symbolic_object_resonance_target=target,
        symbolic_object_resonance_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "symbolic_object_resonance",
        ASPECT_SYMBOLIC_OBJECT_RESONANCE,
        validation,
        build_symbolic_object_resonance_aspect_record(
            target=target,
            state=state_record,
            validation=validation,
            source="validator",
        ),
    )
def _capture_sensory_context(ctx: _RuntimeAspectBuild) -> None:
    state_record = _state_dict(ctx, "sensory_context_state")
    target = _state_dict(ctx, "sensory_context_target")
    validation = validate_sensory_context_realization(
        sensory_context_target=target,
        sensory_context_state=state_record,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "sensory_context",
        ASPECT_SENSORY_CONTEXT,
        validation,
        ctx.hooks.sensory_context_aspect_record(
            state_record=state_record,
            target=target,
            validation=validation,
        ),
    )
def _capture_information_disclosure(ctx: _RuntimeAspectBuild) -> None:
    target = _state_dict(ctx, "information_disclosure_target")
    validation = validate_information_disclosure_realization(
        information_disclosure_target=target,
        structured_output=ctx.structured_output,
    )
    _record_validation(
        ctx,
        "information_disclosure",
        ASPECT_INFORMATION_DISCLOSURE,
        validation,
        ctx.hooks.information_disclosure_aspect_record(target=target, validation=validation),
    )
