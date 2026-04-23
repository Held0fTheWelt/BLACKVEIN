"""Experience-aware packaging of the visible output bundle.

The bundle produced by ``goc_turn_seams.run_visible_render`` is narration-first.
This module takes that bundle plus a ``StoryRuntimeExperiencePolicy`` and
re-packages it so recap, dramatic_turn, and live_dramatic_scene_simulator
modes are *materially* different in what the player sees.

The rules applied here are intentionally bounded:

* recap mode keeps narration primary and clamps spoken lines/pulses.
* dramatic_turn promotes spoken lines and splits narration into
  narration blocks + action pulses, and carries a beat_progression hint.
* live_dramatic_scene_simulator additionally allows multiple pulses and
  exposes scene continuation metadata.

Every transform leaves the *committed* truth untouched — this is packaging,
not commit mutation.
"""

from __future__ import annotations

import re
from typing import Any

from ai_stack.story_runtime_experience import StoryRuntimeExperiencePolicy


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9\"“])")
_QUOTED_LINE_RE = re.compile(r"[\"“”‚„«»]([^\"“”‚„«»]{2,240})[\"“”‚„«»]")


def _split_sentences(block: str) -> list[str]:
    text = (block or "").strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def _extract_spoken_lines(text: str) -> list[str]:
    matches = _QUOTED_LINE_RE.findall(text or "")
    out: list[str] = []
    for m in matches:
        clean = m.strip()
        if clean and len(clean) >= 2:
            out.append(clean)
    return out


def _is_action_sentence(sentence: str) -> bool:
    lowered = (sentence or "").lower()
    action_hints = (
        " steps", " leans", " rises", " stands", " turns", " slams",
        " strikes", " grips", " pulls", " pushes", " reaches", " shoves",
        " glares", " glances", " snarls", " smirks", " stares", " pounds",
    )
    if any(hint in lowered for hint in action_hints):
        return True
    if lowered.endswith(" forward.") or lowered.endswith(" closer."):
        return True
    return False


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _repetition_guard_strength(policy: StoryRuntimeExperiencePolicy) -> str:
    return str(policy.effective.get("repetition_guard") or "medium").lower()


def _narrator_presence(policy: StoryRuntimeExperiencePolicy) -> str:
    return str(policy.effective.get("narrator_presence") or "medium").lower()


def _dialogue_priority(policy: StoryRuntimeExperiencePolicy) -> str:
    return str(policy.effective.get("dialogue_priority") or "medium").lower()


def _action_visibility(policy: StoryRuntimeExperiencePolicy) -> str:
    return str(policy.effective.get("action_visibility") or "medium").lower()


def _prose_density(policy: StoryRuntimeExperiencePolicy) -> str:
    return str(policy.effective.get("prose_density") or "medium").lower()


def _narration_target_sentence_count(policy: StoryRuntimeExperiencePolicy) -> int:
    density = _prose_density(policy)
    if policy.is_live_mode:
        return {"low": 1, "medium": 2, "high": 3}.get(density, 2)
    if policy.is_dramatic_turn:
        return {"low": 1, "medium": 2, "high": 3}.get(density, 2)
    # recap
    return {"low": 2, "medium": 4, "high": 6}.get(density, 4)


def _max_spoken_lines(policy: StoryRuntimeExperiencePolicy) -> int:
    priority = _dialogue_priority(policy)
    if policy.is_live_mode:
        return {"low": 2, "medium": 4, "high": 6}.get(priority, 4)
    if policy.is_dramatic_turn:
        return {"low": 1, "medium": 3, "high": 5}.get(priority, 3)
    # recap
    return {"low": 0, "medium": 1, "high": 2}.get(priority, 1)


def apply_repetition_guard(lines: list[str], policy: StoryRuntimeExperiencePolicy) -> list[str]:
    strength = _repetition_guard_strength(policy)
    if strength == "low":
        return lines
    deduped = _dedupe_preserve_order(lines)
    if strength == "high" and len(deduped) > 1:
        # Drop lines that are substring-near-duplicates of earlier lines.
        filtered: list[str] = []
        for line in deduped:
            low = line.lower()
            is_near_dup = any(
                low in prev.lower() or prev.lower() in low
                for prev in filtered
            )
            if not is_near_dup:
                filtered.append(line)
        return filtered
    return deduped


