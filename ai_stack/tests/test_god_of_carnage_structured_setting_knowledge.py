"""God of Carnage structured setting YAML — bundle exposure and cross-layer consistency."""

from __future__ import annotations

from pathlib import Path

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import (
    clear_goc_yaml_slice_cache,
    load_goc_apartment_layout_yaml,
    load_goc_scene_affordances_block,
    load_goc_scene_affordances_yaml_inner,
    load_goc_yaml_slice_bundle,
)
from ai_stack.langgraph.langgraph_runtime_executor import RuntimeTurnGraphExecutor


def setup_module(_m: object) -> None:
    clear_goc_yaml_slice_cache()


def test_yaml_slice_bundle_exposes_structured_setting_keys() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    for key in (
        "character_documents",
        "scene_graph",
        "canonical_path",
        "modularity_policy",
        "locations",
        "objects",
        "content_access_policy",
        "scene_affordances",
        "apartment_layout",
        "premise_and_backstory",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "narrator_sensory_palette",
        "opening_scene_sequence",
        "opening_quote_anchors",
        "hard_forbidden_rules",
    ):
        assert key in bundle
    assert bundle["opening_scene_sequence"].get("id") == "goc_opening_sequence_v1"
    assert (bundle.get("opening_quote_anchors") or {}).get("anchors")
    assert "hard_forbidden" in (bundle.get("hard_forbidden_rules") or {})
    assert len((bundle.get("scene_graph") or {}).get("nodes") or []) > 10
    assert len((bundle.get("canonical_path") or {}).get("steps") or []) >= 16
    assert (bundle.get("modularity_policy") or {}).get("authority_boundaries")
    assert (bundle.get("locations") or {}).get("places")
    assert (bundle.get("objects") or {}).get("object_documents")
    assert (bundle.get("content_access_policy") or {}).get("blocked_entities")
    assert set((bundle.get("character_documents") or {}).keys()) == {"veronique", "michel", "annette", "alain"}
    assert bundle["apartment_layout"].get("setting_id") == "vallon_paris_evening_apartment"
    assert "phase_1" in (bundle.get("phase_beat_policy") or {}).get("phases", {})


def test_scene_affordances_aligns_layout_room_ids() -> None:
    inner = load_goc_scene_affordances_yaml_inner()
    layout = load_goc_apartment_layout_yaml()
    loc_ids = {str(x.get("id")) for x in (inner.get("locations") or []) if isinstance(x, dict)}
    layout_room_ids = {r.get("id") for r in (layout.get("rooms") or []) if isinstance(r, dict)}
    assert {
        "building_hallway",
        "building_stairwell",
        "bathroom",
        "kitchen",
        "hallway",
        "dining_room",
        "bedroom",
        "hallway_bathroom_locked",
        "pantry",
        "study",
    }.issubset(loc_ids)
    assert layout_room_ids.issuperset(
        {
            "building_hallway",
            "building_stairwell",
            "bathroom",
            "kitchen",
            "hallway",
            "dining_room",
            "bedroom",
            "hallway_bathroom_locked",
            "pantry",
            "study",
            "living_room",
            "bedroom_one_locked",
            "bedroom_two_locked",
        }
    )


def test_apartment_layout_models_requested_room_topology() -> None:
    layout = load_goc_apartment_layout_yaml()
    rooms = {str(r.get("id")): r for r in (layout.get("rooms") or []) if isinstance(r, dict)}
    living = rooms["living_room"]
    hallway = rooms["hallway"]
    kitchen = rooms["kitchen"]
    building_hallway = rooms["building_hallway"]
    building_stairwell = rooms["building_stairwell"]

    assert "building_hallway" in (living.get("adjacent_room_ids") or [])
    assert "kitchen" in (living.get("adjacent_room_ids") or [])
    assert "building_stairwell" in (building_hallway.get("adjacent_room_ids") or [])
    assert building_stairwell.get("access_pattern") == "prevented_currently"
    assert building_stairwell.get("prevented_actions")
    hallway_adjacent = set(hallway.get("adjacent_room_ids") or [])
    assert {"kitchen", "dining_room", "bedroom", "pantry", "study", "bedroom_one_locked", "bedroom_two_locked"}.issubset(
        hallway_adjacent
    )
    assert "bathroom" not in hallway_adjacent
    assert "bathroom" in set(rooms["bedroom"].get("adjacent_room_ids") or [])
    assert "bedroom" in set(rooms["bathroom"].get("adjacent_room_ids") or [])
    assert "hallway_bathroom_locked" in hallway_adjacent
    assert rooms["hallway_bathroom_locked"].get("access_pattern") == "locked_non_playable"
    assert {"living_room", "hallway"}.issubset(set(kitchen.get("adjacent_room_ids") or []))
    assert rooms["bedroom_one_locked"].get("access_pattern") == "locked_non_playable"
    assert rooms["bedroom_two_locked"].get("access_pattern") == "locked_non_playable"


