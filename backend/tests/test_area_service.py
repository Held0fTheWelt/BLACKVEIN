"""Tests for app.services.area_service."""

from __future__ import annotations

from werkzeug.security import generate_password_hash

from app.auth.feature_registry import FEATURE_MANAGE_USERS
from app.extensions import db
from app.models import Area, FeatureArea, Role, User
from app.services.area_service import (
    create_area,
    delete_area,
    get_area_by_id,
    get_area_by_slug,
    get_user_area_ids,
    list_areas,
    list_feature_areas_mapping,
    set_feature_areas,
    set_user_areas,
    update_area,
)


def _create_basic_user(username: str) -> User:
    role = Role.query.filter_by(name=Role.NAME_USER).first()
    user = User(
        username=username,
        password_hash=generate_password_hash("Secret123"),
        role_id=role.id,
    )
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


class TestAreaService:
    def test_create_list_get_and_search_areas(self, app):
        with app.app_context():
            created, error = create_area("Patch Search Area", description="Searchable")
            assert error is None
            assert created.slug == "patch_search_area"

            fetched_by_id = get_area_by_id(created.id)
            fetched_by_slug = get_area_by_slug(" PATCH_SEARCH_AREA ")
            results, total = list_areas(page=1, per_page=10, q="patch_search")

            assert fetched_by_id.id == created.id
            assert fetched_by_slug.id == created.id
            assert total >= 1
            assert any(area.slug == "patch_search_area" for area in results)
            assert get_area_by_id(None) is None
            assert get_area_by_id("abc") is None
            assert get_area_by_slug(None) is None
            assert get_area_by_slug("") is None

    def test_create_and_update_area_validation_and_duplicates(self, app):
        with app.app_context():
            area, error = create_area("Patch Editable", slug="patch_editable", description=" initial ")
            assert error is None
            assert area.description == "initial"

            duplicate_slug, error = create_area("Another Name", slug="patch_editable")
            assert duplicate_slug is None
            assert error == "Area slug already exists"

            duplicate_name, error = create_area("Patch Editable", slug="different_slug")
            assert duplicate_name is None
            assert error == "Area name already exists"

            updated, error = update_area(area.id, name="Patch Updated", slug="patch_updated", description=" changed ")
            assert error is None
            assert updated.name == "Patch Updated"
            assert updated.slug == "patch_updated"
            assert updated.description == "changed"

            other, _ = create_area("Other Area", slug="other_area")
            _, error = update_area(area.id, name=other.name)
            assert error == "Area name already exists"
            _, error = update_area(area.id, slug=other.slug)
            assert error == "Area slug already exists"
            _, error = update_area(999999, name="Missing")
            assert error == "Area not found"

    def test_system_area_protections(self, app):
        with app.app_context():
            all_area = Area.query.filter_by(slug=Area.SLUG_ALL).first()
            _, error = update_area(all_area.id, name="Nope")
            assert error == "Cannot modify the system 'all' area"

            system_area, _ = create_area("Patch System", slug="patch_system", is_system=True)
            _, error = update_area(system_area.id, slug="changed")
            assert error == "Cannot change slug of system area"

            ok, error = delete_area(system_area.id)
            assert ok is False
            assert error == "Cannot delete system area"

    def test_set_user_areas_and_delete_assignment_guards(self, app):
        with app.app_context():
            area_a, _ = create_area("Area A", slug="area_a")
            area_b, _ = create_area("Area B", slug="area_b")
            user = _create_basic_user("area_patch_user")

            assigned_user, error = set_user_areas(user.id, [area_a.id, area_b.id])
            assert error is None
            assert {a.slug for a in assigned_user.areas} == {"area_a", "area_b"}
            assert set(get_user_area_ids(user.id)) == {area_a.id, area_b.id}

            _, error = set_user_areas(user.id, [area_a.id, 999999])
            assert "Unknown area id(s)" in error
            missing_user, error = set_user_areas(999999, [area_a.id])
            assert missing_user is None
            assert error == "User not found"

            ok, error = delete_area(area_a.id)
            assert ok is False
            assert error == "Area is assigned to users; remove assignments first"

            set_user_areas(user.id, [])
            ok, error = delete_area(area_a.id)
            assert ok is True
            assert error is None

    def test_feature_area_mapping_and_delete_feature_guard(self, app):
        with app.app_context():
            feature_area, _ = create_area("Feature Scoped", slug="feature_scoped")

            ok, error = set_feature_areas("invalid.feature", [feature_area.id])
            assert ok is False
            assert "Unknown feature_id" in error

            ok, error = set_feature_areas(FEATURE_MANAGE_USERS, [feature_area.id])
            assert ok is True
            assert error is None

            mapping = list_feature_areas_mapping()
            manage_users = next(item for item in mapping if item["feature_id"] == FEATURE_MANAGE_USERS)
            assert manage_users["area_ids"] == [feature_area.id]
            assert manage_users["area_slugs"] == ["feature_scoped"]

            ok, error = delete_area(feature_area.id)
            assert ok is False
            assert error == "Area is assigned to features; remove assignments first"

            FeatureArea.query.filter_by(feature_id=FEATURE_MANAGE_USERS).delete()
            db.session.commit()
            ok, error = delete_area(feature_area.id)
            assert ok is True
            assert error is None
