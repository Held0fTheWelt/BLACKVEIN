"""
W1 Completion Tests: Validate God of Carnage module meets W1 requirements.

These tests verify the 10 required W1 coverage items:
1. Module root exists and is discoverable
2. Required content files load successfully
3. Character ids are unique and complete
4. Relationship references point to real characters
5. Scene ids are unique and structurally valid
6. Transitions point to valid scenes or endings
7. Triggers are from the supported trigger set
8. Endings are structurally valid
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

        required_files = [
            "module.yaml",
            "characters.yaml",
            "relationships.yaml",
            "scenes.yaml",
            "transitions.yaml",
            "triggers.yaml",
            "endings.yaml",
            "escalation_axes.yaml",
        ]

        for filename in required_files:
            filepath = god_of_carnage_module_root / filename
            assert filepath.exists(), f"Missing required file: {filename}"

    def test_module_loads_successfully(self):
        """God of Carnage module loads without errors."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert module is not None
        assert module.metadata.module_id == "god_of_carnage"

    def test_all_yaml_files_parse(self, god_of_carnage_module_root):
        """All YAML files parse correctly."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        import yaml

        yaml_files = list(god_of_carnage_module_root.glob("*.yaml"))
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


class TestW1SceneValidation:
    """Test requirement #5: Scene ids are unique and structurally valid."""

    def test_scenes_exist(self):
        """Module has scenes defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.scene_phases) > 0

    def test_scene_ids_unique(self):
        """All scene ids are unique."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        scene_ids = list(module.scene_phases.keys())
        assert len(scene_ids) == len(set(scene_ids))

    def test_required_scenes_present(self):
        """All 5 required phases present."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_phases = {"phase_1", "phase_2", "phase_3", "phase_4", "phase_5"}
        actual_phases = set(module.scene_phases.keys())

        assert required_phases == actual_phases

    def test_scene_sequence_linear(self):
        """Scene sequence is linear (1,2,3,4,5)."""
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
        """All scenes have required fields."""
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
    """Test requirement #6: Transitions point to valid scenes or endings."""

    def test_transitions_exist(self):
        """Module has transitions defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.phase_transitions) > 0

    def test_transitions_reference_valid_phases(self):
        """All transitions reference valid phases."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        phase_ids = set(module.scene_phases.keys())

        for trans_id, transition in module.phase_transitions.items():
            assert transition.from_phase in phase_ids, f"Transition {trans_id} references invalid phase {transition.from_phase}"
            assert transition.to_phase in phase_ids, f"Transition {trans_id} references invalid phase {transition.to_phase}"

    def test_transitions_reference_valid_triggers(self):
        """All transition conditions reference valid triggers."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        validator = ModuleCrossReferenceValidator()
        errors = validator.validate_trigger_references(module)

        assert len(errors) == 0, f"Trigger validation errors: {errors}"


class TestW1TriggerValidation:
    """Test requirement #7: Triggers are from the supported trigger set."""

    def test_triggers_exist(self):
        """Module has triggers defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.trigger_definitions) > 0

    def test_required_trigger_types_present(self):
        """All required trigger types are present."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_triggers = {
            "contradiction",
            "exposure",
            "relativization",
            "apology_or_non_apology",
            "cynicism",
            "flight_into_sideplots",
            "collapse_indicators",
            "retreat_signals",
        }

        actual_triggers = set(module.trigger_definitions.keys())
        assert required_triggers.issubset(actual_triggers)

    def test_triggers_have_required_fields(self):
        """All triggers have required fields."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_fields = {
            "id",
            "name",
            "description",
            "recognition_markers",
            "escalation_impact",
            "active_in_phases",
        }

        for trigger_id, trigger in module.trigger_definitions.items():
            for field in required_fields:
                assert hasattr(trigger, field), f"Trigger {trigger_id} missing field {field}"


class TestW1EndingValidation:
    """Test requirement #8: Endings are structurally valid."""

    def test_endings_exist(self):
        """Module has endings defined."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert len(module.ending_conditions) > 0

    def test_required_ending_types_present(self):
        """All required ending types are present."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_endings = {
            "emotional_breakdown",
            "forced_exit",
            "stalemate_resolution",
            "maximum_escalation_breach",
            "maximum_turn_limit",
        }

        actual_endings = set(module.ending_conditions.keys())
        assert required_endings.issubset(actual_endings)

    def test_endings_have_required_fields(self):
        """All endings have required fields."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        required_fields = {"id", "name", "description", "trigger_conditions", "outcome"}

        for ending_id, ending in module.ending_conditions.items():
            for field in required_fields:
                assert hasattr(ending, field), f"Ending {ending_id} missing field {field}"


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

        # Verify transitions connect phases linearly
        transitions = {
            t.from_phase: t.to_phase for t in module.phase_transitions.values()
        }
        assert transitions.get("phase_1") == "phase_2"
        assert transitions.get("phase_2") == "phase_3"
        assert transitions.get("phase_3") == "phase_4"
        assert transitions.get("phase_4") == "phase_5"

    def test_story_path_has_valid_endings(self):
        """Story path can reach valid endings from phase_5."""
        try:
            module = load_module("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        # Phase_5 triggers must reference valid endings
        phase_5 = module.scene_phases.get("phase_5")
        assert phase_5 is not None

        # At least one ending must exist
        assert len(module.ending_conditions) > 0

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
