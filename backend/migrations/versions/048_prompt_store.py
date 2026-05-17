"""prompt store table

Revision ID: 048
Revises: 047
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "prompt_store_prompts" not in existing:
        op.create_table(
            "prompt_store_prompts",
            sa.Column("prompt_key", sa.String(length=160), primary_key=True),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("category", sa.String(length=96), nullable=False),
            sa.Column("prompt_type", sa.String(length=64), nullable=False, server_default="runtime_prompt"),
            sa.Column("domain", sa.String(length=96), nullable=False, server_default="ai_stack"),
            sa.Column("template", sa.Text(), nullable=False),
            sa.Column("variables_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("tags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("source_path", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("source_symbol", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("seed_version", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("seed_content_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("current_content_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_editable", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_seeded", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("last_seeded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_by", sa.String(length=128), nullable=True),
        )
        op.create_index("ix_prompt_store_prompts_category", "prompt_store_prompts", ["category"])
        op.create_index("ix_prompt_store_prompts_prompt_type", "prompt_store_prompts", ["prompt_type"])
        op.create_index("ix_prompt_store_prompts_domain", "prompt_store_prompts", ["domain"])
        op.create_index("ix_prompt_store_prompts_is_active", "prompt_store_prompts", ["is_active"])
        op.create_index("ix_prompt_store_prompts_is_seeded", "prompt_store_prompts", ["is_seeded"])


def downgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    if "prompt_store_prompts" in existing:
        op.drop_index("ix_prompt_store_prompts_is_seeded", table_name="prompt_store_prompts")
        op.drop_index("ix_prompt_store_prompts_is_active", table_name="prompt_store_prompts")
        op.drop_index("ix_prompt_store_prompts_domain", table_name="prompt_store_prompts")
        op.drop_index("ix_prompt_store_prompts_prompt_type", table_name="prompt_store_prompts")
        op.drop_index("ix_prompt_store_prompts_category", table_name="prompt_store_prompts")
        op.drop_table("prompt_store_prompts")
