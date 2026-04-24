"""Add observability configuration and credential tables for Langfuse

Revision ID: 044
Revises: 043
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create observability_configs and observability_credentials tables."""
    # Create observability_configs table
    op.create_table(
        "observability_configs",
        sa.Column("service_id", sa.String(64), nullable=False, primary_key=True),
        sa.Column("service_type", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False, server_default="https://cloud.langfuse.com"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("environment", sa.String(64), nullable=False, server_default="development"),
        sa.Column("release", sa.String(128), nullable=False, server_default="unknown"),
        sa.Column("sample_rate", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("capture_prompts", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("capture_outputs", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("capture_retrieval", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("redaction_mode", sa.String(32), nullable=False, server_default="strict"),
        sa.Column("credential_configured", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("credential_fingerprint", sa.String(256), nullable=True),
        sa.Column("health_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create observability_credentials table
    op.create_table(
        "observability_credentials",
        sa.Column("credential_id", sa.String(128), nullable=False, primary_key=True),
        sa.Column("service_id", sa.String(64), nullable=False),
        sa.Column("secret_name", sa.String(128), nullable=False),
        sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_dek", sa.LargeBinary(), nullable=False),
        sa.Column("secret_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("dek_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("dek_algorithm", sa.String(64), nullable=False, server_default="AES-256-GCM"),
        sa.Column("kek_key_id", sa.String(128), nullable=True),
        sa.Column("secret_fingerprint", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("rotation_in_progress", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["observability_configs.service_id"],
            name="fk_observability_credentials_service_id",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_observability_credentials_service_id",
        "observability_credentials",
        ["service_id"],
    )
    op.create_index(
        "ix_observability_credentials_secret_fingerprint",
        "observability_credentials",
        ["secret_fingerprint"],
    )


def downgrade() -> None:
    """Drop observability tables."""
    op.drop_table("observability_credentials")
    op.drop_table("observability_configs")
