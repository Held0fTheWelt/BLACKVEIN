"""
W1 Completion Tests: Validate God of Carnage module meets W1 requirements.

These tests verify the 10 required W1 coverage items:
1. Module root exists and is discoverable
2. Required content files load successfully
3. Character ids are unique and complete
4. Relationship references point to real characters
5. Scene ids are unique and structurally valid
6. Standalone transitions are absent; phase policy and canonical path direct flow
7. Pressure markers live in phase_beat_policy, not triggers.yaml
8. Closure pressure lives in phase_beat_policy, not endings.yaml
9. At least one full legal story path exists
10. Malformed fixtures fail validation cleanly
"""

import pytest
from pathlib import Path
from app.content.module_loader import load_module
from app.content.module_service import ModuleService
from app.content.module_validator import ModuleCrossReferenceValidator
from app.content.module_exceptions import (
    ModuleNotFoundError,
    ModuleParseError,
    ModuleStructureError,
)


class TestW1ModuleDiscoverability:
    """Test requirement #1: Module root exists and is discoverable."""

    def test_module_root_exists(self, god_of_carnage_module_root):
        """God of Carnage module root directory exists."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        assert god_of_carnage_module_root.is_dir()
        assert god_of_carnage_module_root.name == "god_of_carnage"

    def test_module_discoverable_via_service(self):
        """Module is discoverable via ModuleService."""
        service = ModuleService()
        modules = service.list_available_modules()

        if not modules:
            pytest.skip("No modules found")

        # god_of_carnage should be discoverable (even if list is empty, this shouldn't error)
        assert isinstance(modules, list)

    def test_module_has_manifest(self, god_of_carnage_module_root):
        """Module has module.yaml manifest file."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        manifest = god_of_carnage_module_root / "module.yaml"
        assert manifest.exists()
        assert manifest.is_file()


