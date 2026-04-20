"""email_verification_tokens table (0.0.7)

Revision ID: 006_evt
Revises: 005_email_verified
Create Date: 2025-03-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "006_evt"
down_revision = "005_email_verified"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if inspect(conn).has_table("email_verification_tokens"):
        return
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="activation"),
        sa.Column("sent_to_email", sa.String(length=254), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade():
    op.drop_table("email_verification_tokens")
