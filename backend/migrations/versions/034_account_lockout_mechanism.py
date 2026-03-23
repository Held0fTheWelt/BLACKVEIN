"""Add account lockout mechanism: failed_login_attempts and locked_until fields.

Revision ID: 034
Revises: 033
Create Date: 2026-03-22 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade():
    # Add failed_login_attempts column with default value 0
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))

    # Add locked_until column (nullable datetime for tracking lock expiration)
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    # Create index on locked_until for efficient lock status checks
    op.create_index('ix_users_locked_until', 'users', ['locked_until'], unique=False)


def downgrade():
    # Remove the index
    op.drop_index('ix_users_locked_until', table_name='users')

    # Remove columns
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