def test_apartment_objects_cover_requested_new_room_surfaces() -> None:
    inner = load_goc_scene_affordances_yaml_inner()
    objects = {str(x.get("id")): x for x in (inner.get("objects") or []) if isinstance(x, dict)}
    assert {
        "study_pinboard",
        "africa_map_darfur_pins",
        "glassware_cabinet",
        "locked_bathroom_door",
    }.issubset(objects)
    assert objects["study_pinboard"].get("portable") is False
    assert objects["locked_bathroom_door"].get("portable") is False
    assert objects["study_pinboard"].get("description_source_ref")
    assert objects["africa_map_darfur_pins"].get("description_source_ref")


def _read_yaml(path):
    """Read a YAML file as a dict; used by language-boundary and consistency audits."""
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _has_german_authoring_string(value) -> str | None:
    """Return a flagged substring if the value contains German-looking authoring text.

    Detects characteristic German-only orthography (ä/ö/ü/ß) embedded in authoring text.
    Comments are stripped by yaml parsing, so this only inspects authored values.
    """
    if isinstance(value, str):
        text = value.strip()
        if any(ch in text for ch in "äöüÄÖÜß"):
            return text[:80]
        return None
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in {"de", "german", "de_de"}:
                continue  # legitimate explicit language subkey
            hit = _has_german_authoring_string(v)
            if hit:
                return hit
        return None
    if isinstance(value, list):
        for item in value:
            hit = _has_german_authoring_string(item)
            if hit:
                return hit
    return None


