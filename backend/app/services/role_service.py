"""CRUD and helpers for Role model. Used by API and user_service."""
import re

from sqlalchemy import func

from app.extensions import db
from app.models import Role, User
from app.services.search_utils import _escape_sql_like_wildcards

ROLE_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def list_roles(page: int = 1, per_page: int = 50, q: str | None = None):
    """Return (list of Role, total count). Optional search by name (case-insensitive contains)."""
    query = Role.query
    if q and q.strip():
        escaped_term = _escape_sql_like_wildcards(q.strip().lower())
        term = f"%{escaped_term}%"
        query = query.filter(func.lower(Role.name).like(term, escape="\\"))
    total = query.count()
    query = query.order_by(Role.name.asc()).offset((page - 1) * per_page).limit(per_page)
    return query.all(), total


def get_role_by_id(role_id) -> Role | None:
    """Return Role by id or None."""
    if role_id is None:
        return None
    try:
        rid = int(role_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Role, rid)


def validate_role_name(name: str) -> str | None:
    """Validate role name. Returns error message or None if valid."""
    if not name or not isinstance(name, str):
        return "Role name is required"
    name = name.strip().lower()
    if len(name) < 1:
        return "Role name cannot be empty"
    if len(name) > Role.NAME_MAX_LENGTH:
        return f"Role name must be at most {Role.NAME_MAX_LENGTH} characters"
    if not ROLE_NAME_PATTERN.match(name):
        return "Role name may only contain lowercase letters, digits, and underscore"
    return None


def _validate_role_level(level) -> str | None:
    """Validate default_role_level. Returns error message or None."""
    if level is None:
        return None
    try:
        n = int(level)
        if n < 0 or n > 9999:
            return "default_role_level must be between 0 and 9999"
        return None
    except (TypeError, ValueError):
        return "default_role_level must be an integer"


def create_role(
    name: str,
    description: str | None = None,
    default_role_level: int | None = None,
) -> tuple[Role | None, str | None]:
    """Create a role. Returns (role, None) or (None, error_message)."""
    err = validate_role_name(name)
    if err:
        return None, err
    err = _validate_role_level(default_role_level)
    if err:
        return None, err
    name = name.strip().lower()
    if Role.query.filter_by(name=name).first():
        return None, "Role name already exists"
    role = Role(
        name=name,
        description=(description or "").strip() or None,
        default_role_level=int(default_role_level) if default_role_level is not None else None,
    )
    db.session.add(role)
    db.session.commit()
    db.session.refresh(role)
    return role, None


def update_role(
    role_id: int,
    name: str | None = None,
    description: str | None = None,
    default_role_level: int | None = None,
) -> tuple[Role | None, str | None]:
    """Update a role. Returns (role, None) or (None, error_message)."""
    role = get_role_by_id(role_id)
    if not role:
        return None, "Role not found"
    if name is not None:
        err = validate_role_name(name)
        if err:
            return None, err
        name = name.strip().lower()
        existing = Role.query.filter_by(name=name).first()
        if existing and existing.id != role_id:
            return None, "Role name already exists"
        role.name = name
    if description is not None:
        role.description = (description or "").strip() or None
    if default_role_level is not None:
        err = _validate_role_level(default_role_level)
        if err:
            return None, err
        role.default_role_level = int(default_role_level)
    db.session.commit()
    db.session.refresh(role)
    return role, None


def delete_role(role_id: int) -> tuple[bool, str | None]:
    """Delete a role. Fails if any user has this role. Returns (True, None) or (False, error_message)."""
    role = get_role_by_id(role_id)
    if not role:
        return False, "Role not found"
    user_count = User.query.filter_by(role_id=role_id).count()
    if user_count > 0:
        return False, f"Cannot delete role: {user_count} user(s) have this role"
    db.session.delete(role)
    db.session.commit()
    return True, None
