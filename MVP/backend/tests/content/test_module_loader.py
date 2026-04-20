"""
Tests for module_loader.py (ModuleFileLoader and entry point).
"""

import pytest
import yaml
from pathlib import Path

from app.content.module_loader import (
    ModuleFileLoader,
    ModuleStructureValidator,
    content_modules_root,
    load_module,
)
from app.content.module_exceptions import (
    ModuleLoadError,
    ModuleNotFoundError,
    ModuleFileReadError,
    ModuleParseError,
    ModuleStructureError,
)
from app.content.module_models import ContentModule


class TestModuleFileLoader:
    """Tests for ModuleFileLoader class."""

    def test_load_file_valid_yaml(self, valid_module_root):
        """Load a valid YAML file."""
        loader = ModuleFileLoader()
        module_yaml = valid_module_root / "module.yaml"

        data = loader.load_file(module_yaml)

        assert isinstance(data, dict)
        assert data["module_id"] == "test_module"
        assert data["title"] == "Test Module"

    def test_load_file_nonexistent(self):
        """Loading nonexistent file raises ModuleFileReadError."""
        loader = ModuleFileLoader()

        with pytest.raises(ModuleFileReadError):
            loader.load_file(Path("/nonexistent/file.yaml"))

    def test_load_file_malformed_yaml(self, malformed_yaml_root):
        """Loading malformed YAML raises ModuleParseError."""
        loader = ModuleFileLoader()
        malformed_file = malformed_yaml_root / "module.yaml"

        with pytest.raises(ModuleParseError):
            loader.load_file(malformed_file)

    def test_load_all_module_files_valid(self, valid_module_root):
        """Load all files in a valid module directory."""
        loader = ModuleFileLoader()

        files = loader.load_all_module_files(valid_module_root)

        assert isinstance(files, dict)
        assert "module" in files
        assert "characters" in files
        assert "relationships" in files
        assert files["module"]["module_id"] == "test_module"

    def test_load_all_module_files_nonexistent_dir(self):
        """Loading from nonexistent directory raises ModuleFileReadError."""
        loader = ModuleFileLoader()

        with pytest.raises(ModuleFileReadError):
            loader.load_all_module_files(Path("/nonexistent/dir"))


class TestModuleStructureValidator:
    """Tests for ModuleStructureValidator class."""

    def test_validate_structure_valid(self, valid_module_root):
        """Validate valid module structure."""
        loader = ModuleFileLoader()
        raw_data = loader.load_all_module_files(valid_module_root)

        validator = ModuleStructureValidator()
        module = validator.validate_structure(raw_data)

        assert isinstance(module, ContentModule)
        assert module.metadata.module_id == "test_module"
        assert len(module.characters) == 2

    def test_validate_structure_missing_required_field(self, invalid_module_root):
        """Validate fails when required fields missing."""
        loader = ModuleFileLoader()
        raw_data = loader.load_all_module_files(invalid_module_root)

        validator = ModuleStructureValidator()

        with pytest.raises(ModuleStructureError) as exc_info:
            validator.validate_structure(raw_data)

        # Should contain validation errors
        assert exc_info.value.errors
        assert len(exc_info.value.errors) > 0

    def test_validate_structure_invalid_type(self):
        """Validate fails when field has wrong type."""
        validator = ModuleStructureValidator()
        invalid_data = {
            "module": {
                "module_id": "test",
                "title": "Test",
                "version": "0.1.0",
                "contract_version": "0.2.0",
                "content": {},
                "files": "not_a_list",  # Should be list
            }
        }

        with pytest.raises(ModuleStructureError):
            validator.validate_structure(invalid_data)