def test_p2_1_english_only_knowledge_files_contain_no_german_authoring_strings() -> None:
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P2.1: language boundary — English-authored knowledge
    files must not contain German authoring strings outside explicit language subkeys.

    No module language lookup layer is expected; runtime language is generated by the AI adapter.
    """
    from pathlib import Path

    knowledge_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage" / "knowledge"
    english_only_files = [
        knowledge_dir / "opening_scene_sequence.yaml",
        knowledge_dir / "opening_quote_anchors.yaml",
        knowledge_dir / "hard_forbidden_rules.yaml",
        knowledge_dir / "content_access_policy.yaml",
        knowledge_dir / "premise_and_backstory.yaml",
        knowledge_dir / "modularity_policy.yaml",
        knowledge_dir / "narrator_sensory_palette.yaml",
        knowledge_dir.parent / "locations" / "index.yaml",
        knowledge_dir.parent / "locations" / "opening" / "park_edge.yaml",
        knowledge_dir.parent / "locations" / "opening" / "basketball_court.yaml",
        knowledge_dir.parent / "objects" / "opening" / "bicycle_rack.yaml",
        knowledge_dir.parent / "locations" / "building" / "building_hallway.yaml",
        knowledge_dir.parent / "locations" / "building" / "building_stairwell.yaml",
        knowledge_dir.parent / "scene_graph.yaml",
        knowledge_dir.parent / "locations" / "appartment_vallon" / "apartment_layout.yaml",
        knowledge_dir.parent / "objects" / "appartment_vallon" / "living_room" / "coffee_table.yaml",
        knowledge_dir.parent / "objects" / "appartment_vallon" / "living_room" / "dining_table.yaml",
        knowledge_dir.parent / "objects" / "appartment_vallon" / "living_room" / "window.yaml",
        knowledge_dir.parent / "objects" / "appartment_vallon" / "living_room" / "television.yaml",
        knowledge_dir.parent / "objects" / "building" / "elevator.yaml",
        knowledge_dir.parent / "canonical_path" / "index.yaml",
        knowledge_dir.parent / "canonical_path" / "001_parc_montsouris_edge.yaml",
        knowledge_dir.parent / "canonical_path" / "002_argument_stick_blow.yaml",
        knowledge_dir.parent / "canonical_path" / "003_bicycle_disappearance.yaml",
        knowledge_dir.parent / "canonical_path" / "004_dark_building_hallway.yaml",
        knowledge_dir.parent / "canonical_path" / "005_living_room_threshold.yaml",
        knowledge_dir.parent / "canonical_path" / "006_apartment_entry_greetings.yaml",
        knowledge_dir.parent / "canonical_path" / "007_living_room_arrangement.yaml",
        knowledge_dir.parent / "canonical_path" / "008_statement_on_table.yaml",
        knowledge_dir.parent / "canonical_path" / "009_wording_dispute_armed_carrying.yaml",
        *sorted((knowledge_dir.parent / "canonical_path").glob("01*.yaml")),
        knowledge_dir.parent / "characters" / "actor_pressure_profiles.yaml",
        knowledge_dir.parent / "phase_beat_policy.yaml",
    ]
    failures: list[str] = []
    for path in english_only_files:
        if not path.is_file():
            continue
        data = _read_yaml(path)
        hit = _has_german_authoring_string(data)
        if hit:
            failures.append(f"{path.name}: '{hit}'")
    assert not failures, f"German authoring strings found in English-only knowledge: {failures}"


def test_p2_2_direction_and_knowledge_opening_transitions_are_consistent() -> None:
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P2.2: direction/opening_sequence.yaml and
    knowledge/opening_scene_sequence.yaml must agree on the phase-1 first playable state so the
    runtime is not torn between two contracts."""
    from pathlib import Path

    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
    direction_data = _read_yaml(module_dir / "direction" / "opening_sequence.yaml")
    knowledge_data = _read_yaml(module_dir / "knowledge" / "opening_scene_sequence.yaml")

    knowledge_opening = knowledge_data.get("opening_scene_sequence") or {}
    knowledge_first_playable = None
    for event in (knowledge_opening.get("narrative_events") or []):
        if isinstance(event, dict) and event.get("first_playable_scene_phase"):
            knowledge_first_playable = event["first_playable_scene_phase"]
            break
    assert knowledge_first_playable == "phase_1", (
        f"knowledge/opening_scene_sequence first playable phase expected phase_1, got {knowledge_first_playable}"
    )

    # Direction file must keep the same first playable phase; nothing should point elsewhere.
    direction_text = (module_dir / "direction" / "opening_sequence.yaml").read_text(encoding="utf-8")
    assert "phase_1" in direction_text, "direction/opening_sequence.yaml should reference phase_1"
    # The direction file must reference the canonical knowledge contract so the relationship is explicit.
    assert "knowledge/opening_scene_sequence.yaml" in direction_text, (
        "direction/opening_sequence.yaml must point at knowledge/opening_scene_sequence.yaml"
    )


def test_opening_incident_content_is_concrete_in_direction_and_knowledge() -> None:
    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
    opening_doc = (module_dir / "direction" / "opening.md").read_text(encoding="utf-8").lower()
    direction_text = (module_dir / "direction" / "opening_sequence.yaml").read_text(encoding="utf-8").lower()
    knowledge_text = (module_dir / "knowledge" / "opening_scene_sequence.yaml").read_text(encoding="utf-8").lower()
    premise_text = (module_dir / "knowledge" / "premise_and_backstory.yaml").read_text(encoding="utf-8").lower()
    location_text = "\n".join(
        p.read_text(encoding="utf-8").lower()
        for p in sorted((module_dir / "locations" / "opening").glob("*.yaml"))
    )
    canonical_text = "\n".join(
        p.read_text(encoding="utf-8").lower()
        for p in sorted((module_dir / "canonical_path").glob("*.yaml"))
    )

    for text in (opening_doc, direction_text, knowledge_text, premise_text):
        assert "canonical_path/" in text or "canonical_path" in text
        assert "locations/" in text or "location_refs" in text

    for token in ("parc mont sourire", "basketball", "bicycle", "stick"):
        assert token in location_text or token in canonical_text or token in premise_text