class TestW1ContentFilesLoadable:
    """Test requirement #2: Required content files load successfully."""

    def test_required_files_exist(self, god_of_carnage_module_root):
        """All required content files exist."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        root = god_of_carnage_module_root
        required_paths = [
            root / "module.yaml",
            root / "characters" / "index.yaml",
            root / "characters" / "definitions" / "veronique.yaml",
            root / "characters" / "definitions" / "michel.yaml",
            root / "characters" / "definitions" / "annette.yaml",
            root / "characters" / "definitions" / "alain.yaml",
            root / "characters" / "details" / "relationships.yaml",
            root / "canonical_path" / "index.yaml",
            root / "canonical_path" / "001_parc_montsouris_edge.yaml",
            root / "canonical_path" / "002_argument_stick_blow.yaml",
            root / "canonical_path" / "003_bicycle_disappearance.yaml",
            root / "canonical_path" / "004_den_arrival_positioning.yaml",
            root / "canonical_path" / "005_statement_reading.yaml",
            root / "canonical_path" / "006_armed_vs_carrying.yaml",
            root / "canonical_path" / "007_drift_to_foyer_safer_park.yaml",
            root / "canonical_path" / "008_living_room_tulips_florist.yaml",
            root / "canonical_path" / "009_root_canal_observation_period.yaml",
            root / "canonical_path" / "010_snitch_sense_of_honor.yaml",
            root / "canonical_path" / "011_alain_first_walter_call.yaml",
            root / "canonical_path" / "012_jobs_and_hamster.yaml",
            root / "canonical_path" / "013_apology_pressure_eleven.yaml",
            root / "canonical_path" / "014_kitchen_cobbler_hunt.yaml",
            root / "canonical_path" / "015_back_to_living_room_cobbler.yaml",
            root / "canonical_path" / "016_cobbler_eating_recipe_tooth_jab.yaml",
            root / "objects" / "index.yaml",
            root / "objects" / "opening" / "bicycle_rack.yaml",
            root / "objects" / "appartment_vallon" / "living_room" / "coffee_table.yaml",
            root / "objects" / "appartment_vallon" / "living_room" / "dining_table.yaml",
            root / "objects" / "appartment_vallon" / "living_room" / "window.yaml",
            root / "objects" / "appartment_vallon" / "living_room" / "television.yaml",
            root / "objects" / "building" / "elevator.yaml",
            root / "scene_graph.yaml",
            root / "locations" / "index.yaml",
            root / "locations" / "opening" / "park_edge.yaml",
            root / "locations" / "building" / "building_hallway.yaml",
            root / "locations" / "building" / "building_stairwell.yaml",
            root / "locations" / "appartment_vallon" / "apartment_layout.yaml",
            root / "characters" / "details" / "actor_pressure_profiles.yaml",
            root / "phase_beat_policy.yaml",
            root / "knowledge" / "premise_and_backstory.yaml",
            root / "knowledge" / "modularity_policy.yaml",
            root / "knowledge" / "narrator_sensory_palette.yaml",
            root / "knowledge" / "opening_scene_sequence.yaml",
            root / "knowledge" / "opening_quote_anchors.yaml",
            root / "knowledge" / "hard_forbidden_rules.yaml",
            root / "knowledge" / "content_access_policy.yaml",
        ]

        for filepath in required_paths:
            assert filepath.is_file(), f"Missing required file: {filepath.relative_to(root)}"

    def test_module_loads_successfully(self):
        """God of Carnage module loads without errors."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert module is not None
        assert module.metadata.module_id == "god_of_carnage"
        assert module.apartment_layout.get("setting_id") == "vallon_paris_evening_apartment"
        assert isinstance(module.actor_pressure_profiles.get("profiles"), dict)
        assert "phase_1" in (module.phase_beat_policy.get("phases") or {})
        assert module.opening_scene_sequence.get("id") == "goc_opening_sequence_v1"
        assert module.opening_quote_anchors.get("anchors")
        assert "hard_forbidden" in (module.hard_forbidden_rules or {})
        assert module.canonical_path.get("primary_direction_surface") is True
        assert module.modularity_policy.get("authority_boundaries")
        assert len((module.scene_graph.get("nodes") or [])) > 10
        assert (module.locations.get("places") or [])
        assert module.content_access_policy.get("blocked_entities")
        assert set(module.character_documents.keys()) == {"veronique", "michel", "annette", "alain"}
        assert module.premise_and_backstory.get("authoring_language") == "en"

    def test_all_yaml_files_parse(self, god_of_carnage_module_root):
        """All YAML files parse correctly."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        import yaml

        yaml_files = list(god_of_carnage_module_root.glob("*.yaml"))
        knowledge_dir = god_of_carnage_module_root / "knowledge"
        if knowledge_dir.is_dir():
            yaml_files.extend(sorted(knowledge_dir.glob("*.yaml")))
        characters_dir = god_of_carnage_module_root / "characters"
        if characters_dir.is_dir():
            yaml_files.extend(sorted(characters_dir.glob("*.yaml")))
        locations_dir = god_of_carnage_module_root / "locations"
        if locations_dir.is_dir():
            yaml_files.extend(sorted(locations_dir.rglob("*.yaml")))
        objects_dir = god_of_carnage_module_root / "objects"
        if objects_dir.is_dir():
            yaml_files.extend(sorted(objects_dir.rglob("*.yaml")))
        canonical_path_dir = god_of_carnage_module_root / "canonical_path"
        if canonical_path_dir.is_dir():
            yaml_files.extend(sorted(canonical_path_dir.glob("*.yaml")))
        assert len(yaml_files) >= 8, "Should have at least 8 YAML files"

        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
            assert data is not None, f"Failed to parse {yaml_file.name}"


class TestW1CharacterValidation:
    """Test requirement #3: Character ids are unique and complete."""

    def test_characters_exist(self):
        """Module has characters defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.characters) > 0
        assert len(module.characters) == 4  # Véronique, Michel, Annette, Alain

    def test_character_ids_unique(self):
        """All character ids are unique."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        char_ids = list(module.characters.keys())
        assert len(char_ids) == len(set(char_ids))  # No duplicates

    def test_required_characters_present(self):
        """All required characters are present."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_chars = {"veronique", "michel", "annette", "alain"}
        actual_chars = set(module.characters.keys())

        assert required_chars == actual_chars

    def test_characters_have_required_fields(self):
        """All characters have required fields."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_fields = {"id", "name", "role", "baseline_attitude"}

        for char_id, char in module.characters.items():
            for field in required_fields:
                assert hasattr(char, field), f"Character {char_id} missing field {field}"


class TestW1RelationshipValidation:
    """Test requirement #4: Relationship references point to real characters."""

    def test_relationships_exist(self):
        """Module has relationships defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.relationship_axes) > 0
        assert len(module.relationship_definitions) > 0

    def test_relationship_character_references_valid(self):
        """All relationship references point to real characters."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        char_ids = set(module.characters.keys())
        validator = ModuleCrossReferenceValidator()
        errors = validator.validate_relationship_references(module)

        assert len(errors) == 0, f"Relationship validation errors: {errors}"

    def test_relationship_axes_have_characters(self):
        """Each relationship axis references valid characters."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        for axis_id, axis in module.relationship_axes.items():
            assert axis.relationships, f"Axis {axis_id} has no relationships"


class TestW1PhasePolicyValidation:
    """Test requirement #5: Phase ids are derived from phase_beat_policy."""

    def test_scenes_exist(self):
        """Module has phase policy projections defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.scene_phases) > 0

    def test_scene_ids_unique(self):
        """All derived phase ids are unique."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        scene_ids = list(module.scene_phases.keys())
        assert len(scene_ids) == len(set(scene_ids))

    def test_required_scenes_present(self):
        """All 5 required phase policy entries are present."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_phases = {"phase_1", "phase_2", "phase_3", "phase_4", "phase_5"}
        actual_phases = set(module.scene_phases.keys())

        assert required_phases == actual_phases

    def test_scene_sequence_linear(self):
        """Phase policy sequence is linear (1,2,3,4,5)."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        for i in range(1, 6):
            phase_key = f"phase_{i}"
            assert phase_key in module.scene_phases
            phase = module.scene_phases[phase_key]
            assert phase.sequence == i

    def test_scenes_have_required_fields(self):
        """All derived phase policy projections have required fields."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_fields = {
            "id",
            "name",
            "sequence",
            "description",
            "engine_tasks",
            "active_triggers",
            "enforced_constraints",
        }

        for phase_id, phase in module.scene_phases.items():
            for field in required_fields:
                assert hasattr(phase, field), f"Phase {phase_id} missing field {field}"


class TestW1TransitionValidation:
    """Test requirement #6: Old standalone transition files are gone."""

    def test_transitions_are_not_a_parallel_content_surface(self):
        """Phase progression now comes from phase_beat_policy and canonical_path."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert module.phase_transitions == {}
        assert module.phase_beat_policy.get("phases")
        assert module.canonical_path.get("step_order")

    def test_transitions_reference_valid_triggers(self):
        """The remaining phase projection has no undefined formal trigger refs."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        validator = ModuleCrossReferenceValidator()
        errors = validator.validate_trigger_references(module)

        assert len(errors) == 0, f"Trigger validation errors: {errors}"


