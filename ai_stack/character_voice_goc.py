"""GoC character voice profiles derived from canonical module YAML."""

from __future__ import annotations

from typing import Any

from ai_stack.character_mind_contract import FieldProvenance
from ai_stack.character_mind_goc import resolve_runtime_actor_id
from ai_stack.character_voice_contract import CharacterVoiceProfileRecord
from ai_stack.goc_scene_identity import (
    GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY,
    guidance_phase_key_for_scene_id,
)


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _str_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(val).strip()
        for key, val in value.items()
        if str(key).strip() and isinstance(val, str) and val.strip()
    }


def _marker_dict(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, raw_block in value.items():
        marker_key = str(key or "").strip()
        if not marker_key:
            continue
        if isinstance(raw_block, dict):
            markers = _str_list(raw_block.get("markers"))
        else:
            markers = _str_list(raw_block)
        if markers:
            out[marker_key] = markers
    return out


def build_character_voice_profiles_for_goc(
    *,
    yaml_slice: dict[str, Any] | None,
    active_character_keys: list[str],
    current_scene_id: str,
    module_id: str | None = None,
) -> list[CharacterVoiceProfileRecord]:
    """Build voice profiles from canonical GoC YAML for runtime enforcement."""

    if not isinstance(yaml_slice, dict):
        yaml_slice = {}
    voice_root = yaml_slice.get("character_voice") if isinstance(yaml_slice.get("character_voice"), dict) else {}
    chars_root = yaml_slice.get("characters") if isinstance(yaml_slice.get("characters"), dict) else {}
    policy_root = (
        yaml_slice.get("voice_consistency")
        if isinstance(yaml_slice.get("voice_consistency"), dict)
        else {}
    )
    consistency_rules = _str_list(policy_root.get("maintain_consistency"))
    pitfalls = _str_list(policy_root.get("pitfalls_to_avoid"))
    forbidden_markers = _marker_dict(policy_root.get("forbidden_language_markers"))
    phase_key = guidance_phase_key_for_scene_id(current_scene_id or "living_room")
    arc_key = GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY.get(phase_key, "")

    profiles: list[CharacterVoiceProfileRecord] = []
    for raw_key in active_character_keys:
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        vblock = voice_root.get(key) if isinstance(voice_root.get(key), dict) else {}
        cblock = chars_root.get(key) if isinstance(chars_root.get(key), dict) else {}
        runtime_actor_id = resolve_runtime_actor_id(
            key,
            yaml_characters=chars_root,
            module_id=module_id,
        )
        formal_role = str(vblock.get("formal_role") or cblock.get("role") or "").strip()
        baseline_tone = str(vblock.get("baseline_tone") or "").strip()
        speech_patterns = _str_dict(vblock.get("speech_patterns"))
        escalation_arc = _str_dict(vblock.get("escalation_arc"))
        current_phase_hint = str(escalation_arc.get(arc_key, "") or "").strip()

        provenance: dict[str, FieldProvenance] = {}
        if formal_role:
            provenance["formal_role_label"] = FieldProvenance(source="authored")
        if baseline_tone:
            provenance["baseline_tone"] = FieldProvenance(source="authored")
        if speech_patterns:
            provenance["speech_patterns"] = FieldProvenance(source="authored")
        if current_phase_hint:
            provenance["current_phase_voice_hint"] = FieldProvenance(
                source="authored_derived",
                derivation_key=f"escalation_arc.{arc_key}",
            )
        if consistency_rules or pitfalls:
            provenance["voice_consistency_policy"] = FieldProvenance(source="authored")
        if forbidden_markers:
            provenance["forbidden_language_markers"] = FieldProvenance(
                source="authored",
                derivation_key="voice_consistency.forbidden_language_markers",
            )

        profiles.append(
            CharacterVoiceProfileRecord(
                character_key=key,
                runtime_actor_id=runtime_actor_id,
                formal_role_label=formal_role[:512],
                baseline_tone=baseline_tone[:512],
                speech_patterns=speech_patterns,
                escalation_arc=escalation_arc,
                current_phase_voice_hint=current_phase_hint[:512],
                forbidden_language_markers=forbidden_markers,
                consistency_rules=consistency_rules[:12],
                pitfalls_to_avoid=pitfalls[:12],
                provenance=provenance,
            )
        )
    return profiles