def test_goc_content_surfaces_reference_locations_instead_of_rewriting_them() -> None:
    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
    non_location_files = [
        module_dir / "direction" / "opening.md",
        module_dir / "direction" / "opening_sequence.yaml",
        module_dir / "knowledge" / "opening_scene_sequence.yaml",
        module_dir / "knowledge" / "premise_and_backstory.yaml",
        module_dir / "knowledge" / "narrator_sensory_palette.yaml",
        module_dir / "scene_graph.yaml",
        *sorted((module_dir / "canonical_path").glob("*.yaml")),
    ]
    banned_location_rewrites = (
        "gray autumn sky, bare trees",
        "sloping lawns, winding paths",
        "other apartment doors and an elevator that does not arrive",
        "the kitchen attached to the living room",
        "the small hallway leading to the kitchen",
        "art books, tulips, coffee, dessert",
    )
    failures: list[str] = []
    for path in non_location_files:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in banned_location_rewrites:
            if phrase in text:
                failures.append(f"{path.relative_to(module_dir)} repeats '{phrase}'")
    assert not failures

    canonical = _read_yaml(module_dir / "canonical_path" / "index.yaml").get("canonical_path") or {}
    assert (canonical.get("reference_policy") or {}).get("steps_must_not_duplicate_location_descriptions") is True
    for step_path in sorted((module_dir / "canonical_path").glob("00*.yaml")):
        step = (_read_yaml(step_path).get("canonical_path_step") or {})
        loc_ref = step.get("location_ref")
        assert isinstance(loc_ref, dict) and loc_ref.get("source"), f"{step_path.name} missing location_ref.source"
        assert "point" not in step, f"{step_path.name} still uses legacy descriptive point block"


def test_canonical_path_scene_index_and_modular_character_documents_are_primary_surfaces() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    graph = bundle.get("scene_graph") or {}
    canonical_path = bundle.get("canonical_path") or {}
    docs = bundle.get("character_documents") or {}
    locations = bundle.get("locations") or {}
    objects = bundle.get("objects") or {}
    access = bundle.get("content_access_policy") or {}

    nodes = graph.get("nodes") or []
    assert len(nodes) >= 12
    assert canonical_path.get("primary_direction_surface") is True
    sequences = [step.get("sequence") for step in (canonical_path.get("steps") or [])]
    assert sequences == list(range(1, len(sequences) + 1))
    assert len(sequences) >= 16
    assert all((step.get("location_ref") or {}).get("source") for step in (canonical_path.get("steps") or []))
    assert "bicycle_rack" in (objects.get("object_documents") or {})
    assert "coffee_table" in (objects.get("object_documents") or {})
    assert "window" in (objects.get("object_documents") or {})
    assert all(isinstance(row.get("portable"), bool) for row in (objects.get("object_documents") or {}).values())
    assert (objects.get("object_documents") or {}).get("glasses", {}).get("portable") is True
    assert (objects.get("object_documents") or {}).get("coffee_table", {}).get("portable") is False
    assert graph.get("default_start_node_id") == "prologue_park_edge"
    assert graph.get("first_playable_node_id") == "first_playable_courtesy_gap"
    assert all(isinstance(row, dict) and row.get("location_id") for row in nodes)
    assert set(docs) == {"veronique", "michel", "annette", "alain"}
    assert all((doc.get("canonical_path_usage") or {}) for doc in docs.values())
    assert {doc.get("runtime_actor_id") for doc in docs.values()} == {
        "veronique_vallon",
        "michel_longstreet",
        "annette_reille",
        "alain_reille",
    }
    assert (bundle.get("characters") or {}).get("annette", {}).get("actor_id") == "annette_reille"
    assert {row.get("id") for row in (locations.get("places") or [])}.issuperset(
        {
            "park_edge",
            "basketball_court",
            "building_hallway",
            "building_stairwell",
            "living_room",
            "hallway",
            "bathroom",
            "kitchen",
            "dining_room",
            "bedroom",
            "hallway_bathroom_locked",
            "pantry",
            "study",
            "bedroom_one_locked",
            "bedroom_two_locked",
        }
    )
    assert set(access.get("scopes") or []).issuperset({"action", "location", "object", "scene_node"})
    blocked_targets = {row.get("target_id") for row in (access.get("blocked_entities") or []) if isinstance(row, dict)}
    assert {"bedroom_one_locked", "bedroom_two_locked", "hallway_bathroom_locked"}.issubset(blocked_targets)


