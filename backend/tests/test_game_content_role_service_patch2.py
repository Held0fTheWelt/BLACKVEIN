from __future__ import annotations

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import GameExperienceTemplate, Role, User
from app.services.game_content_service import (
    GameContentConflictError,
    GameContentNotFoundError,
    GameContentValidationError,
    create_experience,
    ensure_default_game_content_seeded,
    get_experience,
    list_experiences,
    list_published_experience_payloads,
    publish_experience,
    slugify,
    update_experience,
)
from app.services.role_service import create_role, delete_role, list_roles, update_role, validate_role_name


@pytest.fixture
def authored_payload() -> dict:
    return {
        "id": "patch_round2_story",
        "title": "Patch Round 2 Story",
        "kind": "solo_story",
        "join_policy": "owner_only",
        "summary": "Test payload for additive service coverage.",
        "max_humans": 1,
        "initial_beat_id": "intro",
        "style_profile": "retro_pulp",
        "tags": ["patch", "round2"],
        "roles": [
            {
                "id": "visitor",
                "display_name": "Visitor",
                "description": "Human role",
                "mode": "human",
                "initial_room_id": "hall",
                "can_join": True,
            }
        ],
        "rooms": [
            {
                "id": "hall",
                "name": "Hall",
                "description": "Entry room",
                "exits": [],
                "prop_ids": [],
                "action_ids": [],
            }
        ],
        "props": [],
        "actions": [],
        "beats": [
            {
                "id": "intro",
                "name": "Introduction",
                "description": "Opening beat",
                "summary": "The situation begins.",
            }
        ],
    }


class TestGameContentServiceAdditionalCoverage:
    def test_slugify_normalizes_and_rejects_empty_values(self):
        assert slugify("  Hello, Better Tomorrow!  ") == "hello-better-tomorrow"
        with pytest.raises(GameContentValidationError, match="slug cannot be empty"):
            slugify("---")

    def test_default_seed_is_idempotent(self, app):
        with app.app_context():
            ensure_default_game_content_seeded()
            ensure_default_game_content_seeded()
            rows = GameExperienceTemplate.query.all()
            assert len(rows) == 1
            assert rows[0].template_id == "god_of_carnage_solo"

    def test_create_update_publish_and_list_experience(self, app, authored_payload):
        with app.app_context():
            created = create_experience(payload=authored_payload, actor_user_id=None)
            fetched = get_experience(created["id"])
            payload_v2 = dict(authored_payload)
            payload_v2["title"] = "Patch Round 2 Story Updated"
            payload_v2["slug"] = "Patch Round 2 Updated"

            updated = update_experience(created["id"], payload=payload_v2, actor_user_id=None)
            published = publish_experience(created["id"], actor_user_id=None)
            published_payloads = list_published_experience_payloads()
            listed = list_experiences(include_payload=True)

            assert fetched["template_id"] == authored_payload["id"]
            assert updated["title"] == "Patch Round 2 Story Updated"
            assert updated["slug"] == "patch-round-2-updated"
            assert updated["version"] == 2
            assert updated["updated_by_user_id"] is None
            assert published["is_published"] is True
            assert any(row["template_id"] == authored_payload["id"] for row in listed)
            assert any(row["id"] == authored_payload["id"] for row in published_payloads)

    def test_create_experience_rejects_duplicate_template_id_or_slug(self, app, authored_payload):
        with app.app_context():
            create_experience(payload=authored_payload)

            duplicate_template = dict(authored_payload)
            duplicate_template["slug"] = "different-slug"
            with pytest.raises(GameContentConflictError, match="template_id already exists"):
                create_experience(payload=duplicate_template)

            duplicate_slug = dict(authored_payload)
            duplicate_slug["id"] = "patch_round2_story_b"
            duplicate_slug["slug"] = "patch-round2-story"
            with pytest.raises(GameContentConflictError, match="slug already exists"):
                create_experience(payload=duplicate_slug)

    def test_get_and_update_raise_for_missing_experience(self, app, authored_payload):
        with app.app_context():
            with pytest.raises(GameContentNotFoundError):
                get_experience(999999)
            with pytest.raises(GameContentNotFoundError):
                update_experience(999999, payload=authored_payload)


class TestRoleServiceAdditionalCoverage:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("qa_ops", None),
            ("", "Role name is required"),
            ("MixedCase", None),
            ("bad-name", "Role name may only contain lowercase letters, digits, and underscore"),
        ],
    )
    def test_validate_role_name_contract(self, name, expected):
        assert validate_role_name(name) == expected

    def test_create_update_list_and_delete_role(self, app):
        with app.app_context():
            role, error = create_role("qa_patch2", description=" initial ", default_role_level=12)
            assert error is None
            assert role is not None
            assert role.description == "initial"
            assert role.default_role_level == 12

            updated, error = update_role(role.id, name="qa_patch2_updated", description=" changed ", default_role_level=18)
            assert error is None
            assert updated.name == "qa_patch2_updated"
            assert updated.description == "changed"
            assert updated.default_role_level == 18

            roles, total = list_roles(q="qa_patch2_")
            assert total >= 1
            assert any(r.name == "qa_patch2_updated" for r in roles)

            ok, error = delete_role(role.id)
            assert ok is True
            assert error is None

    def test_delete_role_rejects_when_users_still_assigned(self, app):
        with app.app_context():
            role, error = create_role("qa_bound_patch2")
            assert error is None
            user = User(
                username="bound_patch2_user",
                password_hash=generate_password_hash("Secret123"),
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()

            ok, error = delete_role(role.id)

            assert ok is False
            assert "Cannot delete role" in error
