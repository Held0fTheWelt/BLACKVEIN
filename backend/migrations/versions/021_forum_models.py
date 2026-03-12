"""Forum module tables: categories, threads, posts, likes, reports, subscriptions.

Revision ID: 021_forum_models
Revises: 020_feature_areas
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


revision = "021_forum_models"
down_revision = "020_feature_areas"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "forum_categories" not in existing_tables:
        op.create_table(
            "forum_categories",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("forum_categories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("slug", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
            sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("required_role", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("slug", name="uq_forum_category_slug"),
        )
        op.create_index("ix_forum_categories_slug", "forum_categories", ["slug"], unique=False)

    if "forum_threads" not in existing_tables:
        op.create_table(
            "forum_threads",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("forum_categories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()),
            sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_post_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_post_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("slug", name="uq_forum_thread_slug"),
        )
        op.create_index("ix_forum_threads_slug", "forum_threads", ["slug"], unique=False)

    if "forum_posts" not in existing_tables:
        op.create_table(
            "forum_posts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("thread_id", sa.Integer(), sa.ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("parent_post_id", sa.Integer(), sa.ForeignKey("forum_posts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="visible"),
            sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("edited_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_forum_posts_thread_id", "forum_posts", ["thread_id"], unique=False)

    if "forum_post_likes" not in existing_tables:
        op.create_table(
            "forum_post_likes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("post_id", sa.Integer(), sa.ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("post_id", "user_id", name="uq_forum_post_like_post_user"),
        )

    if "forum_reports" not in existing_tables:
        op.create_table(
            "forum_reports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("target_type", sa.String(length=16), nullable=False),
            sa.Column("target_id", sa.Integer(), nullable=False),
            sa.Column("reported_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reason", sa.String(length=512), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
            sa.Column("handled_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "forum_thread_subscriptions" not in existing_tables:
        op.create_table(
            "forum_thread_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("thread_id", sa.Integer(), sa.ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("thread_id", "user_id", name="uq_forum_thread_subscription_thread_user"),
        )

    # Add foreign key from forum_threads.last_post_id to forum_posts.id (needs posts table to exist).
    # SQLite does not support ALTER TABLE ADD CONSTRAINT in the same way; in that case we skip the
    # explicit constraint here (the ORM-level relationship still works) to keep migrations runnable
    # without batch mode. Other databases will get a proper FK constraint.
    if bind.dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_forum_threads_last_post",
            "forum_threads",
            "forum_posts",
            ["last_post_id"],
            ["id"],
            ondelete="SET NULL",
        )

def downgrade():
    # Drop FK constraint only if it exists (non-SQLite backends).
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_forum_threads_last_post", "forum_threads", type_="foreignkey")
    op.drop_table("forum_thread_subscriptions")
    op.drop_table("forum_reports")
    op.drop_table("forum_post_likes")
    op.drop_index("ix_forum_posts_thread_id", table_name="forum_posts")
    op.drop_table("forum_posts")
    op.drop_index("ix_forum_threads_slug", table_name="forum_threads")
    op.drop_table("forum_threads")
    op.drop_index("ix_forum_categories_slug", table_name="forum_categories")
    op.drop_table("forum_categories")

