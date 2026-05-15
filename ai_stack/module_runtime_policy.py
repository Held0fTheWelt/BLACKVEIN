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
from ai_stack.hierarchical_memory_contracts import normalize_hierarchical_memory_policy
from ai_stack.improvisational_coherence_contracts import (
    normalize_improvisational_coherence_policy,
)
from ai_stack.information_disclosure_contracts import normalize_information_disclosure_policy
from ai_stack.meta_narrative_awareness_contracts import (
    normalize_meta_narrative_awareness_policy,
)
from ai_stack.narrative_aspect_contracts import normalize_narrative_aspect_policy
from ai_stack.pacing_rhythm_contracts import normalize_pacing_rhythm_policy
from ai_stack.relationship_state_contracts import normalize_relationship_state_policy
from ai_stack.scene_energy_contracts import normalize_scene_energy_policy
from ai_stack.sensory_context_contracts import normalize_sensory_context_policy
from ai_stack.social_pressure_contracts import normalize_social_pressure_policy
from ai_stack.temporal_control_contracts import normalize_temporal_control_policy


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
    locale_payload: dict[str, Any],
) -> dict[str, Any]:
    layout = _unwrap(layout_payload, "apartment_layout")
    locale = _unwrap(locale_payload, "scene_affordances")
    rooms = layout.get("rooms") if isinstance(layout.get("rooms"), list) else []
    locations = locale.get("locations") if isinstance(locale.get("locations"), list) else []
    by_id: dict[str, Any] = {}
    for row in rooms + locations:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue
        by_id.setdefault(rid, {}).update(_json_safe(row))
    return {
        "setting_id": layout.get("setting_id"),
        "narrative_anchor_area_id": layout.get("narrative_anchor_area_id") or locale.get("current_area"),
        "global_rules": layout.get("global_rules") if isinstance(layout.get("global_rules"), dict) else {},
        "locations": by_id,
        "transitions": layout.get("transitions") if isinstance(layout.get("transitions"), list) else [],
    }


def _object_model(
    *,
    objects_payload: dict[str, Any],
    locale_payload: dict[str, Any],
) -> dict[str, Any]:
    objects_doc = _unwrap(objects_payload, "apartment_objects")
    locale = _unwrap(locale_payload, "scene_affordances")
    by_id: dict[str, Any] = {}
    for source in (
        objects_doc.get("objects") if isinstance(objects_doc.get("objects"), list) else [],
        locale.get("objects") if isinstance(locale.get("objects"), list) else [],
    ):
        for row in source:
            if not isinstance(row, dict):
                continue
            oid = str(row.get("id") or "").strip()
            if not oid:
                continue
            by_id.setdefault(oid, {}).update(_json_safe(row))
    return {
        "default_placement_room_id": objects_doc.get("default_placement_room_id"),
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
    expectation_variation = raw.get("expectation_variation")
    expectation_variation = (
        expectation_variation if isinstance(expectation_variation, dict) else {}
    )
    pacing_rhythm = raw.get("pacing_rhythm")
    pacing_rhythm = pacing_rhythm if isinstance(pacing_rhythm, dict) else {}
    sensory_context = raw.get("sensory_context")
    sensory_context = sensory_context if isinstance(sensory_context, dict) else {}
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
        "callback_web": normalize_callback_web_policy(callback_web),
        "consequence_cascade": normalize_consequence_cascade_policy(consequence_cascade),
        "temporal_control": normalize_temporal_control_policy(temporal_control),
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
    locale_policy: dict[str, Any] = field(default_factory=dict)
    narrative_aspect_policy: dict[str, Any] = field(default_factory=dict)
    information_disclosure_policy: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    dramatic_irony_policy: dict[str, Any] = field(default_factory=dict)
    improvisational_coherence_policy: dict[str, Any] = field(default_factory=dict)
    expectation_variation_policy: dict[str, Any] = field(default_factory=dict)
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
    characters = _read_yaml(module_dir / "characters.yaml")
    layout = _read_yaml(module_dir / "apartment_layout.yaml")
    objects = _read_yaml(module_dir / "apartment_objects.yaml")
    actor_pressure = _read_yaml(module_dir / "actor_pressure_profiles.yaml")
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
    scene_affordances = _unwrap(
        _read_yaml(module_dir / "locale" / "scene_affordances.yaml"),
        "scene_affordances",
    )
    player_input_rules = _read_yaml(module_dir / "locale" / "player_input_rules.yaml")
    module_strings = _read_yaml(module_dir / "locale" / "module_strings.yaml")
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
    meta_narrative_awareness_raw = (
        runtime_intelligence.get("meta_narrative_awareness")
        if isinstance(runtime_intelligence.get("meta_narrative_awareness"), dict)
        else {}
    )
    meta_narrative_awareness_policy = normalize_meta_narrative_awareness_policy(
        meta_narrative_awareness_raw if meta_narrative_awareness_raw else None
    )

    sources = []
    for label, payload in (
        ("module", module_yaml),
        ("characters", characters),
        ("apartment_layout", layout),
        ("apartment_objects", objects),
        ("actor_pressure_profiles", actor_pressure),
        ("phase_beat_policy", phase_policy),
        ("opening_scene_sequence", opening_policy),
        ("hard_forbidden_rules", hard_forbidden),
        ("scene_affordances", scene_affordances),
        ("player_input_rules", player_input_rules),
        ("module_strings", module_strings),
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
        ("expectation_variation_policy", expectation_variation_raw),
        ("meta_narrative_awareness_policy", meta_narrative_awareness_raw),
        ("runtime_intelligence", module_yaml.get("runtime_intelligence") if isinstance(module_yaml.get("runtime_intelligence"), dict) else {}),
    ):
        if payload:
            sources.append(label)

    actor_roster = _actors_from_characters(characters)
    playable_roles = _playable_roles_from_opening(opening_policy)
    locale_policy = {
        "scene_affordances": scene_affordances,
        "player_input_rules": player_input_rules,
        "module_strings": {
            "available": bool(module_strings),
            "top_level_keys": sorted(module_strings.keys()) if isinstance(module_strings, dict) else [],
        },
    }

    return ModuleRuntimePolicy(
        module_id=mid,
        runtime_profile_id=str(runtime_profile_id).strip() if runtime_profile_id else None,
        actor_roster=actor_roster,
        playable_roles=playable_roles,
        location_model=_location_model(layout_payload=layout, locale_payload=scene_affordances),
        object_model=_object_model(objects_payload=objects, locale_payload=scene_affordances),
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
        locale_policy=locale_policy,
        narrative_aspect_policy=narrative_aspect_policy,
        information_disclosure_policy=information_disclosure_policy,
        memory_policy=memory_policy,
        dramatic_irony_policy=dramatic_irony_policy,
        improvisational_coherence_policy=improvisational_coherence_policy,
        expectation_variation_policy=expectation_variation_policy,
        meta_narrative_awareness_policy=meta_narrative_awareness_policy,
        runtime_governance_policy=_runtime_governance_policy(module_yaml),
        content_sources=sources,
    )
