"""Add JWT token blacklist for logout and token revocation.

Revision ID: 033
Revises: 032
Create Date: 2026-03-22 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '033'
down_revision = '032'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jti VARCHAR(36) NOT NULL UNIQUE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            blacklisted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        )
    """)
    op.execute('CREATE INDEX IF NOT EXISTS ix_token_blacklist_jti ON token_blacklist (jti)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_token_blacklist_user_id ON token_blacklist (user_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_token_blacklist_expires_at ON token_blacklist (expires_at)')


def downgrade():
    op.drop_index('ix_token_blacklist_expires_at', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_user_id', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_jti', table_name='token_blacklist')
    op.drop_table('token_blacklist')
