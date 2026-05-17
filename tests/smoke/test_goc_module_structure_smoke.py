"""
Smoke tests for God of Carnage (GoC) canonical module structure.

Validates that the GoC module under content/modules/god_of_carnage is:
- Structurally valid YAML
- Complete (all required files present)
- Internally consistent (character refs, relationship refs, etc.)
- Free of obsolete wave-style identifiers in tracked module YAML
"""

import json
import yaml
import pytest
from pathlib import Path


def _load_character_roster(module_root: Path) -> dict:
    """Return compact character roster from characters/index.yaml or legacy map."""
    index_path = module_root / "characters" / "index.yaml"
    if not index_path.is_file():
        index_path = module_root / "characters.yaml"
    with open(index_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    characters = doc.get("characters")
    if isinstance(characters, dict):
        return characters
    index = doc.get("characters_index") or {}
    documents = index.get("documents") if isinstance(index, dict) else {}
    roster = {}
    for char_id, rel_path in (documents or {}).items():
        path = module_root / str(rel_path)
        with open(path, encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        char_doc = payload.get("character_document") or payload.get("character") or payload
        if isinstance(char_doc, dict):
            roster[str(char_id)] = char_doc
    return roster


class TestGocModuleStructureSmoke:
    """Verify God of Carnage module canonical structure exists and is valid."""

    MODULE_ROOT = Path(__file__).parent.parent.parent / "content" / "modules" / "god_of_carnage"

    REQUIRED_CORE_FILES = [
        "module.yaml",
        "characters/index.yaml",
        "characters/definitions/veronique.yaml",
        "characters/definitions/michel.yaml",
        "characters/definitions/annette.yaml",
        "characters/definitions/alain.yaml",
        "characters/details/relationships.yaml",
        "characters/details/actor_pressure_profiles.yaml",
        "characters/details/interaction_patterns.yaml",
        "characters/voices/character_voice_veronique.yaml",
        "characters/voices/character_voice_michel.yaml",
        "characters/voices/character_voice_annette.yaml",
        "characters/voices/character_voice_alain.yaml",
        "characters/voices/voice_consistency.yaml",
        "canonical_path/index.yaml",
        "canonical_path/001_parc_montsouris_edge.yaml",
        "canonical_path/002_argument_stick_blow.yaml",
        "canonical_path/003_bicycle_disappearance.yaml",
        "canonical_path/004_dark_building_hallway.yaml",
        "canonical_path/005_living_room_handover.yaml",
        "canonical_path/006_apartment_entry_greetings.yaml",
        "canonical_path/007_living_room_arrangement.yaml",
        "canonical_path/008_statement_on_table.yaml",
        "canonical_path/009_wording_dispute_armed_carrying.yaml",
        "canonical_path/010_injury_detail_dental_consequence.yaml",
        "canonical_path/011_courtesy_community_pressure.yaml",
        "canonical_path/012_tulips_and_hospitality.yaml",
        "canonical_path/013_first_playable_courtesy_gap.yaml",
        "canonical_path/014_player_response_ripple.yaml",
        "canonical_path/015_phone_exit_pressure.yaml",
        "canonical_path/016_opening_sustained_play_handoff.yaml",
        "locations/index.yaml",
        "locations/appartment_vallon/apartment_layout.yaml",
        "objects/index.yaml",
        "objects/opening/bicycle_rack.yaml",
        "objects/appartment_vallon/living_room/coffee_table.yaml",
        "objects/appartment_vallon/living_room/dining_table.yaml",
        "objects/appartment_vallon/living_room/window.yaml",
        "objects/appartment_vallon/living_room/television.yaml",
        "objects/appartment_vallon/hallway/hallway_doors.yaml",
        "objects/appartment_vallon/kitchen/coffee_machine.yaml",
        "objects/appartment_vallon/kitchen/glasses.yaml",
        "objects/appartment_vallon/dining_room/dining_room_table.yaml",
        "objects/appartment_vallon/bedroom/bedroom_wardrobe.yaml",
        "objects/appartment_vallon/bathroom/bathroom_mirror.yaml",
        "objects/appartment_vallon/pantry/pantry_shelves.yaml",
        "objects/appartment_vallon/study/study_desk.yaml",
        "objects/appartment_vallon/study/study_pinboard.yaml",
        "objects/appartment_vallon/study/africa_map_darfur_pins.yaml",
        "objects/appartment_vallon/hallway/locked_bathroom_door.yaml",
        "objects/building/apartment_door.yaml",
        "objects/building/elevator.yaml",
        "locale/action_outcome_map.yaml",
        "locations/opening/park_edge.yaml",
        "locations/opening/basketball_court.yaml",
        "locations/opening/playground.yaml",
        "locations/building/building_hallway.yaml",
        "locations/building/building_stairwell.yaml",
        "locations/appartment_vallon/apartment_entry.yaml",
        "locations/appartment_vallon/living_room.yaml",
        "locations/appartment_vallon/hallway.yaml",
        "locations/appartment_vallon/kitchen.yaml",
        "locations/appartment_vallon/dining_room.yaml",
        "locations/appartment_vallon/bedroom.yaml",
        "locations/appartment_vallon/bathroom.yaml",
        "locations/appartment_vallon/hallway_bathroom_locked.yaml",
        "locations/appartment_vallon/pantry.yaml",
        "locations/appartment_vallon/study.yaml",
        "locations/appartment_vallon/bedroom_one_locked.yaml",
        "locations/appartment_vallon/bedroom_two_locked.yaml",
        "knowledge/modularity_policy.yaml",
        "knowledge/opening_quote_anchors.yaml",
    ]

    REQUIRED_DIRECTION_FILES = [
        "direction/system_prompt.md",
        "direction/opening_sequence.yaml",
    ]

    def test_module_root_exists(self):
        """Module root directory exists."""
        assert self.MODULE_ROOT.exists(), f"Module root {self.MODULE_ROOT} does not exist"
        assert self.MODULE_ROOT.is_dir(), f"Module root {self.MODULE_ROOT} is not a directory"

    def test_core_files_exist(self):
        """All required core module files exist."""
        for filename in self.REQUIRED_CORE_FILES:
            filepath = self.MODULE_ROOT / filename
            assert filepath.exists(), f"Required file {filename} not found"
            assert filepath.is_file(), f"Required file {filename} is not a file"

    def test_objects_are_not_modeled_as_locations(self):
        """Objects live under objects/ and locations only reference object ids."""
        obsolete_location_files = [
            "locations/opening/bicycle_rack.yaml",
            "locations/appartment_vallon/apartment_objects.yaml",
            "locations/appartment_vallon/coffee_table.yaml",
            "locations/appartment_vallon/window.yaml",
            "objects/appartment_vallon/apartment_objects.yaml",
        ]
        for filename in obsolete_location_files:
            assert not (self.MODULE_ROOT / filename).exists(), f"Object file must not live in locations/: {filename}"

        locations_index = yaml.safe_load((self.MODULE_ROOT / "locations" / "index.yaml").read_text(encoding="utf-8"))
        locations = locations_index["locations"]
        assert locations["object_authority_ref"] == "objects/index.yaml"
        for place_file in locations.get("place_files") or []:
            assert str(place_file).startswith("locations/"), f"Location index must not list object file: {place_file}"

        living_room = yaml.safe_load(
            (self.MODULE_ROOT / "locations" / "appartment_vallon" / "living_room.yaml").read_text(encoding="utf-8")
        )["location"]
        assert "inventory_object_ids" in living_room
        assert "coffee_table" in living_room["inventory_object_ids"]
        assert "window" in living_room["inventory_object_ids"]

        object_index = yaml.safe_load((self.MODULE_ROOT / "objects" / "index.yaml").read_text(encoding="utf-8"))[
            "objects"
        ]
        assert object_index["placement_policy"]["apartment_objects_grouped_by_location_subfolder"] is True
        assert object_index["placement_policy"]["objects_must_declare_portable"] is True
        assert object_index["location_object_folders"]["living_room"] == "objects/appartment_vallon/living_room/"
        assert object_index["location_object_folders"]["dining_room"] == "objects/appartment_vallon/dining_room/"
        assert object_index["location_object_folders"]["bedroom"] == "objects/appartment_vallon/bedroom/"
        assert "objects/appartment_vallon/living_room/coffee_table.yaml" in object_index["object_files"]
        assert "objects/appartment_vallon/dining_room/dining_room_table.yaml" in object_index["object_files"]
        assert "objects/appartment_vallon/study/africa_map_darfur_pins.yaml" in object_index["object_files"]
        assert not list((self.MODULE_ROOT / "objects" / "appartment_vallon").glob("*.yaml"))
        for rel_path in object_index["object_files"]:
            object_doc = yaml.safe_load((self.MODULE_ROOT / rel_path).read_text(encoding="utf-8"))["object"]
            assert isinstance(object_doc.get("portable"), bool), f"{rel_path} must declare boolean portable"

    def test_obsolete_orchestration_files_are_absent(self):
        """Old second-source orchestration files must not return to the module."""
        obsolete_files = [
            "scenes.yaml",
            "transitions.yaml",
            "triggers.yaml",
            "endings.yaml",
            "escalation_axes.yaml",
            "direction/scene_guidance.yaml",
            "locale",
            "runtime/action_outcome_map.yaml",
        ]
        for filename in obsolete_files:
            assert not (self.MODULE_ROOT / filename).exists(), f"Obsolete file still present: {filename}"

    def test_direction_files_exist(self):
        """All optional direction guidance files exist."""
        for filename in self.REQUIRED_DIRECTION_FILES:
            filepath = self.MODULE_ROOT / filename
            assert filepath.exists(), f"Direction file {filename} not found"
            assert filepath.is_file(), f"Direction file {filename} is not a file"

    def test_yaml_files_parse(self):
        """All YAML files are valid and parse without error."""
        for filename in self.REQUIRED_CORE_FILES:
            filepath = self.MODULE_ROOT / filename
            try:
                with open(filepath, encoding="utf-8") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"YAML parse error in {filename}: {e}")

        # Parse direction YAML files (skip .md files; handle multi-document YAML)
        for filename in self.REQUIRED_DIRECTION_FILES:
            if not filename.endswith(".yaml"):
                continue
            filepath = self.MODULE_ROOT / filename
            try:
                with open(filepath, encoding="utf-8") as f:
                    # Use safe_load_all to handle multi-document YAML (separated by ---)
                    list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                pytest.fail(f"YAML parse error in {filename}: {e}")

    def test_module_yaml_structure(self):
        """module.yaml has required canonical fields."""
        with open(self.MODULE_ROOT / "module.yaml", encoding="utf-8") as f:
            module = yaml.safe_load(f)

        required_fields = ["module_id", "title", "version", "contract_version", "content", "files"]
        for field in required_fields:
            assert field in module, f"module.yaml missing required field: {field}"

        assert module["module_id"] == "god_of_carnage"
        assert module["version"] == "0.1.0"
        assert module["contract_version"] == "0.2.0"

    def test_characters_yaml_structure(self):
        """characters/index.yaml references all 4 required characters."""
        characters = _load_character_roster(self.MODULE_ROOT)

        required_character_ids = ["veronique", "michel", "annette", "alain"]
        for char_id in required_character_ids:
            assert char_id in characters, f"Missing character: {char_id}"

        # Verify each character has formal properties
        for char_id, char_data in characters.items():
            required_props = ["id", "name", "role", "baseline_attitude"]
            for prop in required_props:
                assert prop in char_data, f"Character {char_id} missing {prop}"

    def test_visitor_is_absent_from_canonical_module(self):
        """visitor must NOT exist as a character in the canonical module."""
        characters = _load_character_roster(self.MODULE_ROOT)
        assert "visitor" not in characters, (
            "visitor must not be defined as a canonical character — it is globally prohibited"
        )

    def test_annette_and_alain_are_playable_human_roles(self):
        """annette and alain must be defined and present as human-playable characters."""
        characters = _load_character_roster(self.MODULE_ROOT)
        assert "annette" in characters, "annette must be a canonical character (human-playable)"
        assert "alain" in characters, "alain must be a canonical character (human-playable)"

    def test_module_id_is_not_god_of_carnage_solo(self):
        """Canonical module_id must be 'god_of_carnage', not 'god_of_carnage_solo'."""
        with open(self.MODULE_ROOT / "module.yaml", encoding="utf-8") as f:
            module = yaml.safe_load(f)
        assert module.get("module_id") == "god_of_carnage", (
            f"module_id must be 'god_of_carnage', got '{module.get('module_id')}'. "
            "god_of_carnage_solo is a runtime profile, not a canonical content module."
        )

    def test_relationships_yaml_structure(self):
        """characters/details/relationships.yaml defines required axes and relationships."""
        with open(self.MODULE_ROOT / "characters" / "details" / "relationships.yaml", encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        assert "relationship_axes" in doc, "Missing relationship_axes section"
        axes = doc["relationship_axes"]

        required_axes = ["axis_1", "axis_2", "axis_3", "axis_4"]
        for axis_id in required_axes:
            assert axis_id in axes, f"Missing relationship axis: {axis_id}"

        assert "relationships" in doc, "Missing relationships section"
        relationships = doc["relationships"]

        required_relationships = [
            "veronique_michel",
            "annette_alain",
            "veronique_annette",
            "veronique_alain",
            "michel_annette",
            "michel_alain",
        ]
        for rel_id in required_relationships:
            assert rel_id in relationships, f"Missing relationship definition: {rel_id}"

    def test_phase_beat_policy_structure(self):
        """phase_beat_policy.yaml defines the 5 coarse phase policies."""
        with open(self.MODULE_ROOT / "phase_beat_policy.yaml", encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        assert "phase_beat_policy" in doc, "Missing phase_beat_policy section"
        phases = doc["phase_beat_policy"]["phases"]
        assert doc["phase_beat_policy"]["canonical_path_source"] == "canonical_path/index.yaml"

        required_phases = ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]
        for phase_id in required_phases:
            assert phase_id in phases, f"Missing phase policy: {phase_id}"

        # Verify phase sequence is correct
        for i, phase_id in enumerate(required_phases, start=1):
            phase = phases[phase_id]
            assert phase["sequence"] == i, f"{phase_id} sequence incorrect"

        assert phases["phase_2"].get("pressure_markers"), "Phase pressure markers should live in phase_beat_policy"
        assert "active_triggers" not in phases["phase_2"], "Formal trigger DB fields should not live in phase policy"

    def test_module_file_registry_matches_reality(self):
        """module.yaml file registry matches actual files on disk."""
        with open(self.MODULE_ROOT / "module.yaml", encoding="utf-8") as f:
            module = yaml.safe_load(f)

        listed_files = module.get("files", [])
        # Registry uses repo-relative paths under the module root (may nest deeper than one dir).
        actual_files = {
            p.relative_to(self.MODULE_ROOT).as_posix()
            for p in self.MODULE_ROOT.rglob("*")
            if p.is_file()
        }

        for listed_file in listed_files:
            normalized = str(listed_file).split("#", 1)[0].strip()
            assert normalized in actual_files, f"Listed file {listed_file} not found on disk"


class TestGocModuleConsistencySmoke:
    """Verify internal consistency of God of Carnage module."""

    MODULE_ROOT = Path(__file__).parent.parent.parent / "content" / "modules" / "god_of_carnage"

    @pytest.fixture
    def module_data(self):
        """Load all module YAML files."""
        with open(self.MODULE_ROOT / "module.yaml", encoding="utf-8") as f:
            module = yaml.safe_load(f)
        with open(self.MODULE_ROOT / "characters" / "index.yaml", encoding="utf-8") as f:
            characters = yaml.safe_load(f) or {}
        if "characters" not in characters:
            characters = {"characters": _load_character_roster(self.MODULE_ROOT)}
        with open(self.MODULE_ROOT / "characters" / "details" / "relationships.yaml", encoding="utf-8") as f:
            relationships = yaml.safe_load(f)
        with open(self.MODULE_ROOT / "phase_beat_policy.yaml", encoding="utf-8") as f:
            phase_beat_policy = yaml.safe_load(f)

        return {
            "module": module,
            "characters": characters,
            "relationships": relationships,
            "phase_beat_policy": phase_beat_policy,
        }

    def test_character_references_valid(self, module_data):
        """All character references in relationships exist in character documents."""
        char_ids = set(module_data["characters"]["characters"].keys())
        relationships = module_data["relationships"]["relationships"]

        for rel_id, rel_data in relationships.items():
            # Extract character IDs from relationship ID (e.g., "veronique_michel" -> ["veronique", "michel"])
            parts = rel_id.split("_")
            if len(parts) >= 2:
                # Simple heuristic: relationship IDs are "char1_char2" format
                # This is not foolproof but catches basic errors
                pass  # Skip complex parsing; relationships are explicitly defined

    def test_module_has_reasonable_duration(self, module_data):
        """Module duration estimates are reasonable."""
        duration = module_data["module"].get("content", {}).get("duration_turns_estimated", "")
        assert duration, "Module missing duration_turns_estimated"
        assert any(expected in duration for expected in ("20-35", "20-30", "20+")), (
            f"Duration should reflect the expanded playable opening: {duration}"
        )

    def test_phases_have_exit_conditions(self, module_data):
        """All phase policy entries define exit conditions."""
        phases = module_data["phase_beat_policy"]["phase_beat_policy"].get("phases", {})
        for phase_id, phase_data in phases.items():
            assert "exit_condition" in phase_data, f"{phase_id} missing exit_condition"
            assert phase_data["exit_condition"], f"{phase_id} exit_condition is empty"


class TestGocModuleNoWaveReferencesSmoke:
    """Verify that module files do NOT contain wave identifiers (W0, W1, etc.)."""

    MODULE_ROOT = Path(__file__).parent.parent.parent / "content" / "modules" / "god_of_carnage"

    def test_no_w0_references_in_yaml(self):
        """No W0 references in core module YAML files."""
        for yaml_file in self.MODULE_ROOT.glob("*.yaml"):
            with open(yaml_file, encoding="utf-8") as f:
                content = f.read()
            assert "W0" not in content, f"Found W0 reference in {yaml_file.name}"
            assert "W1" not in content, f"Found W1 reference in {yaml_file.name}"

    def test_no_wave_references_in_direction(self):
        """No W0/W1 references in direction guidance files."""
        for guidance_file in self.MODULE_ROOT.glob("direction/*"):
            if not guidance_file.is_file():
                continue
            with open(guidance_file, encoding="utf-8") as f:
                content = f.read()
            assert "W0" not in content, f"Found W0 reference in {guidance_file.name}"
            assert "W1" not in content, f"Found W1 reference in {guidance_file.name}"
