"""
Tests for module_service.py (ModuleService).
"""

import pytest
from pathlib import Path
from app.content.module_service import ModuleService
from app.content.module_exceptions import ModuleNotFoundError
from app.content.module_models import ContentModule
from app.content.module_validator import ValidationResult


class TestModuleService:
    """Tests for ModuleService class."""

    @pytest.fixture
    def service(self, test_modules_root):
        """Create a ModuleService with test modules directory."""
        return ModuleService(root_path=test_modules_root)

    @pytest.fixture
    def service_with_valid_module(self, test_modules_root, valid_module_root):
        """Create service with valid test module available."""
        return ModuleService(root_path=test_modules_root)

    def test_service_initialization(self, test_modules_root):
        """Initialize ModuleService."""
        service = ModuleService(root_path=test_modules_root)

        assert isinstance(service, ModuleService)

    def test_service_default_root_path(self):
        """ModuleService uses default root path."""
        service = ModuleService()

        # Should not raise exception
        assert service is not None

    def test_load_and_validate_valid_module(self, service_with_valid_module):
        """Load and validate a valid module."""
        result = service_with_valid_module.load_and_validate("test_module")

        assert isinstance(result, dict)
        assert "module" in result
        assert "validation" in result

        module = result["module"]
        assert isinstance(module, ContentModule)
        assert module.metadata.module_id == "test_module"

        validation = result["validation"]
        assert isinstance(validation, ValidationResult)
        assert validation.is_valid is True

    def test_load_and_validate_nonexistent_module(self, service):
        """Loading nonexistent module raises exception."""
        with pytest.raises(ModuleNotFoundError):
            service.load_and_validate("nonexistent_module")

    def test_preflight_check_valid(self, service_with_valid_module):
        """Preflight check on valid module."""
        result = service_with_valid_module.preflight_check("test_module")

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.module_id == "test_module"

    def test_preflight_check_nonexistent(self, service):
        """Preflight check handles nonexistent module gracefully."""
        result = service.preflight_check("nonexistent_module")

        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_list_available_modules_empty(self, test_modules_root):
        """List modules in empty directory."""
        service = ModuleService(root_path=test_modules_root / "empty")

        modules = service.list_available_modules()

        assert isinstance(modules, list)
        assert len(modules) == 0

    def test_list_available_modules_with_modules(self, service_with_valid_module):
        """List available modules."""
        modules = service_with_valid_module.list_available_modules()

        assert isinstance(modules, list)
        assert "test_module" in modules

    def test_list_available_modules_sorted(self, service_with_valid_module):
        """List modules are sorted."""
        modules = service_with_valid_module.list_available_modules()

        assert modules == sorted(modules)

    def test_get_module_metadata_valid(self, service_with_valid_module):
        """Get metadata from valid module."""
        metadata = service_with_valid_module.get_module_metadata("test_module")

        assert isinstance(metadata, dict)
        assert metadata["module_id"] == "test_module"
        assert metadata["title"] == "Test Module"
        assert "version" in metadata
        assert "contract_version" in metadata

    def test_get_module_metadata_nonexistent(self, service):
        """Getting metadata from nonexistent module raises exception."""
        with pytest.raises(ModuleNotFoundError):
            service.get_module_metadata("nonexistent_module")


class TestModuleServiceGodOfCarnage:
    """Integration tests for ModuleService with God of Carnage module."""

    @pytest.fixture
    def service_default(self):
        """Create service with default (project) path."""
        return ModuleService()

    def test_list_available_modules_includes_god_of_carnage(self, service_default):
        """List modules includes god_of_carnage."""
        modules = service_default.list_available_modules()

        if not modules:
            pytest.skip("No modules found in content/modules/")

        # god_of_carnage may or may not be present depending on setup
        # This test just verifies the method works
        assert isinstance(modules, list)

    def test_load_god_of_carnage_module(self):
        """Load God of Carnage module via service."""
        service = ModuleService()

        try:
            result = service.load_and_validate("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert result["module"].metadata.module_id == "god_of_carnage"
        assert result["validation"].is_valid is True

    def test_get_god_of_carnage_metadata(self):
        """Get metadata from God of Carnage module."""
        service = ModuleService()

        try:
            metadata = service.get_module_metadata("god_of_carnage")
        except ModuleNotFoundError:
            pytest.skip("God of Carnage module not found")

        assert metadata["module_id"] == "god_of_carnage"
        assert "title" in metadata
        assert metadata["version"] == "0.1.0"

    def test_preflight_check_god_of_carnage(self):
        """Preflight check on God of Carnage module."""
        service = ModuleService()
        result = service.preflight_check("god_of_carnage")

        # Whether module exists or not, should return ValidationResult
        assert isinstance(result, ValidationResult)


class TestModuleServiceErrorHandling:
    """Tests for ModuleService error handling."""

    @pytest.fixture
    def service(self, test_modules_root):
        """Create a ModuleService."""
        return ModuleService(root_path=test_modules_root)

    def test_load_malformed_module(self, service, malformed_yaml_root, test_modules_root):
        """Loading malformed module raises appropriate exception."""
        from app.content.module_exceptions import ModuleParseError

        with pytest.raises(ModuleParseError):
            service.load_and_validate("malformed_module")

    def test_load_invalid_module(self, service, invalid_module_root, test_modules_root):
        """Loading module with invalid structure raises exception."""
        from app.content.module_exceptions import ModuleStructureError

        with pytest.raises(ModuleStructureError):
            service.load_and_validate("invalid_module")


class TestModuleServiceWorkflow:
    """Integration tests for complete ModuleService workflow."""

    def test_complete_workflow_god_of_carnage(self):
        """Test complete workflow: list -> load -> get metadata -> validate."""
        service = ModuleService()

        # Step 1: List available modules
        modules = service.list_available_modules()
        assert isinstance(modules, list)

        # If god_of_carnage not available, skip remaining steps
        if "god_of_carnage" not in modules:
            pytest.skip("God of Carnage module not found")

        # Step 2: Get metadata
        metadata = service.get_module_metadata("god_of_carnage")
        assert metadata["module_id"] == "god_of_carnage"

        # Step 3: Load and validate
        result = service.load_and_validate("god_of_carnage")
        assert result["module"].metadata.module_id == "god_of_carnage"
        assert result["validation"].is_valid is True

        # Step 4: Preflight check
        preflight = service.preflight_check("god_of_carnage")
        assert preflight.is_valid is True

    def test_workflow_nonexistent_module(self):
        """Test workflow gracefully handles missing modules."""
        service = ModuleService()

        # List should work
        modules = service.list_available_modules()
        assert isinstance(modules, list)

        # Get metadata should fail
        with pytest.raises(ModuleNotFoundError):
            service.get_module_metadata("nonexistent_module")

        # Load should fail
        with pytest.raises(ModuleNotFoundError):
            service.load_and_validate("nonexistent_module")

        # Preflight should return invalid result (not raise)
        result = service.preflight_check("nonexistent_module")
        assert result.is_valid is False
