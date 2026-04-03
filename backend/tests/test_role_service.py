"""Direct unit tests for app.services.role_service (edge cases not reachable via HTTP)."""

from __future__ import annotations

import uuid

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Role, User
from app.services.role_service import (
    create_role,
    delete_role,
    get_role_by_id,
    list_roles,
    update_role,
    validate_role_name,
)


def _unique_role_name() -> str:
    """Alphanumeric name within Role.NAME_MAX_LENGTH (20)."""
    return uuid.uuid4().hex[:20]


def test_get_role_by_id_none_returns_none(app):
    with app.app_context():
        assert get_role_by_id(None) is None


def test_get_role_by_id_non_numeric_returns_none(app):
    with app.app_context():
        assert get_role_by_id("abc") is None
        assert get_role_by_id({}) is None


def test_validate_role_name_whitespace_only_returns_empty_error():
    assert validate_role_name("   ") == "Role name cannot be empty"


def test_validate_role_name_non_string_returns_required():
    assert validate_role_name(None) == "Role name is required"  # type: ignore[arg-type]
    assert validate_role_name(42) == "Role name is required"  # type: ignore[arg-type]


def test_validate_role_name_exceeds_max_length():
    too_long = "a" * (Role.NAME_MAX_LENGTH + 1)
    err = validate_role_name(too_long)
    assert err is not None
    assert str(Role.NAME_MAX_LENGTH) in err


def test_list_roles_without_search_and_with_query(app):
    with app.app_context():
        items, total = list_roles(page=1, per_page=50, q=None)
        assert total >= 1
        assert isinstance(items, list)

        items2, total2 = list_roles(q="user")
        assert total2 >= 1
        assert any("user" in r.name for r in items2)


def test_create_role_invalid_name_short_circuits_before_level(app):
    with app.app_context():
        role, err = create_role("", default_role_level=-1)
        assert role is None
        assert err == "Role name is required"


def test_create_role_duplicate_name(app):
    with app.app_context():
        name = _unique_role_name()
        r1, err = create_role(name)
        assert err is None
        r2, err = create_role(name)
        assert r2 is None
        assert err == "Role name already exists"


@pytest.mark.parametrize(
    "level,expected_substr",
    [
        (-1, "between 0 and 9999"),
        (10000, "between 0 and 9999"),
        ("nope", "must be an integer"),
    ],
)
def test_create_role_rejects_invalid_default_role_level(app, level, expected_substr):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name, default_role_level=level)
        assert role is None
        assert err is not None
        assert expected_substr in err


def test_update_role_description_only_without_name_branch(app):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name, description="old")
        assert err is None
        updated, err = update_role(role.id, description="new desc")
        assert err is None
        assert updated.description == "new desc"
        assert updated.name == name


def test_update_role_default_role_level_only_without_name(app):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name, default_role_level=5)
        assert err is None
        updated, err = update_role(role.id, default_role_level=99)
        assert err is None
        assert updated.default_role_level == 99
        assert updated.name == name


def test_update_role_rejects_invalid_name(app):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name)
        assert err is None
        updated, err = update_role(role.id, name="bad-dash")
        assert updated is None
        assert err is not None
        assert "Role name" in err


def test_update_role_rejects_duplicate_name(app):
    with app.app_context():
        a_name = _unique_role_name()
        b_name = _unique_role_name()
        a, err = create_role(a_name)
        assert err is None
        b, err = create_role(b_name)
        assert err is None
        updated, err = update_role(a.id, name=b.name)
        assert updated is None
        assert err == "Role name already exists"


@pytest.mark.parametrize(
    "level,expected_substr",
    [
        (-1, "between 0 and 9999"),
        (10000, "between 0 and 9999"),
        ("x", "must be an integer"),
    ],
)
def test_update_role_rejects_invalid_default_role_level(app, level, expected_substr):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name, default_role_level=1)
        assert err is None
        updated, err = update_role(role.id, default_role_level=level)
        assert updated is None
        assert err is not None
        assert expected_substr in err


def test_update_role_not_found(app):
    with app.app_context():
        new_name = _unique_role_name()
        updated, err = update_role(999_999, name=new_name)
        assert updated is None
        assert err == "Role not found"


def test_update_role_renames_successfully(app):
    with app.app_context():
        old = _unique_role_name()
        role, err = create_role(old)
        assert err is None
        new = _unique_role_name()
        updated, err = update_role(role.id, name=new)
        assert err is None
        assert updated is not None
        assert updated.name == new


def test_delete_role_success_and_not_found(app):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name)
        assert err is None
        ok, err = delete_role(role.id)
        assert ok is True
        assert err is None

        ok2, err2 = delete_role(999_998)
        assert ok2 is False
        assert err2 == "Role not found"


def test_delete_role_rejects_when_users_assigned(app):
    with app.app_context():
        name = _unique_role_name()
        role, err = create_role(name)
        assert err is None
        user = User(
            username=f"u_{uuid.uuid4().hex[:8]}",
            password_hash=generate_password_hash("Secret123"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()

        ok, err = delete_role(role.id)
        assert ok is False
        assert err is not None
        assert "user" in err.lower()
