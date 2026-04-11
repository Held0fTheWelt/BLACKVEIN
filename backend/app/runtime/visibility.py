"""Per-viewer visibility for runtime snapshots (room, occupants, transcript, inspect)."""

from __future__ import annotations

from typing import Any

from app.content.models import ExperienceTemplate


class RuntimeVisibilityPolicy:
    """Default visibility: current room from template map; occupants + transcript not filtered by fog-of-war."""

    def __init__(self, template: ExperienceTemplate) -> None:
        self.template = template

    def build_current_room_payload(self, instance, viewer) -> dict[str, Any]:
        room = self.template.room_map()[viewer.current_room_id]
        return {"id": room.id, "name": room.name}

    def visible_occupants(self, instance, viewer) -> list[dict[str, Any]]:
        return [{"participant_id": viewer.id, "display_name": viewer.display_name}]

    def visible_transcript(self, instance, viewer):
        return instance.transcript[-5:]

    def public_metadata(self, instance) -> dict[str, Any]:
        return {"kind": instance.kind.value}

    def can_inspect_target(self, instance, actor, target_id: str) -> bool:
        return target_id in instance.props or target_id == actor.current_room_id
