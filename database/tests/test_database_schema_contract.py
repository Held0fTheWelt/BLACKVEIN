from __future__ import annotations

from sqlalchemy import inspect


EXPECTED_TABLES = {
    "activity_logs",
    "areas",
    "email_verification_tokens",
    "feature_areas",
    "forum_categories",
    "forum_post_likes",
    "forum_posts",
    "forum_reports",
    "forum_tags",
    "forum_thread_bookmarks",
    "forum_thread_subscriptions",
    "forum_thread_tags",
    "forum_threads",
    "game_characters",
    "game_experience_templates",
    "game_save_slots",
    "moderator_assignments",
    "news_article_forum_threads",
    "news_article_translations",
    "news_articles",
    "notifications",
    "password_histories",
    "password_reset_tokens",
    "refresh_tokens",
    "roles",
    "site_settings",
    "slogans",
    "token_blacklist",
    "user_areas",
    "users",
    "wiki_page_forum_threads",
    "wiki_page_translations",
    "wiki_pages",
}


CORE_TABLE_COLUMNS = {
    "users": {"id", "username", "email", "password_hash", "role_id", "role_level", "is_banned", "is_active"},
    "roles": {"id", "name", "default_role_level"},
    "areas": {"id", "name", "slug", "is_system", "created_at", "updated_at"},
    "forum_threads": {"id", "category_id", "author_id", "slug", "title", "status", "reply_count", "last_post_id"},
    "forum_posts": {"id", "thread_id", "author_id", "parent_post_id", "content", "status", "like_count"},
    "news_article_translations": {"id", "article_id", "language_code", "title", "slug", "content"},
    "wiki_page_translations": {"id", "page_id", "language_code", "title", "slug", "content_markdown"},
    "game_experience_templates": {"id", "template_id", "slug", "title", "kind", "payload_json", "is_published"},
    "game_save_slots": {"id", "user_id", "character_id", "slot_key", "title", "template_id", "status", "metadata_json"},
    "refresh_tokens": {"id", "jti", "user_id", "refresh_token", "expires_at", "revoked_at"},
    "token_blacklist": {"id", "jti", "user_id", "blacklisted_at", "expires_at"},
}


NOT_NULL_COLUMNS = {
    "users": {"id", "username", "password_hash", "role_id", "role_level", "is_banned", "is_active"},
    "roles": {"id", "name"},
    "areas": {"id", "name", "slug", "is_system", "created_at", "updated_at"},
    "forum_categories": {"id", "slug", "title", "sort_order", "is_active", "is_private", "created_at", "updated_at"},
    "forum_threads": {"id", "category_id", "slug", "title", "status", "is_pinned", "is_locked", "is_featured", "view_count", "reply_count", "created_at", "updated_at"},
    "forum_posts": {"id", "thread_id", "content", "status", "like_count", "created_at", "updated_at"},
    "notifications": {"id", "user_id", "event_type", "target_type", "target_id", "message", "is_read", "created_at"},
    "game_save_slots": {"id", "user_id", "slot_key", "title", "template_id", "status", "created_at", "updated_at"},
    "game_experience_templates": {"id", "template_id", "slug", "title", "kind", "style_profile", "tags_json", "payload_json", "source", "version", "is_published", "created_at", "updated_at"},
}


FOREIGN_KEY_EXPECTATIONS = {
    "users": {("role_id", "roles")},
    "user_areas": {("user_id", "users"), ("area_id", "areas")},
    "feature_areas": {("area_id", "areas")},
    "password_histories": {("user_id", "users")},
    "password_reset_tokens": {("user_id", "users")},
    "email_verification_tokens": {("user_id", "users")},
    "refresh_tokens": {("user_id", "users")},
    "token_blacklist": {("user_id", "users")},
    "forum_categories": {("parent_id", "forum_categories")},
    "forum_threads": {("category_id", "forum_categories"), ("author_id", "users"), ("last_post_id", "forum_posts")},
    "forum_posts": {("thread_id", "forum_threads"), ("author_id", "users"), ("parent_post_id", "forum_posts"), ("edited_by", "users")},
    "forum_post_likes": {("post_id", "forum_posts"), ("user_id", "users")},
    "forum_thread_subscriptions": {("thread_id", "forum_threads"), ("user_id", "users")},
    "forum_thread_bookmarks": {("thread_id", "forum_threads"), ("user_id", "users")},
    "forum_thread_tags": {("thread_id", "forum_threads"), ("tag_id", "forum_tags")},
    "moderator_assignments": {("user_id", "users"), ("category_id", "forum_categories"), ("assigned_by", "users")},
    "news_articles": {("author_id", "users"), ("discussion_thread_id", "forum_threads")},
    "news_article_translations": {("article_id", "news_articles"), ("reviewed_by", "users")},
    "news_article_forum_threads": {("article_id", "news_articles"), ("thread_id", "forum_threads")},
    "wiki_pages": {("parent_id", "wiki_pages"), ("discussion_thread_id", "forum_threads")},
    "wiki_page_translations": {("page_id", "wiki_pages"), ("reviewed_by", "users")},
    "wiki_page_forum_threads": {("page_id", "wiki_pages"), ("thread_id", "forum_threads")},
    "game_characters": {("user_id", "users")},
    "game_save_slots": {("user_id", "users"), ("character_id", "game_characters")},
}


