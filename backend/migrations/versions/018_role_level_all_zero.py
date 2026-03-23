"""Set all users role_level to 0. Authority is per-user; only seed creates SuperAdmin (100).

Revision ID: 018_role_level_zero
Revises: 017_role_level
Create Date: 2025-03-12

RoleLevel is user authority only. All users start at 0; use seed-dev-user --superadmin
or seed-admin-user to create the initial SuperAdmin (role_level 100).
"""
from alembic import op
import sqlalchemy as sa

revision = "018_role_level_zero"
down_revision = "017_role_level"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("UPDATE users SET role_level = 0"))


def downgrade():
    # Cannot restore previous values; no-op.
    pass
