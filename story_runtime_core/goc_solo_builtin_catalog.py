"""Prop, action, and beat catalogs for god_of_carnage_solo (SSOT fragments)."""

from __future__ import annotations

from .experience_template_models import ActionTemplate, BeatTemplate, PropTemplate


def goc_solo_prop_templates() -> list[PropTemplate]:
    return [
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
    ]


def goc_solo_action_templates() -> list[ActionTemplate]:
    from .goc_solo_builtin_catalog_actions import build_goc_solo_action_templates

    return build_goc_solo_action_templates()


def goc_solo_beat_templates() -> list[BeatTemplate]:
    return [
            BeatTemplate(id="courtesy", name="Courtesy", description="Everyone is still trying to sound like good people.", summary="Politeness is the room's first and weakest line of defense."),
            BeatTemplate(id="first_fracture", name="First Fracture", description="The room begins to split into tactics and self-justification.", summary="Civility survives only as performance."),
            BeatTemplate(id="alliances", name="Alliances", description="Subtle pairings and resentments reorganize the room.", summary="The argument becomes positional rather than moral."),
            BeatTemplate(id="unmasked", name="Unmasked", description="Each person drops one layer of self-presentation.", summary="The room now speaks in sharper truths and sharper cruelties."),
            BeatTemplate(id="collapse", name="Collapse", description="Objects and language both become casualties.", summary="The social ritual fails in public."),
            BeatTemplate(id="aftermath", name="Aftermath", description="No one has won; everyone has merely continued.", summary="The scene cools without offering resolution."),
    ]

