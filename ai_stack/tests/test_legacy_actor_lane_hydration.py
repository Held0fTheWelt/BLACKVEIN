"""Unit tests for legacy narrative-only → actor-lane hydration."""

from __future__ import annotations

import re
from pathlib import Path

from ai_stack.legacy_actor_lane_hydration import (
    apply_legacy_structured_hydration,
    hydrate_legacy_actor_lanes,
    should_hydrate_legacy_actor_lanes,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.npc_agency.npc_agency_realization import validate_npc_initiative_realization
from ai_stack.scene_energy_engine import derive_scene_energy, validate_scene_energy_realization


def test_legacy_hydration_module_avoids_scene_energy_runtime_literal() -> None:
    """Legacy shim must not reintroduce scene_energy as a production shortcut literal."""
    text = (Path(__file__).resolve().parents[1] / "legacy_actor_lane_hydration.py").read_text(
        encoding="utf-8"
    )
    assert not re.search(r"\bscene_energy\b", text, re.IGNORECASE)


def test_should_hydrate_when_narrative_only() -> None:
    structured = {"narrative_response": "Michel shouts and accuses you in the room."}
    assert should_hydrate_legacy_actor_lanes(
        structured,
        module_id="god_of_carnage",
    )


def test_hydration_fills_spoken_lines_for_primary_and_secondary() -> None:
    narrative = (
        "Michel raises his voice, attacks your accusation, and threatens another fight if you continue."
    )
    structured = {"narrative_response": narrative}
    hydrated, changed = hydrate_legacy_actor_lanes(
        structured,
        selected_responder_set=[
            {"actor_id": "michel_longstreet", "role": "primary_responder"},
            {"actor_id": "annette_reille", "role": "secondary_reactor"},
        ],
        scene_energy_target={"minimum_actor_response_count": 2},
        pacing_mode="standard",
        selected_scene_function="escalate_conflict",
    )
    assert changed is True
    assert hydrated["schema_version"] == "runtime_actor_turn_v1"
    assert hydrated["primary_responder_id"] == "michel_longstreet"
    assert len(hydrated["spoken_lines"]) >= 1
    assert len(hydrated["action_lines"]) >= 1


def test_hydration_skips_narrator_only_local_consequence() -> None:
    narrative = "The local action is realized by narration, without asking an NPC to perform it."
    generation = {
        "metadata": {
            "structured_output": {
                "schema_version": "runtime_actor_turn_v1",
                "narration_summary": narrative,
                "narrative_response": narrative,
                "spoken_lines": [],
                "action_lines": [],
                "function_type": "local_action_consequence",
            }
        }
    }

    hydrated = apply_legacy_structured_hydration(
        {
            "module_id": "god_of_carnage",
            "interpreted_input": {"npc_response_expected": False},
            "player_action_frame": {"npc_response_expected": False},
            "narrator_consequence_plan": {"requires_model_realization": True},
            "selected_responder_set": [{"actor_id": "alain_reille"}],
            "scene_energy_target": {"minimum_actor_response_count": 1},
            "pacing_mode": "standard",
        },
        generation,
    )

    structured = hydrated["metadata"]["structured_output"]
    assert structured["spoken_lines"] == []
    assert structured["action_lines"] == []
    assert "legacy_actor_lane_hydrated" not in hydrated["metadata"]


def test_hydration_satisfies_scene_energy_and_npc_initiative_counts() -> None:
    policy = load_module_runtime_policy("god_of_carnage", "solo_test").to_dict()
    scene_function = "escalate_conflict"
    energy = derive_scene_energy(
        scene_plan_record={
            "selected_scene_function": scene_function,
            "pacing_mode": "standard",
        },
        pacing_mode="standard",
        selected_responder_set=[
            {"actor_id": "michel_longstreet"},
            {"actor_id": "annette_reille"},
        ],
        module_runtime_policy=policy,
    )
    narrative = "Michel attacks your claim and Annette redirects blame across the table."
    structured = {"narrative_response": narrative}
    npc_plan = {
        "required_actor_ids": ["michel_longstreet"],
        "npc_initiatives": [
            {"actor_id": "michel_longstreet", "required": True, "initiative_type": "seize"},
        ],
    }
    hydrated, changed = hydrate_legacy_actor_lanes(
        structured,
        selected_responder_set=[
            {"actor_id": "michel_longstreet"},
            {"actor_id": "annette_reille"},
        ],
        scene_energy_target=energy["target"],
        pacing_mode="standard",
        module_runtime_policy=policy,
        selected_scene_function=scene_function,
        npc_agency_plan=npc_plan,
    )
    assert changed is True
    sev = validate_scene_energy_realization(
        scene_energy_target=energy["target"],
        scene_energy_transition=energy["transition"],
        structured_output=hydrated,
    )
    assert sev["status"] == "approved"
    niv = validate_npc_initiative_realization(npc_plan, hydrated, strict_required=True)
    assert niv["status"] == "approved"
