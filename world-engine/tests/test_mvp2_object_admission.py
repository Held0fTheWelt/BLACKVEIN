"""MVP2 tests — Object Admission & Content Boundary Hardening (Wave 2.4).

Proves:
- canonical_content object is admitted with commit_allowed=True
- typical_minor_implied object is staged temporarily with commit_allowed=False
- similar_allowed requires similarity_reason
- unadmitted objects (no source_kind) are rejected
- major/dangerous/plot-changing objects are rejected without canonical backing
- runtime profile contains no story truth (content boundary)
- runtime module (god_of_carnage_solo) contains no GoC story truth
- god_of_carnage_solo does not define characters, scenes, props, or plot truth
"""

from __future__ import annotations

import pytest

from app.runtime.models import VALID_SOURCE_KINDS, ObjectAdmissionRecord
from app.runtime.object_admission import admit_object, validate_object_admission


# ---------------------------------------------------------------------------
# Wave 2.4: canonical_content object admission
# ---------------------------------------------------------------------------

def test_canonical_object_admitted():
    record = admit_object({
        "object_id": "mobile_phone",
        "source_kind": "canonical_content",
        "source_reference": "content.modules.god_of_carnage.scene.props.mobile_phone",
        "admission_reason": "Explicitly present in canonical scene content.",
    })
    assert record.status == "admitted"
    assert record.source_kind == "canonical_content"
    assert record.commit_allowed is True
    assert record.temporary_scene_staging is False
    assert record.error_code is None


def test_canonical_object_contract():
    record = admit_object({
        "object_id": "tulips",
        "source_kind": "canonical_content",
        "source_reference": "content.modules.god_of_carnage.props.tulips",
    })
    assert record.contract == "object_admission_record.v1"
    assert record.status == "admitted"
    assert record.commit_allowed is True


# ---------------------------------------------------------------------------
# Wave 2.4: typical_minor_implied object admission
# ---------------------------------------------------------------------------

def test_typical_minor_object_admitted_as_temporary():
    record = admit_object({
        "object_id": "water_glass",
        "source_kind": "typical_minor_implied",
        "source_reference": "scene_context.living_room.typical_minor_props",
        "admission_reason": "A glass of water is a minor plausible living-room object.",
    })
    assert record.status == "admitted"
    assert record.source_kind == "typical_minor_implied"
    assert record.temporary_scene_staging is True
    assert record.commit_allowed is False


def test_typical_minor_coffee_cup():
    record = admit_object({
        "object_id": "coffee_cup",
        "source_kind": "typical_minor_implied",
        "admission_reason": "Common living-room item, minor, does not affect plot.",
    })
    assert record.status == "admitted"
    assert record.temporary_scene_staging is True
    assert record.commit_allowed is False


# ---------------------------------------------------------------------------
# Wave 2.4: similar_allowed object admission
# ---------------------------------------------------------------------------

def test_similar_allowed_requires_similarity_reason():
    record = admit_object({
        "object_id": "picture_frame",
        "source_kind": "similar_allowed",
        "source_reference": "scene_context.living_room.decor",
    })
    assert record.status == "rejected"
    assert record.error_code == "similar_allowed_requires_similarity_reason"


def test_similar_allowed_with_reason_admitted():
    record = admit_object({
        "object_id": "picture_frame",
        "source_kind": "similar_allowed",
        "source_reference": "scene_context.living_room.decor",
        "similarity_reason": "Similar to typical living-room wall decor; does not change plot truth.",
        "admission_reason": "Contextually plausible household decoration.",
    })
    assert record.status == "admitted"
    assert record.similarity_reason is not None
    assert record.commit_allowed is False


def test_similar_allowed_empty_reason_rejected():
    record = admit_object({
        "object_id": "lamp",
        "source_kind": "similar_allowed",
        "similarity_reason": "   ",  # whitespace only
    })
    assert record.status == "rejected"
    assert record.error_code == "similar_allowed_requires_similarity_reason"


