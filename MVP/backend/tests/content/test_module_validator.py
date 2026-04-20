"""
Tests for module_validator.py (ModuleCrossReferenceValidator).
"""

import pytest
from app.content.module_loader import load_module
from app.content.module_validator import (
    ModuleCrossReferenceValidator,
    ValidationResult,
)
from app.content.module_models import ContentModule, ModuleMetadata


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Create a ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            module_id="test_module",
            errors=[],
            warnings=["warning1"],
            validation_time_ms=10.5,
        )

        assert result.is_valid is True
        assert result.module_id == "test_module"
        assert result.warnings == ["warning1"]
        assert result.validation_time_ms == 10.5

    def test_validation_result_with_errors(self):
        """Create ValidationResult with errors."""
        result = ValidationResult(
            is_valid=False,
            module_id="bad_module",
            errors=["error1", "error2"],
            warnings=[],
            validation_time_ms=5.0,
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "error1" in result.errors


class TestModuleCrossReferenceValidator:
    """Tests for ModuleCrossReferenceValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ModuleCrossReferenceValidator()

    @pytest.fixture
    def god_of_carnage_module(self, content_modules_root, god_of_carnage_module_root):
        """Load God of Carnage module for testing."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")
        return load_module("god_of_carnage", root_path=content_modules_root)

    def test_validate_character_references_valid(self, validator, god_of_carnage_module):
        """Validate character references in valid module."""
        errors = validator.validate_character_references(god_of_carnage_module)

        assert isinstance(errors, list)
        assert len(errors) == 0  # No errors in valid module

    def test_validate_relationship_references_valid(
        self, validator, god_of_carnage_module
    ):
        """Validate relationship references in valid module."""
        errors = validator.validate_relationship_references(god_of_carnage_module)

        assert isinstance(errors, list)
        assert len(errors) == 0  # No errors in valid module

    def test_validate_trigger_references_valid(self, validator, god_of_carnage_module):
        """Validate trigger references in valid module."""
        errors = validator.validate_trigger_references(god_of_carnage_module)

        assert isinstance(errors, list)
        assert len(errors) == 0  # No errors in valid module

    def test_validate_phase_sequence_valid(self, validator, god_of_carnage_module):
        """Validate phase sequence in valid module."""
        errors = validator.validate_phase_sequence(god_of_carnage_module)

        assert isinstance(errors, list)
        assert len(errors) == 0  # No errors in valid module

    def test_validate_constraints_valid(self, validator, god_of_carnage_module):
        """Validate constraints in valid module."""
        errors = validator.validate_constraints(god_of_carnage_module)

        assert isinstance(errors, list)
        assert len(errors) == 0  # No errors in valid module

    def test_validate_all_valid(self, validator, god_of_carnage_module):
        """Validate all checks on valid module."""
        result = validator.validate_all(god_of_carnage_module)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.module_id == "god_of_carnage"
        assert len(result.errors) == 0
        assert result.validation_time_ms >= 0

    def test_validate_all_returns_validation_result(
        self, validator, god_of_carnage_module
    ):
        """validate_all returns ValidationResult dataclass."""
        result = validator.validate_all(god_of_carnage_module)

        assert hasattr(result, "is_valid")
        assert hasattr(result, "module_id")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "validation_time_ms")


class TestModuleValidatorErrorDetection:
    """Tests for validator error detection capabilities."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ModuleCrossReferenceValidator()

    def test_detect_undefined_character_reference(self, validator, valid_module_root):
        """Detect when trigger references undefined character."""
        # Placeholder: actual error detection tested via God of Carnage module integrity

    def test_detect_undefined_trigger_reference(self, validator):
        """Detect when phase references undefined trigger."""
        # Placeholder: actual error detection tested via God of Carnage module integrity
        pass

    def test_detect_phase_sequence_gaps(self, validator):
        """Detect gaps in phase sequence."""
        # Placeholder: actual error detection tested via God of Carnage module integrity
        pass


class TestModuleValidatorGodOfCarnage:
    """Integration tests for validator with God of Carnage module."""

    @pytest.fixture
    def god_of_carnage_module(self, content_modules_root, god_of_carnage_module_root):
        """Load God of Carnage module."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")
        return load_module("god_of_carnage", root_path=content_modules_root)

    def test_god_of_carnage_full_validation(self, god_of_carnage_module):
        """Run full validation on God of Carnage module."""
        validator = ModuleCrossReferenceValidator()
        result = validator.validate_all(god_of_carnage_module)

        assert result.is_valid is True
        assert result.module_id == "god_of_carnage"
        assert len(result.errors) == 0

    def test_god_of_carnage_has_all_characters(self, god_of_carnage_module):
        """Verify God of Carnage has expected characters."""
        assert "veronique" in god_of_carnage_module.characters
        assert "michel" in god_of_carnage_module.characters
        assert "annette" in god_of_carnage_module.characters
        assert "alain" in god_of_carnage_module.characters

    def test_god_of_carnage_has_all_phases(self, god_of_carnage_module):
        """Verify God of Carnage has all 5 phases."""
        assert "phase_1" in god_of_carnage_module.scene_phases
        assert "phase_2" in god_of_carnage_module.scene_phases
        assert "phase_3" in god_of_carnage_module.scene_phases
        assert "phase_4" in god_of_carnage_module.scene_phases
        assert "phase_5" in god_of_carnage_module.scene_phases

    def test_god_of_carnage_phase_sequence_correct(self, god_of_carnage_module):
        """Verify God of Carnage phases have correct sequence."""
        phases = god_of_carnage_module.scene_phases
        assert phases["phase_1"].sequence == 1
        assert phases["phase_2"].sequence == 2
        assert phases["phase_3"].sequence == 3
        assert phases["phase_4"].sequence == 4
        assert phases["phase_5"].sequence == 5

    def test_god_of_carnage_has_triggers(self, god_of_carnage_module):
        """Verify God of Carnage has expected trigger types."""
        expected_triggers = {
            "contradiction",
            "exposure",
            "relativization",
            "apology_or_non_apology",
            "cynicism",
            "flight_into_sideplots",
            "collapse_indicators",
            "retreat_signals",
        }
        actual_triggers = set(god_of_carnage_module.trigger_definitions.keys())
        assert expected_triggers.issubset(actual_triggers)

    def test_god_of_carnage_has_endings(self, god_of_carnage_module):
        """Verify God of Carnage has expected ending types."""
        expected_endings = {
            "emotional_breakdown",
            "forced_exit",
            "stalemate_resolution",
            "maximum_escalation_breach",
            "maximum_turn_limit",
        }
        actual_endings = set(god_of_carnage_module.ending_conditions.keys())
        assert expected_endings.issubset(actual_endings)


