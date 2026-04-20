from __future__ import annotations

from collections.abc import Callable

from app.content.models import ExperienceKind, ExperienceTemplate
from app.runtime.models import RuntimeEvent, RuntimeInstance

EmitEvent = Callable[[str, str, str | None, str | None, dict], list[RuntimeEvent]]


class RuntimeNpcDirector:
    def __init__(self, template: ExperienceTemplate, emit: EmitEvent) -> None:
        self.template = template
        self.emit = emit

    def run_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        if self.template.kind == ExperienceKind.SOLO_STORY:
            return self._solo_cycle(instance)
        if self.template.kind == ExperienceKind.GROUP_STORY:
            return self._group_cycle(instance)
        if self.template.kind == ExperienceKind.OPEN_WORLD:
            return self._open_world_cycle(instance)
        return []

    def _group_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        if instance.status.value == "lobby":
            return []
        if "house_ai_prompted" in instance.flags:
            return []
        instance.flags.add("house_ai_prompted")
        return self.emit(
            "npc_reacted",
            "House Recorder: All participants are reminded that tone, interruption, and silence are part of the scene contract.",
            "House Recorder",
            "parlor",
            {"npc_role": "house_ai"},
        )

    def _open_world_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        if "patrol_pattern_seen" in instance.flags and "drone_announced" not in instance.flags:
            instance.flags.add("drone_announced")
            return self.emit(
                "npc_reacted",
                "Patrol Drone: Civic reminder. Unregistered loitering near transit assets may trigger secondary review.",
                "Patrol Drone",
                "plaza",
                {"npc_role": "patrol_drone"},
            )
        return []

    def _solo_cycle(self, instance: RuntimeInstance) -> list[RuntimeEvent]:
        events: list[RuntimeEvent] = []
        beat = instance.beat_id
        if beat == "courtesy" and "entered_living_room" in instance.flags and "courtesy_intro_done" not in instance.flags:
            instance.flags.add("courtesy_intro_done")
            events.extend(
                self.emit(
                    "npc_reacted",
                    "Veronique folds her hands. 'Thank you for coming. Let us try to remain clear and decent.'",
                    "Veronique",
                    "living_room",
                    {"npc_role": "host_veronique"},
                )
            )
            events.extend(
                self.emit(
                    "npc_reacted",
                    "Alain glances at his phone instead of your face, already apologizing with only half his attention.",
                    "Alain",
                    "living_room",
                    {"npc_role": "guest_alain"},
                )
            )
        if beat == "first_fracture" and "fracture_exchange_done" not in instance.flags:
            instance.flags.add("fracture_exchange_done")
            text = (
                "Annette presses a hand to her temple. Michel's smile goes tight. The room keeps speaking in"
                " polite sentences while abandoning any polite intention."
            )
            events.extend(self.emit("npc_reacted", text, "Annette", "living_room", {"npc_role": "guest_annette"}))
        if beat == "unmasked" and "unmasked_exchange_done" not in instance.flags:
            instance.flags.add("unmasked_exchange_done")
            text = (
                "Michel pours without asking. Veronique stops editing herself. Alain sounds more like counsel"
                " than husband. Everyone has chosen their weapon."
            )
            events.extend(self.emit("npc_reacted", text, "Michel", "living_room", {"npc_role": "host_michel"}))
        if beat == "collapse" and "collapse_exchange_done" not in instance.flags:
            instance.flags.add("collapse_exchange_done")
            text = "The room loses its last fiction of control. Objects are no longer neutral. Neither is anyone else."
            events.extend(self.emit("npc_reacted", text, "System", "living_room", {"npc_role": "system"}))
        return events