# ---------------------------------------------------------------------------
# Wave 2.4: unadmitted objects rejected
# ---------------------------------------------------------------------------

def test_unadmitted_plausible_object_rejected():
    """Object with no source_kind must be rejected even if plausible."""
    record = admit_object({
        "object_id": "newspaper",
        "admission_reason": "Plausible for the scene.",
    })
    assert record.status == "rejected"
    assert record.error_code == "object_source_kind_required"


def test_object_missing_source_kind_rejected():
    record = admit_object({"object_id": "ashtray"})
    assert record.status == "rejected"
    assert record.error_code == "object_source_kind_required"


def test_invalid_source_kind_rejected():
    record = admit_object({
        "object_id": "couch",
        "source_kind": "invented_kind",
    })
    assert record.status == "rejected"
    assert record.error_code == "object_source_kind_required"


def test_object_without_id_rejected():
    record = admit_object({})
    assert record.status == "rejected"
    assert record.error_code == "object_source_kind_required"


# ---------------------------------------------------------------------------
# Wave 2.4: major/dangerous/plot-changing objects rejected
# ---------------------------------------------------------------------------

def test_major_plot_changing_object_rejected():
    """Loaded revolver is dangerous and plot-changing — rejected without canonical backing."""
    record = admit_object({
        "object_id": "loaded_revolver",
        "source_kind": "typical_minor_implied",
        "admission_reason": "Someone left it here.",
    })
    assert record.status == "rejected"
    assert record.error_code == "environment_object_not_admitted"


def test_dangerous_object_rejected_as_similar_allowed():
    record = admit_object({
        "object_id": "knife",
        "source_kind": "similar_allowed",
        "similarity_reason": "Similar to kitchen utensils.",
    })
    assert record.status == "rejected"
    assert record.error_code == "environment_object_not_admitted"


def test_canonical_dangerous_object_admitted():
    """A dangerous object with canonical backing is admitted (e.g., if canon has it)."""
    record = admit_object({
        "object_id": "gun",
        "source_kind": "canonical_content",
        "source_reference": "content.modules.god_of_carnage.scene.props.gun",
        "admission_reason": "Explicitly in canonical content.",
    })
    # canonical_content overrides the dangerous-object check
    assert record.status == "admitted"
    assert record.commit_allowed is True


def test_valid_source_kinds_constant():
    assert "canonical_content" in VALID_SOURCE_KINDS
    assert "typical_minor_implied" in VALID_SOURCE_KINDS
    assert "similar_allowed" in VALID_SOURCE_KINDS
    assert len(VALID_SOURCE_KINDS) == 3


def test_validate_object_admission_admitted_record():
    record = admit_object({
        "object_id": "mobile_phone",
        "source_kind": "canonical_content",
    })
    assert validate_object_admission(record) is True


def test_validate_object_admission_rejected_record():
    record = admit_object({"object_id": "unknown_object"})
    assert validate_object_admission(record) is False


def test_validate_object_admission_rejects_invalid_source_kind_on_admitted_record():
    record = admit_object({
        "object_id": "mobile_phone",
        "source_kind": "canonical_content",
    })
    record = record.model_copy(update={"source_kind": "not_a_real_kind"})
    assert validate_object_admission(record) is False


def test_validate_object_admission_rejects_similar_allowed_without_reason():
    record = admit_object({
        "object_id": "napkin",
        "source_kind": "similar_allowed",
        "similarity_reason": "matches table linen",
    })
    record = record.model_copy(update={"similarity_reason": None})
    assert validate_object_admission(record) is False


# ---------------------------------------------------------------------------
# Wave 2.4: Content/profile/runtime boundary hardening
# ---------------------------------------------------------------------------

def test_runtime_profile_contains_no_story_truth():
    """RuntimeProfile must not contain forbidden story truth fields."""
    from app.runtime.profiles import assert_profile_contains_no_story_truth, resolve_runtime_profile

    profile = resolve_runtime_profile("god_of_carnage_solo")
    profile_dict = profile.to_dict()

    # Must not raise
    assert_profile_contains_no_story_truth(profile_dict)

    # Verify none of the forbidden fields are present
    forbidden = ["characters", "roles", "rooms", "props", "beats", "scenes", "relationships", "endings"]
    for field in forbidden:
        assert field not in profile_dict, f"Profile must not contain story truth field: {field!r}"


