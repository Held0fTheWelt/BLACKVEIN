"""Tests for GameExperienceTemplate model serialization."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.game_experience import GameExperienceTemplate


@pytest.mark.usefixtures("isolated_app_context")
def test_game_experience_template_to_dict_includes_expected_defaults():
    template = GameExperienceTemplate(
        id=12,
        key="god_of_carnage",
        title="God of Carnage",
        experience_type=GameExperienceTemplate.TYPE_SOLO,
        summary="A chamber-piece runtime test.",
        tags=["drama", "social"],
        style_profile="retro_pulp",
        status=GameExperienceTemplate.STATUS_REVIEW,
        current_version=3,
        published_version=2,
        created_by=1,
        updated_by=2,
        published_by=3,
        draft_payload={"scene": "start"},
        published_payload={"scene": "published"},
        created_at=datetime(2026, 3, 31, 20, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 31, 21, 0, tzinfo=timezone.utc),
        published_at=datetime(2026, 3, 31, 22, 0, tzinfo=timezone.utc),
    )

    payload = template.to_dict()
    assert payload["id"] == 12
    assert payload["key"] == "god_of_carnage"
    assert payload["title"] == "God of Carnage"
    assert payload["experience_type"] == GameExperienceTemplate.TYPE_SOLO
    assert payload["tags"] == ["drama", "social"]
    assert payload["draft_payload"] == {"scene": "start"}
    assert payload["created_at"].startswith("2026-03-31T20:00:00")
    assert payload["updated_at"].startswith("2026-03-31T21:00:00")
    assert payload["published_at"].startswith("2026-03-31T22:00:00")
    assert "published_payload" not in payload


@pytest.mark.usefixtures("isolated_app_context")
def test_game_experience_template_to_dict_obeys_payload_flags():
    template = GameExperienceTemplate(
        key="better_tomorrow",
        title="Better Tomorrow",
        draft_payload=None,
        published_payload={"state": "live"},
        tags=None,
    )

    without_draft = template.to_dict(include_payload=False, include_published_payload=True)
    assert "draft_payload" not in without_draft
    assert without_draft["published_payload"] == {"state": "live"}
    assert without_draft["tags"] == []

    with_draft = template.to_dict(include_payload=True, include_published_payload=False)
    assert with_draft["draft_payload"] == {}
    assert "published_payload" not in with_draft


@pytest.mark.usefixtures("isolated_app_context")
def test_game_experience_template_to_dict_full_and_compact_variants():
    template = GameExperienceTemplate(
        id=5,
        key="god_of_carnage",
        title="God of Carnage",
        experience_type=GameExperienceTemplate.TYPE_SOLO,
        summary="summary",
        tags=["a", "b"],
        style_profile="retro_pulp",
        status=GameExperienceTemplate.STATUS_PUBLISHED,
        current_version=3,
        published_version=2,
        draft_payload={"draft": True},
        published_payload={"published": True},
        created_by=1,
        updated_by=2,
        published_by=3,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    full = template.to_dict(include_payload=True, include_published_payload=True)
    assert full["draft_payload"] == {"draft": True}
    assert full["published_payload"] == {"published": True}
    assert full["status"] == GameExperienceTemplate.STATUS_PUBLISHED
    assert full["created_at"].startswith("2026-01-01T")

    compact = template.to_dict(include_payload=False, include_published_payload=False)
    assert "draft_payload" not in compact
    assert "published_payload" not in compact
    assert compact["tags"] == ["a", "b"]
