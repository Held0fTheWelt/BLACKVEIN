"""game experience content lifecycle and governance provenance

Revision ID: 040
Revises: 039
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa


revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "game_experience_templates",
        sa.Column("content_lifecycle", sa.String(length=32), nullable=False, server_default="draft"),
    )
    op.add_column(
        "game_experience_templates",
        sa.Column(
            "governance_provenance_json",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "UPDATE game_experience_templates SET content_lifecycle = 'published' "
                "WHERE is_published IS true"
            )
        )
    else:
        op.execute(
            sa.text(
                "UPDATE game_experience_templates SET content_lifecycle = 'published' "
                "WHERE is_published = 1"
            )
        )
    op.create_index(
        "ix_game_experience_templates_content_lifecycle",
        "game_experience_templates",
        ["content_lifecycle"],
    )


def downgrade():
    op.drop_index("ix_game_experience_templates_content_lifecycle", table_name="game_experience_templates")
    op.drop_column("game_experience_templates", "governance_provenance_json")
    op.drop_column("game_experience_templates", "content_lifecycle")
