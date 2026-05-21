"""Assemble the runtime-intelligence projection from section builders."""

from __future__ import annotations

from typing import Any

from .identity_fields import IDENTITY_FIELD_PARAMS, build_identity_fields
from .sections.input_section import build_input_section, BUILD_INPUT_SECTION_PARAMS
from .sections.broad_nlu_listening_section import build_broad_nlu_listening_section, BUILD_BROAD_NLU_LISTENING_SECTION_PARAMS
from .sections.conversational_memory_section import build_conversational_memory_section, BUILD_CONVERSATIONAL_MEMORY_SECTION_PARAMS
from .sections.prompt_authority_section import build_prompt_authority_section, BUILD_PROMPT_AUTHORITY_SECTION_PARAMS
from .sections.beat_section import build_beat_section, BUILD_BEAT_SECTION_PARAMS
from .sections.scene_energy_section import build_scene_energy_section, BUILD_SCENE_ENERGY_SECTION_PARAMS
from .sections.pacing_rhythm_section import build_pacing_rhythm_section, BUILD_PACING_RHYTHM_SECTION_PARAMS
from .sections.sensory_context_section import build_sensory_context_section, BUILD_SENSORY_CONTEXT_SECTION_PARAMS
from .sections.symbolic_object_resonance_section import build_symbolic_object_resonance_section, BUILD_SYMBOLIC_OBJECT_RESONANCE_SECTION_PARAMS
from .sections.improvisational_coherence_section import build_improvisational_coherence_section, BUILD_IMPROVISATIONAL_COHERENCE_SECTION_PARAMS
from .sections.meta_narrative_awareness_section import build_meta_narrative_awareness_section, BUILD_META_NARRATIVE_AWARENESS_SECTION_PARAMS
from .sections.social_pressure_section import build_social_pressure_section, BUILD_SOCIAL_PRESSURE_SECTION_PARAMS
from .sections.relationship_state_section import build_relationship_state_section, BUILD_RELATIONSHIP_STATE_SECTION_PARAMS
from .sections.capability_section import build_capability_section, BUILD_CAPABILITY_SECTION_PARAMS
from .sections.authority_section import build_authority_section, BUILD_AUTHORITY_SECTION_PARAMS
from .sections.npc_agency_section import build_npc_agency_section, BUILD_NPC_AGENCY_SECTION_PARAMS
from .sections.dramatic_irony_section import build_dramatic_irony_section, BUILD_DRAMATIC_IRONY_SECTION_PARAMS
from .sections.expectation_variation_section import build_expectation_variation_section, BUILD_EXPECTATION_VARIATION_SECTION_PARAMS
from .sections.narrative_momentum_section import build_narrative_momentum_section, BUILD_NARRATIVE_MOMENTUM_SECTION_PARAMS
from .sections.visible_projection_section import build_visible_projection_section, BUILD_VISIBLE_PROJECTION_SECTION_PARAMS
from .sections.voice_consistency_section import build_voice_consistency_section, BUILD_VOICE_CONSISTENCY_SECTION_PARAMS
from .sections.tonal_consistency_section import build_tonal_consistency_section, BUILD_TONAL_CONSISTENCY_SECTION_PARAMS
from .sections.genre_awareness_section import build_genre_awareness_section, BUILD_GENRE_AWARENESS_SECTION_PARAMS
from .sections.narrative_aspect_section import build_narrative_aspect_section, BUILD_NARRATIVE_ASPECT_SECTION_PARAMS
from .sections.information_disclosure_section import build_information_disclosure_section, BUILD_INFORMATION_DISCLOSURE_SECTION_PARAMS
from .sections.callback_web_section import build_callback_web_section, BUILD_CALLBACK_WEB_SECTION_PARAMS
from .sections.consequence_cascade_section import build_consequence_cascade_section, BUILD_CONSEQUENCE_CASCADE_SECTION_PARAMS
from .sections.temporal_control_section import build_temporal_control_section, BUILD_TEMPORAL_CONTROL_SECTION_PARAMS
from .sections.hierarchical_memory_section import build_hierarchical_memory_section, BUILD_HIERARCHICAL_MEMORY_SECTION_PARAMS
from .sections.branching_forecast_section import build_branching_forecast_section, BUILD_BRANCHING_FORECAST_SECTION_PARAMS
from .sections.commit_section import build_commit_section, BUILD_COMMIT_SECTION_PARAMS