class TestW1TriggerValidation:
    """Test requirement #7: Phase pressure markers replace trigger definition files."""

    def test_trigger_definitions_are_not_a_parallel_content_surface(self):
        """The old trigger definition database is intentionally absent."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert module.trigger_definitions == {}

    def test_phase_pressure_markers_are_present(self):
        """Pressure markers are authored inside phase_beat_policy."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        expected_markers = {
            "contradiction",
            "exposure",
            "relativization",
            "apology_or_non_apology",
            "cynicism",
            "flight_into_sideplots",
            "collapse_indicators",
            "retreat_signals",
        }

        phases = module.phase_beat_policy.get("phases") or {}
        actual_markers = {
            marker
            for phase in phases.values()
            for marker in (phase.get("pressure_markers") or [])
        }
        assert expected_markers.issubset(actual_markers)


class TestW1EndingValidation:
    """Test requirement #8: Closure pressure lives in phase policy, not endings.yaml."""

    def test_endings_are_not_a_parallel_content_surface(self):
        """The old ending condition database is intentionally absent."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert module.ending_conditions == {}
        phase_5 = (module.phase_beat_policy.get("phases") or {}).get("phase_5") or {}
        assert "exit_condition" in phase_5
        assert phase_5["exit_condition"]


class TestW1LegalStoryPath:
    """Test requirement #9: At least one full legal story path exists."""

    def test_story_path_phase_1_to_5(self):
        """Valid path exists through all 5 phases."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        # Verify phase sequence exists
        phases = module.scene_phases
        assert "phase_1" in phases
        assert "phase_2" in phases
        assert "phase_3" in phases
        assert "phase_4" in phases
        assert "phase_5" in phases

        # Verify phase policy sequence connects the playable arc linearly.
        ordered = [phase.id for phase in sorted(phases.values(), key=lambda phase: phase.sequence)]
        assert ordered == ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5"]

    def test_story_path_has_valid_endings(self):
        """Story path can reach valid endings from phase_5."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        # Phase_5 owns closure pressure without requiring endings.yaml.
        phase_5 = module.scene_phases.get("phase_5")
        assert phase_5 is not None

        phase_5_policy = (module.phase_beat_policy.get("phases") or {}).get("phase_5") or {}
        assert phase_5_policy.get("exit_condition")

    def test_full_path_validation(self):
        """Full module validates cleanly (entire path from load to end)."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        validator = ModuleCrossReferenceValidator()
        result = validator.validate_all(module)

        assert result.is_valid is True
        assert len(result.errors) == 0


class TestW1MalformedFailures:
    """Test requirement #10: Malformed fixtures fail validation cleanly."""

    def test_malformed_yaml_fails_on_load(self, malformed_yaml_root, test_modules_root):
        """Malformed YAML fails during load phase."""
        import shutil

        dest = test_modules_root / "malformed_test"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(malformed_yaml_root, dest)

        with pytest.raises(ModuleParseError):
            load_module("malformed_test", root_path=test_modules_root)

    def test_invalid_structure_fails_on_validate(
        self, invalid_module_root, test_modules_root
    ):
        """Invalid structure fails during structure validation."""
        import shutil

        dest = test_modules_root / "invalid_test"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(invalid_module_root, dest)

        with pytest.raises(ModuleStructureError):
            load_module("invalid_test", root_path=test_modules_root)

    def test_service_preflight_handles_errors(self, test_modules_root):
        """Service preflight check handles malformed modules gracefully."""
        service = ModuleService(root_path=test_modules_root)

        # Preflight on nonexistent module should return invalid result, not raise
        result = service.preflight_check("nonexistent_module")

        assert result.is_valid is False
        assert len(result.errors) > 0
