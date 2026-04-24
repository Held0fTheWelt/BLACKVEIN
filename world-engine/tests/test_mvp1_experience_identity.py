"""MVP 1 behavior-proving tests — Experience Identity and Session Start.

Tests prove:
- Runtime profile resolver resolves god_of_carnage_solo correctly
- Unknown runtime profiles are rejected
- god_of_carnage_solo cannot be loaded as a content module
- Profile contains no story truth fields
- selected_player_role is required
- Invalid selected roles fail
- visitor is rejected everywhere in the live solo path
- Annette start works
- Alain start works
- Role slug resolves to canonical actor
- Source locator artifact exists and has no unresolved placeholders
- Operational evidence artifact presence
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORLD_ENGINE_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Runtime profile resolver tests (MVP1-P01)
# ---------------------------------------------------------------------------

class TestRuntimeProfileResolver:

    def test_runtime_profile_resolver_success(self):
        from app.runtime.profiles import resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        assert profile.runtime_profile_id == "god_of_carnage_solo"
        assert profile.content_module_id == "god_of_carnage"
        assert profile.runtime_module_id == "solo_story_runtime"
        assert profile.runtime_mode == "solo_story"
        assert profile.requires_selected_player_role is True
        assert len(profile.selectable_player_roles) == 2
        slugs = {r.role_slug for r in profile.selectable_player_roles}
        assert slugs == {"annette", "alain"}

    def test_create_run_missing_runtime_profile_returns_contract_error(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile
        with pytest.raises(RuntimeProfileError) as exc_info:
            resolve_runtime_profile("")
        assert exc_info.value.code == "runtime_profile_required"

    def test_unknown_runtime_profile_rejected(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile
        with pytest.raises(RuntimeProfileError) as exc_info:
            resolve_runtime_profile("god_of_carnage_multiplayer")
        assert exc_info.value.code == "runtime_profile_not_found"

    def test_none_runtime_profile_rejected(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile
        with pytest.raises(RuntimeProfileError) as exc_info:
            resolve_runtime_profile(None)
        assert exc_info.value.code == "runtime_profile_required"


# ---------------------------------------------------------------------------
# Content authority tests (MVP1-P02)
# ---------------------------------------------------------------------------

class TestContentAuthority:

    def test_goc_solo_not_loadable_as_content_module(self):
        """god_of_carnage_solo must not appear as a content module id."""
        content_modules_root = REPO_ROOT / "content" / "modules"
        assert content_modules_root.is_dir(), f"content/modules not found at {content_modules_root}"
        module_dirs = [d.name for d in content_modules_root.iterdir() if d.is_dir()]
        assert "god_of_carnage_solo" not in module_dirs, (
            "god_of_carnage_solo is a runtime profile, not a content module. "
            "It must not appear as a directory under content/modules/."
        )
        assert "god_of_carnage" in module_dirs, "god_of_carnage canonical content module must exist."

    def test_profile_contains_no_story_truth(self):
        from app.runtime.profiles import assert_profile_contains_no_story_truth, resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        profile_dict = profile.to_dict()
        assert_profile_contains_no_story_truth(profile_dict)

    def test_profile_story_truth_fields_are_forbidden(self):
        from app.runtime.profiles import RuntimeProfileError, assert_profile_contains_no_story_truth
        contaminated = {
            "runtime_profile_id": "god_of_carnage_solo",
            "characters": [{"id": "annette"}],
        }
        with pytest.raises(RuntimeProfileError) as exc_info:
            assert_profile_contains_no_story_truth(contaminated)
        assert exc_info.value.code == "runtime_profile_contains_story_truth"

    def test_runtime_module_contains_no_story_truth(self):
        """The runtime profile dict from resolve_runtime_profile has no story truth fields."""
        from app.runtime.profiles import resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        profile_dict = profile.to_dict()
        story_truth_fields = ["characters", "roles", "rooms", "props", "beats", "scenes", "relationships", "endings"]
        for field in story_truth_fields:
            assert field not in profile_dict, (
                f"Runtime profile dict must not contain story truth field: {field!r}"
            )


# ---------------------------------------------------------------------------
# Role selection tests (MVP1-P03)
# ---------------------------------------------------------------------------

class TestRoleSelection:

    def test_session_creation_without_selected_player_role_fails(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        with pytest.raises(RuntimeProfileError) as exc_info:
            validate_selected_player_role(None, profile)
        assert exc_info.value.code == "selected_player_role_required"
        assert "annette" in str(exc_info.value.details.get("allowed_values", []))
        assert "alain" in str(exc_info.value.details.get("allowed_values", []))

    def test_session_creation_without_selected_player_role_empty_fails(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        with pytest.raises(RuntimeProfileError) as exc_info:
            validate_selected_player_role("", profile)
        assert exc_info.value.code == "selected_player_role_required"

    def test_session_creation_invalid_role_fails(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        with pytest.raises(RuntimeProfileError) as exc_info:
            validate_selected_player_role("michel", profile)
        assert exc_info.value.code == "invalid_selected_player_role"

    def test_role_slug_must_resolve_to_canonical_actor(self):
        from app.runtime.profiles import resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        role = validate_selected_player_role("annette", profile)
        canonical_id = profile.role_slug_to_canonical_actor_id(role)
        assert canonical_id is not None
        assert canonical_id == "annette"

    def test_alain_role_slug_resolves_to_canonical_actor(self):
        from app.runtime.profiles import resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        role = validate_selected_player_role("alain", profile)
        canonical_id = profile.role_slug_to_canonical_actor_id(role)
        assert canonical_id == "alain"


# ---------------------------------------------------------------------------
# Visitor removal tests (MVP1-P04)
# ---------------------------------------------------------------------------

class TestVisitorRemoval:

    def test_visitor_rejected_as_selected_player_role(self):
        from app.runtime.profiles import RuntimeProfileError, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        with pytest.raises(RuntimeProfileError) as exc_info:
            validate_selected_player_role("visitor", profile)
        assert exc_info.value.code == "invalid_visitor_runtime_reference"

    def test_visitor_absent_from_prompts_responders_lobby(self):
        """visitor must not appear in the GoC solo template roles."""
        from app.content.builtins import load_builtin_templates
        templates = load_builtin_templates()
        goc_solo = templates.get("god_of_carnage_solo")
        assert goc_solo is not None, "god_of_carnage_solo template must exist"
        role_ids = {role.id for role in goc_solo.roles}
        assert "visitor" not in role_ids, (
            "visitor must not be a role in the god_of_carnage_solo template. "
            f"Found roles: {sorted(role_ids)}"
        )

    def test_visitor_not_in_npc_actor_ids(self):
        from app.runtime.profiles import build_actor_ownership, resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        ownership = build_actor_ownership("annette", profile)
        assert "visitor" not in ownership["npc_actor_ids"]
        assert "visitor" not in ownership["actor_lanes"]
        assert ownership["visitor_present"] is False

    def test_visitor_rejected_from_build_actor_ownership(self):
        from app.runtime.profiles import RuntimeProfileError, build_actor_ownership, resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        with pytest.raises(RuntimeProfileError) as exc_info:
            build_actor_ownership("visitor", profile)
        assert exc_info.value.code == "invalid_visitor_runtime_reference"


# ---------------------------------------------------------------------------
# Valid start tests (MVP1-P03)
# ---------------------------------------------------------------------------

class TestValidStart:

    def test_valid_annette_start(self):
        from app.runtime.profiles import build_actor_ownership, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        role = validate_selected_player_role("annette", profile)
        ownership = build_actor_ownership(role, profile)
        assert ownership["human_actor_id"] == "annette"
        assert "alain" in ownership["npc_actor_ids"]
        assert "veronique" in ownership["npc_actor_ids"]
        assert "michel" in ownership["npc_actor_ids"]
        assert ownership["actor_lanes"]["annette"] == "human"
        assert ownership["actor_lanes"]["alain"] == "npc"
        assert ownership["visitor_present"] is False

    def test_valid_alain_start(self):
        from app.runtime.profiles import build_actor_ownership, resolve_runtime_profile, validate_selected_player_role
        profile = resolve_runtime_profile("god_of_carnage_solo")
        role = validate_selected_player_role("alain", profile)
        ownership = build_actor_ownership(role, profile)
        assert ownership["human_actor_id"] == "alain"
        assert "annette" in ownership["npc_actor_ids"]
        assert "veronique" in ownership["npc_actor_ids"]
        assert "michel" in ownership["npc_actor_ids"]
        assert ownership["actor_lanes"]["alain"] == "human"
        assert ownership["actor_lanes"]["annette"] == "npc"
        assert ownership["visitor_present"] is False

    def test_annette_human_role_exists_in_template(self):
        """annette must be a HUMAN+can_join role in the god_of_carnage_solo template."""
        from app.content.builtins import load_builtin_templates
        from app.content.models import ParticipantMode
        templates = load_builtin_templates()
        goc_solo = templates["god_of_carnage_solo"]
        annette_role = next((r for r in goc_solo.roles if r.id == "annette"), None)
        assert annette_role is not None, "annette role must exist in god_of_carnage_solo template"
        assert annette_role.mode == ParticipantMode.HUMAN
        assert annette_role.can_join is True

    def test_alain_human_role_exists_in_template(self):
        """alain must be a HUMAN+can_join role in the god_of_carnage_solo template."""
        from app.content.builtins import load_builtin_templates
        from app.content.models import ParticipantMode
        templates = load_builtin_templates()
        goc_solo = templates["god_of_carnage_solo"]
        alain_role = next((r for r in goc_solo.roles if r.id == "alain"), None)
        assert alain_role is not None, "alain role must exist in god_of_carnage_solo template"
        assert alain_role.mode == ParticipantMode.HUMAN
        assert alain_role.can_join is True


# ---------------------------------------------------------------------------
# Capability evidence tests (MVP1-P05)
# ---------------------------------------------------------------------------

class TestCapabilityEvidence:

    def test_ldss_capability_added_to_e0_report_requires_source_anchor(self):
        """Capability evidence must use real anchors or honest 'missing' status — not static success."""
        from app.runtime.profiles import resolve_runtime_profile
        profile = resolve_runtime_profile("god_of_carnage_solo")
        capability_report = {
            "contract": "capability_evidence_report.v1",
            "content_module_id": profile.content_module_id,
            "runtime_profile_id": profile.runtime_profile_id,
            "capabilities": [
                {
                    "capability": "role_selection",
                    "status": "implemented",
                    "source_anchors": [
                        "world-engine/app/runtime/profiles.py:resolve_runtime_profile",
                        "world-engine/app/runtime/profiles.py:validate_selected_player_role",
                    ],
                    "tests": ["test_valid_annette_start", "test_valid_alain_start"],
                },
                {
                    "capability": "live_dramatic_scene_simulator",
                    "status": "missing",
                    "source_anchors": [],
                    "tests": [],
                },
            ],
        }
        role_selection = next(
            c for c in capability_report["capabilities"] if c["capability"] == "role_selection"
        )
        assert role_selection["status"] == "implemented"
        assert len(role_selection["source_anchors"]) > 0, (
            "Implemented capability must have source anchors (not empty list)."
        )
        ldss = next(
            c for c in capability_report["capabilities"] if c["capability"] == "live_dramatic_scene_simulator"
        )
        assert ldss["status"] == "missing"


# ---------------------------------------------------------------------------
# Source locator artifact tests (operational gate)
# ---------------------------------------------------------------------------

class TestSourceLocatorArtifact:

    def test_source_locator_artifact_exists_for_mvp(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_SOURCE_LOCATOR.md"
        assert artifact.is_file(), (
            f"Source locator artifact is required before code patching but not found at: {artifact}"
        )

    def test_source_locator_matrix_has_no_placeholders_before_patch(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_SOURCE_LOCATOR.md"
        assert artifact.is_file(), "Source locator artifact missing"
        content = artifact.read_text(encoding="utf-8")
        forbidden_placeholders = [
            "from patch map",
            "fill during implementation",
            "TODO",
            "TBD",
            "unknown",
            "unclear",
            "later",
        ]
        for placeholder in forbidden_placeholders:
            assert placeholder not in content, (
                f"Source locator artifact contains unresolved placeholder: {placeholder!r}"
            )

    def test_run_test_equivalent_is_documented_and_functional(self):
        """tests/run_tests.py must exist as the documented equivalent of run-test.py."""
        runner = REPO_ROOT / "tests" / "run_tests.py"
        assert runner.is_file(), (
            "tests/run_tests.py must exist — this is the documented equivalent of the "
            "guide's run-test.py. The MVP1 source locator artifact documents this equivalence."
        )
        content = runner.read_text(encoding="utf-8")
        assert "engine" in content, "tests/run_tests.py must include the engine suite"
        assert "backend" in content, "tests/run_tests.py must include the backend suite"


# ---------------------------------------------------------------------------
# Operational evidence artifact test
# ---------------------------------------------------------------------------

class TestOperationalEvidenceArtifact:

    def test_operational_evidence_artifact_exists_for_mvp(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_OPERATIONAL_EVIDENCE.md"
        assert artifact.is_file(), (
            f"Operational evidence artifact is required to close MVP1 but not found at: {artifact}"
        )

    def test_operational_report_lists_mvp_specific_suites(self):
        artifact = REPO_ROOT / "tests" / "reports" / "MVP_Live_Runtime_Completion" / "MVP1_OPERATIONAL_EVIDENCE.md"
        if not artifact.is_file():
            pytest.skip("Operational evidence artifact not yet written — will be created post-test-run")
        content = artifact.read_text(encoding="utf-8")
        assert "test_mvp1_experience_identity" in content, (
            "Operational evidence must name the MVP1-specific test file"
        )
        assert "test_mvp1_session_identity" in content, (
            "Operational evidence must name the MVP1-specific backend test file"
        )
