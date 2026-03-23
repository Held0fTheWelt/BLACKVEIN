"""Add moderator category assignments table to enforce role-based moderation.

Revision ID: 035
Revises: 034
Create Date: 2026-03-22 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '035'
down_revision = '034'
branch_labels = None
depends_on = None


def upgrade():
    # Create the moderator_assignments table
    op.create_table(
        'moderator_assignments',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['forum_categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'category_id', name='uq_moderator_assignment'),
    )

    # Create indexes for efficient queries
    op.create_index('ix_moderator_assignments_user_id', 'moderator_assignments', ['user_id'])
    op.create_index('ix_moderator_assignments_category_id', 'moderator_assignments', ['category_id'])


def downgrade():
    # Drop the table and indexes
    op.drop_index('ix_moderator_assignments_category_id', table_name='moderator_assignments')
    op.drop_index('ix_moderator_assignments_user_id', table_name='moderator_assignments')
    op.drop_table('moderator_assignments')
