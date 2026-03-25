"""Add password_history field to users table for password reuse prevention.

Revision ID: 036
Revises: 035
Create Date: 2026-03-24 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade():
    # Add password_history column to users table
    op.add_column('users', sa.Column('password_history', sa.Text(), nullable=True))


def downgrade():
    # Remove password_history column
    op.drop_column('users', 'password_history')
