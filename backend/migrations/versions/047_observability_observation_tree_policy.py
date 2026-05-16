"""Add granular Langfuse observation tree policy.

Revision ID: 047
Revises: 046
Create Date: 2026-05-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "observability_configs",
        sa.Column(
            "enabled_observation_trees",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"minimal\"]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("observability_configs", "enabled_observation_trees")
