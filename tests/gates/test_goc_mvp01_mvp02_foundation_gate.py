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
    GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS,
    GOD_OF_CARNAGE_RUNTIME_ACTOR_IDS,
    GOD_OF_CARNAGE_RUNTIME_PROFILE_ID,
    GOD_OF_CARNAGE_SOLO_TEMPLATE_ID,
)

_GOC_MODULE_ROOT = Path(__file__).resolve().parent.parent.parent / "content" / "modules" / "god_of_carnage"


def _canonical_module_doc() -> dict:
    module_file = _GOC_MODULE_ROOT / "module.yaml"
    with open(module_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _canonical_characters_doc() -> dict:
    char_file = _GOC_MODULE_ROOT / "characters" / "index.yaml"
    if not char_file.exists():
        char_file = _GOC_MODULE_ROOT / "characters.yaml"
    with open(char_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _canonical_god_of_carnage_title() -> str:
    """Display title from canonical module.yaml (single source of truth; gate wave 01)."""
    return str(_canonical_module_doc()["title"])


def _canonical_character_ids() -> set[str]:
    doc = _canonical_characters_doc()
    characters = doc.get("characters")
    if isinstance(characters, dict):
        return set(characters.keys())
    index = doc.get("characters_index") if isinstance(doc.get("characters_index"), dict) else {}
    documents = index.get("documents") if isinstance(index.get("documents"), dict) else {}
    return set(documents.keys())


def _canonical_player_character_count() -> int:
    return int((_canonical_module_doc().get("content") or {})["num_player_characters"])


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
        assert set(GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS).issubset(role_ids), (
            "Runtime profile must expose every playable human role declared by the profile contract"
        )
        assert len(GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS) == _canonical_player_character_count()
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
        doc = _canonical_module_doc()
        assert doc.get("module_id") == GOD_OF_CARNAGE_CONTENT_MODULE_ID, (
            f"Canonical module_id must be {GOD_OF_CARNAGE_CONTENT_MODULE_ID!r}"
        )
        assert "version" in doc
        assert "content" in doc

    def test_canonical_module_has_runtime_profile_characters(self):
        """Canonical module must define every runtime-profile actor as story truth."""
        char_file = _GOC_MODULE_ROOT / "characters" / "index.yaml"
        assert char_file.exists(), "characters/index.yaml not found in canonical module"
        present = _canonical_character_ids()
        required = set(GOD_OF_CARNAGE_RUNTIME_ACTOR_IDS)
        assert required.issubset(present), f"Missing characters: {required - present}"
        assert len(present) == int((_canonical_module_doc().get("content") or {})["total_characters"])

    def test_canonical_module_playable_humans_are_content_characters(self):
        """Playable human roles must be canonical characters, derived from the runtime profile."""
        characters = _canonical_character_ids()
        playable_humans = set(GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS)
        assert len(playable_humans) == _canonical_player_character_count()
        assert playable_humans.issubset(characters), (
            f"Missing playable human characters: {playable_humans - characters}"
        )

    def test_canonical_module_visitor_is_absent(self):
        """visitor must not be defined as a character in the canonical module."""
        char_file = _GOC_MODULE_ROOT / "characters" / "index.yaml"
        assert char_file.exists(), "characters/index.yaml not found in canonical module"
        characters = _canonical_character_ids()
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
        doc = _canonical_module_doc()
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

        canonical_char_ids = _canonical_character_ids()
        assert FORBIDDEN_RUNTIME_ACTOR_ID not in canonical_char_ids, "visitor must not be a canonical character"
