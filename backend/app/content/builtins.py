from __future__ import annotations

from app.content.models import (
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


def load_builtin_templates() -> dict[str, ExperienceTemplate]:
    templates = [
        build_god_of_carnage_solo(),
        build_apartment_confrontation_group(),
        build_better_tomorrow_district_open_world(),
    ]
    return {template.id: template for template in templates}


def build_god_of_carnage_solo() -> ExperienceTemplate:
    return ExperienceTemplate(
        id="god_of_carnage_solo",
        title="The Apartment Incident — Solo Study",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary=(
            "A vertical slice for a tense apartment confrontation. One human player enters a"
            " tightly-scriptable social scene that already uses the multiplayer runtime model."
        ),
        max_humans=1,
        initial_beat_id="courtesy",
        tags=["vertical-slice", "social-drama", "world-of-shadows-foundation"],
        roles=[
            RoleTemplate(
                id="visitor",
                display_name="Visitor",
                description="The human viewpoint role entering the apartment to discuss an incident.",
                mode=ParticipantMode.HUMAN,
                initial_room_id="hallway",
                can_join=True,
            ),
            RoleTemplate(
                id="host_veronique",
                display_name="Veronique",
                description="Sharp, controlled, morally certain — until the scene starts to fracture.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="precise, literate, increasingly caustic",
            ),
            RoleTemplate(
                id="host_michel",
                display_name="Michel",
                description="Jovial on the surface, defensive underneath.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="warm, practical, easygoing, then irritated",
            ),
            RoleTemplate(
                id="guest_annette",
                display_name="Annette",
                description="Trying to maintain civility while feeling trapped.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="polite, brittle, quietly overwhelmed",
            ),
            RoleTemplate(
                id="guest_alain",
                display_name="Alain",
                description="Detached, professional, constantly half-elsewhere.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="cool, dismissive, distracted by work",
            ),
        ],
        rooms=[
            RoomTemplate(
                id="hallway",
                name="Apartment Hallway",
                description=(
                    "A narrow Parisian hallway with coats on dark hooks, polished wood, and the"
                    " nervous hush of a meeting that already went wrong before it began."
                ),
                exits=[ExitTemplate(direction="inside", target_room_id="living_room", label="Enter the living room")],
                action_ids=["steady_breath", "ring_again"],
                artwork_prompt=(
                    "1980s adventure game hallway, warm apartment light, polished wooden floor,"
                    " anxious atmosphere, retro pixel-art composition"
                ),
            ),
            RoomTemplate(
                id="living_room",
                name="Living Room",
                description=(
                    "A tasteful living room staged for civilized conversation: art books, tulips,"
                    " expensive furniture, and the unstable tension of four adults trying to sound"
                    " reasonable."
                ),
                exits=[ExitTemplate(direction="back", target_room_id="hallway", label="Step back into the hallway")],
                prop_ids=["tulips", "coffee_table", "phone"],
                action_ids=["offer_apology", "deflect_blame", "address_group", "sit_down", "pour_rum"],
                artwork_prompt=(
                    "retro pixel-art living room inspired by 1980s graphic adventures, cultured"
                    " paris apartment, soft lamps, art books, flowers, high social tension"
                ),
            ),
        ],
        props=[
            PropTemplate(
                id="tulips",
                name="Tulips",
                description="A bright arrangement that feels increasingly accusatory.",
                initial_state="intact",
                action_ids=["inspect_tulips", "upset_tulips"],
            ),
            PropTemplate(
                id="coffee_table",
                name="Coffee Table",
                description="Books, glassware, and a carefully curated surface for social performance.",
                initial_state="orderly",
                action_ids=["inspect_table"],
            ),
            PropTemplate(
                id="phone",
                name="Vibrating Phone",
                description="A symbol of distance, interruption, and corporate indifference.",
                initial_state="buzzing",
                action_ids=["inspect_phone", "silence_phone"],
            ),
        ],
        actions=[
            ActionTemplate(
                id="steady_breath",
                label="Steady yourself",
                description="Pause at the threshold and collect yourself before entering.",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="composed"),
                    Effect(type=EffectType.TRANSCRIPT, text="You take one measured breath before stepping into the performance of civility."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="ring_again",
                label="Ring the bell again",
                description="Announce your arrival with slightly more insistence.",
                scope="room",
                effects=[
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.TRANSCRIPT, text="The second ring echoes as if impatience itself had pressed the buzzer."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="offer_apology",
                label="Offer a careful apology",
                description="Try to lower the temperature with an open conciliatory statement.",
                scope="room",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="courtesy")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="apology_offered"),
                    Effect(type=EffectType.ADVANCE_BEAT, value="first_fracture"),
                    Effect(type=EffectType.TRANSCRIPT, text="You choose the language of restraint, hoping reason still has a chair at the table."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="deflect_blame",
                label="Deflect the blame",
                description="Shift responsibility away from yourself and test the room's patience.",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="blame_deflected"),
                    Effect(type=EffectType.ADD_TENSION, value=2),
                    Effect(type=EffectType.ADVANCE_BEAT, value="first_fracture"),
                    Effect(type=EffectType.TRANSCRIPT, text="Your answer lands with the smoothness of a legal defense and the warmth of polished steel."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="address_group",
                label="Address the entire room",
                description="State your case to everyone, as if authority can still organize the scene.",
                scope="room",
                available_if=[Condition(type=ConditionType.CURRENT_ROOM_EQUALS, value="living_room")],
                effects=[
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.TRANSCRIPT, text="You turn from private discomfort toward public declaration."),
                ],
            ),
            ActionTemplate(
                id="sit_down",
                label="Sit down",
                description="Accept the domestic choreography and take a seat.",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="seated"),
                    Effect(type=EffectType.TRANSCRIPT, text="The sofa receives you like a witness stand upholstered in etiquette."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="pour_rum",
                label="Pour a stronger drink",
                description="Test whether alcohol is courtesy, surrender, or escalation.",
                scope="room",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="first_fracture")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="rum_poured"),
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.ADVANCE_BEAT, value="unmasked"),
                    Effect(type=EffectType.TRANSCRIPT, text="Glass touches bottle; the scene decides it no longer wants to behave."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_tulips",
                label="Inspect the tulips",
                description="Look for meaning in the room's most decorative hostage.",
                scope="prop",
                target_id="tulips",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The flowers stand too upright, like they were arranged to testify." )],
            ),
            ActionTemplate(
                id="upset_tulips",
                label="Brush the tulips aside",
                description="Make the room's decor pay for the room's mood.",
                scope="prop",
                target_id="tulips",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="unmasked")],
                effects=[
                    Effect(type=EffectType.SET_PROP_STATE, target_id="tulips", value="disturbed"),
                    Effect(type=EffectType.ADD_TENSION, value=2),
                    Effect(type=EffectType.ADVANCE_BEAT, value="collapse"),
                    Effect(type=EffectType.TRANSCRIPT, text="The arrangement tips, and decor finally admits what the people refused to."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_table",
                label="Inspect the coffee table",
                description="Study the surface everyone keeps orbiting.",
                scope="prop",
                target_id="coffee_table",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="Books, glass, polish, performance — the table is civilization flattened into objects." )],
            ),
            ActionTemplate(
                id="inspect_phone",
                label="Watch the phone buzz",
                description="Notice how the outside world keeps interrupting the room.",
                scope="prop",
                target_id="phone",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The phone trembles like a trapped insect with better priorities than any of you." )],
            ),
            ActionTemplate(
                id="silence_phone",
                label="Insist that the phone be silenced",
                description="Try to force the room to stay inside its own conflict.",
                scope="prop",
                target_id="phone",
                effects=[
                    Effect(type=EffectType.SET_PROP_STATE, target_id="phone", value="silent"),
                    Effect(type=EffectType.SET_FLAG, key="phone_silenced"),
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.TRANSCRIPT, text="For one sharp second, everyone is required to remain here, together, with no escape hatch."),
                ],
                single_use=True,
            ),
        ],
        beats=[
            BeatTemplate(id="courtesy", name="Courtesy", description="Everyone is still trying to sound like good people.", summary="Politeness holds the frame together."),
            BeatTemplate(id="first_fracture", name="First Fracture", description="The room begins to divide and perform self-justification.", summary="Civility is now a technique, not a feeling."),
            BeatTemplate(id="unmasked", name="Unmasked", description="Everyone drops one layer of self-presentation.", summary="The scene sharpens into accusation and exposure."),
            BeatTemplate(id="collapse", name="Collapse", description="Objects and language both become casualties.", summary="The social ritual fails in public."),
        ],
    )


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
