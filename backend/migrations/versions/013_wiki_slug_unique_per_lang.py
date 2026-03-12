"""Wiki: unique slug per language across all pages.

Revision ID: 013_wiki_slug
Revises: 012_wiki_pages
Create Date: 2025-03-11

"""
from alembic import op

revision = "013_wiki_slug"
down_revision = "012_wiki_pages"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("wiki_page_translations", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_wiki_page_translation_lang_slug", ["language_code", "slug"])


def downgrade():
    with op.batch_alter_table("wiki_page_translations", schema=None) as batch_op:
        batch_op.drop_constraint("uq_wiki_page_translation_lang_slug", type_="unique")
