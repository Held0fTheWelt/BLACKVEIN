"""game experience content lifecycle and governance provenance

Revision ID: 040
Revises: 039
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def _game_experience_template_column_names(bind) -> set[str]:
    insp = inspect(bind)
    if not insp.has_table("game_experience_templates"):
        return set()
    return {c["name"] for c in insp.get_columns("game_experience_templates")}


def _game_experience_template_index_names(bind) -> set[str]:
    insp = inspect(bind)
    if not insp.has_table("game_experience_templates"):
        return set()
    return {ix["name"] for ix in insp.get_indexes("game_experience_templates")}


def upgrade():
    bind = op.get_bind()
    cols = _game_experience_template_column_names(bind)

    if "content_lifecycle" not in cols:
        op.add_column(
            "game_experience_templates",
            sa.Column("content_lifecycle", sa.String(length=32), nullable=False, server_default="draft"),
        )
    if "governance_provenance_json" not in cols:
        op.add_column(
            "game_experience_templates",
            sa.Column(
                "governance_provenance_json",
                sa.JSON(),
                nullable=False,
                server_default="{}",
            ),
        )

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

    idx = _game_experience_template_index_names(bind)
    if "ix_game_experience_templates_content_lifecycle" not in idx:
        op.create_index(
            "ix_game_experience_templates_content_lifecycle",
            "game_experience_templates",
            ["content_lifecycle"],
        )


def downgrade():
    bind = op.get_bind()
    idx = _game_experience_template_index_names(bind)
    if "ix_game_experience_templates_content_lifecycle" in idx:
        op.drop_index("ix_game_experience_templates_content_lifecycle", table_name="game_experience_templates")
    cols = _game_experience_template_column_names(bind)
    if "governance_provenance_json" in cols:
        op.drop_column("game_experience_templates", "governance_provenance_json")
    if "content_lifecycle" in cols:
        op.drop_column("game_experience_templates", "content_lifecycle")
