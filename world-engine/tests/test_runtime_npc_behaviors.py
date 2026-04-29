"""Tests for builtin templates and RuntimeNpcDirector cycles."""

from __future__ import annotations

from app.content.builtins import (
    build_apartment_confrontation_group,
    build_better_tomorrow_district_open_world,
    build_god_of_carnage_solo,
    load_builtin_templates,
)
from app.runtime.models import RunStatus, RuntimeInstance
from app.runtime.npc_behaviors import RuntimeNpcDirector


class _Emitter:
    def __init__(self):
        self.calls = []

    def __call__(self, event_type, text, actor, room_id, payload):
        self.calls.append(
            {
                "event_type": event_type,
                "text": text,
                "actor": actor,
                "room_id": room_id,
                "payload": payload,
            }
        )
        return [self.calls[-1]]


class TestBuiltinTemplates:
    def test_load_builtin_templates_exposes_expected_template_ids(self):
        templates = load_builtin_templates()

        assert set(templates) == {
            "god_of_carnage_solo",
            "apartment_confrontation_group",
            "better_tomorrow_district_alpha",
        }
        # god_of_carnage_solo is runtime-profile-only (no story truth, beats come from canonical module)
        assert templates["god_of_carnage_solo"].initial_beat_id == ""
        assert templates["apartment_confrontation_group"].max_humans >= 2
        assert templates["better_tomorrow_district_alpha"].persistent is True

    def test_solo_template_has_consistent_cross_references(self):
        template = build_god_of_carnage_solo()
        # god_of_carnage_solo is runtime-profile-only: no story truth (beats/actions/props)
        # Roles and rooms are runtime bootstrap structure, not story truth.
        assert len(template.beats) == 0, "Runtime profile must not contain beats"
        assert len(template.actions) == 0, "Runtime profile must not contain actions"
        assert len(template.props) == 0, "Runtime profile must not contain props"
        # Roles: annette + alain (selectable human) + veronique + michel (NPC) — no visitor
        role_ids = {r.id for r in template.roles}
        assert "annette" in role_ids, "annette must be a selectable player role"
        assert "alain" in role_ids, "alain must be a selectable player role"
        assert "visitor" not in role_ids, "visitor must not exist as a role"
        # Rooms: runtime structure for navigation
        assert len(template.rooms) > 0, "Runtime profile must expose rooms for bootstrap navigation"


class TestRuntimeNpcDirector:
    def test_group_cycle_emits_house_ai_only_once_after_start(self):
        template = build_apartment_confrontation_group()
        emitter = _Emitter()
        director = RuntimeNpcDirector(template, emitter)
        instance = RuntimeInstance(
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            beat_id=template.initial_beat_id,
            status=RunStatus.RUNNING,
        )

        first_events = director.run_cycle(instance)
        second_events = director.run_cycle(instance)

        assert len(first_events) == 1
        assert first_events[0]["actor"] == "House Recorder"
        assert second_events == []
        assert "house_ai_prompted" in instance.flags

    def test_open_world_cycle_requires_patrol_flag_and_runs_once(self):
        template = build_better_tomorrow_district_open_world()
        emitter = _Emitter()
        director = RuntimeNpcDirector(template, emitter)
        instance = RuntimeInstance(
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            beat_id=template.initial_beat_id,
            status=RunStatus.RUNNING,
        )

        assert director.run_cycle(instance) == []
        instance.flags.add("patrol_pattern_seen")
        first_events = director.run_cycle(instance)
        second_events = director.run_cycle(instance)

        assert len(first_events) == 1
        assert first_events[0]["actor"] == "Patrol Drone"
        assert second_events == []
        assert "drone_announced" in instance.flags

    def test_solo_cycle_progresses_each_story_beat_once(self):
        template = build_god_of_carnage_solo()
        emitter = _Emitter()
        director = RuntimeNpcDirector(template, emitter)
        instance = RuntimeInstance(
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            beat_id="courtesy",
            status=RunStatus.RUNNING,
        )
        instance.flags.add("entered_living_room")

        courtesy_events = director.run_cycle(instance)
        repeat_courtesy = director.run_cycle(instance)
        instance.beat_id = "first_fracture"
        fracture_events = director.run_cycle(instance)
        instance.beat_id = "unmasked"
        unmasked_events = director.run_cycle(instance)
        instance.beat_id = "collapse"
        collapse_events = director.run_cycle(instance)

        assert len(courtesy_events) == 2
        assert repeat_courtesy == []
        assert len(fracture_events) == 1
        assert len(unmasked_events) == 1
        assert len(collapse_events) == 1
        assert "courtesy_intro_done" in instance.flags
        assert "fracture_exchange_done" in instance.flags
        assert "unmasked_exchange_done" in instance.flags
        assert "collapse_exchange_done" in instance.flags
