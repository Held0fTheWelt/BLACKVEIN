"""Canonical actor alias matching for the God of Carnage runtime slice."""

from __future__ import annotations

from story_runtime_core.player_input_intent_contract import normalize_for_intent_matching

GOC_ACTOR_ALIASES: dict[str, tuple[str, ...]] = {
    "annette_reille": ("annette",),
    "alain_reille": ("alain",),
    "michel_longstreet": ("michel", "michael"),
    "veronique_vallon": ("veronique", "véronique", "penelope", "pénélope"),
}


def resolve_goc_actor_alias(text: object) -> str | None:
    normalized = normalize_for_intent_matching(text)
    if not normalized:
        return None
    for actor_id, aliases in GOC_ACTOR_ALIASES.items():
        for alias in aliases:
            needle = normalize_for_intent_matching(alias)
            if needle and needle in normalized:
                return actor_id
    return None