class TestLoadModuleEntryPoint:
    """Tests for load_module() entry point."""

    def test_load_module_valid(self, valid_module_root, test_modules_root):
        """Load a valid module by ID."""
        module = load_module("test_module", root_path=test_modules_root)

        assert isinstance(module, ContentModule)
        assert module.metadata.module_id == "test_module"

    def test_load_module_nonexistent(self, test_modules_root):
        """Loading nonexistent module raises ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            load_module("nonexistent_module", root_path=test_modules_root)

    def test_load_module_malformed_yaml(self, malformed_yaml_root, test_modules_root):
        """Loading module with malformed YAML raises ModuleParseError."""
        with pytest.raises(ModuleParseError):
            load_module("malformed_module", root_path=test_modules_root)

    def test_load_module_invalid_structure(self, invalid_module_root, test_modules_root):
        """Loading module with invalid structure raises ModuleStructureError."""
        with pytest.raises(ModuleStructureError):
            load_module("invalid_module", root_path=test_modules_root)

    def test_load_module_default_path(self, god_of_carnage_module_root):
        """Load module using default path (real God of Carnage module)."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        # This should load the real God of Carnage module
        module = load_module("god_of_carnage")

        assert module.metadata.module_id == "god_of_carnage"
        assert len(module.characters) == 4  # Véronique, Michel, Annette, Alain
        assert "phase_1" in module.scene_phases


class TestModuleLoaderIntegration:
    """Integration tests for loader with real module structure."""

    def test_load_god_of_carnage_full(self, god_of_carnage_module_root):
        """Load and validate God of Carnage module."""
        if not god_of_carnage_module_root.exists():
            pytest.skip("God of Carnage module not found")

        loader = ModuleFileLoader()
        files = loader.load_all_module_files(god_of_carnage_module_root)

        # Should have all expected files
        assert "module" in files
        assert "characters" in files
        assert "relationships" in files
        assert "scenes" in files
        assert "transitions" in files
        assert "triggers" in files
        assert "endings" in files
        assert "escalation_axes" in files

        # Structure validation
        validator = ModuleStructureValidator()
        module = validator.validate_structure(files)

        assert module.metadata.module_id == "god_of_carnage"
        assert module.metadata.version == "0.1.0"


def _minimal_metadata() -> dict:
    return {
        "module_id": "cov_extra",
        "title": "Coverage Extra",
        "version": "0.1.0",
        "contract_version": "0.2.0",
        "files": [],
    }


def _axis_dict(aid: str = "ax1") -> dict:
    return {
        "id": aid,
        "name": "Axis",
        "description": "d",
        "relationships": [],
        "baseline": {},
    }


def test_content_modules_root_points_at_repo_content_modules():
    root = content_modules_root()
    assert root.name == "modules"
    assert root.parent.name == "content"


def test_load_file_empty_yaml_returns_empty_dict(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    loader = ModuleFileLoader()
    assert loader.load_file(path) == {}


def test_load_all_module_files_rejects_file_not_directory(tmp_path):
    f = tmp_path / "not_a_dir.yaml"
    f.write_text("k: v\n", encoding="utf-8")
    loader = ModuleFileLoader()
    with pytest.raises(ModuleFileReadError, match="not a directory"):
        loader.load_all_module_files(f)


def test_load_all_module_files_permission_error_on_glob(tmp_path, monkeypatch):
    root = tmp_path / "mod"
    root.mkdir()
    loader = ModuleFileLoader()
    orig_glob = Path.glob
    target = root.resolve()

    def guarded(self, pattern):
        if self.resolve() == target:
            raise PermissionError("simulated")
        return orig_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", guarded)
    with pytest.raises(ModuleFileReadError, match="Failed to read module directory"):
        loader.load_all_module_files(root)


def test_unwrap_escalation_axes_wrapped_yaml(tmp_path):
    mod = tmp_path / "m"
    mod.mkdir()
    inner = {"level_1": {"weight": 1}}
    (mod / "escalation_axes.yaml").write_text(
        yaml.safe_dump({"escalation_axes": inner}),
        encoding="utf-8",
    )
    (mod / "module.yaml").write_text(yaml.safe_dump(_minimal_metadata()), encoding="utf-8")
    loader = ModuleFileLoader()
    raw = loader.load_all_module_files(mod)
    assert raw["escalation_axes"] == inner


def test_validate_structure_maps_trigger_types_alias():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "trigger_types": {
            "t1": {"id": "t1", "name": "T", "description": "d"},
        },
    }
    m = v.validate_structure(raw)
    assert isinstance(m, ContentModule)
    assert "t1" in m.trigger_definitions


