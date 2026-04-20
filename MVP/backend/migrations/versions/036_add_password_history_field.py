"""Add password_history field to users table for password reuse prevention.

Revision ID: 036
Revises: 035
Create Date: 2026-03-24 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '036'
down_revision = '035'
branch_labels = None
depends_on = None


def upgrade():
    # Add password_history column to users table (if it doesn't already exist)
    # This check prevents errors when the column already exists from db.create_all()
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'password_history' not in columns:
        op.add_column('users', sa.Column('password_history', sa.Text(), nullable=True))


def downgrade():
    # Remove password_history column
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'password_history' in columns:
        op.drop_column('users', 'password_history')
