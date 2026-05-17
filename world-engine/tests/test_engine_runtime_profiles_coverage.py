"""Contract tests for runtime profile edge paths required by the engine coverage gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.profiles import (
    RuntimeProfile,
    RuntimeProfileError,
    SelectablePlayerRole,
    _resolve_goc_content,
    assert_runtime_module_contains_no_story_truth,
    validate_selected_player_role,
)
from ai_stack.goc_yaml_authority import goc_actor_ids_from_content
from tests.test_runtime_engine import _build_test_solo_template


@pytest.mark.contract
def test_runtime_profile_error_to_dict_includes_details() -> None:
    err = RuntimeProfileError(code="fixture_code", message="fixture message", field="x")
    payload = err.to_dict()
    assert payload["code"] == "fixture_code"
    assert payload["message"] == "fixture message"
    assert payload["field"] == "x"


@pytest.mark.contract
def test_resolve_goc_content_empty_characters_uses_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goc_dir = tmp_path / "content" / "modules" / "god_of_carnage"
    goc_dir.mkdir(parents=True)
    (goc_dir / "characters.yaml").write_text("characters: {}\n", encoding="utf-8")

    monkeypatch.setattr(
        "app.repo_root.resolve_wos_repo_root",
        lambda *, start: tmp_path,
    )
    actor_ids, content_hash = _resolve_goc_content(allow_fallback=True)

    assert actor_ids == goc_actor_ids_from_content()
    assert content_hash.startswith("sha256:")


@pytest.mark.contract
def test_resolve_goc_content_uses_fallback_when_file_unreadable_and_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.repo_root.resolve_wos_repo_root",
        lambda *, start: Path("/definitely/missing/wos-root"),
    )
    actor_ids, content_hash = _resolve_goc_content(allow_fallback=True)
    assert actor_ids == goc_actor_ids_from_content()
    assert content_hash.startswith("sha256:")


@pytest.mark.contract
def test_resolve_goc_content_raises_without_fallback_when_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken_repo_root(*, start: Path | None = None) -> Path:
        return Path("/definitely/missing/wos-root")

    monkeypatch.setattr("app.repo_root.resolve_wos_repo_root", _broken_repo_root)
    with pytest.raises(RuntimeProfileError) as exc_info:
        _resolve_goc_content(allow_fallback=False)
    assert exc_info.value.code == "runtime_profile_not_content_module"


@pytest.mark.contract
def test_validate_selected_player_role_requires_canonical_mapping() -> None:
    profile = RuntimeProfile(
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        runtime_mode="solo_story",
        requires_selected_player_role=True,
        selectable_player_roles=[],
        profile_version="goc-solo.v1",
    )
    with pytest.raises(RuntimeProfileError) as exc_info:
        validate_selected_player_role("annette", profile)
    assert exc_info.value.code == "invalid_selected_player_role"


@pytest.mark.contract
def test_assert_runtime_module_contains_no_story_truth_rejects_owned_beats() -> None:
    template = _build_test_solo_template()
    with pytest.raises(RuntimeProfileError) as exc_info:
        assert_runtime_module_contains_no_story_truth(template)
    assert exc_info.value.code == "runtime_module_contains_story_truth"
    assert "beats" in exc_info.value.details.get("violations", {})


@pytest.mark.contract
def test_assert_runtime_module_contains_no_story_truth_rejects_owned_props() -> None:
    from app.content.models import (
        BeatTemplate,
        ExperienceKind,
        ExperienceTemplate,
        JoinPolicy,
        PropTemplate,
        RoleTemplate,
        ParticipantMode,
    )

    template = ExperienceTemplate(
        id="props_only_fixture",
        title="Props Only",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary="fixture",
        max_humans=1,
        initial_beat_id="opening",
        roles=[
            RoleTemplate(
                id="player",
                display_name="Player",
                description="Player",
                mode=ParticipantMode.HUMAN,
                initial_room_id="hallway",
            )
        ],
        rooms=[],
        actions=[],
        beats=[BeatTemplate(id="opening", name="Opening", description="x", summary="x")],
        props=[PropTemplate(id="phone", name="Phone", description="fixture prop")],
    )
    with pytest.raises(RuntimeProfileError) as exc_info:
        assert_runtime_module_contains_no_story_truth(template)
    assert "props" in exc_info.value.details.get("violations", {})
