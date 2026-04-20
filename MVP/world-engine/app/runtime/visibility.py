from __future__ import annotations

from typing import Any

from app.content.models import ExperienceTemplate
from app.runtime.models import ParticipantState, RuntimeInstance, TranscriptEntry


class RuntimeVisibilityPolicy:
    def __init__(self, template: ExperienceTemplate) -> None:
        self.template = template
        self.rooms = template.room_map()
        self.props = template.prop_map()

    def build_current_room_payload(self, instance: RuntimeInstance, viewer: ParticipantState) -> dict[str, Any]:
        room = self.rooms[viewer.current_room_id]
        room_props = [self._prop_payload(instance, prop_id) for prop_id in room.prop_ids]
        return {
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "artwork_prompt": room.artwork_prompt,
            "exits": [exit_.model_dump() for exit_ in room.exits],
            "props": room_props,
        }

    def visible_occupants(self, instance: RuntimeInstance, viewer: ParticipantState) -> list[dict[str, Any]]:
        occupants: list[dict[str, Any]] = []
        for participant in instance.participants.values():
            if participant.current_room_id != viewer.current_room_id:
                continue
            occupants.append(
                {
                    "participant_id": participant.id,
                    "display_name": participant.display_name,
                    "role_id": participant.role_id,
                    "mode": participant.mode.value,
                    "connected": participant.connected,
                    "is_self": participant.id == viewer.id,
                }
            )
        return occupants

    def visible_transcript(self, instance: RuntimeInstance, viewer: ParticipantState, tail: int = 30) -> list[TranscriptEntry]:
        visible_entries = [entry for entry in instance.transcript if self._entry_visible_to_viewer(entry, viewer)]
        return visible_entries[-tail:]

    def can_inspect_target(self, instance: RuntimeInstance, viewer: ParticipantState, target_id: str) -> bool:
        if target_id == viewer.current_room_id:
            return True
        room = self.rooms[viewer.current_room_id]
        return target_id in room.prop_ids

    def public_metadata(self, instance: RuntimeInstance) -> dict[str, Any]:
        human_count = len([participant for participant in instance.participants.values() if participant.mode.value == "human"])
        return {
            "persistent": instance.persistent,
            "human_participant_count": human_count,
        }

    def _entry_visible_to_viewer(self, entry: TranscriptEntry, viewer: ParticipantState) -> bool:
        if entry.room_id is None:
            return True
        if entry.room_id == viewer.current_room_id:
            return True
        participant_id = entry.payload.get("participant_id")
        if participant_id == viewer.id:
            return True
        return False

    def _prop_payload(self, instance: RuntimeInstance, prop_id: str) -> dict[str, Any]:
        prop = instance.props[prop_id]
        return {
            "id": prop.id,
            "name": prop.name,
            "description": prop.description,
            "state": prop.state,
            "room_id": prop.room_id,
        }
