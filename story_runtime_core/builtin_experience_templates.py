from __future__ import annotations

from .experience_template_models import (
    ActionTemplate,
    BeatTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    ExperienceKind,
    ExperienceTemplate,
    ExitTemplate,
    JoinPolicy,
    ParticipantMode,
    PropTemplate,
    RoleTemplate,
    RoomTemplate,
)

from .goc_solo_builtin_catalog import goc_solo_action_templates, goc_solo_beat_templates, goc_solo_prop_templates
from .goc_solo_builtin_roles_rooms import goc_solo_role_templates, goc_solo_room_templates_with_content
from .goc_solo_builtin_template import build_god_of_carnage_solo


def build_god_of_carnage_content_template() -> ExperienceTemplate:
    """Full content template for god_of_carnage with all props, actions, beats, and rooms."""
    return ExperienceTemplate(
        id="god_of_carnage",
        title="God of Carnage",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary=(
            "A tense apartment confrontation between two couples. One human player navigates"
            " a dramatic social conflict with fully authored props, actions, and beats."
        ),
        max_humans=1,
        initial_beat_id="courtesy",
        tags=["authored", "single-adventure", "social-drama", "better-tomorrow"],
        roles=goc_solo_role_templates(),
        rooms=goc_solo_room_templates_with_content(),
        props=goc_solo_prop_templates(),
        actions=goc_solo_action_templates(),
        beats=goc_solo_beat_templates(),
    )


def load_builtin_templates() -> dict[str, ExperienceTemplate]:
    # Backend builtins seed and validate authored template shapes. They are not the
    # primary runtime content authority; published backend feed remains canonical.
    templates = [
        build_god_of_carnage_solo(),
        build_apartment_confrontation_group(),
        build_better_tomorrow_district_open_world(),
    ]
    return {template.id: template for template in templates}




def build_apartment_confrontation_group() -> ExperienceTemplate:
    return ExperienceTemplate(
        id="apartment_confrontation_group",
        title="Apartment Incident — Group Story",
        kind=ExperienceKind.GROUP_STORY,
        join_policy=JoinPolicy.INVITED_PARTY,
        summary="A pre-authored group scenario for 2-4 players sharing a tightly framed dramatic scene.",
        max_humans=4,
        min_humans_to_start=2,
        initial_beat_id="briefing",
        tags=["group-story", "party-instance", "social-conflict"],
        roles=[
            RoleTemplate(id="mediator", display_name="Mediator", description="Tries to keep the meeting on track.", mode=ParticipantMode.HUMAN, initial_room_id="foyer", can_join=True),
            RoleTemplate(id="parent_a", display_name="Parent A", description="Wants recognition more than peace.", mode=ParticipantMode.HUMAN, initial_room_id="parlor", can_join=True),
            RoleTemplate(id="parent_b", display_name="Parent B", description="Hides discomfort behind professionalism.", mode=ParticipantMode.HUMAN, initial_room_id="parlor", can_join=True),
            RoleTemplate(id="observer", display_name="Observer", description="A quiet witness who can destabilize the room with a single comment.", mode=ParticipantMode.HUMAN, initial_room_id="foyer", can_join=True),
            RoleTemplate(id="house_ai", display_name="House Recorder", description="A system layer standing in for moderation and stage direction.", mode=ParticipantMode.NPC, initial_room_id="parlor", npc_voice="stage directions, measured prompts"),
        ],
        rooms=[
            RoomTemplate(
                id="foyer",
                name="Foyer",
                description="A transitional space with too many expectations and nowhere to hide.",
                exits=[ExitTemplate(direction="parlor", target_room_id="parlor", label="Enter the parlor")],
                action_ids=["group_ready_check"],
                artwork_prompt="retro adventure foyer, muted wallpaper, cramped staging, social pressure",
            ),
            RoomTemplate(
                id="parlor",
                name="Parlor",
                description="A controlled domestic arena designed to host conversation and expose character.",
                exits=[ExitTemplate(direction="foyer", target_room_id="foyer", label="Step back to the foyer")],
                prop_ids=["minibar", "case_file"],
                action_ids=["group_open_statement", "group_call_break"],
                artwork_prompt="1980s point-and-click parlor, rich colors, chairs facing each other, social standoff",
            ),
        ],
        props=[
            PropTemplate(id="minibar", name="Mini Bar", description="Liquid diplomacy waiting to fail.", initial_state="closed", action_ids=["open_minibar"]),
            PropTemplate(id="case_file", name="Case File", description="A folder with facts, versions, and omissions.", initial_state="sealed", action_ids=["open_case_file"]),
        ],
        actions=[
            ActionTemplate(id="group_ready_check", label="Signal ready", description="Mark yourself ready to begin.", scope="room", effects=[Effect(type=EffectType.SET_FLAG, key="ready_ping"), Effect(type=EffectType.TRANSCRIPT, text="A participant signals readiness; the room pretends preparation means control.")]),
            ActionTemplate(id="group_open_statement", label="Open the discussion", description="Start the formal exchange.", scope="room", effects=[Effect(type=EffectType.ADVANCE_BEAT, value="debate"), Effect(type=EffectType.TRANSCRIPT, text="The discussion begins with an agreed fiction: that it will remain orderly.")]),
            ActionTemplate(id="group_call_break", label="Call for a break", description="Temporarily stop the pressure from rising.", scope="room", available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="debate")], effects=[Effect(type=EffectType.SET_FLAG, key="break_called"), Effect(type=EffectType.ADD_TENSION, value=-1), Effect(type=EffectType.TRANSCRIPT, text="A pause is proposed, though nobody truly leaves the argument behind.")]),
            ActionTemplate(id="open_minibar", label="Open the mini bar", description="Offer drinks and risk changing the tone.", scope="prop", target_id="minibar", effects=[Effect(type=EffectType.SET_PROP_STATE, target_id="minibar", value="open"), Effect(type=EffectType.ADD_TENSION, value=1), Effect(type=EffectType.TRANSCRIPT, text="Glasses appear. Hospitality and strategy become difficult to separate.")]),
            ActionTemplate(id="open_case_file", label="Open the case file", description="Bring the record into the room.", scope="prop", target_id="case_file", effects=[Effect(type=EffectType.SET_PROP_STATE, target_id="case_file", value="open"), Effect(type=EffectType.ADVANCE_BEAT, value="exposure"), Effect(type=EffectType.TRANSCRIPT, text="Once the file opens, memory loses the comfort of vagueness.")]),
        ],
        beats=[
            BeatTemplate(id="briefing", name="Briefing", description="Players gather and orient themselves.", summary="The scenario is still preparatory."),
            BeatTemplate(id="debate", name="Debate", description="The room turns interactive and unstable.", summary="Social control is actively contested."),
            BeatTemplate(id="exposure", name="Exposure", description="Records, props, and roles are weaponized.", summary="The room now reveals rather than contains."),
        ],
    )