TIMESTAMP_TABLES = {
    "activity_logs": {"created_at"},
    "areas": {"created_at", "updated_at"},
    "forum_categories": {"created_at", "updated_at"},
    "forum_threads": {"created_at", "updated_at"},
    "forum_posts": {"created_at", "updated_at"},
    "game_characters": {"created_at", "updated_at"},
    "game_experience_templates": {"created_at", "updated_at"},
    "game_save_slots": {"created_at", "updated_at"},
    "news_articles": {"created_at", "updated_at"},
    "notifications": {"created_at"},
    "refresh_tokens": {"created_at"},
    "slogans": {"created_at", "updated_at"},
    "users": {"created_at", "updated_at"},
    "wiki_pages": {"created_at", "updated_at"},
}


def _column_map(inspector, table_name: str) -> dict:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


class TestDatabaseSchemaContract:
    def test_all_expected_tables_exist(self, db):
        inspector = inspect(db.engine)
        assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))

    def test_core_tables_expose_expected_columns(self, db):
        inspector = inspect(db.engine)
        for table_name, expected_columns in CORE_TABLE_COLUMNS.items():
            actual_columns = set(_column_map(inspector, table_name))
            assert expected_columns.issubset(actual_columns), f"{table_name} missing columns"

    def test_not_nullable_columns_match_contract(self, db):
        inspector = inspect(db.engine)
        for table_name, expected_not_null in NOT_NULL_COLUMNS.items():
            columns = _column_map(inspector, table_name)
            for column_name in expected_not_null:
                assert column_name in columns, f"{table_name}.{column_name} missing"
                assert columns[column_name]["nullable"] is False, f"{table_name}.{column_name} must be non-nullable"

    def test_foreign_keys_cover_expected_relationships(self, db):
        inspector = inspect(db.engine)
        for table_name, expected_pairs in FOREIGN_KEY_EXPECTATIONS.items():
            actual_pairs = {
                (fk["constrained_columns"][0], fk["referred_table"])
                for fk in inspector.get_foreign_keys(table_name)
                if fk.get("constrained_columns") and fk.get("referred_table")
            }
            assert expected_pairs.issubset(actual_pairs), f"{table_name} missing foreign keys"

    def test_mutable_tables_have_timestamp_columns(self, db):
        inspector = inspect(db.engine)
        for table_name, expected_columns in TIMESTAMP_TABLES.items():
            actual_columns = set(_column_map(inspector, table_name))
            assert expected_columns.issubset(actual_columns), f"{table_name} missing timestamps"

    def test_join_and_lookup_tables_have_primary_keys(self, db):
        inspector = inspect(db.engine)
        for table_name in [
            "user_areas",
            "feature_areas",
            "forum_post_likes",
            "forum_thread_subscriptions",
            "forum_thread_bookmarks",
            "forum_thread_tags",
            "moderator_assignments",
            "site_settings",
        ]:
            primary_key = inspector.get_pk_constraint(table_name)
            assert primary_key["constrained_columns"], f"{table_name} must define a primary key"

    def test_indexed_lookup_columns_exist_on_query_heavy_tables(self, db):
        inspector = inspect(db.engine)
        indexed_columns_by_table = {
            "areas": {"slug"},
            "forum_categories": {"slug"},
            "forum_threads": {"slug"},
            "forum_posts": {"thread_id"},
            "forum_tags": {"slug"},
            "news_article_translations": {"article_id", "language_code", "slug"},
            "wiki_page_translations": {"page_id", "language_code", "slug"},
            "game_experience_templates": {"template_id", "slug", "kind", "is_published"},
            "game_save_slots": {"user_id", "character_id", "template_id", "run_id"},
            "notifications": {"user_id", "event_type", "created_at"},
            "refresh_tokens": {"jti", "user_id", "expires_at", "revoked_at"},
            "token_blacklist": {"jti", "expires_at"},
            "users": {"username"},
            "wiki_pages": {"key", "discussion_thread_id"},
            "news_articles": {"discussion_thread_id"},
        }

        for table_name, expected_indexed_columns in indexed_columns_by_table.items():
            indexed_columns = set()
            for index in inspector.get_indexes(table_name):
                indexed_columns.update(index.get("column_names") or [])
            for constraint in inspector.get_unique_constraints(table_name):
                indexed_columns.update(constraint.get("column_names") or [])
            pk = inspector.get_pk_constraint(table_name)
            indexed_columns.update(pk.get("constrained_columns") or [])
            assert expected_indexed_columns.issubset(indexed_columns), f"{table_name} missing indexed lookup columns"
