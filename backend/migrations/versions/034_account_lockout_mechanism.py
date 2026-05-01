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
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Add failed_login_attempts column with default value 0
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))

        # Add locked_until column (nullable datetime for tracking lock expiration)
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

        # Create index on locked_until for efficient lock status checks
        batch_op.create_index('ix_users_locked_until', ['locked_until'], unique=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Remove the index
        batch_op.drop_index('ix_users_locked_until')

        # Remove columns
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