def test_goc_resolve_canonical_content_projects_structured_knowledge_onto_state() -> None:
    """P0.1: _goc_resolve_canonical_content surfaces all 9 knowledge keys + _loaded flags onto runtime state."""
    clear_goc_yaml_slice_cache()
    graph = object.__new__(RuntimeTurnGraphExecutor)
    update = graph._goc_resolve_canonical_content({"module_id": "god_of_carnage"})

    assert update["goc_slice_active"] is True
    assert isinstance(update.get("opening_scene_sequence"), dict) and update["opening_scene_sequence"]
    assert isinstance(update.get("hard_forbidden_rules"), dict) and update["hard_forbidden_rules"]
    for key in (
        "character_documents",
        "scene_graph",
        "canonical_path",
        "modularity_policy",
        "beat_library",
        "opening_quote_anchors",
        "locations",
        "objects",
        "content_access_policy",
        "apartment_layout",
        "premise_and_backstory",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "narrator_sensory_palette",
        "scene_affordances",
    ):
        assert isinstance(update.get(key), dict) and update[key], f"state missing {key}"

    loaded = update.get("knowledge_runtime_loaded")
    assert isinstance(loaded, dict)
    for flag in (
        "opening_scene_sequence_loaded",
        "hard_forbidden_rules_loaded",
        "character_documents_loaded",
        "scene_graph_loaded",
        "canonical_path_loaded",
        "modularity_policy_loaded",
        "beat_library_loaded",
        "opening_quote_anchors_loaded",
        "locations_loaded",
        "objects_loaded",
        "content_access_policy_loaded",
        "apartment_layout_loaded",
        "premise_and_backstory_loaded",
        "actor_pressure_profiles_loaded",
        "phase_beat_policy_loaded",
        "narrator_sensory_palette_loaded",
        "scene_affordances_loaded",
    ):
        assert loaded.get(flag) is True, f"flag {flag} not True"

    contract = update.get("goc_runtime_knowledge_contract")
    assert isinstance(contract, dict)
    assert contract.get("opening_scene_sequence_id") == "goc_opening_sequence_v1"
    assert "single_word_challenge" in update["beat_library"]["patterns"]


def test_semantic_interaction_surface_is_derived_from_content_authorities() -> None:
    block = load_goc_scene_affordances_block()
    sa = block.get("scene_affordances") or {}
    locs = {str(x.get("id")): x for x in (sa.get("locations") or []) if isinstance(x, dict)}
    objs = {str(x.get("id")): x for x in (sa.get("objects") or []) if isinstance(x, dict)}
    kitchen = locs.get("kitchen") or {}
    bathroom = locs.get("bathroom") or {}
    assert kitchen.get("description")
    assert bathroom.get("description")
    assert kitchen.get("description_source_ref")
    assert bathroom.get("description_source_ref")
    win = objs.get("window") or {}
    assert win.get("description")
    assert win.get("description_source_ref")
    contract = sa.get("semantic_resolution_contract") or {}
    assert contract.get("policy", {}).get("no_hardcoded_language_maps") is True


def test_semantic_resolution_contract_replaces_old_relationship_tables() -> None:
    sa = load_goc_scene_affordances_yaml_inner()
    contract = sa.get("semantic_resolution_contract") or {}
    assert contract.get("schema_version") == "semantic_language_adapter.player_action_resolution.v1"
    assert contract.get("policy", {}).get("infer_meaning_from_player_utterance_and_content_catalog") is True
    assert contract.get("policy", {}).get("do_not_translate_by_lookup_table") is True
    assert contract.get("expected_ai_output", {}).get("resolved_target_id")
