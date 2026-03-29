from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.models import ActivityLog, Area, FeatureArea, Notification, Role, SiteSetting, Slogan, User
from app.models.area import DEFAULT_AREAS, ensure_areas_seeded
from app.models.role import ensure_roles_seeded
from app.models.user import PasswordHistory, SUPERADMIN_THRESHOLD


class TestSeedData:
    def test_default_roles_are_seeded_and_idempotent(self, db):
        ensure_roles_seeded()
        ensure_roles_seeded()

        roles = Role.query.order_by(Role.default_role_level.asc(), Role.name.asc()).all()
        role_names = [role.name for role in roles]
        assert set(role_names) >= {Role.NAME_USER, Role.NAME_QA, Role.NAME_MODERATOR, Role.NAME_ADMIN}

        counts_by_name = {name: Role.query.filter_by(name=name).count() for name in {Role.NAME_USER, Role.NAME_QA, Role.NAME_MODERATOR, Role.NAME_ADMIN}}
        assert counts_by_name == {
            Role.NAME_USER: 1,
            Role.NAME_QA: 1,
            Role.NAME_MODERATOR: 1,
            Role.NAME_ADMIN: 1,
        }

    def test_default_areas_are_seeded_and_idempotent(self, db):
        ensure_areas_seeded()
        ensure_areas_seeded()

        expected_slugs = {entry[0] for entry in DEFAULT_AREAS}
        actual_slugs = {area.slug for area in Area.query.all()}
        assert expected_slugs.issubset(actual_slugs)
        for slug in expected_slugs:
            assert Area.query.filter_by(slug=slug).count() == 1


