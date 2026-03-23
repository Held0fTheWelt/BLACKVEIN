"""Add role_level to users; add description and default_role_level to roles; seed QA.

Revision ID: 017_role_level
Revises: 016_site_settings
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "017_role_level"
down_revision = "016_site_settings"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    # roles: add description, default_role_level
    if not any(c["name"] == "description" for c in insp.get_columns("roles")):
        op.add_column("roles", sa.Column("description", sa.String(length=512), nullable=True))
    if not any(c["name"] == "default_role_level" for c in insp.get_columns("roles")):
        op.add_column("roles", sa.Column("default_role_level", sa.Integer(), nullable=True))

    # Set default_role_level for existing roles
    op.execute(
        sa.text("UPDATE roles SET default_role_level = 0 WHERE name = 'user' AND default_role_level IS NULL")
    )
    op.execute(
        sa.text("UPDATE roles SET default_role_level = 10 WHERE name = 'moderator' AND default_role_level IS NULL")
    )
    op.execute(
        sa.text("UPDATE roles SET default_role_level = 50 WHERE name = 'admin' AND default_role_level IS NULL")
    )
    # Insert QA if not present
    op.execute(
        sa.text(
            "INSERT INTO roles (name, default_role_level) SELECT 'qa', 5 "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'qa')"
        )
    )
    op.execute(
        sa.text("UPDATE roles SET default_role_level = 5 WHERE name = 'qa' AND default_role_level IS NULL")
    )

    # users: add role_level (SQLite does not support ALTER COLUMN SET NOT NULL; add with server_default)
    if not any(c["name"] == "role_level" for c in insp.get_columns("users")):
        op.add_column(
            "users",
            sa.Column("role_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )
        # Backfill from role default
        op.execute(
            sa.text(
                "UPDATE users SET role_level = COALESCE("
                "(SELECT default_role_level FROM roles WHERE roles.id = users.role_id), 0)"
            )
        )


def downgrade():
    op.drop_column("users", "role_level")
    op.drop_column("roles", "default_role_level")
    op.drop_column("roles", "description")
