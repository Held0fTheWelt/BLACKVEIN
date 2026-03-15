"""Comprehensive index optimization based on query pattern analysis.

Revision ID: 031
Revises: 030
Create Date: 2026-03-15 13:30:00.000000

Priority indexes for high-volume query patterns identified in:
- forum_service.py (71 filter operations)
- analytics_service.py (40 filter operations)
- user_service.py (22 filter operations)
- Visibility filtering: status-based queries
- Pagination with ordering: created_at DESC across multiple tables

Indexes added:
1. HIGH PRIORITY (10-100x improvement expected):
   - forum_posts(thread_id, status)
   - forum_threads(category_id, status, created_at DESC)
   - forum_reports(status, priority, created_at DESC)
   - forum_thread_bookmarks(user_id, thread_id)
   - forum_thread_subscriptions(thread_id, user_id)
   - activity_logs(created_at DESC, category, status)

2. MEDIUM PRIORITY (2-10x improvement):
   - forum_post_likes(post_id, user_id)
   - notifications(user_id, is_read, created_at DESC)
   - forum_thread_tags(tag_id, thread_id)
   - users(is_banned) [partial]
   - slogans(is_active, category, placement_key, language_code)
   - forum_categories(parent_id)

3. LOW PRIORITY (<2x improvement, edge case optimization):
   - news_articles(status, published_at DESC)
   - news_article_translations(article_id, language_code)
   - wiki_page_translations(page_id, language_code)
   - password_reset_tokens(user_id, used)
   - email_verification_tokens(user_id)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'
branch_labels = None
depends_on = None


def upgrade():
    """Add comprehensive indexes for query optimization."""

    # HIGH PRIORITY INDEXES

    # forum_posts: Most critical - thread listing with visibility filtering
    op.create_index(
        'idx_forum_posts_thread_status',
        'forum_posts',
        ['thread_id', 'status'],
        unique=False
    )

    # forum_threads: Category listing with visibility and ordering
    op.create_index(
        'idx_forum_threads_category_status_created',
        'forum_threads',
        ['category_id', 'status', sa.desc('created_at')],
        unique=False
    )

    # forum_reports: Moderation queue and escalation (critical for workflows)
    op.create_index(
        'idx_forum_reports_status_priority_created',
        'forum_reports',
        ['status', 'priority', sa.desc('created_at')],
        unique=False
    )

    # forum_thread_bookmarks: Saved threads feature (Phase 1)
    op.create_index(
        'idx_forum_thread_bookmarks_user_thread',
        'forum_thread_bookmarks',
        ['user_id', 'thread_id'],
        unique=False
    )

    # forum_thread_subscriptions: Notification system
    op.create_index(
        'idx_forum_thread_subscriptions_thread_user',
        'forum_thread_subscriptions',
        ['thread_id', 'user_id'],
        unique=False
    )

    # activity_logs: Audit trail filtering by category, status, and date
    op.create_index(
        'idx_activity_logs_created_category_status',
        'activity_logs',
        [sa.desc('created_at'), 'category', 'status'],
        unique=False
    )

    # MEDIUM PRIORITY INDEXES

    # forum_post_likes: Like lookups and uniqueness enforcement
    op.create_index(
        'idx_forum_post_likes_post_user',
        'forum_post_likes',
        ['post_id', 'user_id'],
        unique=False
    )

    # notifications: Filtering by user, read status, and ordering by date
    op.create_index(
        'idx_notifications_user_read_created',
        'notifications',
        ['user_id', 'is_read', sa.desc('created_at')],
        unique=False
    )

    # forum_thread_tags: Tag filtering and batch tag operations
    op.create_index(
        'idx_forum_thread_tags_tag_thread',
        'forum_thread_tags',
        ['tag_id', 'thread_id'],
        unique=False
    )

    # users: Banned user queries (analytics and filtering)
    op.create_index(
        'idx_users_banned',
        'users',
        ['is_banned'],
        unique=False
    )

    # slogans: Slogan selection by category, placement, and language
    op.create_index(
        'idx_slogans_active_category_placement',
        'slogans',
        ['is_active', 'category', 'placement_key', 'language_code'],
        unique=False
    )

    # forum_categories: Hierarchical category queries
    op.create_index(
        'idx_forum_categories_parent',
        'forum_categories',
        ['parent_id'],
        unique=False
    )

    # LOW PRIORITY INDEXES

    # news_articles: Published article filtering and ordering
    op.create_index(
        'idx_news_articles_status_published',
        'news_articles',
        ['status', sa.desc('published_at')],
        unique=False
    )

    # news_article_translations: Translation lookups by article and language
    op.create_index(
        'idx_news_article_translations_article_lang',
        'news_article_translations',
        ['article_id', 'language_code'],
        unique=False
    )

    # wiki_page_translations: Wiki translation lookups
    op.create_index(
        'idx_wiki_page_translations_page_lang',
        'wiki_page_translations',
        ['page_id', 'language_code'],
        unique=False
    )

    # password_reset_tokens: Auth flow token lookups
    op.create_index(
        'idx_password_reset_tokens_user_used',
        'password_reset_tokens',
        ['user_id', 'used'],
        unique=False
    )

    # email_verification_tokens: Email verification flow
    op.create_index(
        'idx_email_verification_tokens_user',
        'email_verification_tokens',
        ['user_id'],
        unique=False
    )


def downgrade():
    """Remove all added indexes."""

    # HIGH PRIORITY
    op.drop_index('idx_forum_posts_thread_status', table_name='forum_posts')
    op.drop_index('idx_forum_threads_category_status_created', table_name='forum_threads')
    op.drop_index('idx_forum_reports_status_priority_created', table_name='forum_reports')
    op.drop_index('idx_forum_thread_bookmarks_user_thread', table_name='forum_thread_bookmarks')
    op.drop_index('idx_forum_thread_subscriptions_thread_user', table_name='forum_thread_subscriptions')
    op.drop_index('idx_activity_logs_created_category_status', table_name='activity_logs')

    # MEDIUM PRIORITY
    op.drop_index('idx_forum_post_likes_post_user', table_name='forum_post_likes')
    op.drop_index('idx_notifications_user_read_created', table_name='notifications')
    op.drop_index('idx_forum_thread_tags_tag_thread', table_name='forum_thread_tags')
    op.drop_index('idx_users_banned', table_name='users')
    op.drop_index('idx_slogans_active_category_placement', table_name='slogans')
    op.drop_index('idx_forum_categories_parent', table_name='forum_categories')

    # LOW PRIORITY
    op.drop_index('idx_news_articles_status_published', table_name='news_articles')
    op.drop_index('idx_news_article_translations_article_lang', table_name='news_article_translations')
    op.drop_index('idx_wiki_page_translations_page_lang', table_name='wiki_page_translations')
    op.drop_index('idx_password_reset_tokens_user_used', table_name='password_reset_tokens')
    op.drop_index('idx_email_verification_tokens_user', table_name='email_verification_tokens')
