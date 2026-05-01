"""add email and reset tokens

Revision ID: 002_email_reset
Revises: 001_initial
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "002_email_reset"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def _users_has_column(conn, name):
    return any(c["name"] == name for c in inspect(conn).get_columns("users"))


def upgrade():
    conn = op.get_bind()
    if not _users_has_column(conn, "email"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(sa.Column("email", sa.String(length=254), nullable=True))
            batch_op.create_unique_constraint("uq_users_email", ["email"])

    if not inspect(conn).has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )


def downgrade():
    op.drop_table("password_reset_tokens")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("email")
