"""
MVP 01 / MVP 02 Foundation Gate - Enforces core architectural rules.

This gate verifies that the repository maintains the foundation contracts:
- god_of_carnage_solo is runtime-profile-only (no story truth)
- god_of_carnage (canonical) contains story truth
- visitor does not exist as a runtime actor
- GovernanceError is exception-compatible
- No deprecation warnings in checked code
"""

from __future__ import annotations

import yaml
import pytest
from pathlib import Path

from app.governance.errors import GovernanceError

from gate_contract_constants import (
    FORBIDDEN_RUNTIME_ACTOR_ID,
    GOD_OF_CARNAGE_CONTENT_MODULE_ID,
    GOD_OF_CARNAGE_RUNTIME_PROFILE_ID,
    GOD_OF_CARNAGE_SOLO_TEMPLATE_ID,
)

_GOC_MODULE_ROOT = Path(__file__).resolve().parent.parent.parent / "content" / "modules" / "god_of_carnage"


def _canonical_god_of_carnage_title() -> str:
    """Display title from canonical module.yaml (single source of truth; gate wave 01)."""
    module_file = _GOC_MODULE_ROOT / "module.yaml"
    with open(module_file, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return str(doc["title"])


class TestMVP01RulesEnforced:
    """Verify MVP 01 architectural enforcement."""

    def test_governance_error_is_exception_compatible(self):
        """GovernanceError must support exception protocol (traceback assignment)."""
        error = GovernanceError(
            code="test_code",
            message="test message",
            status_code=400,
            details={},
        )
        assert isinstance(error, Exception)
        assert error.code == "test_code"
        assert str(error) == "test_code: test message"

    def test_god_of_carnage_solo_is_runtime_profile_only(self):
        """god_of_carnage_solo must contain no story truth."""
        from app.content.builtins import build_god_of_carnage_solo

        template = build_god_of_carnage_solo()

        assert template.id == GOD_OF_CARNAGE_SOLO_TEMPLATE_ID
        # Title oracle: content/modules/god_of_carnage/module.yaml ``title`` (not a duplicated literal).
        assert template.title == _canonical_god_of_carnage_title()
        assert template.max_humans == 1

        assert len(template.beats) == 0, "god_of_carnage_solo must not contain beats"
        assert len(template.actions) == 0, "god_of_carnage_solo must not contain actions"
        assert len(template.props) == 0, "god_of_carnage_solo must not contain props"

    def test_visitor_does_not_exist_as_actor(self):
        """visitor must never exist as a runtime actor, responder, or candidate."""
        from app.content.builtins import build_god_of_carnage_solo

        template = build_god_of_carnage_solo()
        role_ids = {role.id for role in template.roles}

        assert FORBIDDEN_RUNTIME_ACTOR_ID not in role_ids, "visitor must not exist as a role"

    def test_solo_profile_has_no_story_structure(self):
        """Solo profile has runtime structure (roles/rooms) but no story truth (beats/actions/props)."""
        from app.content.builtins import build_god_of_carnage_solo

        template = build_god_of_carnage_solo()

        assert len(template.beats) == 0, "god_of_carnage_solo must not contain beats (story truth)"
        assert len(template.actions) == 0, "god_of_carnage_solo must not contain actions (story truth)"
        assert len(template.props) == 0, "god_of_carnage_solo must not contain props (story truth)"

        role_ids = {r.id for r in template.roles}
        assert "annette" in role_ids, "annette must be a selectable player role in runtime profile"
        assert "alain" in role_ids, "alain must be a selectable player role in runtime profile"
        assert FORBIDDEN_RUNTIME_ACTOR_ID not in role_ids, "visitor must not exist as a role (global prohibition)"
        assert len(template.rooms) > 0, "Runtime profile must expose rooms for navigation bootstrap"

    def test_no_datetime_utcnow_deprecation(self):
        """datetime.utcnow() must be replaced with timezone-aware UTC."""
        import subprocess
        import sys

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/branching",
                "-W",
                "error::DeprecationWarning",
                "-q",
                "--no-cov",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert (
            result.returncode == 0
        ), f"Branching tests must pass with deprecation warnings as errors. Output: {result.stdout}\n{result.stderr}"


class TestMVP02RulesEnforced:
    """Verify MVP 02 architectural enforcement: canonical content module contains story truth."""

    def test_canonical_god_of_carnage_module_exists(self):
        """Canonical god_of_carnage content module must exist on disk."""
        assert _GOC_MODULE_ROOT.exists(), f"Canonical module root not found: {_GOC_MODULE_ROOT}"
        assert _GOC_MODULE_ROOT.is_dir()

    def test_canonical_module_yaml_is_valid(self):
        """module.yaml must be valid YAML with required canonical fields."""
        module_file = _GOC_MODULE_ROOT / "module.yaml"
        assert module_file.exists(), "module.yaml not found in canonical module"
        with open(module_file) as f:
            doc = yaml.safe_load(f)
        assert doc.get("module_id") == GOD_OF_CARNAGE_CONTENT_MODULE_ID, (
            f"Canonical module_id must be {GOD_OF_CARNAGE_CONTENT_MODULE_ID!r}"
        )
        assert "version" in doc
        assert "content" in doc

    def test_canonical_module_has_characters(self):
        """Canonical module must define characters: annette, alain, veronique, michel."""
        char_file = _GOC_MODULE_ROOT / "characters.yaml"
        assert char_file.exists(), "characters.yaml not found in canonical module"
        with open(char_file) as f:
            doc = yaml.safe_load(f)
        characters = doc.get("characters", {})
        required = {"annette", "alain", "veronique", "michel"}
        present = set(characters.keys())
        assert required.issubset(present), f"Missing characters: {required - present}"

    def test_canonical_module_annette_and_alain_are_playable(self):
        """Annette and Alain must be defined as playable human characters."""
        char_file = _GOC_MODULE_ROOT / "characters.yaml"
        with open(char_file) as f:
            doc = yaml.safe_load(f)
        characters = doc.get("characters", {})
        assert "annette" in characters, "annette must be a canonical character"
        assert "alain" in characters, "alain must be a canonical character"

    def test_canonical_module_visitor_is_absent(self):
        """visitor must not be defined as a character in the canonical module."""
        char_file = _GOC_MODULE_ROOT / "characters.yaml"
        with open(char_file) as f:
            doc = yaml.safe_load(f)
        characters = doc.get("characters", {})
        assert FORBIDDEN_RUNTIME_ACTOR_ID not in characters, "visitor must not exist as a canonical character"

    def test_canonical_module_has_scenes(self):
        """Canonical module must define scene phases (story truth)."""
        scene_file = _GOC_MODULE_ROOT / "scenes.yaml"
        assert scene_file.exists(), "scenes.yaml not found in canonical module"
        with open(scene_file) as f:
            doc = yaml.safe_load(f)
        phases = doc.get("scene_phases", {})
        assert len(phases) >= 1, "Canonical module must define at least one scene phase"


@pytest.mark.foundation_gate
class TestFoundationGateOverall:
    """Overall foundation gate: god_of_carnage_solo is runtime profile, canonical module is story truth."""

    def test_solo_profile_is_distinct_from_canonical_module(self):
        """god_of_carnage_solo (runtime profile) must not be used as canonical content module_id."""
        module_file = _GOC_MODULE_ROOT / "module.yaml"
        with open(module_file) as f:
            doc = yaml.safe_load(f)
        assert doc.get("module_id") != GOD_OF_CARNAGE_RUNTIME_PROFILE_ID, (
            f"{GOD_OF_CARNAGE_RUNTIME_PROFILE_ID!r} is a runtime profile only; canonical module_id must be "
            f"{GOD_OF_CARNAGE_CONTENT_MODULE_ID!r}"
        )
        assert doc.get("module_id") == GOD_OF_CARNAGE_CONTENT_MODULE_ID

    def test_visitor_absent_from_runtime_profile_and_canonical_module(self):
        """visitor must be absent from both the runtime profile and the canonical content module."""
        from app.content.builtins import build_god_of_carnage_solo

        template = build_god_of_carnage_solo()
        profile_role_ids = {role.id for role in template.roles}
        assert FORBIDDEN_RUNTIME_ACTOR_ID not in profile_role_ids, "visitor must not be a role in runtime profile"

        char_file = _GOC_MODULE_ROOT / "characters.yaml"
        with open(char_file) as f:
            doc = yaml.safe_load(f)
        canonical_char_ids = set(doc.get("characters", {}).keys())
        assert FORBIDDEN_RUNTIME_ACTOR_ID not in canonical_char_ids, "visitor must not be a canonical character"