def test_validate_structure_maps_ending_types_alias():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "ending_types": {
            "e1": {
                "id": "e1",
                "name": "E",
                "description": "d",
                "outcome": {},
            },
        },
    }
    m = v.validate_structure(raw)
    assert "e1" in m.ending_conditions


def test_validate_structure_relationships_as_list():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "relationships": [_axis_dict("from_list")],
    }
    m = v.validate_structure(raw)
    assert "from_list" in m.relationship_axes


def test_validate_structure_relationships_plain_dict_axes():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "relationships": {"plain_ax": _axis_dict("plain_ax")},
    }
    m = v.validate_structure(raw)
    assert "plain_ax" in m.relationship_axes


def test_validate_structure_escalation_axes_none_normalized():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "escalation_axes": None,
    }
    m = v.validate_structure(raw)
    assert m.escalation_axes == {}


def test_validate_structure_module_structure_error_includes_metadata_module_id():
    v = ModuleStructureValidator()
    raw = {
        "module": {**_minimal_metadata(), "files": "bad_not_list"},
    }
    with pytest.raises(ModuleStructureError) as ei:
        v.validate_structure(raw)
    assert ei.value.module_id == "cov_extra"
    assert ei.value.errors


def test_load_module_accepts_str_root_path(valid_module_root, test_modules_root):
    m = load_module("test_module", root_path=str(test_modules_root))
    assert m.metadata.module_id == "test_module"


def test_unwrap_non_mapped_yaml_file_passthrough(tmp_path):
    mod = tmp_path / "m"
    mod.mkdir()
    payload = {"custom_root": {"x": 1}}
    (mod / "custom.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
    (mod / "module.yaml").write_text(yaml.safe_dump(_minimal_metadata()), encoding="utf-8")
    loader = ModuleFileLoader()
    raw = loader.load_all_module_files(mod)
    assert raw["custom"] == payload


def test_load_file_uses_utf8_encoding(tmp_path):
    path = tmp_path / "u.yaml"
    path.write_text("k: café\n", encoding="utf-8")
    loader = ModuleFileLoader()
    assert loader.load_file(path)["k"] == "café"


def test_load_file_oserror_on_open(tmp_path, monkeypatch):
    path = tmp_path / "x.yaml"
    path.write_text("k: 1\n", encoding="utf-8")
    loader = ModuleFileLoader()

    def boom(*_a, **_k):
        raise OSError("simulated read failure")

    monkeypatch.setattr("builtins.open", boom)
    with pytest.raises(ModuleFileReadError, match="Failed to read YAML file"):
        loader.load_file(path)


def test_load_file_invalid_yaml_syntax(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("k: [\n", encoding="utf-8")
    loader = ModuleFileLoader()
    with pytest.raises(ModuleParseError, match="Failed to parse YAML file"):
        loader.load_file(path)


def test_validate_structure_relationships_skips_non_dict_pair_definitions():
    v = ModuleStructureValidator()
    raw = {
        "module": _minimal_metadata(),
        "relationships": {
            "relationship_axes": {"ax1": _axis_dict("ax1")},
            "relationship_pair_definitions": ["not-a-dict"],
        },
    }
    m = v.validate_structure(raw)
    assert m.relationship_definitions == {}


def test_load_module_module_not_found(tmp_path):
    with pytest.raises(ModuleNotFoundError, match="Module not found"):
        load_module("does_not_exist_ever", root_path=tmp_path)