def build_better_tomorrow_district_open_world() -> ExperienceTemplate:
    return ExperienceTemplate(
        id="better_tomorrow_district_alpha",
        title="Better Tomorrow District Alpha",
        kind=ExperienceKind.OPEN_WORLD,
        join_policy=JoinPolicy.PUBLIC,
        summary="A tiny persistent public shard proving the architecture can host an open multiplayer layer.",
        max_humans=24,
        persistent=True,
        initial_beat_id="streetlife",
        tags=["open-world", "better-tomorrow", "public-shard"],
        roles=[
            RoleTemplate(id="citizen", display_name="Citizen", description="A player entering the district.", mode=ParticipantMode.HUMAN, initial_room_id="plaza", can_join=True),
            RoleTemplate(id="vendor_ai", display_name="Vendor AI", description="A kiosk intelligence selling certainty and noodles.", mode=ParticipantMode.NPC, initial_room_id="noodle_bar", npc_voice="friendly corporate sales patter"),
            RoleTemplate(id="patrol_drone", display_name="Patrol Drone", description="A persistent public-order presence.", mode=ParticipantMode.NPC, initial_room_id="plaza", npc_voice="procedural authority, crisp and polite"),
        ],
        rooms=[
            RoomTemplate(
                id="plaza",
                name="Transit Plaza",
                description="Neon reflections, commuter flow, surveillance halos, and civic advertising promising a better tomorrow.",
                exits=[
                    ExitTemplate(direction="bar", target_room_id="noodle_bar", label="Enter the noodle bar"),
                    ExitTemplate(direction="alley", target_room_id="service_alley", label="Slip into the service alley"),
                ],
                prop_ids=["billboard", "turnstile"],
                action_ids=["observe_crowd", "check_patrol_route"],
                artwork_prompt="retro cyberpunk pixel-art plaza, giant slogan screens, wet pavement, surveillance lights",
            ),
            RoomTemplate(
                id="noodle_bar",
                name="Noodle Bar",
                description="Steam, cheap food, coded whispers, and a counter that knows more than it says.",
                exits=[ExitTemplate(direction="plaza", target_room_id="plaza", label="Return to the plaza")],
                prop_ids=["counter_terminal"],
                action_ids=["order_noodles", "ask_for_rumor"],
                artwork_prompt="1980s inspired cyberpunk noodle bar, warm steam, pixel lighting, grounded details",
            ),
            RoomTemplate(
                id="service_alley",
                name="Service Alley",
                description="Power conduits, maintenance hatches, and the feeling that the city has a backstage full of secrets.",
                exits=[ExitTemplate(direction="plaza", target_room_id="plaza", label="Return to the plaza")],
                prop_ids=["maintenance_panel"],
                action_ids=["inspect_graffiti"],
                artwork_prompt="retro pixel-art service alley, industrial conduits, warning lights, urban decay",
            ),
        ],
        props=[
            PropTemplate(id="billboard", name="Corporate Billboard", description="A giant Better Tomorrow slogan fused into the architecture.", initial_state="active", action_ids=["inspect_billboard"]),
            PropTemplate(id="turnstile", name="Transit Turnstile", description="A controlled seam between public flow and controlled access.", initial_state="idle", action_ids=["inspect_turnstile"]),
            PropTemplate(id="counter_terminal", name="Counter Terminal", description="A small terminal for ordering food and seeing who is watching.", initial_state="active", action_ids=["inspect_terminal"]),
            PropTemplate(id="maintenance_panel", name="Maintenance Panel", description="A locked panel with promises of utility and trespass.", initial_state="locked", action_ids=["inspect_panel"]),
        ],
        actions=[
            ActionTemplate(id="observe_crowd", label="Observe the crowd", description="Take in the district mood.", scope="room", effects=[Effect(type=EffectType.TRANSCRIPT, text="Commuters flow like data packets under indifferent light." )]),
            ActionTemplate(id="check_patrol_route", label="Check the patrol route", description="Watch the drone and learn its rhythm.", scope="room", effects=[Effect(type=EffectType.SET_FLAG, key="patrol_pattern_seen"), Effect(type=EffectType.TRANSCRIPT, text="The drone repeats its loop with the confidence of a system that expects obedience." )]),
            ActionTemplate(id="order_noodles", label="Order noodles", description="Buy a quiet minute and a bowl of fuel.", scope="room", effects=[Effect(type=EffectType.TRANSCRIPT, text="The bowl arrives hot, cheap, and strangely comforting beneath the district's neon theology." )]),
            ActionTemplate(id="ask_for_rumor", label="Ask for a rumor", description="Probe the bar for something useful.", scope="room", effects=[Effect(type=EffectType.TRANSCRIPT, text="Somebody murmurs about a maintenance route that stays unmonitored for exactly ninety seconds." )]),
            ActionTemplate(id="inspect_graffiti", label="Inspect the graffiti", description="Read what the walls are brave enough to say.", scope="room", effects=[Effect(type=EffectType.TRANSCRIPT, text="Under the grime: BETTER TOMORROW, scratched into BETTER FOR WHOM?" )]),
            ActionTemplate(id="inspect_billboard", label="Inspect the billboard", description="Study the district's central promise.", scope="prop", target_id="billboard", effects=[Effect(type=EffectType.TRANSCRIPT, text="The slogan smiles down with the confidence of a company that can afford history." )]),
            ActionTemplate(id="inspect_turnstile", label="Inspect the turnstile", description="Look at the city's gating logic.", scope="prop", target_id="turnstile", effects=[Effect(type=EffectType.TRANSCRIPT, text="Every bar and light on the turnstile says movement is a privilege, not a default." )]),
            ActionTemplate(id="inspect_terminal", label="Inspect the terminal", description="Study the ordering console.", scope="prop", target_id="counter_terminal", effects=[Effect(type=EffectType.TRANSCRIPT, text="Menus, loyalty prompts, and a silent request for biometrics crowd the little screen." )]),
            ActionTemplate(id="inspect_panel", label="Inspect the maintenance panel", description="See how difficult trespass would be.", scope="prop", target_id="maintenance_panel", effects=[Effect(type=EffectType.TRANSCRIPT, text="The panel looks old enough to fail and new enough to report you when it does." )]),
        ],
        beats=[
            BeatTemplate(id="streetlife", name="Streetlife", description="Normal open-world social flow.", summary="The shard is persistent and publicly joinable."),
        ],
    )