def package_bundle_with_policy(
    bundle: dict[str, Any] | None,
    policy: StoryRuntimeExperiencePolicy,
) -> dict[str, Any]:
    """Transform a visible_output_bundle according to the policy.

    Returns a new bundle with added first-class surfaces while preserving the
    original ``gm_narration`` and ``spoken_lines`` (so downstream consumers
    that only know the recap shape still work).
    """
    source = dict(bundle) if isinstance(bundle, dict) else {}
    gm_narration_raw = source.get("gm_narration") or []
    gm_narration: list[str] = [
        s.strip() for s in gm_narration_raw if isinstance(s, str) and s.strip()
    ]
    spoken_lines_raw = source.get("spoken_lines") or []
    spoken_lines: list[str] = [
        s.strip() for s in spoken_lines_raw if isinstance(s, str) and s.strip()
    ]

    full_text = " ".join(gm_narration)
    extracted_spoken = _extract_spoken_lines(full_text)
    combined_spoken = apply_repetition_guard(spoken_lines + extracted_spoken, policy)

    sentences: list[str] = []
    for block in gm_narration:
        sentences.extend(_split_sentences(block))

    narration_blocks: list[str] = []
    action_pulses: list[dict[str, Any]] = []
    kept_narration: list[str] = []

    for sentence in sentences:
        if _is_action_sentence(sentence) and _action_visibility(policy) != "low":
            action_pulses.append(
                {
                    "kind": "action_beat",
                    "text": sentence,
                    "responder_id": source.get("responder_actor_id"),
                }
            )
        else:
            kept_narration.append(sentence)

    narration_cap = _narration_target_sentence_count(policy)
    if _narrator_presence(policy) == "low":
        narration_cap = min(narration_cap, 1 if policy.is_live_mode else 2)
    if narration_cap > 0:
        narration_blocks = kept_narration[:narration_cap]

    spoken_cap = _max_spoken_lines(policy)
    capped_spoken = combined_spoken[: max(0, spoken_cap)]

    # Recap mode intentionally keeps narration dominant: the original
    # ``gm_narration`` list is preserved as primary output. Dramatic_turn and
    # live mode rebuild it from narration_blocks + pulses.
    if policy.is_live_mode or policy.is_dramatic_turn:
        rebuilt_gm: list[str] = []
        if narration_blocks:
            rebuilt_gm.append(" ".join(narration_blocks))
        for pulse in action_pulses[: _pulse_cap(policy)]:
            rebuilt_gm.append(pulse["text"])
        if capped_spoken and policy.is_live_mode:
            # Live mode weaves dialogue between beats.
            for line in capped_spoken:
                rebuilt_gm.append(f"“{line}”")
        if not rebuilt_gm and gm_narration:
            rebuilt_gm = gm_narration
        out_gm = rebuilt_gm
    else:
        # Recap collapses everything into the original narration blocks but
        # still applies repetition guard at the sentence level.
        out_gm = gm_narration or ([" ".join(narration_blocks)] if narration_blocks else [])

    packaged: dict[str, Any] = dict(source)
    packaged["gm_narration"] = out_gm
    packaged["spoken_lines"] = capped_spoken
    packaged["narration_blocks"] = narration_blocks
    packaged["action_pulses"] = action_pulses[: _pulse_cap(policy)]
    packaged["scene_motion_summary"] = _scene_motion_summary(policy, action_pulses, capped_spoken)
    packaged["continuation_state"] = _continuation_state(policy, source)
    packaged["responder_trace"] = _responder_trace(source, action_pulses, capped_spoken)
    packaged["experience_packaging"] = {
        "experience_mode": policy.experience_mode,
        "delivery_profile": policy.delivery_profile,
        "packaging_contract_version": policy.packaging_contract_version,
        "narration_sentence_cap": narration_cap,
        "spoken_line_cap": spoken_cap,
        "pulse_cap": _pulse_cap(policy),
        "repetition_guard": _repetition_guard_strength(policy),
        "narrator_presence": _narrator_presence(policy),
        "dialogue_priority": _dialogue_priority(policy),
        "action_visibility": _action_visibility(policy),
        "pulse_count_emitted": len(packaged["action_pulses"]),
        "spoken_line_count_emitted": len(capped_spoken),
        "degradation_markers": [dict(m) for m in policy.degradation_markers],
    }
    return packaged


def _pulse_cap(policy: StoryRuntimeExperiencePolicy) -> int:
    cap = policy.max_scene_pulses_per_response
    if policy.experience_mode == "turn_based_narrative_recap":
        return min(cap, 1)
    if policy.experience_mode == "dramatic_turn":
        return min(cap, 2)
    return max(1, min(cap, 3))


def _scene_motion_summary(
    policy: StoryRuntimeExperiencePolicy,
    pulses: list[dict[str, Any]],
    spoken: list[str],
) -> dict[str, Any]:
    return {
        "pulses_emitted": len(pulses[: _pulse_cap(policy)]),
        "spoken_line_count": len(spoken),
        "inter_npc_exchange_intensity": policy.effective.get(
            "inter_npc_exchange_intensity"
        ),
        "allow_scene_progress_without_player_action": (
            policy.allow_scene_progress_without_player_action
        ),
        "beat_progression_speed": policy.effective.get("beat_progression_speed"),
    }


def _continuation_state(
    policy: StoryRuntimeExperiencePolicy,
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scene_continues": policy.is_live_mode
        or policy.is_dramatic_turn,
        "experience_mode": policy.experience_mode,
        "last_responder_actor_id": source.get("responder_actor_id"),
    }


def _responder_trace(
    source: dict[str, Any],
    pulses: list[dict[str, Any]],
    spoken: list[str],
) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    primary = source.get("responder_actor_id")
    if primary:
        trace.append({"actor_id": primary, "kind": "primary_responder"})
    for pulse in pulses:
        actor = pulse.get("responder_id")
        if actor:
            trace.append({"actor_id": actor, "kind": "action_pulse"})
    for line in spoken:
        trace.append({"actor_id": primary, "kind": "spoken_line", "excerpt": line[:80]})
    return trace


__all__ = [
    "package_bundle_with_policy",
    "apply_repetition_guard",
]
