"""Operations invoked from Flask CLI (and tests); keep DB logic out of run.py where practical."""

from __future__ import annotations

from app.extensions import db
from app.models import Role, User
from app.models.area import assign_user_area_all, ensure_areas_seeded
from app.models.role import ensure_roles_seeded


def ensure_superadmin_for_username(username: str) -> str:
    """
    Promote existing user: admin role, role_level 100, attach area 'all'.

    Returns a one-line status message. Raises ValueError if user or admin role missing.
    """
    u_name = (username or "").strip()
    if not u_name:
        raise ValueError("username required")

    ensure_roles_seeded()
    ensure_areas_seeded()

    user = User.query.filter(db.func.lower(User.username) == u_name.lower()).first()
    if not user:
        raise ValueError(f"user not found: {u_name!r}")

    admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
    if not admin_role:
        raise ValueError("admin role missing; run migrations or flask init-db")

    old_role = user.role_rel.name if user.role_rel else "?"
    old_level = user.role_level
    user.role_id = admin_role.id
    user.role_level = 100
    assign_user_area_all(user)
    db.session.commit()

    return (
        f"Updated {user.username}: role {old_role} -> admin, "
        f"role_level {old_level} -> 100, area 'all' attached if missing."
    )
