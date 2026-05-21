"""Collect canonical aspect records before projection assembly."""

from __future__ import annotations

from typing import Any

from ..constants import *

_ASPECT_RECORD_NAMES: tuple[tuple[str, str], ...] = (
    ("input_rec", ASPECT_INPUT),
    ("broad_nlu_rec", ASPECT_BROAD_NLU_LISTENING),
    ("action_rec", ASPECT_ACTION_RESOLUTION),
    ("conversational_memory_rec", ASPECT_CONVERSATIONAL_MEMORY),
    ("prompt_authority_rec", ASPECT_PROMPT_AUTHORITY),
    ("beat_rec", ASPECT_BEAT),
    ("scene_energy_rec", ASPECT_SCENE_ENERGY),
    ("pacing_rhythm_rec", ASPECT_PACING_RHYTHM),
    ("sensory_context_rec", ASPECT_SENSORY_CONTEXT),
    ("symbolic_object_rec", ASPECT_SYMBOLIC_OBJECT_RESONANCE),
    ("improvisational_rec", ASPECT_IMPROVISATIONAL_COHERENCE),
    ("meta_narrative_rec", ASPECT_META_NARRATIVE_AWARENESS),
    ("social_pressure_rec", ASPECT_SOCIAL_PRESSURE),
    ("relationship_state_rec", ASPECT_RELATIONSHIP_STATE),
    ("cap_rec", ASPECT_CAPABILITY_SELECTION),
    ("narr_rec", ASPECT_NARRATOR_AUTHORITY),
    ("npc_rec", ASPECT_NPC_AUTHORITY),
    ("npc_agency_rec", ASPECT_NPC_AGENCY),
    ("dramatic_irony_rec", ASPECT_DRAMATIC_IRONY),
    ("expectation_variation_rec", ASPECT_EXPECTATION_VARIATION),
    ("narrative_momentum_rec", ASPECT_NARRATIVE_MOMENTUM),
    ("voice_rec", ASPECT_VOICE_CONSISTENCY),
    ("tonal_rec", ASPECT_TONAL_CONSISTENCY),
    ("genre_awareness_rec", ASPECT_GENRE_AWARENESS),
    ("narrative_rec", ASPECT_NARRATIVE_ASPECT),
    ("disclosure_rec", ASPECT_INFORMATION_DISCLOSURE),
    ("memory_rec", ASPECT_HIERARCHICAL_MEMORY),
    ("callback_rec", ASPECT_CALLBACK_WEB),
    ("cascade_rec", ASPECT_CONSEQUENCE_CASCADE),
    ("temporal_control_rec", ASPECT_TEMPORAL_CONTROL),
    ("validation_rec", ASPECT_VALIDATION),
    ("commit_rec", ASPECT_COMMIT),
    ("visible_rec", ASPECT_VISIBLE_PROJECTION),
)


def _record_or_empty(aspects: dict[str, Any], aspect_key: str) -> dict[str, Any]:
    record = aspects.get(aspect_key)
    return record if isinstance(record, dict) else {}


def collect_aspect_record_sources(ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Collect canonical aspect records and root ledger fields for projection."""
    src = ledger if isinstance(ledger, dict) else {}
    aspect_map = src.get("turn_aspect_ledger")
    aspects = aspect_map if isinstance(aspect_map, dict) else {}
    values = {
        record_name: _record_or_empty(aspects, aspect_key)
        for record_name, aspect_key in _ASPECT_RECORD_NAMES
    }
    values.update(
        src=src,
        aspects=aspects,
        branching_forecast=(
            src.get("branching_forecast")
            if isinstance(src.get("branching_forecast"), dict)
            else {}
        ),
    )
    return values
