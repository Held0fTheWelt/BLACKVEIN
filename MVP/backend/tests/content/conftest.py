"""
Fixtures for content module tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def content_modules_root():
    """Path to content/modules directory."""
    return Path(__file__).resolve().parent.parent.parent.parent / "content" / "modules"


@pytest.fixture
def god_of_carnage_module_root(content_modules_root):
    """Path to God of Carnage module."""
    return content_modules_root / "god_of_carnage"


@pytest.fixture
def test_modules_root(tmp_path):
    """Temporary directory for test modules."""
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    return modules_dir


@pytest.fixture
def valid_module_root(test_modules_root):
    """Create a valid test module structure."""
    module_root = test_modules_root / "test_module"
    module_root.mkdir()

    # Create module.yaml
    module_root.joinpath("module.yaml").write_text("""
module_id: test_module
title: Test Module
version: "0.1.0"
contract_version: "0.2.0"
content:
  duration_turns_estimated: "10-15"
  num_characters: 2
files:
  - characters.yaml
  - relationships.yaml
""")

    # Create characters.yaml
    module_root.joinpath("characters.yaml").write_text("""
characters:
  char1:
    id: char1
    name: Character One
    role: protagonist
    baseline_attitude: neutral
  char2:
    id: char2
    name: Character Two
    role: antagonist
    baseline_attitude: hostile
""")

    # Create relationships.yaml
    module_root.joinpath("relationships.yaml").write_text("""
relationship_axes:
  axis_1:
    id: axis_1
    name: Primary Relationship
    description: Main relationship axis
    relationships:
      - char1_char2
    baseline:
      stability: 50
relationships:
  char1_char2:
    id: char1_char2
    type: adversarial
    baseline_stability: 50
""")

    return module_root


@pytest.fixture
def invalid_module_root(test_modules_root):
    """Create an invalid test module (missing fields)."""
    module_root = test_modules_root / "invalid_module"
    module_root.mkdir()

    # Create incomplete module.yaml (missing version)
    module_root.joinpath("module.yaml").write_text("""
module_id: invalid_module
title: Invalid Module
contract_version: "0.2.0"
files: []
""")

    # Create empty characters.yaml
    module_root.joinpath("characters.yaml").write_text("characters: {}")

    return module_root


@pytest.fixture
def malformed_yaml_root(test_modules_root):
    """Create a module with malformed YAML."""
    module_root = test_modules_root / "malformed_module"
    module_root.mkdir()

    # Create malformed module.yaml (bad YAML syntax)
    module_root.joinpath("module.yaml").write_text("""
module_id: malformed
  title: Malformed Module
    version: "0.1.0"
  contract_version: "0.2.0"
""")

    return module_root
