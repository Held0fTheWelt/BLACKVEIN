"""Generic module runtime policy loader.

This loader assembles module-specific runtime intelligence data into a neutral
``ModuleRuntimePolicy`` shape. The engine consumes the shape, not concrete
module names, actor names, locations, beats, or prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ai_stack.authority_contracts import default_authority_policy
from ai_stack.callback_web_contracts import normalize_callback_web_policy
from ai_stack.consequence_cascade_contracts import normalize_consequence_cascade_policy
from ai_stack.dramatic_capability_contracts import default_capability_policy
from ai_stack.dramatic_irony_contracts import normalize_dramatic_irony_policy
from ai_stack.expectation_variation_contracts import normalize_expectation_variation_policy
from ai_stack.genre_awareness_contracts import normalize_genre_awareness_policy
from ai_stack.hierarchical_memory_contracts import normalize_hierarchical_memory_policy
from ai_stack.improvisational_coherence_contracts import (
    normalize_improvisational_coherence_policy,
)
from ai_stack.information_disclosure_contracts import normalize_information_disclosure_policy
from ai_stack.meta_narrative_awareness_contracts import (
    normalize_meta_narrative_awareness_policy,
)
from ai_stack.narrative_aspect_contracts import normalize_narrative_aspect_policy
from ai_stack.narrative_momentum_contracts import normalize_narrative_momentum_policy
from ai_stack.pacing_rhythm_contracts import normalize_pacing_rhythm_policy
from ai_stack.relationship_state_contracts import normalize_relationship_state_policy
from ai_stack.scene_energy_contracts import normalize_scene_energy_policy
from ai_stack.sensory_context_contracts import normalize_sensory_context_policy
from ai_stack.social_pressure_contracts import normalize_social_pressure_policy
from ai_stack.symbolic_object_resonance_contracts import (
    normalize_symbolic_object_resonance_policy,
)
from ai_stack.temporal_control_contracts import normalize_temporal_control_policy
from ai_stack.tonal_consistency_contracts import normalize_tonal_consistency_policy
from story_runtime_core.language_adapter import build_interaction_surface


MODULE_RUNTIME_POLICY_SCHEMA_VERSION = "module_runtime_policy.v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


def _read_first_yaml(paths: list[Path]) -> dict[str, Any]:
    for path in paths:
        payload = _read_yaml(path)
        if payload:
            return payload
    return {}


def _read_character_documents(module_dir: Path) -> dict[str, Any]:
    char_dir = module_dir / "characters"
    if not char_dir.is_dir():
        return {}
    chars: dict[str, Any] = {}
    for path in sorted(char_dir.rglob("*.yaml")):
        payload = _read_yaml(path)
        doc = payload.get("character_document") or payload.get("character")
        if not isinstance(doc, dict):
            continue
        char_id = str(doc.get("id") or doc.get("canonical_id") or path.stem).strip()
        if not char_id:
            continue
        chars[char_id] = {
            "id": char_id,
            "actor_id": doc.get("actor_id") or doc.get("runtime_actor_id") or char_id,
            "runtime_actor_id": doc.get("runtime_actor_id") or doc.get("actor_id") or char_id,
            "name": doc.get("name") or char_id,
            "role": doc.get("role"),
            **doc,
        }
    return {"characters": chars} if chars else {}


def _read_locations(module_dir: Path) -> dict[str, Any]:
    locations = _unwrap(
        _read_first_yaml(
            [
                module_dir / "locations" / "index.yaml",
                module_dir / "locations" / "locations.yaml",
                module_dir / "locations.yaml",
            ]
        ),
        "locations",
    )
    loc_dir = module_dir / "locations"
    reserved = {"index.yaml", "locations.yaml", "apartment_layout.yaml"}
    merged: dict[str, Any] = {}
    for row in locations.get("places") if isinstance(locations.get("places"), list) else []:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").strip()
        if rid:
            merged[rid] = row
    if loc_dir.is_dir():
        for path in sorted(loc_dir.rglob("*.yaml")):
            if path.name in reserved:
                continue
            payload = _read_yaml(path)
            row = payload.get("location") or payload.get("place")
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or path.stem).strip()
            if rid:
                merged[rid] = row
    if merged:
        locations = dict(locations)
        locations["places"] = list(merged.values())
    return locations


def _read_objects(module_dir: Path) -> dict[str, Any]:
    objects = _unwrap(
        _read_first_yaml(
            [
                module_dir / "objects" / "index.yaml",
                module_dir / "objects" / "objects.yaml",
                module_dir / "objects.yaml",
            ]
        ),
        "objects",
    )
    obj_dir = module_dir / "objects"
    reserved = {"index.yaml", "objects.yaml"}
    object_documents: dict[str, Any] = {}
    if obj_dir.is_dir():
        for path in sorted(obj_dir.rglob("*.yaml")):
            if path.name in reserved:
                continue
            payload = _read_yaml(path)
            row = payload.get("object") or payload.get("object_document")
            if not isinstance(row, dict):
                continue
            oid = str(row.get("id") or path.stem).strip()
            if not oid:
                continue
            object_doc = dict(row)
            object_doc.setdefault("source_ref", path.relative_to(module_dir).as_posix())
            object_documents[oid] = object_doc
    if object_documents:
        objects = dict(objects)
        objects["object_documents"] = object_documents
    return objects


def _unwrap(payload: dict[str, Any], key: str) -> dict[str, Any]:
    nested = payload.get(key)
    return nested if isinstance(nested, dict) else payload


def _actors_from_characters(characters_payload: dict[str, Any]) -> dict[str, Any]:
    chars = characters_payload.get("characters")
    if not isinstance(chars, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in chars.items():
        if not isinstance(value, dict):
            continue
        actor_id = str(value.get("id") or key).strip()
        if not actor_id:
            continue
        out[actor_id] = {
            "id": actor_id,
            "runtime_actor_id": value.get("runtime_actor_id") or value.get("actor_id") or actor_id,
            "display_name": value.get("name") or value.get("display_name") or actor_id,
            "role": value.get("role"),
            "profile": _json_safe(value),
        }
    return out


def _playable_roles_from_opening(opening_policy: dict[str, Any]) -> list[str]:
    events = opening_policy.get("narrative_events")
    if not isinstance(events, list):
        return []
    roles: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        variants = event.get("role_variants")
        if not isinstance(variants, dict):
            continue
        for role_id in variants:
            rid = str(role_id or "").strip()
            if rid and rid not in roles:
                roles.append(rid)
    return roles


def _location_model(
    *,
    layout_payload: dict[str, Any],
    interaction_surface_payload: dict[str, Any],
    locations_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layout = _unwrap(layout_payload, "apartment_layout")
    interaction_surface = _unwrap(interaction_surface_payload, "scene_affordances")
    authored_locations = _unwrap(locations_payload or {}, "locations")
    rooms = layout.get("rooms") if isinstance(layout.get("rooms"), list) else []
    locations = (
        interaction_surface.get("locations")
        if isinstance(interaction_surface.get("locations"), list)
        else []
    )
    authored_places = (
        authored_locations.get("places") if isinstance(authored_locations.get("places"), list) else []
    )
    by_id: dict[str, Any] = {}
    for row in rooms + authored_places + locations:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue
        by_id.setdefault(rid, {}).update(_json_safe(row))
    return {
        "setting_id": layout.get("setting_id"),
        "narrative_anchor_area_id": layout.get("narrative_anchor_area_id")
        or interaction_surface.get("current_area"),
        "global_rules": layout.get("global_rules") if isinstance(layout.get("global_rules"), dict) else {},
        "locations": by_id,
        "transitions": layout.get("transitions") if isinstance(layout.get("transitions"), list) else [],
    }


def _object_model(
    *,
    objects_payload: dict[str, Any],
    interaction_surface_payload: dict[str, Any],
) -> dict[str, Any]:
    objects_doc = _unwrap(objects_payload, "objects")
    interaction_surface = _unwrap(interaction_surface_payload, "scene_affordances")
    by_id: dict[str, Any] = {}
    object_documents = (
        objects_doc.get("object_documents")
        if isinstance(objects_doc.get("object_documents"), dict)
        else {}
    )
    for object_id, doc in object_documents.items():
        if not isinstance(doc, dict):
            continue
        oid = str(doc.get("id") or object_id or "").strip()
        if not oid:
            continue
        placement = doc.get("placement_location_id") or doc.get("placement_room_id")
        by_id.setdefault(oid, {}).update(
            _json_safe(
                {
                    "id": oid,
                    "placement_location_id": placement,
                    "placement_room_id": placement,
                    "materiality": doc.get("description"),
                    **doc,
                }
            )
        )
    for source in (
        interaction_surface.get("objects")
        if isinstance(interaction_surface.get("objects"), list)
        else [],
    ):
        for row in source:
            if not isinstance(row, dict):
                continue
            oid = str(row.get("id") or "").strip()
            if not oid:
                continue
            by_id.setdefault(oid, {}).update(_json_safe(row))
    return {
        "default_placement_room_id": objects_doc.get("default_placement_location_id"),
        "objects": by_id,
    }


def _authority_policy(hard_forbidden_policy: dict[str, Any]) -> dict[str, Any]:
    policy = default_authority_policy()
    policy["hard_forbidden_policy"] = _json_safe(hard_forbidden_policy)
    structural = (
        hard_forbidden_policy.get("hard_forbidden_detection", {}).get("structural_checks")
        if isinstance(hard_forbidden_policy.get("hard_forbidden_detection"), dict)
        else []
    )
    if isinstance(structural, list):
        policy["structural_checks"] = _json_safe(structural)
    return policy


def _capability_policy(hard_forbidden_policy: dict[str, Any]) -> dict[str, Any]:
    policy = default_capability_policy()
    marker_map = (
        hard_forbidden_policy.get("hard_forbidden_detection", {}).get("marker_map")
        if isinstance(hard_forbidden_policy.get("hard_forbidden_detection"), dict)
        else {}
    )
    if isinstance(marker_map, dict):
        policy["hard_forbidden_marker_map"] = _json_safe(marker_map)
    return policy


def _runtime_governance_policy(module_yaml: dict[str, Any]) -> dict[str, Any]:
    raw = module_yaml.get("runtime_intelligence")
    raw = raw if isinstance(raw, dict) else {}
    action_short_path = raw.get("action_resolution_short_path")
    action_short_path = action_short_path if isinstance(action_short_path, dict) else {}
    player_freedom = raw.get("player_freedom")
    player_freedom = player_freedom if isinstance(player_freedom, dict) else {}
    visible_projection = raw.get("visible_projection")
    visible_projection = visible_projection if isinstance(visible_projection, dict) else {}
    continuity = raw.get("continuity")
    continuity = continuity if isinstance(continuity, dict) else {}
    capability_gate = raw.get("capability_gate")
    capability_gate = capability_gate if isinstance(capability_gate, dict) else {}
    scene_energy = raw.get("scene_energy")
    scene_energy = scene_energy if isinstance(scene_energy, dict) else {}
    dramatic_irony = raw.get("dramatic_irony")
    dramatic_irony = dramatic_irony if isinstance(dramatic_irony, dict) else {}
    callback_web = raw.get("callback_web")
    callback_web = callback_web if isinstance(callback_web, dict) else {}
    consequence_cascade = raw.get("consequence_cascade")
    consequence_cascade = consequence_cascade if isinstance(consequence_cascade, dict) else {}
    temporal_control = raw.get("temporal_control")
    temporal_control = temporal_control if isinstance(temporal_control, dict) else {}
    tonal_consistency = raw.get("tonal_consistency")
    tonal_consistency = tonal_consistency if isinstance(tonal_consistency, dict) else {}
    genre_awareness = raw.get("genre_awareness")
    genre_awareness = genre_awareness if isinstance(genre_awareness, dict) else {}
    expectation_variation = raw.get("expectation_variation")
    expectation_variation = (
        expectation_variation if isinstance(expectation_variation, dict) else {}
    )
    narrative_momentum = raw.get("narrative_momentum")
    narrative_momentum = narrative_momentum if isinstance(narrative_momentum, dict) else {}
    pacing_rhythm = raw.get("pacing_rhythm")
    pacing_rhythm = pacing_rhythm if isinstance(pacing_rhythm, dict) else {}
    sensory_context = raw.get("sensory_context")
    sensory_context = sensory_context if isinstance(sensory_context, dict) else {}
    symbolic_object_resonance = raw.get("symbolic_object_resonance")
    symbolic_object_resonance = (
        symbolic_object_resonance
        if isinstance(symbolic_object_resonance, dict)
        else {}
    )
    improvisational_coherence = raw.get("improvisational_coherence")
    improvisational_coherence = (
        improvisational_coherence
        if isinstance(improvisational_coherence, dict)
        else {}
    )
    meta_narrative_awareness = raw.get("meta_narrative_awareness")
    meta_narrative_awareness = (
        meta_narrative_awareness
        if isinstance(meta_narrative_awareness, dict)
        else {}
    )
    social_pressure = raw.get("social_pressure")
    social_pressure = social_pressure if isinstance(social_pressure, dict) else {}
    relationship_state_machine = raw.get("relationship_state_machine")
    relationship_state_machine = (
        relationship_state_machine
        if isinstance(relationship_state_machine, dict)
        else {}
    )

    return {
        "action_resolution_short_path": {
            "enabled": bool(action_short_path.get("enabled", False)),
            "allowed_player_input_kinds": _json_safe(
                action_short_path.get("allowed_player_input_kinds")
                if isinstance(action_short_path.get("allowed_player_input_kinds"), list)
                else []
            ),
            "allowed_verbs": _json_safe(
                action_short_path.get("allowed_verbs")
                if isinstance(action_short_path.get("allowed_verbs"), list)
                else []
            ),
            "blocked_player_input_kinds": _json_safe(
                action_short_path.get("blocked_player_input_kinds")
                if isinstance(action_short_path.get("blocked_player_input_kinds"), list)
                else []
            ),
        },
        "player_freedom": {
            "enabled": bool(player_freedom.get("enabled", False)),
            "policy_ref": str(player_freedom.get("policy_ref") or "").strip() or None,
            "canonical_path_control": str(player_freedom.get("canonical_path_control") or "").strip() or None,
            "plausible_affordance_inference": str(player_freedom.get("plausible_affordance_inference") or "").strip()
            or None,
        },
        "visible_projection": {
            "enabled": bool(visible_projection.get("enabled", False)),
            "hard_failure_behavior": str(
                visible_projection.get("hard_failure_behavior") or "recover"
            ).strip()
            or "recover",
            "require_origin_metadata": bool(visible_projection.get("require_origin_metadata", True)),
        },
        "capability_gate": {
            "forbidden_capability_behavior": str(
                capability_gate.get("forbidden_capability_behavior") or "reject"
            ).strip()
            or "reject",
            "missing_required_capability_behavior": str(
                capability_gate.get("missing_required_capability_behavior") or "recover"
            ).strip()
            or "recover",
        },
        "continuity": {
            "hooks": _json_safe(
                continuity.get("hooks") if isinstance(continuity.get("hooks"), list) else []
            ),
        },
        "scene_energy": normalize_scene_energy_policy(scene_energy),
        "pacing_rhythm": normalize_pacing_rhythm_policy(pacing_rhythm),
        "sensory_context": normalize_sensory_context_policy(sensory_context),
        "symbolic_object_resonance": normalize_symbolic_object_resonance_policy(
            symbolic_object_resonance
        ),
        "improvisational_coherence": normalize_improvisational_coherence_policy(
            improvisational_coherence
        ),
        "meta_narrative_awareness": normalize_meta_narrative_awareness_policy(
            meta_narrative_awareness
        ),
        "social_pressure": normalize_social_pressure_policy(social_pressure),
        "relationship_state_machine": normalize_relationship_state_policy(
            relationship_state_machine
        ),
        "dramatic_irony": normalize_dramatic_irony_policy(dramatic_irony),
        "expectation_variation": normalize_expectation_variation_policy(
            expectation_variation
        ),
        "narrative_momentum": normalize_narrative_momentum_policy(
            narrative_momentum
        ),
        "callback_web": normalize_callback_web_policy(callback_web),
        "consequence_cascade": normalize_consequence_cascade_policy(consequence_cascade),
        "temporal_control": normalize_temporal_control_policy(temporal_control),
        "tonal_consistency": normalize_tonal_consistency_policy(tonal_consistency),
        "genre_awareness": normalize_genre_awareness_policy(genre_awareness),
    }


@dataclass(frozen=True)
class ModuleRuntimePolicy:
    module_id: str
    runtime_profile_id: str | None = None
    schema_version: str = MODULE_RUNTIME_POLICY_SCHEMA_VERSION
    actor_roster: dict[str, Any] = field(default_factory=dict)
    playable_roles: list[str] = field(default_factory=list)
    location_model: dict[str, Any] = field(default_factory=dict)
    object_model: dict[str, Any] = field(default_factory=dict)
    phase_policy: dict[str, Any] = field(default_factory=dict)
    beat_policy: dict[str, Any] = field(default_factory=dict)
    authority_policy: dict[str, Any] = field(default_factory=dict)
    capability_policy: dict[str, Any] = field(default_factory=dict)
    hard_forbidden_policy: dict[str, Any] = field(default_factory=dict)
    opening_policy: dict[str, Any] = field(default_factory=dict)
    language_policy: dict[str, Any] = field(default_factory=dict)
    narrative_aspect_policy: dict[str, Any] = field(default_factory=dict)
    information_disclosure_policy: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    dramatic_irony_policy: dict[str, Any] = field(default_factory=dict)
    improvisational_coherence_policy: dict[str, Any] = field(default_factory=dict)
    tonal_consistency_policy: dict[str, Any] = field(default_factory=dict)
    genre_awareness_policy: dict[str, Any] = field(default_factory=dict)
    symbolic_object_resonance_policy: dict[str, Any] = field(default_factory=dict)
    expectation_variation_policy: dict[str, Any] = field(default_factory=dict)
    narrative_momentum_policy: dict[str, Any] = field(default_factory=dict)
    meta_narrative_awareness_policy: dict[str, Any] = field(default_factory=dict)
    runtime_governance_policy: dict[str, Any] = field(default_factory=dict)
    content_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def load_module_runtime_policy(
    module_id: str,
    runtime_profile_id: str | None = None,
    *,
    content_modules_root: Path | str | None = None,
) -> ModuleRuntimePolicy:
    """Load neutral runtime intelligence policy for a content module."""
    mid = str(module_id or "").strip()
    root = Path(content_modules_root) if content_modules_root else _repo_root() / "content" / "modules"
    module_dir = root / mid
    module_yaml = _read_yaml(module_dir / "module.yaml")
    character_documents = _read_character_documents(module_dir)
    characters = character_documents or _read_first_yaml(
        [
            module_dir / "characters" / "index.yaml",
            module_dir / "characters.yaml",
        ]
    )
    layout = _read_first_yaml(
            [
                module_dir / "locations" / "appartment_vallon" / "apartment_layout.yaml",
                module_dir / "locations" / "appartment" / "apartment_layout.yaml",
                module_dir / "locations" / "apartment" / "apartment_layout.yaml",
                module_dir / "locations" / "apartment_layout.yaml",
                module_dir / "apartment_layout.yaml",
            ]
    )
    objects = _read_objects(module_dir)
    locations = _read_locations(module_dir)
    actor_pressure = _read_first_yaml(
        [
            module_dir / "characters" / "details" / "actor_pressure_profiles.yaml",
            module_dir / "characters" / "actor_pressure_profiles.yaml",
            module_dir / "actor_pressure_profiles.yaml",
        ]
    )
    phase_policy_raw = _read_yaml(module_dir / "phase_beat_policy.yaml")
    phase_policy = _unwrap(phase_policy_raw, "phase_beat_policy")
    opening_policy = _unwrap(
        _read_yaml(module_dir / "knowledge" / "opening_scene_sequence.yaml"),
        "opening_scene_sequence",
    )
    hard_forbidden = _unwrap(
        _read_yaml(module_dir / "knowledge" / "hard_forbidden_rules.yaml"),
        "hard_forbidden_rules",
    )
    scene_affordances = build_interaction_surface(mid, content_modules_root=root)
    narrative_aspect_policy = normalize_narrative_aspect_policy(
        _unwrap(
            _read_yaml(module_dir / "narrative_aspect_policy.yaml"),
            "narrative_aspect_policy",
        )
    )
    information_disclosure_policy = normalize_information_disclosure_policy(
        _unwrap(
            _read_yaml(module_dir / "information_disclosure_policy.yaml"),
            "information_disclosure_policy",
        )
    )
    memory_policy = normalize_hierarchical_memory_policy(
        _unwrap(
            _read_yaml(module_dir / "memory_policy.yaml"),
            "memory_policy",
        )
    )
    runtime_intelligence = (
        module_yaml.get("runtime_intelligence")
        if isinstance(module_yaml.get("runtime_intelligence"), dict)
        else {}
    )
    dramatic_irony_raw = (
        runtime_intelligence.get("dramatic_irony")
        if isinstance(runtime_intelligence.get("dramatic_irony"), dict)
        else {}
    )
    dramatic_irony_policy = normalize_dramatic_irony_policy(
        dramatic_irony_raw if dramatic_irony_raw else None
    )
    improvisational_coherence_raw = (
        runtime_intelligence.get("improvisational_coherence")
        if isinstance(runtime_intelligence.get("improvisational_coherence"), dict)
        else {}
    )
    improvisational_coherence_policy = normalize_improvisational_coherence_policy(
        improvisational_coherence_raw if improvisational_coherence_raw else None
    )
    expectation_variation_raw = (
        runtime_intelligence.get("expectation_variation")
        if isinstance(runtime_intelligence.get("expectation_variation"), dict)
        else {}
    )
    expectation_variation_policy = normalize_expectation_variation_policy(
        expectation_variation_raw if expectation_variation_raw else None
    )
    narrative_momentum_raw = (
        runtime_intelligence.get("narrative_momentum")
        if isinstance(runtime_intelligence.get("narrative_momentum"), dict)
        else {}
    )
    narrative_momentum_policy = normalize_narrative_momentum_policy(
        narrative_momentum_raw if narrative_momentum_raw else None
    )
    meta_narrative_awareness_raw = (
        runtime_intelligence.get("meta_narrative_awareness")
        if isinstance(runtime_intelligence.get("meta_narrative_awareness"), dict)
        else {}
    )
    meta_narrative_awareness_policy = normalize_meta_narrative_awareness_policy(
        meta_narrative_awareness_raw if meta_narrative_awareness_raw else None
    )
    tonal_consistency_raw = (
        runtime_intelligence.get("tonal_consistency")
        if isinstance(runtime_intelligence.get("tonal_consistency"), dict)
        else {}
    )
    tonal_consistency_policy = normalize_tonal_consistency_policy(
        tonal_consistency_raw if tonal_consistency_raw else None
    )
    genre_awareness_raw = (
        runtime_intelligence.get("genre_awareness")
        if isinstance(runtime_intelligence.get("genre_awareness"), dict)
        else {}
    )
    genre_awareness_policy = normalize_genre_awareness_policy(
        genre_awareness_raw if genre_awareness_raw else None
    )
    symbolic_object_resonance_raw = (
        runtime_intelligence.get("symbolic_object_resonance")
        if isinstance(runtime_intelligence.get("symbolic_object_resonance"), dict)
        else {}
    )
    symbolic_object_resonance_policy = normalize_symbolic_object_resonance_policy(
        symbolic_object_resonance_raw if symbolic_object_resonance_raw else None
    )

    sources = []
    for label, payload in (
        ("module", module_yaml),
        ("character_documents", character_documents),
        ("characters", characters),
        ("apartment_layout", layout),
        ("objects", objects),
        ("locations", locations),
        ("actor_pressure_profiles", actor_pressure),
        ("phase_beat_policy", phase_policy),
        ("opening_scene_sequence", opening_policy),
        ("hard_forbidden_rules", hard_forbidden),
        ("interaction_surface", scene_affordances),
        ("universal_language_adapter", {"enabled": True}),
        ("narrative_aspect_policy", narrative_aspect_policy if narrative_aspect_policy.get("aspects") else {}),
        (
            "information_disclosure_policy",
            information_disclosure_policy
            if information_disclosure_policy.get("enabled")
            and information_disclosure_policy.get("units")
            else {},
        ),
        ("memory_policy", memory_policy if memory_policy.get("enabled") else {}),
        ("dramatic_irony_policy", dramatic_irony_raw),
        ("improvisational_coherence_policy", improvisational_coherence_raw),
        ("tonal_consistency_policy", tonal_consistency_raw),
        ("genre_awareness_policy", genre_awareness_raw),
        ("symbolic_object_resonance_policy", symbolic_object_resonance_raw),
        ("expectation_variation_policy", expectation_variation_raw),
        ("narrative_momentum_policy", narrative_momentum_raw),
        ("meta_narrative_awareness_policy", meta_narrative_awareness_raw),
        ("runtime_intelligence", module_yaml.get("runtime_intelligence") if isinstance(module_yaml.get("runtime_intelligence"), dict) else {}),
    ):
        if payload:
            sources.append(label)

    actor_roster = _actors_from_characters(characters)
    playable_roles = _playable_roles_from_opening(opening_policy)
    language_policy = {
        "interaction_surface": scene_affordances,
        "adapter": {
            "id": "universal_language_adapter",
            "module_language_lookup_files_required": False,
            "engine_maps_allowed": False,
            "player_input_resolution_source": "ai_semantic_resolution",
            "visible_language_source": "ai_semantic_generation",
        },
    }

    return ModuleRuntimePolicy(
        module_id=mid,
        runtime_profile_id=str(runtime_profile_id).strip() if runtime_profile_id else None,
        actor_roster=actor_roster,
        playable_roles=playable_roles,
        location_model=_location_model(
            layout_payload=layout,
            interaction_surface_payload=scene_affordances,
            locations_payload=locations,
        ),
        object_model=_object_model(
            objects_payload=objects,
            interaction_surface_payload=scene_affordances,
        ),
        phase_policy=phase_policy,
        beat_policy={
            "phase_policy": phase_policy,
            "opening_events": opening_policy.get("narrative_events")
            if isinstance(opening_policy.get("narrative_events"), list)
            else [],
        },
        authority_policy=_authority_policy(hard_forbidden),
        capability_policy=_capability_policy(hard_forbidden),
        hard_forbidden_policy=hard_forbidden,
        opening_policy=opening_policy,
        language_policy=language_policy,
        narrative_aspect_policy=narrative_aspect_policy,
        information_disclosure_policy=information_disclosure_policy,
        memory_policy=memory_policy,
        dramatic_irony_policy=dramatic_irony_policy,
        improvisational_coherence_policy=improvisational_coherence_policy,
        tonal_consistency_policy=tonal_consistency_policy,
        genre_awareness_policy=genre_awareness_policy,
        symbolic_object_resonance_policy=symbolic_object_resonance_policy,
        expectation_variation_policy=expectation_variation_policy,
        narrative_momentum_policy=narrative_momentum_policy,
        meta_narrative_awareness_policy=meta_narrative_awareness_policy,
        runtime_governance_policy=_runtime_governance_policy(module_yaml),
        content_sources=sources,
    )


def minimum_actor_response_count_from_governance(
    *,
    actor_response_floor_target: dict[str, Any] | None = None,
    pacing_mode: str | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
    selected_scene_function: str | None = None,
) -> int:
    """Resolve the minimum actor-response floor from policy or a pre-derived target."""
    if isinstance(actor_response_floor_target, dict):
        try:
            return max(0, int(actor_response_floor_target.get("minimum_actor_response_count") or 0))
        except (TypeError, ValueError):
            pass
    policy = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = policy.get("runtime_governance_policy")
    governance = governance if isinstance(governance, dict) else {}
    energy_policy = governance.get("scene_energy")
    energy_policy = energy_policy if isinstance(energy_policy, dict) else {}
    if not energy_policy.get("enabled"):
        return 1
    profiles = energy_policy.get("scene_function_profiles") or {}
    pacing_profiles = energy_policy.get("pacing_profiles") or {}
    scene_fn = str(selected_scene_function or "").strip()
    pacing = str(pacing_mode or "").strip()
    minimum = 0
    if scene_fn and isinstance(profiles.get(scene_fn), dict):
        try:
            minimum = max(minimum, int(profiles[scene_fn].get("minimum_actor_response_count") or 0))
        except (TypeError, ValueError):
            pass
    if pacing and isinstance(pacing_profiles.get(pacing), dict):
        try:
            minimum = max(
                minimum,
                int(pacing_profiles[pacing].get("minimum_actor_response_count") or 0),
            )
        except (TypeError, ValueError):
            pass
    return minimum if minimum > 0 else 1
