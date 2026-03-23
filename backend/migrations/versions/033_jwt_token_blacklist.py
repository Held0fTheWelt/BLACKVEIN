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
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('jti', sa.String(length=36), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('blacklisted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_token_blacklist_jti', 'token_blacklist', ['jti'], unique=False)
    op.create_index('ix_token_blacklist_user_id', 'token_blacklist', ['user_id'], unique=False)
    op.create_index('ix_token_blacklist_expires_at', 'token_blacklist', ['expires_at'], unique=False)


def downgrade():
    op.drop_index('ix_token_blacklist_expires_at', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_user_id', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_jti', table_name='token_blacklist')
    op.drop_table('token_blacklist')