class TestRoleAreaAndFeatureModels:
    def test_role_to_dict_contains_non_null_fields_only(self):
        role = Role(name="architect", description="Design role", default_role_level=42)
        assert role.to_dict() == {
            "id": None,
            "name": "architect",
            "description": "Design role",
            "default_role_level": 42,
        }

    def test_area_global_flag_and_to_dict(self, db):
        area = Area.query.filter_by(slug=Area.SLUG_ALL).first()
        assert area is not None
        assert area.is_global is True
        payload = area.to_dict()
        assert payload["slug"] == Area.SLUG_ALL
        assert payload["is_system"] is True
        assert payload["created_at"] is not None
        assert payload["updated_at"] is not None

    def test_user_can_be_assigned_multiple_areas(self, db, user_factory):
        user = user_factory()
        area_all = Area.query.filter_by(slug="all").first()
        area_game = Area.query.filter_by(slug="game").first()

        user.areas.extend([area_all, area_game])
        db.session.commit()
        db.session.refresh(user)

        assert {area.slug for area in user.areas} == {"all", "game"}
        assert {linked_user.username for linked_user in area_game.users} == {user.username}

    def test_feature_area_duplicate_pair_is_rejected(self, db):
        area = Area.query.filter_by(slug="game").first()
        db.session.add(FeatureArea(feature_id="dashboard.metrics", area_id=area.id))
        db.session.commit()

        db.session.add(FeatureArea(feature_id="dashboard.metrics", area_id=area.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_deleting_area_cascades_feature_area_links(self, db):
        area = Area(name="temp area", slug="temp-area")
        db.session.add(area)
        db.session.commit()

        db.session.add(FeatureArea(feature_id="feature.temp", area_id=area.id))
        db.session.commit()

        db.session.delete(area)
        db.session.commit()

        assert Area.query.filter_by(slug="temp-area").first() is None
        assert FeatureArea.query.filter_by(feature_id="feature.temp").first() is None


class TestUserModel:
    def test_user_requires_unique_username(self, db, user_factory):
        user_factory(username="duplicate-name")
        user_factory(username="different-name")

        role = Role.query.filter_by(name=Role.NAME_USER).first()
        db.session.add(User(username="duplicate-name", password_hash=generate_password_hash("x"), role_id=role.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_requires_unique_email_when_present(self, db, user_factory):
        user_factory(email="same@example.com")
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        db.session.add(User(username="other-user", email="same@example.com", password_hash=generate_password_hash("x"), role_id=role.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_requires_role_id(self, db):
        db.session.add(User(username="orphan", password_hash=generate_password_hash("x"), role_id=None))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_role_properties_and_permission_helpers(self, user_factory):
        user = user_factory(role_name=Role.NAME_USER)
        moderator = user_factory(role_name=Role.NAME_MODERATOR)
        admin = user_factory(role_name=Role.NAME_ADMIN, role_level=SUPERADMIN_THRESHOLD)

        assert user.role == Role.NAME_USER
        assert user.has_role(Role.NAME_USER) is True
        assert user.has_any_role([Role.NAME_MODERATOR, Role.NAME_USER]) is True
        assert user.is_admin is False
        assert user.is_super_admin is False
        assert user.is_moderator_or_admin is False
        assert moderator.can_write_news() is True
        assert moderator.is_moderator_or_admin is True
        assert admin.is_admin is True
        assert admin.is_super_admin is True

    def test_user_to_dict_can_include_email_ban_and_areas(self, db, user_factory):
        user = user_factory(
            email="dict@example.com",
            preferred_language="en",
            is_banned=True,
            banned_at=datetime.now(timezone.utc),
            ban_reason="testing",
        )
        user.areas.append(Area.query.filter_by(slug="game").first())
        db.session.commit()
        db.session.refresh(user)

        payload = user.to_dict(include_email=True, include_ban=True, include_areas=True)
        assert payload["username"] == user.username
        assert payload["email"] == "dict@example.com"
        assert payload["is_banned"] is True
        assert payload["ban_reason"] == "testing"
        assert payload["preferred_language"] == "en"
        assert payload["areas"][0]["slug"] == "game"
        assert payload["area_ids"] == [user.areas[0].id]

    def test_password_history_helpers_roundtrip_and_limit_to_last_three(self, db, user_factory):
        user = user_factory(password_history=json.dumps([]))
        hashes = [generate_password_hash(f"Secret{i}!") for i in range(1, 5)]

        for password_hash in hashes:
            user.add_to_password_history(password_hash)

        db.session.refresh(user)
        history = json.loads(user.password_history)
        assert len(history) == 3
        assert history == hashes[-3:]
        assert user.is_password_in_history("Secret1!") is False
        assert user.is_password_in_history("Secret2!") is True
        assert user.is_password_in_history("Secret4!") is True

    def test_password_history_table_cascades_on_user_delete(self, db, user_factory):
        user = user_factory()
        history = PasswordHistory(user_id=user.id, password_hash=generate_password_hash("Secret!"))
        db.session.add(history)
        db.session.commit()

        db.session.delete(user)
        db.session.commit()

        assert PasswordHistory.query.count() == 0


class TestMiscDatabaseModels:
    def test_activity_log_to_dict_maps_meta_to_metadata(self, db, user_factory):
        user = user_factory(role_name=Role.NAME_ADMIN)
        log = ActivityLog(
            actor_user_id=user.id,
            actor_username_snapshot=user.username,
            actor_role_snapshot=user.role,
            category="security",
            action="ban",
            status="warning",
            message="User banned",
            tags=["rbac", "moderation"],
            meta={"target": "user_2"},
            target_type="user",
            target_id="2",
        )
        db.session.add(log)
        db.session.commit()

        payload = log.to_dict()
        assert payload["actor_user_id"] == user.id
        assert payload["tags"] == ["rbac", "moderation"]
        assert payload["metadata"] == {"target": "user_2"}
        assert payload["target_type"] == "user"

    def test_notification_to_dict_includes_read_state(self, db, user_factory):
        user = user_factory()
        notification = Notification(
            user_id=user.id,
            event_type="thread_reply",
            target_type="forum_thread",
            target_id=7,
            message="A new reply arrived",
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
        db.session.add(notification)
        db.session.commit()

        payload = notification.to_dict()
        assert payload["user_id"] == user.id
        assert payload["event_type"] == "thread_reply"
        assert payload["is_read"] is True
        assert payload["read_at"] is not None

    def test_site_setting_acts_as_key_value_store(self, db):
        setting = SiteSetting(key="landing.hero.title", value="Better Tomorrow")
        db.session.add(setting)
        db.session.commit()

        loaded = SiteSetting.query.get("landing.hero.title")
        assert loaded is not None
        assert loaded.value == "Better Tomorrow"

    def test_slogan_to_dict_roundtrip(self, db, user_factory):
        user = user_factory(role_name=Role.NAME_ADMIN)
        slogan = Slogan(
            text="Tomorrow belongs to those who build it.",
            category=Slogan.CATEGORIES[0],
            placement_key=Slogan.PLACEMENTS[0],
            language_code="en",
            is_active=True,
            is_pinned=True,
            priority=10,
            created_by=user.id,
            updated_by=user.id,
        )
        db.session.add(slogan)
        db.session.commit()

        payload = slogan.to_dict()
        assert payload["text"].startswith("Tomorrow belongs")
        assert payload["category"] == Slogan.CATEGORIES[0]
        assert payload["placement_key"] == Slogan.PLACEMENTS[0]
        assert payload["is_pinned"] is True
        assert payload["created_by"] == user.id
