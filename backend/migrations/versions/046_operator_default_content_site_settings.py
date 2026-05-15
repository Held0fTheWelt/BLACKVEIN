"""Seed operator default content module / experience template in site_settings.

Revision ID: 046
Revises: 045
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert defaults only when keys are absent (idempotent)."""
    conn = op.get_bind()
    pairs = (
        ("default_content_module_id", "god_of_carnage"),
        ("default_experience_template_id", "god_of_carnage_solo"),
    )
    for key, value in pairs:
        conn.execute(
            sa.text(
                "INSERT INTO site_settings (key, value) "
                "SELECT :k, :v WHERE NOT EXISTS (SELECT 1 FROM site_settings WHERE key = :k)"
            ),
            {"k": key, "v": value},
        )


def downgrade() -> None:
    """Remove seeded keys only if values still match seed (avoid deleting admin overrides)."""
    conn = op.get_bind()
    expected = (
        ("default_content_module_id", "god_of_carnage"),
        ("default_experience_template_id", "god_of_carnage_solo"),
    )
    for key, value in expected:
        conn.execute(
            sa.text("DELETE FROM site_settings WHERE key = :k AND value = :v"),
            {"k": key, "v": value},
        )
