"""Fixtures for runtime tests."""

import os
import pytest
from pathlib import Path

from app.content.module_loader import load_module
from app.runtime.session_start import start_session
from app.runtime.w2_models import SessionState


@pytest.fixture
def content_modules_root():
    """Path to content/modules directory at project root."""
    # Find project root (parent of backend)
    backend_dir = Path(__file__).parent.parent.parent
    project_root = backend_dir.parent
    return project_root / "content" / "modules"


@pytest.fixture
def god_of_carnage_module_root(content_modules_root):
    """Path to god_of_carnage module directory."""
    return content_modules_root / "god_of_carnage"


@pytest.fixture
def god_of_carnage_module(god_of_carnage_module_root):
    """Load the god_of_carnage ContentModule."""
    # Pass the module directory itself
    return load_module("god_of_carnage", root_path=god_of_carnage_module_root)


@pytest.fixture
def god_of_carnage_module_with_state(god_of_carnage_module_root):
    """Start a session with god_of_carnage module and return initialized SessionState."""
    # start_session will pass root_path to load_module, which expects the module directory
    result = start_session("god_of_carnage", root_path=god_of_carnage_module_root)
    return result.session


@pytest.fixture
def test_modules_root(tmp_path):
    """Temporary directory for test modules."""
    return tmp_path / "test_modules"


@pytest.fixture
def valid_module_root(test_modules_root):
    """Create a valid test module structure."""
    module_root = test_modules_root / "test_valid_module"
    module_root.mkdir(parents=True, exist_ok=True)

    # Create minimal valid module files
    module_yaml = module_root / "module.yaml"
    module_yaml.write_text(
        """module_id: test_valid_module
title: Test Valid Module
version: 0.1.0
contract_version: 1.0.0
"""
    )

    return module_root
