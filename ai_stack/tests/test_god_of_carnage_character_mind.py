"""CharacterMind deterministic derivation from YAML slice."""

from __future__ import annotations

from ai_stack.story_runtime.npc_agency.character.god_of_carnage_character_mind import build_character_mind_records_for_goc
from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import load_goc_yaml_slice_bundle


def test_character_mind_provenance_has_authored_or_derived() -> None:
    bundle = load_goc_yaml_slice_bundle()
    minds = build_character_mind_records_for_goc(
        yaml_slice=bundle,
        active_character_keys=["veronique", "michel"],
        current_scene_id="living_room",
    )
    assert len(minds) == 2
    for m in minds:
        assert m.runtime_actor_id
        assert m.provenance.get("formal_role_label") is not None
        src = m.provenance["formal_role_label"].source
        assert src in ("authored", "authored_derived", "fallback_default")
