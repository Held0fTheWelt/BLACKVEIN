"""GoC solo template — Rollen und Räume (DS-012 Fragment)."""

from __future__ import annotations

from .experience_template_models import (
    ExitTemplate,
    ParticipantMode,
    RoleTemplate,
    RoomTemplate,
)


def goc_solo_role_templates() -> list[RoleTemplate]:
    # MVP1: visitor removed from live solo path (GLOBAL PROHIBITION).
    # annette and alain are selectable human roles; the player chooses one via
    # selected_player_role at create_run time (preferred_role_id in _bootstrap_instance).
    # The unselected role's lobby seat remains open; the story runtime treats
    # all non-human-occupied canonical characters as NPC dramatic actors.
    return [
        RoleTemplate(
            id="annette",
            display_name="Annette",
            description="Trying to remain composed while the room tightens around her.",
            mode=ParticipantMode.HUMAN,
            initial_room_id="hallway",
            can_join=True,
            npc_voice="polite, brittle, quietly overwhelmed",
        ),
        RoleTemplate(
            id="alain",
            display_name="Alain",
            description="Half in the room, half on the phone, professionally detached.",
            mode=ParticipantMode.HUMAN,
            initial_room_id="hallway",
            can_join=True,
            npc_voice="cool, dismissive, distracted by work",
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
    ]


def goc_solo_room_templates() -> list[RoomTemplate]:
    return [
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
    ]
