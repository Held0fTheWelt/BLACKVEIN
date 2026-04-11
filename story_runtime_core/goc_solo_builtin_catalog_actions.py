"""GoC solo action templates by thematic cluster (DS-036)."""

from __future__ import annotations

from .experience_template_models import (
    ActionTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
)

def _goc_action_templates_threshold() -> list[ActionTemplate]:
    return [
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
    ]


def _goc_action_templates_room_discourse() -> list[ActionTemplate]:
    return [
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
    ]


def _goc_action_templates_escalation() -> list[ActionTemplate]:
    return [
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
    ]


def _goc_action_templates_props() -> list[ActionTemplate]:
    return [
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
    ]


def _goc_action_templates_bathroom_aftermath() -> list[ActionTemplate]:
    return [
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
    ]

def build_goc_solo_action_templates() -> list[ActionTemplate]:
    return (
        _goc_action_templates_threshold()
        + _goc_action_templates_room_discourse()
        + _goc_action_templates_escalation()
        + _goc_action_templates_props()
        + _goc_action_templates_bathroom_aftermath()
    )
