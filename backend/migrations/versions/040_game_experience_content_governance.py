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
    idx = _game_experience_template_index_names(bind)

    with op.batch_alter_table("game_experience_templates", schema=None) as batch_op:
        if "content_lifecycle" not in cols:
            batch_op.add_column(
                sa.Column("content_lifecycle", sa.String(length=32), nullable=False, server_default="draft"),
            )
        if "governance_provenance_json" not in cols:
            batch_op.add_column(
                sa.Column(
                    "governance_provenance_json",
                    sa.JSON(),
                    nullable=False,
                    server_default="{}",
                ),
            )

        if "ix_game_experience_templates_content_lifecycle" not in idx:
            batch_op.create_index(
                "ix_game_experience_templates_content_lifecycle",
                ["content_lifecycle"],
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


def downgrade():
    bind = op.get_bind()
    idx = _game_experience_template_index_names(bind)
    cols = _game_experience_template_column_names(bind)

    with op.batch_alter_table("game_experience_templates", schema=None) as batch_op:
        if "ix_game_experience_templates_content_lifecycle" in idx:
            batch_op.drop_index("ix_game_experience_templates_content_lifecycle")
        if "governance_provenance_json" in cols:
            batch_op.drop_column("governance_provenance_json")
        if "content_lifecycle" in cols:
            batch_op.drop_column("content_lifecycle")
