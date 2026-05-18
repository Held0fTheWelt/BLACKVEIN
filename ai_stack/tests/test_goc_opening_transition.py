from __future__ import annotations

from ai_stack.goc_opening_transition import (
    deterministic_part1_premise,
    enforce_opening_transition_on_beats,
    generic_conflict_resolution_detected,
    opening_part_1_premise_present,
    opening_part_2_room_present,
    prosecutorial_opening_detected,
    schoolyard_incident_present,
)


def test_enforce_transition_fills_weak_premise():
    beats, meta = enforce_opening_transition_on_beats(
        ["The room is quiet.", "Paris apartment with tulips and espresso.", "You are Annette Reille, arriving as a guest beside Alain — not a spectator."],
        output_language="en",
        human_actor_id="annette_reille",
        selected_player_role="annette",
    )
    assert meta.get("opening_transition_applied") is True
    assert meta.get("opening_transition_backfill_enabled") is False
    assert "part_1_premise_weak" in meta.get("opening_transition_swap_reasons", [])
    assert not schoolyard_incident_present(beats[0])
    assert opening_part_2_room_present(beats[1])
    assert "Annette" in beats[2]


def test_generic_conflict_resolution_pattern():
    assert generic_conflict_resolution_detected("This is a conflict resolution meeting.")
    assert not generic_conflict_resolution_detected("On the schoolyard two boys fought.")


def test_prosecutorial_actor_line():
    assert prosecutorial_opening_detected("You did this on purpose.")
    assert not prosecutorial_opening_detected("Please sit; I will bring coffee.")


def test_opening_part_1_requires_schoolyard_and_civilised():
    assert opening_part_1_premise_present(
        "On the playground two boys used a stick; parents agreed to a civilised sit-down."
    )
    assert schoolyard_incident_present(
        "At the edge of Parc Montsouris, near a basketball court, boys argued over a stick."
    )
    assert not opening_part_1_premise_present("Two families meet in a Paris salon.")


def test_deterministic_opening_premise_uses_park_basketball_bicycle_details():
    beat = deterministic_part1_premise(output_language="en").lower()

    assert "fallback:" in beat
    assert "substitute story text" in beat
    assert "parc montsouris" not in beat
    assert "basketball" not in beat
    assert "bicycle" not in beat
    assert "stick" not in beat


def test_deterministic_opening_premise_stays_in_german_when_requested():
    beat = deterministic_part1_premise(output_language="de").lower()

    assert "fallback:" in beat
    assert "ersatz-erzählung" in beat
    assert "parc montsouris" not in beat
    assert "basketballplatz" not in beat
    assert "fahrrad" not in beat
    assert "their parents" not in beat