def test_runtime_module_contains_no_goc_story_truth():
    """God of Carnage solo builtin template must not own story truth."""
    from app.runtime.profiles import assert_runtime_module_contains_no_story_truth
    from app.content.builtins import load_builtin_templates

    templates = load_builtin_templates()
    goc_solo = templates.get("god_of_carnage_solo")
    assert goc_solo is not None, "god_of_carnage_solo template must exist in builtins"

    # Must not raise — template has empty beats, props, actions
    assert_runtime_module_contains_no_story_truth(goc_solo)

    assert goc_solo.beats == [], "god_of_carnage_solo beats must be empty"
    assert goc_solo.props == [], "god_of_carnage_solo props must be empty"
    assert goc_solo.actions == [], "god_of_carnage_solo actions must be empty"


def test_god_of_carnage_solo_does_not_define_characters_scenes_props_or_plot_truth():
    """god_of_carnage_solo must not own any canonical story truth.

    The template is runtime configuration only. All story truth lives in
    content/modules/god_of_carnage/. This is the Wave 2.4 content boundary gate.
    """
    from app.content.builtins import load_builtin_templates

    templates = load_builtin_templates()
    goc_solo = templates.get("god_of_carnage_solo")
    assert goc_solo is not None

    # No beats (scene progression truth)
    assert not goc_solo.beats, "god_of_carnage_solo must not define beats"
    # No props (canonical objects)
    assert not goc_solo.props, "god_of_carnage_solo must not define props"
    # No actions (canonical action verbs)
    assert not goc_solo.actions, "god_of_carnage_solo must not define actions"

    # The template id is runtime profile id, not a content module id
    assert goc_solo.id == "god_of_carnage_solo"

    # No visitor role
    role_ids = {role.id for role in goc_solo.roles}
    assert "visitor" not in role_ids, "god_of_carnage_solo must not have a visitor role"

    # All four canonical characters are represented (no invented characters)
    assert role_ids == {"annette", "alain", "veronique", "michel"}, (
        f"god_of_carnage_solo must have exactly the 4 canonical GoC roles, got: {role_ids!r}"
    )

    # Only annette and alain are selectable human roles (mode=HUMAN, can_join=True)
    from app.content.models import ParticipantMode
    human_joinable = {r.id for r in goc_solo.roles if r.mode == ParticipantMode.HUMAN and r.can_join}
    assert human_joinable == {"annette", "alain"}, (
        f"Only annette and alain may be selectable human roles, got: {human_joinable!r}"
    )


def test_god_of_carnage_content_module_owns_story_truth():
    """The canonical content module god_of_carnage must exist and own story truth."""
    import os
    from pathlib import Path
    from app.repo_root import resolve_wos_repo_root

    repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
    goc_dir = repo_root / "content" / "modules" / "god_of_carnage"

    assert goc_dir.is_dir(), "content/modules/god_of_carnage/ must exist"
    assert (goc_dir / "characters" / "index.yaml").exists(), "characters/index.yaml must exist in canonical content"
    assert (goc_dir / "canonical_path" / "index.yaml").exists(), "canonical_path/index.yaml must exist in canonical content"
    assert (goc_dir / "phase_beat_policy.yaml").exists(), "phase_beat_policy.yaml must exist in canonical content"


def test_goc_solo_not_under_content_modules():
    """god_of_carnage_solo must not be loadable as a content module."""
    import os
    from pathlib import Path
    from app.repo_root import resolve_wos_repo_root

    repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
    solo_as_content = repo_root / "content" / "modules" / "god_of_carnage_solo"
    assert not solo_as_content.exists(), (
        "god_of_carnage_solo must not exist as a content module directory"
    )
