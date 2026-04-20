"""Add areas table and user_areas for area-based access control.

Revision ID: 019_areas
Revises: 018_role_level_zero
Create Date: 2026-03-12

Areas: admin-managed; slug 'all' is wildcard. user_areas: many-to-many user<->area.
"""
from alembic import op
import sqlalchemy as sa

revision = "019_areas"
down_revision = "018_role_level_zero"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_areas_slug"), "areas", ["slug"], unique=True)

    op.create_table(
        "user_areas",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "area_id"),
    )

    # Seed default areas (insert only if not present)
    conn = op.get_bind()
    defaults = [
        ("all", "all", "Global access (wildcard). Users with this area can access all area-scoped features.", 1),
        ("community", "community", "Community moderation and content.", 0),
        ("website content", "website_content", "Website and editorial content.", 0),
        ("rules and system", "rules_and_system", "Rules and system configuration.", 0),
        ("ai integration", "ai_integration", "AI integration features.", 0),
        ("game", "game", "Game-related features.", 0),
        ("wiki", "wiki", "Wiki and documentation.", 0),
    ]
    for name, slug, description, is_system in defaults:
        conn.execute(
            sa.text(
                "INSERT INTO areas (name, slug, description, is_system, created_at, updated_at) "
                "SELECT :name, :slug, :desc, :is_sys, datetime('now'), datetime('now') "
                "WHERE NOT EXISTS (SELECT 1 FROM areas WHERE slug = :slug)"
            ),
            {"name": name, "slug": slug, "desc": description, "is_sys": is_system},
        )


def downgrade():
    op.drop_table("user_areas")
    op.drop_index(op.f("ix_areas_slug"), table_name="areas")
    op.drop_table("areas")
