"""DEPRECATED (transitional): In-process experience runtime engine (rooms, actions, snapshots).

Mirrors World Engine mechanics for **unit tests and local experiments** only. The Flask
app does not expose this as public live play; ``game_service`` targets the external
World Engine. See ``docs/technical/architecture/backend-runtime-classification.md``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.content.models import (
    ActionTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    ExperienceKind,
    ExperienceTemplate,
)
from app.runtime.models import CommandResult, ParticipantState, RunStatus, RuntimeEvent, RuntimeInstance, RuntimeSnapshot, TranscriptEntry
from app.runtime.npc_behaviors import RuntimeNpcDirector
from app.runtime.visibility import RuntimeVisibilityPolicy


class RuntimeEngine:
    def __init__(self, template: ExperienceTemplate) -> None:
        self.template = template
        self.rooms = template.room_map()
        self.roles = template.role_map()
        self.props = template.prop_map()
        self.actions = template.action_map()
        self.visibility = RuntimeVisibilityPolicy(template)
        self.npc_director = RuntimeNpcDirector(template, self._emit_npc_event)

    def build_snapshot(self, instance: RuntimeInstance, viewer_participant_id: str) -> RuntimeSnapshot:
        viewer = instance.participants[viewer_participant_id]
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
            viewer_account_id=viewer.account_id,
            viewer_character_id=viewer.character_id,
            viewer_room_id=viewer.current_room_id,
            viewer_role_id=viewer.role_id,
            viewer_display_name=viewer.display_name,
            current_room=self.visibility.build_current_room_payload(instance, viewer),
            visible_occupants=self.visibility.visible_occupants(instance, viewer),
            available_actions=available_actions,
            transcript_tail=self.visibility.visible_transcript(instance, viewer),
            lobby=self.build_lobby_payload(instance),
            metadata={
                **self.visibility.public_metadata(instance),
                "min_humans_to_start": self.template.min_humans_to_start,
                "store_backend": instance.metadata.get("store_backend", "unknown"),
            },
        )

    def build_lobby_payload(self, instance: RuntimeInstance) -> dict[str, Any] | None:
        if self.template.kind != ExperienceKind.GROUP_STORY:
            return None
        seats = []
        for role in self.template.roles:
            if role.mode.value != "human" or not role.can_join:
                continue
            seat = instance.lobby_seats.get(role.id)
            if seat is None:
                continue
            seats.append(
                {
                    "role_id": seat.role_id,
                    "role_display_name": seat.role_display_name,
                    "participant_id": seat.participant_id,
                    "occupant_display_name": seat.occupant_display_name,
                    "reserved_for_account_id": seat.reserved_for_account_id,
                    "reserved_for_display_name": seat.reserved_for_display_name,
                    "connected": seat.connected,
                    "ready": seat.ready,
                    "joined_at": seat.joined_at,
                }
            )
        occupied = [seat for seat in seats if seat["participant_id"]]
        ready = [seat for seat in seats if seat["ready"]]
        can_start = len(occupied) >= self.template.min_humans_to_start and len(occupied) == len(ready)
        return {
            "status": instance.status.value,
            "min_humans_to_start": self.template.min_humans_to_start,
            "occupied_human_seats": len(occupied),
            "ready_human_seats": len(ready),
            "can_start": can_start,
            "seats": seats,
        }

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
        if action == "set_ready":
            return self._set_ready(instance, actor, bool(command.get("ready", True)))
        if action == "start_run":
            return self._start_run(instance, actor)
        return CommandResult(accepted=False, reason=f"Unknown command: {action}")

    def run_npc_cycle(self, instance: RuntimeInstance, trigger_actor_id: str | None = None) -> list[RuntimeEvent]:
        self._npc_instance = instance
        try:
            events = self.npc_director.run_cycle(instance)
        finally:
            self._npc_instance = None
        if events:
            instance.updated_at = datetime.now(timezone.utc)
        return events

    def _move(self, instance: RuntimeInstance, actor: ParticipantState, target_room_id: str) -> CommandResult:
        if self.template.kind == ExperienceKind.GROUP_STORY and instance.status == RunStatus.LOBBY:
            return CommandResult(accepted=False, reason="The group story is still in the lobby phase. Start the run first.")
        room = self.rooms[actor.current_room_id]
        possible = {exit_.target_room_id: exit_ for exit_ in room.exits}
        if target_room_id not in possible:
            return CommandResult(accepted=False, reason="That room is not reachable from here.")
        actor.current_room_id = target_room_id
        if target_room_id == "living_room":
            instance.flags.add("entered_living_room")
        return CommandResult(
            accepted=True,
            events=self._append_event(
                instance,
                event_type="room_changed",
                actor=actor.display_name,
                room_id=target_room_id,
                text=f"{actor.display_name} moves to {self.rooms[target_room_id].name}.",
                payload={"participant_id": actor.id, "target_room_id": target_room_id},
            ),
        )

    def _say(self, instance: RuntimeInstance, actor: ParticipantState, text: str) -> CommandResult:
        if not text:
            return CommandResult(accepted=False, reason="Say what?")
        return CommandResult(
            accepted=True,
            events=self._append_event(
                instance,
                event_type="speech_committed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f'{actor.display_name} says: "{text}"',
                payload={"participant_id": actor.id, "text": text},
            ),
        )

    def _emote(self, instance: RuntimeInstance, actor: ParticipantState, text: str) -> CommandResult:
        if not text:
            return CommandResult(accepted=False, reason="Emote what?")
        return CommandResult(
            accepted=True,
            events=self._append_event(
                instance,
                event_type="emote_committed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"{actor.display_name} {text}",
                payload={"participant_id": actor.id, "text": text},
            ),
        )

    def _inspect(self, instance: RuntimeInstance, actor: ParticipantState, target_id: str) -> CommandResult:
        if not self.visibility.can_inspect_target(instance, actor, target_id):
            return CommandResult(accepted=False, reason="That target is not visible from your current room.")
        if target_id in self.props:
            prop = instance.props[target_id]
            text = f"You inspect {prop.name}: {prop.description} (state: {prop.state})."
            return CommandResult(
                accepted=True,
                events=self._append_event(
                    instance,
                    event_type="inspection_committed",
                    actor=actor.display_name,
                    room_id=actor.current_room_id,
                    text=text,
                    payload={"participant_id": actor.id, "target_id": target_id},
                ),
            )
        if target_id == actor.current_room_id:
            room = self.rooms[target_id]
            text = f"You look over {room.name}: {room.description}"
            return CommandResult(
                accepted=True,
                events=self._append_event(
                    instance,
                    event_type="inspection_committed",
                    actor=actor.display_name,
                    room_id=actor.current_room_id,
                    text=text,
                    payload={"participant_id": actor.id, "target_id": target_id},
                ),
            )
        return CommandResult(accepted=False, reason="Nothing by that id can be inspected.")

    def _use_action(self, instance: RuntimeInstance, actor: ParticipantState, action_id: str) -> CommandResult:
        if self.template.kind == ExperienceKind.GROUP_STORY and instance.status == RunStatus.LOBBY:
            return CommandResult(accepted=False, reason="Scene actions unlock after the host starts the group story.")
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

    def _set_ready(self, instance: RuntimeInstance, actor: ParticipantState, ready: bool) -> CommandResult:
        if self.template.kind != ExperienceKind.GROUP_STORY:
            return CommandResult(accepted=False, reason="Ready state only applies to group story lobbies.")
        seat = instance.lobby_seats.get(actor.role_id)
        if seat is None or seat.participant_id != actor.id:
            return CommandResult(accepted=False, reason="You do not control a lobby seat in this run.")
        seat.ready = ready
        text = f"{actor.display_name} marks {seat.role_display_name} as {'ready' if ready else 'not ready'}."
        return CommandResult(
            accepted=True,
            events=self._append_event(
                instance,
                event_type="lobby_ready_changed",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=text,
                payload={"participant_id": actor.id, "role_id": actor.role_id, "ready": ready},
            ),
        )

    def _start_run(self, instance: RuntimeInstance, actor: ParticipantState) -> CommandResult:
        if self.template.kind != ExperienceKind.GROUP_STORY:
            return CommandResult(accepted=False, reason="Only group stories use an explicit lobby start.")
        if instance.status != RunStatus.LOBBY:
            return CommandResult(accepted=False, reason="This run has already started.")
        if actor.account_id and instance.owner_account_id and actor.account_id != instance.owner_account_id:
            return CommandResult(accepted=False, reason="Only the host can start this run.")
        lobby = self.build_lobby_payload(instance) or {}
        if not lobby.get("can_start"):
            return CommandResult(
                accepted=False,
                reason=(
                    f"Need at least {self.template.min_humans_to_start} occupied ready seats before starting."
                ),
            )
        instance.status = RunStatus.RUNNING
        return CommandResult(
            accepted=True,
            events=self._append_event(
                instance,
                event_type="run_started",
                actor=actor.display_name,
                room_id=actor.current_room_id,
                text=f"{actor.display_name} starts the group story. The lobby dissolves into the scene.",
                payload={"participant_id": actor.id},
            ),
        )

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

    def _emit_npc_event(
        self,
        event_type: str,
        text: str,
        actor: str | None,
        room_id: str | None,
        payload: dict[str, Any],
    ) -> list[RuntimeEvent]:
        return self._append_event(
            self._npc_instance,
            event_type=event_type,
            text=text,
            actor=actor,
            room_id=room_id,
            payload=payload,
        )

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

    @property
    def _npc_instance(self) -> RuntimeInstance:
        instance = getattr(self, "__npc_instance", None)
        if instance is None:
            raise RuntimeError("NPC cycle invoked without active runtime instance binding")
        return instance

    @_npc_instance.setter
    def _npc_instance(self, instance: RuntimeInstance | None) -> None:
        setattr(self, "__npc_instance", instance)
