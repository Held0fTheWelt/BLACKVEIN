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
    # Builtins are fallback/test/demo templates. Published backend content is primary
    # for canonical operations and may override matching template ids at sync time.
    templates = [
        build_god_of_carnage_solo(),
        build_apartment_confrontation_group(),
        build_better_tomorrow_district_open_world(),
    ]
    return {template.id: template for template in templates}


def build_god_of_carnage_solo() -> ExperienceTemplate:
    # Secondary surface; canonical title from content/modules/god_of_carnage/module.yaml (VERTICAL_SLICE_CONTRACT_GOC.md §6.1).
    return ExperienceTemplate(
        id="god_of_carnage_solo",
        title="God of Carnage",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary=(
            "A authored single-adventure slice for a tense apartment confrontation. One human player"
            " enters a controlled dramatic scene that already uses the multiplayer runtime model,"
            " authored beats, props, and operational observability."
        ),
        max_humans=1,
        initial_beat_id="courtesy",
        tags=["authored", "single-adventure", "social-drama", "better-tomorrow"],
        roles=[
            RoleTemplate(
                id="visitor",
                display_name="Visitor",
                description="The human viewpoint role entering the apartment to discuss the violence between two children.",
                mode=ParticipantMode.HUMAN,
                initial_room_id="hallway",
                can_join=True,
            ),
            RoleTemplate(
                id="veronique",
                display_name="Véronique",
                description="Sharp, articulate, morally certain until the room fractures.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="precise, literary, increasingly cutting",
            ),
            RoleTemplate(
                id="michel",
                display_name="Michel",
                description="Affable on the surface, defensive underneath.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="warm, practical, increasingly irritated",
            ),
            RoleTemplate(
                id="annette",
                display_name="Annette",
                description="Trying to remain composed while the room tightens around her.",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
                npc_voice="polite, brittle, quietly overwhelmed",
            ),
            RoleTemplate(
                id="alain",
                display_name="Alain",
                description="Half in the room, half on the phone, professionally detached.",
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
                    "A narrow Parisian hallway with dark hooks, polished wood, and the hush of a meeting"
                    " that was already tense before anyone spoke."
                ),
                exits=[ExitTemplate(direction="inside", target_room_id="living_room", label="Enter the living room")],
                action_ids=["steady_breath", "ring_again", "review_notes"],
                artwork_prompt=(
                    "1980s point-and-click hallway, polished wood floor, apartment coats, anxious warm light,"
                    " cultured domestic tension, pixel art"
                ),
            ),
            RoomTemplate(
                id="living_room",
                name="Living Room",
                description=(
                    "A carefully curated living room of books, tulips, glassware, and educated taste — all of it"
                    " increasingly unable to contain the people arranged around it."
                ),
                exits=[
                    ExitTemplate(direction="back", target_room_id="hallway", label="Step back into the hallway"),
                    ExitTemplate(direction="bathroom", target_room_id="bathroom", label="Withdraw toward the bathroom"),
                ],
                prop_ids=["tulips", "coffee_table", "phone", "art_books", "rum_bottle"],
                action_ids=[
                    "offer_apology",
                    "deflect_blame",
                    "address_group",
                    "sit_down",
                    "ask_to_silence_phone",
                    "pour_rum",
                    "challenge_alain",
                    "comfort_annette",
                ],
                artwork_prompt=(
                    "retro pixel-art paris living room, books, flowers, tasteful furniture, glassware, social"
                    " pressure, 1980s adventure composition"
                ),
            ),
            RoomTemplate(
                id="bathroom",
                name="Bathroom",
                description=(
                    "A smaller, brighter room of tile, mirror, and temporary privacy. It is the only place in the"
                    " apartment that promises retreat, and even that promise feels fragile."
                ),
                exits=[ExitTemplate(direction="living_room", target_room_id="living_room", label="Return to the living room")],
                prop_ids=["washbasin"],
                action_ids=["wash_face", "return_composure"],
                artwork_prompt=(
                    "1980s adventure bathroom, ceramic sink, mirror, pale tile, private but tense, pixel art"
                ),
            ),
        ],
        props=[
            PropTemplate(
                id="tulips",
                name="Tulips",
                description="A bright arrangement that feels more accusatory the longer the meeting lasts.",
                initial_state="intact",
                action_ids=["inspect_tulips", "upset_tulips"],
            ),
            PropTemplate(
                id="coffee_table",
                name="Coffee Table",
                description="Books, glassware, and a curated surface for social performance.",
                initial_state="orderly",
                action_ids=["inspect_table"],
            ),
            PropTemplate(
                id="phone",
                name="Vibrating Phone",
                description="A small machine carrying the authority of the outside world into the room.",
                initial_state="buzzing",
                action_ids=["inspect_phone", "silence_phone"],
            ),
            PropTemplate(
                id="art_books",
                name="Art Books",
                description="Large, serious books positioned as evidence of refinement.",
                initial_state="stacked",
                action_ids=["inspect_books", "straighten_books"],
            ),
            PropTemplate(
                id="rum_bottle",
                name="Rum Bottle",
                description="An instrument of hospitality that can turn into an instrument of escalation.",
                initial_state="sealed",
                action_ids=["inspect_rum", "open_rum"],
            ),
            PropTemplate(
                id="washbasin",
                name="Washbasin",
                description="Cold water, white ceramic, and a mirror that reflects less self-control than expected.",
                initial_state="dry",
                action_ids=["inspect_sink"],
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
                description="Announce your arrival with a touch more insistence.",
                scope="room",
                effects=[
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.TRANSCRIPT, text="The second ring sounds less like etiquette and more like pressure."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="review_notes",
                label="Review your notes",
                description="Mentally rehearse the facts before stepping into the room.",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="prepared_statement"),
                    Effect(type=EffectType.TRANSCRIPT, text="You silently reorder the facts, hoping sequence might still produce sense."),
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
                    Effect(type=EffectType.TRANSCRIPT, text="You stop speaking to individuals and start speaking to the room itself."),
                ],
            ),
            ActionTemplate(
                id="sit_down",
                label="Sit down",
                description="Accept the domestic choreography and take your assigned place in it.",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="seated"),
                    Effect(type=EffectType.TRANSCRIPT, text="The sofa receives you like a witness stand upholstered in etiquette."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="ask_to_silence_phone",
                label="Ask that the phone be silenced",
                description="Try to force the room to remain inside its own conflict.",
                scope="room",
                available_if=[Condition(type=ConditionType.CURRENT_ROOM_EQUALS, value="living_room")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="phone_challenged"),
                    Effect(type=EffectType.ADVANCE_BEAT, value="alliances"),
                    Effect(type=EffectType.TRANSCRIPT, text="You ask for a minimum of respect, and the room immediately begins measuring how much of it remains."),
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
                    Effect(type=EffectType.SET_PROP_STATE, target_id="rum_bottle", value="open"),
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.ADVANCE_BEAT, value="unmasked"),
                    Effect(type=EffectType.TRANSCRIPT, text="Glass touches bottle; the scene decides it no longer wants to behave."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="challenge_alain",
                label="Challenge Alain directly",
                description="Break the room's politeness by forcing the distracted father into the conflict.",
                scope="room",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="alliances")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="alain_challenged"),
                    Effect(type=EffectType.ADD_TENSION, value=2),
                    Effect(type=EffectType.ADVANCE_BEAT, value="unmasked"),
                    Effect(type=EffectType.TRANSCRIPT, text="You stop accepting detachment as neutrality and put Alain squarely back into the room."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="comfort_annette",
                label="Try to comfort Annette",
                description="Offer a brief human gesture in the middle of the conflict.",
                scope="room",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="unmasked")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="annette_comforted"),
                    Effect(type=EffectType.ADD_TENSION, value=-1),
                    Effect(type=EffectType.TRANSCRIPT, text="For one moment the room remembers there are bodies here, not just positions."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_tulips",
                label="Inspect the tulips",
                description="Look for meaning in the room's most decorative hostage.",
                scope="prop",
                target_id="tulips",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The flowers stand too upright, like they were arranged to testify.")],
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
                effects=[Effect(type=EffectType.TRANSCRIPT, text="Books, glass, polish, performance — the table is civilization flattened into objects.")],
            ),
            ActionTemplate(
                id="inspect_phone",
                label="Watch the phone buzz",
                description="Notice how the outside world keeps interrupting the room.",
                scope="prop",
                target_id="phone",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The phone trembles like a trapped insect with better priorities than any of you.")],
            ),
            ActionTemplate(
                id="silence_phone",
                label="Insist the phone be silenced",
                description="Force the room to confront itself without digital escape.",
                scope="prop",
                target_id="phone",
                effects=[
                    Effect(type=EffectType.SET_PROP_STATE, target_id="phone", value="silent"),
                    Effect(type=EffectType.SET_FLAG, key="phone_silenced"),
                    Effect(type=EffectType.ADD_TENSION, value=1),
                    Effect(type=EffectType.TRANSCRIPT, text="For one sharp second, everyone is required to remain here together, with no escape hatch."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_books",
                label="Inspect the art books",
                description="Study the room's curated seriousness.",
                scope="prop",
                target_id="art_books",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The books seem selected to reassure the room that taste can still pass for virtue.")],
            ),
            ActionTemplate(
                id="straighten_books",
                label="Straighten the books",
                description="Restore order to at least one surface in the room.",
                scope="prop",
                target_id="art_books",
                effects=[
                    Effect(type=EffectType.SET_PROP_STATE, target_id="art_books", value="straightened"),
                    Effect(type=EffectType.TRANSCRIPT, text="You align the books as if straight lines could still save anyone here."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_rum",
                label="Inspect the rum bottle",
                description="Consider the room's liquid contingency plan.",
                scope="prop",
                target_id="rum_bottle",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The bottle glows with the practical honesty of escalation." )],
            ),
            ActionTemplate(
                id="open_rum",
                label="Open the rum bottle",
                description="Prepare the room's next phase before anyone admits it wants one.",
                scope="prop",
                target_id="rum_bottle",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="alliances")],
                effects=[
                    Effect(type=EffectType.SET_PROP_STATE, target_id="rum_bottle", value="open"),
                    Effect(type=EffectType.SET_FLAG, key="rum_opened"),
                    Effect(type=EffectType.TRANSCRIPT, text="The seal gives way with the sound of one more restraint being abandoned."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="inspect_sink",
                label="Inspect the washbasin",
                description="Take in the room's promise of private recovery.",
                scope="prop",
                target_id="washbasin",
                effects=[Effect(type=EffectType.TRANSCRIPT, text="The sink offers cold water, reflection, and no actual absolution." )],
            ),
            ActionTemplate(
                id="wash_face",
                label="Wash your face",
                description="Use the bathroom to recover a measure of composure.",
                scope="room",
                available_if=[Condition(type=ConditionType.CURRENT_ROOM_EQUALS, value="bathroom")],
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="face_washed"),
                    Effect(type=EffectType.SET_PROP_STATE, target_id="washbasin", value="running"),
                    Effect(type=EffectType.ADD_TENSION, value=-1),
                    Effect(type=EffectType.TRANSCRIPT, text="Cold water and ceramic edges offer a thinner kind of mercy than words."),
                ],
                single_use=True,
            ),
            ActionTemplate(
                id="return_composure",
                label="Return to the room with composure",
                description="Step back into the scene and force it into its last beat.",
                scope="room",
                available_if=[
                    Condition(type=ConditionType.CURRENT_ROOM_EQUALS, value="bathroom"),
                    Condition(type=ConditionType.FLAG_PRESENT, key="face_washed"),
                ],
                effects=[
                    Effect(type=EffectType.MOVE_ACTOR, value="living_room"),
                    Effect(type=EffectType.ADVANCE_BEAT, value="aftermath"),
                    Effect(type=EffectType.TRANSCRIPT, text="You return cleaner, colder, and no more reconciled than before."),
                ],
                single_use=True,
            ),
        ],
        beats=[
            BeatTemplate(id="courtesy", name="Courtesy", description="Everyone is still trying to sound like good people.", summary="Politeness is the room's first and weakest line of defense."),
            BeatTemplate(id="first_fracture", name="First Fracture", description="The room begins to split into tactics and self-justification.", summary="Civility survives only as performance."),
            BeatTemplate(id="alliances", name="Alliances", description="Subtle pairings and resentments reorganize the room.", summary="The argument becomes positional rather than moral."),
            BeatTemplate(id="unmasked", name="Unmasked", description="Each person drops one layer of self-presentation.", summary="The room now speaks in sharper truths and sharper cruelties."),
            BeatTemplate(id="collapse", name="Collapse", description="Objects and language both become casualties.", summary="The social ritual fails in public."),
            BeatTemplate(id="aftermath", name="Aftermath", description="No one has won; everyone has merely continued.", summary="The scene cools without offering resolution."),
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