def _pick(values: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    return {name: values[name] for name in names}


def build_projection_payload(values: dict[str, Any]) -> dict[str, Any]:
    payload = build_identity_fields(**_pick(values, IDENTITY_FIELD_PARAMS))
    payload['input'] = build_input_section(**_pick(values, BUILD_INPUT_SECTION_PARAMS))
    payload['broad_nlu_listening'] = build_broad_nlu_listening_section(**_pick(values, BUILD_BROAD_NLU_LISTENING_SECTION_PARAMS))
    payload['conversational_memory'] = build_conversational_memory_section(**_pick(values, BUILD_CONVERSATIONAL_MEMORY_SECTION_PARAMS))
    payload['prompt_authority'] = build_prompt_authority_section(**_pick(values, BUILD_PROMPT_AUTHORITY_SECTION_PARAMS))
    payload['beat'] = build_beat_section(**_pick(values, BUILD_BEAT_SECTION_PARAMS))
    payload['scene_energy'] = build_scene_energy_section(**_pick(values, BUILD_SCENE_ENERGY_SECTION_PARAMS))
    payload['pacing_rhythm'] = build_pacing_rhythm_section(**_pick(values, BUILD_PACING_RHYTHM_SECTION_PARAMS))
    payload['sensory_context'] = build_sensory_context_section(**_pick(values, BUILD_SENSORY_CONTEXT_SECTION_PARAMS))
    payload['symbolic_object_resonance'] = build_symbolic_object_resonance_section(**_pick(values, BUILD_SYMBOLIC_OBJECT_RESONANCE_SECTION_PARAMS))
    payload['improvisational_coherence'] = build_improvisational_coherence_section(**_pick(values, BUILD_IMPROVISATIONAL_COHERENCE_SECTION_PARAMS))
    payload['meta_narrative_awareness'] = build_meta_narrative_awareness_section(**_pick(values, BUILD_META_NARRATIVE_AWARENESS_SECTION_PARAMS))
    payload['social_pressure'] = build_social_pressure_section(**_pick(values, BUILD_SOCIAL_PRESSURE_SECTION_PARAMS))
    payload['relationship_state'] = build_relationship_state_section(**_pick(values, BUILD_RELATIONSHIP_STATE_SECTION_PARAMS))
    payload['capability'] = build_capability_section(**_pick(values, BUILD_CAPABILITY_SECTION_PARAMS))
    payload['authority'] = build_authority_section(**_pick(values, BUILD_AUTHORITY_SECTION_PARAMS))
    payload['npc_agency'] = build_npc_agency_section(**_pick(values, BUILD_NPC_AGENCY_SECTION_PARAMS))
    payload['dramatic_irony'] = build_dramatic_irony_section(**_pick(values, BUILD_DRAMATIC_IRONY_SECTION_PARAMS))
    payload['expectation_variation'] = build_expectation_variation_section(**_pick(values, BUILD_EXPECTATION_VARIATION_SECTION_PARAMS))
    payload['narrative_momentum'] = build_narrative_momentum_section(**_pick(values, BUILD_NARRATIVE_MOMENTUM_SECTION_PARAMS))
    payload['visible_projection'] = build_visible_projection_section(**_pick(values, BUILD_VISIBLE_PROJECTION_SECTION_PARAMS))
    payload['voice_consistency'] = build_voice_consistency_section(**_pick(values, BUILD_VOICE_CONSISTENCY_SECTION_PARAMS))
    payload['tonal_consistency'] = build_tonal_consistency_section(**_pick(values, BUILD_TONAL_CONSISTENCY_SECTION_PARAMS))
    payload['genre_awareness'] = build_genre_awareness_section(**_pick(values, BUILD_GENRE_AWARENESS_SECTION_PARAMS))
    payload['narrative_aspect'] = build_narrative_aspect_section(**_pick(values, BUILD_NARRATIVE_ASPECT_SECTION_PARAMS))
    payload['information_disclosure'] = build_information_disclosure_section(**_pick(values, BUILD_INFORMATION_DISCLOSURE_SECTION_PARAMS))
    payload['callback_web'] = build_callback_web_section(**_pick(values, BUILD_CALLBACK_WEB_SECTION_PARAMS))
    payload['consequence_cascade'] = build_consequence_cascade_section(**_pick(values, BUILD_CONSEQUENCE_CASCADE_SECTION_PARAMS))
    payload['temporal_control'] = build_temporal_control_section(**_pick(values, BUILD_TEMPORAL_CONTROL_SECTION_PARAMS))
    payload['hierarchical_memory'] = build_hierarchical_memory_section(**_pick(values, BUILD_HIERARCHICAL_MEMORY_SECTION_PARAMS))
    payload['branching_forecast'] = build_branching_forecast_section(**_pick(values, BUILD_BRANCHING_FORECAST_SECTION_PARAMS))
    payload['commit'] = build_commit_section(**_pick(values, BUILD_COMMIT_SECTION_PARAMS))
    return payload