class TestModuleValidatorSyntheticErrors:
    """Synthetic ContentModule fixtures for validator edge branches."""

    @pytest.fixture
    def validator(self):
        return ModuleCrossReferenceValidator()

    @staticmethod
    def _meta(module_id: str = "synthetic") -> ModuleMetadata:
        return ModuleMetadata(
            module_id=module_id,
            title="Synthetic",
            version="1.0.0",
            contract_version="1",
        )

    def test_trigger_character_vulnerability_unknown_character(self, validator):
        from app.content.module_models import (
            CharacterDefinition,
            ContentModule,
            TriggerDefinition,
        )

        mod = ContentModule(
            metadata=self._meta(),
            characters={
                "alice": CharacterDefinition(
                    id="alice",
                    name="Alice",
                    role="r",
                    baseline_attitude="calm",
                )
            },
            trigger_definitions={
                "t1": TriggerDefinition(
                    id="t1",
                    name="T",
                    description="D",
                    character_vulnerability={"ghost": 1},
                )
            },
        )
        err = validator.validate_character_references(mod)
        assert any("ghost" in e for e in err)

    def test_relationship_axis_unknown_relationship_id(self, validator):
        from app.content.module_models import ContentModule, RelationshipAxis

        mod = ContentModule(
            metadata=self._meta(),
            relationship_axes={
                "ax1": RelationshipAxis(
                    id="ax1",
                    name="Axis",
                    description="Desc",
                    relationships=["no_such_rel"],
                    baseline={},
                )
            },
        )
        err = validator.validate_relationship_references(mod)
        assert any("no_such_rel" in e for e in err)

    def test_phase_active_trigger_unknown(self, validator):
        from app.content.module_models import ContentModule, ScenePhase

        mod = ContentModule(
            metadata=self._meta(),
            scene_phases={
                "p1": ScenePhase(
                    id="p1",
                    name="P1",
                    sequence=1,
                    description="d",
                    active_triggers=["missing_trigger"],
                )
            },
        )
        err = validator.validate_trigger_references(mod)
        assert any("missing_trigger" in e for e in err)

    def test_phase_sequence_gap_and_bad_transition_and_cycle(self, validator):
        from app.content.module_models import ContentModule, PhaseTransition, ScenePhase

        mod = ContentModule(
            metadata=self._meta(),
            scene_phases={
                "p1": ScenePhase(
                    id="p1", name="A", sequence=1, description="d"
                ),
                "p3": ScenePhase(
                    id="p3", name="C", sequence=3, description="d"
                ),
            },
            phase_transitions={
                "bad": PhaseTransition(from_phase="ghost", to_phase="p1"),
                "c1": PhaseTransition(from_phase="p1", to_phase="p3"),
                "c2": PhaseTransition(from_phase="p3", to_phase="p1"),
            },
        )
        err = validator.validate_phase_sequence(mod)
        assert any("sequence" in e.lower() for e in err)
        assert any("ghost" in e for e in err)
        assert any("cycle" in e.lower() for e in err)

    def test_constraints_empty_fields_and_negative_baseline(self, validator):
        from app.content.module_models import (
            CharacterDefinition,
            ContentModule,
            EndingCondition,
            RelationshipAxis,
            ScenePhase,
            TriggerDefinition,
        )

        mod = ContentModule(
            metadata=self._meta(),
            characters={
                "c1": CharacterDefinition.model_construct(
                    id="c1",
                    name="N",
                    role="",
                    baseline_attitude="",
                )
            },
            relationship_axes={
                "ax": RelationshipAxis.model_construct(
                    id="ax",
                    name="",
                    description="",
                    relationships=[],
                    baseline=-5,
                )
            },
            scene_phases={
                "p1": ScenePhase.model_construct(
                    id="p1",
                    name="",
                    sequence=1,
                    description="d",
                )
            },
            trigger_definitions={
                "tr": TriggerDefinition.model_construct(
                    id="tr",
                    name="",
                    description="",
                )
            },
            ending_conditions={
                "e1": EndingCondition.model_construct(
                    id="e1",
                    name="",
                    description="",
                    outcome={},
                )
            },
        )
        err = validator.validate_constraints(mod)
        msgs = " ".join(err).lower()
        assert "baseline_attitude" in msgs or "empty role" in msgs
        assert "axis" in msgs
        assert "trigger" in msgs
        assert "ending" in msgs
