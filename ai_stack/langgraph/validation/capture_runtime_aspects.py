"""Run each narrative/runtime aspect validator into the shared context."""

from __future__ import annotations

from .contracts import _RuntimeAspectBuild
from .capture_dramatic_foundation import (
    _capture_improvisational_coherence, _capture_pacing_rhythm,
    _capture_scene_energy, _capture_temporal_control,
)
from .capture_dramatic_arc import (
    _capture_dramatic_irony, _capture_expectation_variation,
    _capture_narrative_momentum,
)
from .capture_meta_and_npc import _capture_meta_narrative, _capture_npc_agency
from .capture_narrative_texture import (
    _capture_genre_awareness, _capture_information_disclosure,
    _capture_sensory_context, _capture_symbolic_object,
)
from .capture_social_voice import (
    _capture_relationship_state, _capture_social_pressure,
    _capture_tonal_consistency,
)

def _capture_runtime_validations(ctx: _RuntimeAspectBuild) -> None:
    _capture_scene_energy(ctx)
    _capture_pacing_rhythm(ctx)
    _capture_temporal_control(ctx)
    _capture_improvisational_coherence(ctx)
    _capture_social_pressure(ctx)
    _capture_tonal_consistency(ctx)
    _capture_relationship_state(ctx)
    _capture_genre_awareness(ctx)
    _capture_symbolic_object(ctx)
    _capture_sensory_context(ctx)
    _capture_information_disclosure(ctx)
    _capture_dramatic_irony(ctx)
    _capture_expectation_variation(ctx)
    _capture_narrative_momentum(ctx)
    _capture_meta_narrative(ctx)
    _capture_npc_agency(ctx)
