"""roles table and users.role_id (replace users.role string)

Revision ID: 007_roles
Revises: 006_evt
Create Date: 2025-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "007_roles"
down_revision = "006_evt"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if inspect(conn).has_table("roles"):
        return
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.execute("INSERT INTO roles (name) VALUES ('user')")
    op.execute("INSERT INTO roles (name) VALUES ('moderator')")
    op.execute("INSERT INTO roles (name) VALUES ('editor')")
    op.execute("INSERT INTO roles (name) VALUES ('admin')")

    op.add_column(
        "users",
        sa.Column("role_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text("UPDATE users SET role_id = (SELECT id FROM roles WHERE roles.name = users.role)")
    )
    op.alter_column(
        "users",
        "role_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key("fk_users_role_id", "users", "roles", ["role_id"], ["id"])
    op.drop_column("users", "role")


def downgrade():
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=True),
    )
    op.execute(
        sa.text("UPDATE users SET role = (SELECT name FROM roles WHERE roles.id = users.role_id)")
    )
    op.alter_column("users", "role", nullable=False)
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_table("roles")
