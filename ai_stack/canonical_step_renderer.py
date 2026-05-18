"""Canonical step → SceneBlock renderer.

Walks the resolved `mandatory_beats` of a `CanonicalStep` and emits the
deterministic `SceneBlock` sequence the LDSS commits as visible scene output.

The renderer is deterministic and side-effect-free. It does not call an LLM;
it produces the same blocks every time for a given step + turn number.

For NPC speech beats (`paraphrase_required_with_facts`, `single_word_challenge`,
`amiable_echo`, monologue segments), the rendered text is a deterministic
projection: a short tag line including the actor's intent and the required
facts. A future Phase 7 LLM-paraphrase step may replace this projection with
generated prose while preserving the required-fact tokens; the rendered block
shape stays the same so downstream validators continue to work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_stack.canonical_path_resolver import (
    CanonicalPath,
    CanonicalStep,
    ResolvedBeat,
)
from ai_stack.live_dramatic_scene_simulator import (
    NPCAgencyPlan,
    NPCInitiative,
    SceneBlock,
    SceneBlockDelivery,
    VisibleSceneOutput,
)


# ---------------------------------------------------------------------------
# Renderer output container
# ---------------------------------------------------------------------------

@dataclass
class RenderedStep:
    step_id: str
    visible_scene_output: VisibleSceneOutput
    npc_agency_plan: NPCAgencyPlan | None
    forces_response_records: list[dict[str, Any]]
    state_change_records: list[dict[str, Any]]
    themes_realized: list[dict[str, Any]]
    next_step_unlock_when: dict[str, Any]
    next_step_id: str | None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_canonical_step(
    canonical_path: CanonicalPath,
    step_id: str,
    *,
    turn_number: int,
    human_actor_id: str,
) -> RenderedStep | None:
    """Render a canonical step into deterministic SceneBlocks.

    Returns None if `step_id` is unknown.
    """
    step = canonical_path.get_step(step_id)
    if step is None:
        return None

    blocks: list[SceneBlock] = []
    forces_response_records: list[dict[str, Any]] = []
    npc_initiatives: list[NPCInitiative] = []
    primary_responder_id: str | None = None
    secondary_responder_ids: list[str] = []

    for beat in step.mandatory_beats:
        beat_blocks = _render_beat(step, beat, turn_number=turn_number)
        for b in beat_blocks:
            blocks.append(b)
            if b.block_type == "actor_line" and b.actor_id and b.actor_id != human_actor_id:
                if primary_responder_id is None:
                    primary_responder_id = b.actor_id
                elif b.actor_id != primary_responder_id and b.actor_id not in secondary_responder_ids:
                    secondary_responder_ids.append(b.actor_id)

        speech_intent = _extract_intent_for_initiative(beat)
        if speech_intent:
            actor = speech_intent["actor"]
            if actor and actor != human_actor_id:
                npc_initiatives.append(
                    NPCInitiative(
                        actor_id=actor,
                        intent=speech_intent["intent"],
                        allowed_block_types=speech_intent["allowed_block_types"],
                        target_actor_id=None,
                        passivity_risk="low",
                    )
                )

        if beat.forces_response_from:
            forces_response_records.append({
                "source_step_id": step.id,
                "source_beat_id": beat.id,
                **beat.forces_response_from,
            })

    state_change_records = _project_state_changes(step)

    npc_agency_plan: NPCAgencyPlan | None = None
    if primary_responder_id:
        npc_agency_plan = NPCAgencyPlan(
            turn_number=turn_number,
            primary_responder_id=primary_responder_id,
            secondary_responder_ids=list(secondary_responder_ids),
            npc_initiatives=npc_initiatives,
        )

    return RenderedStep(
        step_id=step.id,
        visible_scene_output=VisibleSceneOutput(blocks=blocks),
        npc_agency_plan=npc_agency_plan,
        forces_response_records=forces_response_records,
        state_change_records=state_change_records,
        themes_realized=list(step.themes_realized_here),
        next_step_unlock_when=dict(step.next_step_unlock_when),
        next_step_id=step.next_step_id(),
    )


# ---------------------------------------------------------------------------
# Per-beat rendering
# ---------------------------------------------------------------------------

def _render_beat(
    step: CanonicalStep,
    beat: ResolvedBeat,
    *,
    turn_number: int,
) -> list[SceneBlock]:
    blocks: list[SceneBlock] = []
    base_id = f"turn-{turn_number}-{step.id}-{beat.id}"

    instruction = beat.director_instruction or {}

    perception_lines = instruction.get("narrator_perception_only") or []
    for idx, line in enumerate(perception_lines):
        text = str(line).strip()
        if not text:
            continue
        blocks.append(SceneBlock(
            id=f"{base_id}-narrator-{idx}",
            block_type="narrator",
            text=text,
            speaker_label="",
            actor_id=None,
            target_actor_id=None,
            delivery=SceneBlockDelivery(),
        ))

    npc_speak = instruction.get("npc_speak")
    if isinstance(npc_speak, dict):
        actor = str(npc_speak.get("actor") or "").strip()
        if actor:
            if "segments" in npc_speak and isinstance(npc_speak["segments"], list):
                for seg_idx, segment in enumerate(npc_speak["segments"]):
                    if not isinstance(segment, dict):
                        continue
                    blocks.append(SceneBlock(
                        id=f"{base_id}-actor-segment-{seg_idx}",
                        block_type="actor_line",
                        text=_render_segment_text(actor, segment),
                        speaker_label=actor,
                        actor_id=actor,
                        target_actor_id=None,
                        delivery=SceneBlockDelivery(),
                    ))
            else:
                blocks.append(SceneBlock(
                    id=f"{base_id}-actor",
                    block_type="actor_line",
                    text=_render_npc_speak_text(actor, npc_speak),
                    speaker_label=actor,
                    actor_id=actor,
                    target_actor_id=None,
                    delivery=SceneBlockDelivery(),
                ))

    state_change = instruction.get("state_change")
    if isinstance(state_change, dict):
        blocks.append(SceneBlock(
            id=f"{base_id}-env",
            block_type="environment_interaction",
            text=_render_state_change_text(state_change),
            speaker_label="",
            actor_id=None,
            target_actor_id=None,
            object_id=_object_id_from_state_key(state_change.get("state_key")),
            affordance_tier="canonical",
            delivery=SceneBlockDelivery(),
        ))

    phone_interruption = instruction.get("phone_interruption")
    if isinstance(phone_interruption, dict):
        blocks.extend(_render_phone_interruption(base_id, phone_interruption))

    return blocks


def _render_npc_speak_text(actor: str, npc_speak: dict[str, Any]) -> str:
    intent = str(npc_speak.get("intent") or "").strip()
    facts = npc_speak.get("required_facts") or []
    minimum_visible = str(npc_speak.get("minimum_visible") or "").strip()
    fact_str = " | ".join(str(f) for f in facts if str(f).strip())
    parts: list[str] = []
    if intent:
        parts.append(f"[{intent}]")
    if minimum_visible:
        parts.append(f"({minimum_visible})")
    if fact_str:
        parts.append(fact_str)
    body = " ".join(parts) if parts else "[speech]"
    return f"{actor}: {body}"


def _render_segment_text(actor: str, segment: dict[str, Any]) -> str:
    segment_id = str(segment.get("segment_id") or "").strip()
    intent = str(segment.get("intent") or "").strip()
    facts = segment.get("required_facts") or []
    fact_str = " | ".join(str(f) for f in facts if str(f).strip())
    return f"{actor}: [{segment_id} / {intent}] {fact_str}".strip()


def _render_state_change_text(state_change: dict[str, Any]) -> str:
    key = str(state_change.get("state_key") or "").strip()
    to_value = state_change.get("to_value")
    rollback = str(state_change.get("rollback_policy") or "never").strip()
    return f"[state_commit {key} -> {to_value!r} ({rollback})]"


def _object_id_from_state_key(state_key: Any) -> str | None:
    if not state_key:
        return None
    key = str(state_key)
    if "." in key:
        return key.split(".", 1)[1]
    return key


def _render_phone_interruption(base_id: str, phone: dict[str, Any]) -> list[SceneBlock]:
    caller_actor = str(phone.get("caller_actor") or "").strip()
    speaker_label = caller_actor or "caller"
    visible_facts = phone.get("caller_visible_facts") or []
    vibrate_text = (
        f"{caller_actor.title()}'s phone vibrates in the inside pocket."
        if caller_actor
        else "A phone vibrates in the inside pocket."
    )
    call_text = (
        f"{speaker_label}: [phone call with {phone.get('call_partner')!r} re "
        f"{phone.get('call_topic')!r}] "
        + " | ".join(str(f) for f in visible_facts)
    )
    return [
        SceneBlock(
            id=f"{base_id}-phone-vibrate",
            block_type="narrator",
            text=vibrate_text,
            speaker_label="",
            actor_id=None,
            target_actor_id=None,
            delivery=SceneBlockDelivery(),
        ),
        SceneBlock(
            id=f"{base_id}-phone-call",
            block_type="actor_line",
            text=call_text,
            speaker_label=speaker_label,
            actor_id=caller_actor or None,
            target_actor_id=None,
            delivery=SceneBlockDelivery(),
        ),
    ]


def _extract_intent_for_initiative(beat: ResolvedBeat) -> dict[str, Any] | None:
    npc_speak = beat.director_instruction.get("npc_speak") if isinstance(beat.director_instruction, dict) else None
    if not isinstance(npc_speak, dict):
        return None
    actor = str(npc_speak.get("actor") or "").strip()
    intent = str(npc_speak.get("intent") or "").strip()
    if not actor:
        return None
    allowed = ["actor_line"]
    if "segments" in npc_speak:
        allowed = ["actor_line"]
    return {
        "actor": actor,
        "intent": intent or "speak",
        "allowed_block_types": allowed,
    }


def _project_state_changes(step: CanonicalStep) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in step.state_changes_committed:
        if not isinstance(entry, dict):
            continue
        records.append({
            "step_id": step.id,
            "key": entry.get("key"),
            "from_value": entry.get("from_value"),
            "to_value": entry.get("to_value"),
            "commit_irreversible": bool(entry.get("commit_irreversible", False)),
        })
    return records
