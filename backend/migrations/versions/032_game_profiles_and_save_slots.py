"""Add game character profiles and save slot metadata.

Revision ID: 032
Revises: 031
Create Date: 2026-03-19 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '032'
down_revision = '031'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'game_characters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_game_characters_user_id', 'game_characters', ['user_id'], unique=False)

    op.create_table(
        'game_save_slots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('game_characters.id', ondelete='SET NULL'), nullable=True),
        sa.Column('slot_key', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=140), nullable=False),
        sa.Column('template_id', sa.String(length=120), nullable=False),
        sa.Column('template_title', sa.String(length=160), nullable=True),
        sa.Column('run_id', sa.String(length=120), nullable=True),
        sa.Column('kind', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_played_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'slot_key', name='uq_game_save_slots_user_slot_key'),
    )
    op.create_index('ix_game_save_slots_user_id', 'game_save_slots', ['user_id'], unique=False)
    op.create_index('ix_game_save_slots_character_id', 'game_save_slots', ['character_id'], unique=False)
    op.create_index('ix_game_save_slots_run_id', 'game_save_slots', ['run_id'], unique=False)
    op.create_index('ix_game_save_slots_template_id', 'game_save_slots', ['template_id'], unique=False)


def downgrade():
    op.drop_index('ix_game_save_slots_template_id', table_name='game_save_slots')
    op.drop_index('ix_game_save_slots_run_id', table_name='game_save_slots')
    op.drop_index('ix_game_save_slots_character_id', table_name='game_save_slots')
    op.drop_index('ix_game_save_slots_user_id', table_name='game_save_slots')
    op.drop_table('game_save_slots')

    op.drop_index('ix_game_characters_user_id', table_name='game_characters')
    op.drop_table('game_characters')
