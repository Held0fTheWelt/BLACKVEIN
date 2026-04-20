"""add game experience templates

Revision ID: 037
Revises: 036
Create Date: 2026-03-26
"""
from alembic import op
import sqlalchemy as sa


revision = '037'
down_revision = '036'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'game_experience_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('template_id', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=140), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('style_profile', sa.String(length=80), nullable=False, server_default='retro_pulp'),
        sa.Column('tags_json', sa.JSON(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=40), nullable=False, server_default='authored'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('template_id', name='uq_game_experience_templates_template_id'),
        sa.UniqueConstraint('slug', name='uq_game_experience_templates_slug'),
    )
    op.create_index('ix_game_experience_templates_kind', 'game_experience_templates', ['kind'])
    op.create_index('ix_game_experience_templates_is_published', 'game_experience_templates', ['is_published'])


def downgrade():
    op.drop_index('ix_game_experience_templates_is_published', table_name='game_experience_templates')
    op.drop_index('ix_game_experience_templates_kind', table_name='game_experience_templates')
    op.drop_table('game_experience_templates')
