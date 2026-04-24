"""Add canonical readiness gates schema for AI Stack release readiness tracking

Revision ID: 045
Revises: 044
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create readiness_gates table for canonical gate definitions."""
    op.create_table(
        "readiness_gates",
        sa.Column("gate_id", sa.String(128), nullable=False, primary_key=True),
        sa.Column("gate_name", sa.String(256), nullable=False, index=True),
        sa.Column("owner_service", sa.String(128), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, default="open", index=True),
        sa.Column("reason", sa.Text(), nullable=False, default=""),
        sa.Column("expected_evidence", sa.Text(), nullable=False, default=""),
        sa.Column("actual_evidence", sa.Text(), nullable=True),
        sa.Column("evidence_path", sa.String(512), nullable=True),
        sa.Column("truth_source", sa.String(64), nullable=False, default="live_endpoint"),
        sa.Column("remediation", sa.Text(), nullable=False, default=""),
        sa.Column("remediation_steps_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("checked_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for fast lookups
    op.create_index("ix_readiness_gates_status", "readiness_gates", ["status"])
    op.create_index("ix_readiness_gates_owner_service", "readiness_gates", ["owner_service"])
    op.create_index("ix_readiness_gates_last_checked_at", "readiness_gates", ["last_checked_at"])


def downgrade() -> None:
    """Drop readiness_gates table."""
    op.drop_table("readiness_gates")
