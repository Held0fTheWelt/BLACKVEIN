from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.content.models import (
    ActionTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    ExperienceTemplate,
    ParticipantMode,
)
from app.runtime.models import CommandResult, ParticipantState, RuntimeEvent, RuntimeInstance, RuntimeSnapshot, TranscriptEntry


class RuntimeEngine:
    def __init__(self, template: ExperienceTemplate) -> None:
        self.template = template
        self.rooms = template.room_map()
        self.roles = template.role_map()
        self.props = template.prop_map()
        self.actions = template.action_map()

    def build_snapshot(self, instance: RuntimeInstance, viewer_participant_id: str) -> RuntimeSnapshot:
        viewer = instance.participants[viewer_participant_id]
        room_occupants: dict[str, list[dict[str, Any]]] = {room.id: [] for room in self.template.rooms}
        for participant in instance.participants.values():
            room_occupants.setdefault(participant.current_room_id, []).append(
                {
                    "participant_id": participant.id,
                    "display_name": participant.display_name,
                    "role_id": participant.role_id,
                    "mode": participant.mode.value,
                    "connected": participant.connected,
                }
            )

        rooms_payload: list[dict[str, Any]] = []
        for room in self.template.rooms:
            room_props = [self._prop_payload(instance, prop_id) for prop_id in room.prop_ids]
            rooms_payload.append(
                {
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "artwork_prompt": room.artwork_prompt,
                    "exits": [exit_.model_dump() for exit_ in room.exits],
                    "props": room_props,
                }
            )

        available_actions = self.available_actions(instance, viewer)
        return RuntimeSnapshot(
            run_id=instance.id,
            template_id=self.template.id,
            template_title=self.template.title,
            kind=self.template.kind,
            join_policy=self.template.join_policy,
            status=instance.status,
            beat_id=instance.beat_id,
            tension=instance.tension,
            flags=sorted(instance.flags),
            viewer_participant_id=viewer.id,
            viewer_room_id=viewer.current_room_id,
            viewer_role_id=viewer.role_id,
            viewer_display_name=viewer.display_name,
            rooms=rooms_payload,
            room_occupants=room_occupants,
            available_actions=available_actions,
            transcript_tail=instance.transcript[-30:],
            metadata=instance.metadata,
        )

    def available_actions(self, instance: RuntimeInstance, viewer: ParticipantState) -> list[dict[str, Any]]:
        room = self.rooms[viewer.current_room_id]
        actions: list[dict[str, Any]] = []
        room_action_ids = [*room.action_ids]
        for prop_id in room.prop_ids:
            room_action_ids.extend(self.props[prop_id].action_ids)

        for action_id in room_action_ids:
            action = self.actions[action_id]
            if self._is_action_available(action, instance, viewer):
                actions.append(
                    {
                        "id": action.id,
                        "label": action.label,
                        "description": action.description,
                        "scope": action.scope,
                        "target_id": action.target_id,
                    }
                )
        return actions

    def apply_command(self, instance: RuntimeInstance, actor_id: str, command: dict[str, Any]) -> CommandResult:
        actor = instance.participants[actor_id]
        action = command.get("action")
        if action == "move":
            return self._move(instance, actor, str(command.get("target_room_id")))
        if action == "say":
            return self._say(instance, actor, str(command.get("text", "")).strip())
        if action == "emote":
            return self._emote(instance, actor, str(command.get("text", "")).strip())
        if action == "inspect":
            return self._inspect(instance, actor, str(command.get("target_id", "")).strip())
        if action == "use_action":
            return self._use_action(instance, actor, str(command.get("action_id", "")).strip())
        return CommandResult(accepted=False, reason=f"Unknown command: {action}")

    def run_npc_cycle(self, instance: RuntimeInstance, trigger_actor_id: str | None = None) -> list[RuntimeEvent]:
        events: list[RuntimeEvent] = []
        if self.template.kind.value == "solo_story":
            events.extend(self._solo_npc_cycle(instance))
        elif self.template.kind.value == "open_world":
            events.extend(self._open_world_npc_cycle(instance))
        elif self.template.kind.value == "group_story":
            events.extend(self._group_npc_cycle(instance))
        if events:
            instance.updated_at = datetime.now(timezone.utc)
        return events

    def _group_npc_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        if "house_ai_prompted" in instance.flags:
            return []
        instance.flags.add("house_ai_prompted")
        return self._append_event(
            instance,
            event_type="npc_reacted",
            text="House Recorder: All participants are reminded that tone, interruption, and silence are part of the scene contract.",
            actor="House Recorder",
            room_id="parlor",
            payload={"npc_role": "house_ai"},
        )

    def _open_world_npc_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        if "patrol_pattern_seen" in instance.flags and "drone_announced" not in instance.flags:
            instance.flags.add("drone_announced")
            return self._append_event(
                instance,
                event_type="npc_reacted",
                text="Patrol Drone: Civic reminder. Unregistered loitering near transit assets may trigger secondary review.",
                actor="Patrol Drone",
                room_id="plaza",
                payload={"npc_role": "patrol_drone"},
            )
        return []

    def _solo_npc_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        events: list[RuntimeEvent] = []
        beat = instance.beat_id
        if beat == "courtesy" and "entered_living_room" in instance.flags and "courtesy_intro_done" not in instance.flags:
            instance.flags.add("courtesy_intro_done")
            events.extend(
                self._append_event(
                    instance,
                    event_type="npc_reacted",
                    actor="Veronique",
                    room_id="living_room",
                    text="Veronique folds her hands. 'Thank you for coming. Let us try to remain clear and decent.'",
                    payload={"npc_role": "host_veronique"},
                )
            )
            events.extend(
                self._append_event(
                    instance,
                    event_type="npc_reacted",
                    actor="Alain",
                    room_id="living_room",
                    text="Alain glances at his phone instead of your face, already apologizing with only half his attention.",
                    payload={"npc_role": "guest_alain"},
                )
            )
        if beat == "first_fracture" and "fracture_exchange_done" not in instance.flags:
            instance.flags.add("fracture_exchange_done")
            text = (
                "Annette presses a hand to her temple. Michel's smile goes tight. The room keeps speaking in"
                " polite sentences while abandoning any polite intention."
            )
            events.extend(self._append_event(instance, event_type="npc_reacted", actor="Annette", room_id="living_room", text=text, payload={"npc_role": "guest_annette"}))
        if beat == "unmasked" and "unmasked_exchange_done" not in instance.flags:
            instance.flags.add("unmasked_exchange_done")
            text = (
                "Michel pours without asking. Veronique stops editing herself. Alain sounds more like counsel"
                " than husband. Everyone has chosen their weapon."
            )
            events.extend(self._append_event(instance, event_type="npc_reacted", actor="Michel", room_id="living_room", text=text, payload={"npc_role": "host_michel"}))
        if beat == "collapse" and "collapse_exchange_done" not in instance.flags:
            instance.flags.add("collapse_exchange_done")
            text = (
                "The room loses its last fiction of control. Objects are no longer neutral. Neither is anyone else."
            )
            events.extend(self._append_event(instance, event_type="npc_reacted", actor="System", room_id="living_room", text=text, payload={"npc_role": "system"}))
        return events

    def _move(self, instance: RuntimeInstance, actor: ParticipantState, target_room_id: str) -> CommandResult:
        room = self.rooms[actor.current_room_id]
        possible = {exit_.target_room_id: exit_ for exit_ in room.exits}
        if target_room_id not in possible:
            return CommandResult(accepted=False, reason="That room is not reachable from here.")
        actor.current_room_id = target_room_id
        if target_room_id == "living_room":
            instance.flags.add("entered_living_room")
        return CommandResult(accepted=True, events=self._append_event(
            instance,
            event_type="room_changed",
            actor=actor.display_name,
            room_id=target_room_id,
            text=f"{actor.display_name} moves to {self.rooms[target_room_id].name}.",
            payload={"participant_id": actor.id, "target_room_id": target_room_id},
        ))

    def _say(self, instance: RuntimeInstance, actor: ParticipantState, text: str) -> CommandResult:
        if not text:
            return CommandResult(accepted=False, reason="Say what?")
        return CommandResult(accepted=True, events=self._append_event(
            instance,
            event_type="speech_committed",
            actor=actor.display_name,
            room_id=actor.current_room_id,
            text=f'{actor.display_name} says: "{text}"',
            payload={"participant_id": actor.id, "text": text},
        ))

    def _emote(self, instance: RuntimeInstance, actor: ParticipantState, text: str) -> CommandResult:
        if not text:
            return CommandResult(accepted=False, reason="Emote what?")
        return CommandResult(accepted=True, events=self._append_event(
            instance,
            event_type="emote_committed",
            actor=actor.display_name,
            room_id=actor.current_room_id,
            text=f"{actor.display_name} {text}",
            payload={"participant_id": actor.id, "text": text},
        ))

    def _inspect(self, instance: RuntimeInstance, actor: ParticipantState, target_id: str) -> CommandResult:
        if target_id in self.props:
            prop = instance.props[target_id]
            text = f"You inspect {prop.name}: {prop.description} (state: {prop.state})."
            return CommandResult(accepted=True, events=self._append_event(
                instance,
                event_type="inspection_committed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=text,
                payload={"participant_id": actor.id, "target_id": target_id},
            ))
        if target_id in self.rooms:
            room = self.rooms[target_id]
            text = f"You look over {room.name}: {room.description}"
            return CommandResult(accepted=True, events=self._append_event(
                instance,
                event_type="inspection_committed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=text,
                payload={"participant_id": actor.id, "target_id": target_id},
            ))
        return CommandResult(accepted=False, reason="Nothing by that id can be inspected.")

    def _use_action(self, instance: RuntimeInstance, actor: ParticipantState, action_id: str) -> CommandResult:
        action = self.actions.get(action_id)
        if not action:
            return CommandResult(accepted=False, reason="Unknown action.")
        if not self._is_action_available(action, instance, actor):
            return CommandResult(accepted=False, reason="That action is not currently available.")
        events: list[RuntimeEvent] = []
        for effect in action.effects:
            events.extend(self._apply_effect(instance, actor, action, effect))
        if action.single_use:
            instance.flags.add(f"used:{action.id}")
        return CommandResult(accepted=True, events=events)

    def _apply_effect(self, instance: RuntimeInstance, actor: ParticipantState, action: ActionTemplate, effect: Effect) -> list[RuntimeEvent]:
        if effect.type == EffectType.SET_FLAG and effect.key:
            instance.flags.add(effect.key)
            return []
        if effect.type == EffectType.CLEAR_FLAG and effect.key:
            instance.flags.discard(effect.key)
            return []
        if effect.type == EffectType.SET_PROP_STATE and effect.target_id and effect.value is not None:
            instance.props[effect.target_id].state = str(effect.value)
            return self._append_event(
                instance,
                event_type="prop_state_changed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"{instance.props[effect.target_id].name} is now {effect.value}.",
                payload={"participant_id": actor.id, "prop_id": effect.target_id, "state": effect.value},
            )
        if effect.type == EffectType.ADVANCE_BEAT and effect.value is not None:
            instance.beat_id = str(effect.value)
            return self._append_event(
                instance,
                event_type="beat_transitioned",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"The scene shifts into beat: {instance.beat_id}.",
                payload={"participant_id": actor.id, "beat_id": instance.beat_id},
            )
        if effect.type == EffectType.ADD_TENSION and effect.value is not None:
            delta = int(effect.value)
            instance.tension = max(0, instance.tension + delta)
            return self._append_event(
                instance,
                event_type="tension_changed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"Tension changes by {delta}. Current tension: {instance.tension}.",
                payload={"participant_id": actor.id, "delta": delta, "tension": instance.tension},
            )
        if effect.type == EffectType.MOVE_ACTOR and effect.value is not None:
            actor.current_room_id = str(effect.value)
            return self._append_event(
                instance,
                event_type="room_changed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"{actor.display_name} moves to {self.rooms[actor.current_room_id].name}.",
                payload={"participant_id": actor.id, "target_room_id": actor.current_room_id},
            )
        if effect.type == EffectType.TRANSCRIPT and effect.text:
            return self._append_event(
                instance,
                event_type="scripted_note",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=effect.text,
                payload={"participant_id": actor.id, "action_id": action.id},
            )
        return []

    def _is_action_available(self, action: ActionTemplate, instance: RuntimeInstance, actor: ParticipantState) -> bool:
        if action.single_use and f"used:{action.id}" in instance.flags:
            return False
        if action.scope == "prop":
            target_prop_id = action.target_id
            if not target_prop_id or instance.props[target_prop_id].room_id != actor.current_room_id:
                return False
        for condition in action.available_if:
            if not self._condition_matches(condition, instance, actor):
                return False
        return True

    def _condition_matches(self, condition: Condition, instance: RuntimeInstance, actor: ParticipantState) -> bool:
        if condition.type == ConditionType.FLAG_PRESENT and condition.key:
            return condition.key in instance.flags
        if condition.type == ConditionType.FLAG_ABSENT and condition.key:
            return condition.key not in instance.flags
        if condition.type == ConditionType.PROP_STATE_EQUALS and condition.key and condition.value:
            return instance.props[condition.key].state == condition.value
        if condition.type == ConditionType.BEAT_EQUALS and condition.value:
            return instance.beat_id == condition.value
        if condition.type == ConditionType.ACTOR_ROLE_EQUALS and condition.value:
            return actor.role_id == condition.value
        if condition.type == ConditionType.CURRENT_ROOM_EQUALS and condition.value:
            return actor.current_room_id == condition.value
        return True

    def _prop_payload(self, instance: RuntimeInstance, prop_id: str) -> dict[str, Any]:
        prop = instance.props[prop_id]
        return {
            "id": prop.id,
            "name": prop.name,
            "description": prop.description,
            "state": prop.state,
            "room_id": prop.room_id,
        }

    def _append_event(
        self,
        instance: RuntimeInstance,
        event_type: str,
        text: str,
        actor: str | None,
        room_id: str | None,
        payload: dict[str, Any],
    ) -> list[RuntimeEvent]:
        event = RuntimeEvent(type=event_type, run_id=instance.id, payload=payload)
        transcript = TranscriptEntry(kind=event_type, actor=actor, room_id=room_id, text=text, payload=payload)
        instance.event_log.append(event)
        instance.transcript.append(transcript)
        instance.updated_at = datetime.now(timezone.utc)
        return [event]
