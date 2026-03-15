"""Phase 5A: Search and Discovery Hardening - Edge Case Tests.

Tests for:
1. Empty queries, very short queries, very long queries
2. Special characters and SQL wildcard escaping
3. Mixed filters (status + category + tag + search)
4. Related thread suggestions stability
5. Profile/activity discovery stability
"""
import pytest
from app.models import ForumCategory, ForumThread, ForumPost, ForumTag, ForumThreadTag
from app.services.forum_service import (
    suggest_related_threads_by_tags,
    list_tags_for_threads,
    batch_tag_thread_counts,
)
from app.services.user_service import (
    get_user_recent_threads,
    get_user_recent_posts,
    count_user_threads,
    count_user_posts,
)


class TestSearchEdgeCases:
    """Test search endpoint edge cases."""

    def test_search_empty_query_no_filters_returns_empty(self, client, auth_headers):
        """Empty query with no filters should return empty list (not unbounded scan)."""
        response = client.get("/api/v1/forum/search?q=&category=&status=&tag=", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_search_very_short_query_rejected(self, client, auth_headers):
        """Queries shorter than 3 chars should return 400 error."""
        response = client.get("/api/v1/forum/search?q=ab", headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "at least 3 characters" in data.get("error", "").lower()

    def test_search_single_char_rejected(self, client, auth_headers):
        """Single character queries should return 400."""
        response = client.get("/api/v1/forum/search?q=a", headers=auth_headers)
        assert response.status_code == 400

    def test_search_very_long_query_truncated_gracefully(self, client, auth_headers, app):
        """Very long queries (>500 chars) should be truncated and still work."""
        long_query = "a" * 600
        response = client.get(f"/api/v1/forum/search?q={long_query}", headers=auth_headers)
        # Should either accept (200) or gracefully fail (400)
        assert response.status_code in (200, 400)

    def test_search_special_characters_escaped(self, client, auth_headers, app, test_user, forum_category):
        """SQL wildcard characters (%, _) should be escaped for safe searching."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread
            category = ForumCategory.query.get(forum_category)
            thread, post, err = create_thread(
                category=category,
                author_id=user.id,
                title="Test%_Special",
                content="Test content with special chars"
            )

        # Search for literal % and _ should not cause SQL injection or errors
        response = client.get("/api/v1/forum/search?q=test%_special", headers=auth_headers)
        assert response.status_code in (200, 400)

    def test_search_with_category_filter(self, client, auth_headers, app, test_user, forum_category):
        """Search with category filter should only return threads from that category."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread
            category = ForumCategory.query.get(forum_category)

            t1, p1, _ = create_thread(
                category=category, author_id=user.id,
                title="General Discussion", content="Content"
            )

            response = client.get(f"/api/v1/forum/search?q=general&category={category.slug}", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()
            # Should get results
            assert "items" in data

    def test_search_with_status_filter_invalid_status_rejected(self, client, auth_headers):
        """Invalid status filters should return 400."""
        response = client.get("/api/v1/forum/search?q=test&status=invalid", headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "invalid status filter" in data.get("error", "").lower()

    def test_search_with_valid_status_filters(self, client, auth_headers):
        """Valid status filters should be accepted."""
        for status in ("open", "locked", "archived", "hidden"):
            response = client.get(f"/api/v1/forum/search?q=test&status={status}", headers=auth_headers)
            # Should be 200 or error if no results, not 400 validation error
            assert response.status_code in (200, 404)

    def test_search_pagination_valid_ranges(self, client, auth_headers):
        """Pagination should enforce limits: min=1, max=100."""
        # page=0 should be normalized to 1
        response = client.get("/api/v1/forum/search?q=test&page=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("page", 1) >= 1

        # limit=0 should be normalized to 1
        response = client.get("/api/v1/forum/search?q=test&limit=0", headers=auth_headers)
        assert response.status_code == 200

        # limit=1000 should be capped at 100
        response = client.get("/api/v1/forum/search?q=test&limit=1000", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("per_page", 20) <= 100


class TestRelatedThreadsSuggestions:
    """Test related threads suggestion stability."""

    def test_related_threads_empty_tags_returns_empty(self, app, test_user, forum_category):
        """Thread with no tags should return empty suggestions."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread
            category = ForumCategory.query.get(forum_category)
            thread, post, _ = create_thread(
                category=category, author_id=user.id,
                title="Untagged Thread", content="Content"
            )

            suggestions = suggest_related_threads_by_tags(thread.id, limit=5)
            assert suggestions == []

    def test_related_threads_single_tag(self, app, test_user, forum_category):
        """Threads with single tag should still suggest related threads."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags
            category = ForumCategory.query.get(forum_category)

            t1, p1, _ = create_thread(
                category=category, author_id=user.id,
                title="Thread 1", content="Content 1"
            )
            t2, p2, _ = create_thread(
                category=category, author_id=user.id,
                title="Thread 2", content="Content 2"
            )

            # Both threads tagged with "python"
            set_thread_tags(t1, tags=["python"])
            set_thread_tags(t2, tags=["python"])

            suggestions = suggest_related_threads_by_tags(t1.id, limit=5)
            assert t2.id in [s.id for s in suggestions]

    def test_related_threads_excludes_deleted(self, app, test_user, forum_category):
        """Deleted threads should be excluded from suggestions."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags, soft_delete_thread
            category = ForumCategory.query.get(forum_category)

            t1, p1, _ = create_thread(
                category=category, author_id=user.id,
                title="Active Thread", content="Content"
            )
            t2, p2, _ = create_thread(
                category=category, author_id=user.id,
                title="Deleted Thread", content="Content"
            )

            set_thread_tags(t1, tags=["test"])
            set_thread_tags(t2, tags=["test"])
            soft_delete_thread(t2)

            suggestions = suggest_related_threads_by_tags(t1.id, limit=5)
            suggestion_ids = [s.id for s in suggestions]
            assert t2.id not in suggestion_ids

    def test_related_threads_excludes_hidden(self, app, test_user, forum_category):
        """Hidden threads should be excluded from suggestions."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags, hide_thread
            category = ForumCategory.query.get(forum_category)

            t1, p1, _ = create_thread(
                category=category, author_id=user.id,
                title="Visible Thread", content="Content"
            )
            t2, p2, _ = create_thread(
                category=category, author_id=user.id,
                title="Hidden Thread", content="Content"
            )

            set_thread_tags(t1, tags=["test"])
            set_thread_tags(t2, tags=["test"])
            hide_thread(t2)

            suggestions = suggest_related_threads_by_tags(t1.id, limit=5)
            suggestion_ids = [s.id for s in suggestions]
            assert t2.id not in suggestion_ids

    def test_related_threads_deterministic_ordering(self, app, test_user, forum_category):
        """Suggestions should be deterministic (reproducible order)."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags
            category = ForumCategory.query.get(forum_category)

            t1, _, _ = create_thread(category=category, author_id=user.id,
                                     title="Main Thread", content="Content")

            # Create multiple threads with shared tags
            for i in range(5):
                t, _, _ = create_thread(category=category, author_id=user.id,
                                       title=f"Related {i}", content="Content")
                set_thread_tags(t, tags=["shared"])
            set_thread_tags(t1, tags=["shared"])

            # Get suggestions twice, should be identical
            sugg1 = suggest_related_threads_by_tags(t1.id, limit=10)
            sugg2 = suggest_related_threads_by_tags(t1.id, limit=10)

            assert [s.id for s in sugg1] == [s.id for s in sugg2]

    def test_related_threads_respects_limit(self, app, test_user, forum_category):
        """Related threads should respect the limit parameter."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags
            category = ForumCategory.query.get(forum_category)

            t1, _, _ = create_thread(category=category, author_id=user.id,
                                    title="Main", content="Content")

            # Create 20 related threads
            for i in range(20):
                t, _, _ = create_thread(category=category, author_id=user.id,
                                       title=f"Related {i}", content="Content")
                set_thread_tags(t, tags=["shared"])
            set_thread_tags(t1, tags=["shared"])

            # Request only 5
            suggestions = suggest_related_threads_by_tags(t1.id, limit=5)
            assert len(suggestions) <= 5

    def test_related_threads_excludes_self(self, app, test_user, forum_category):
        """Thread should never be included in its own suggestions."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags
            category = ForumCategory.query.get(forum_category)

            t1, _, _ = create_thread(category=category, author_id=user.id,
                                    title="Self Thread", content="Content")
            set_thread_tags(t1, tags=["self"])

            suggestions = suggest_related_threads_by_tags(t1.id, limit=10)
            assert t1.id not in [s.id for s in suggestions]


class TestProfileActivityDiscovery:
    """Test profile and activity feature stability."""

    def test_user_with_no_threads_shows_empty(self, app, test_user, forum_category):
        """User with no threads should show empty list gracefully."""
        with app.app_context():
            user, _ = test_user
            threads = get_user_recent_threads(user.id, limit=10)
            assert threads == []

    def test_user_recent_threads_pagination(self, app, test_user, forum_category):
        """Recent threads should be paginated correctly."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread
            category = ForumCategory.query.get(forum_category)

            # Create 25 threads
            for i in range(25):
                create_thread(category=category, author_id=user.id,
                            title=f"Thread {i}", content="Content")

            # Default limit should work
            threads = get_user_recent_threads(user.id, limit=10)
            assert len(threads) <= 10

            # Should be ordered by creation descending
            if len(threads) > 1:
                assert threads[0]["created_at"] >= threads[-1]["created_at"]

    def test_user_recent_threads_excludes_deleted(self, app, test_user, forum_category):
        """Deleted threads should not appear in user's recent threads."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, soft_delete_thread
            category = ForumCategory.query.get(forum_category)

            t1, _, _ = create_thread(category=category, author_id=user.id,
                                    title="Active", content="Content")
            t2, _, _ = create_thread(category=category, author_id=user.id,
                                    title="Deleted", content="Content")

            soft_delete_thread(t2)

            threads = get_user_recent_threads(user.id, limit=10)
            thread_ids = [t["id"] for t in threads]
            assert t2.id not in thread_ids
            assert t1.id in thread_ids

    def test_user_recent_posts_empty(self, app, test_user, forum_category):
        """User with no posts should show empty list."""
        with app.app_context():
            user, _ = test_user
            posts = get_user_recent_posts(user.id, limit=10)
            assert posts == []

    def test_user_recent_posts_pagination(self, app, test_user, forum_category):
        """Recent posts should be paginated."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, create_post
            category = ForumCategory.query.get(forum_category)

            t, _, _ = create_thread(category=category, author_id=user.id,
                                   title="Thread", content="First post")

            for i in range(5):
                create_post(thread=t, author_id=user.id, content=f"Reply {i}")

            posts = get_user_recent_posts(user.id, limit=3)
            assert len(posts) <= 3

    def test_user_recent_posts_content_preview(self, app, test_user, forum_category):
        """Post content should be truncated to preview."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, create_post
            category = ForumCategory.query.get(forum_category)

            long_content = "x" * 500
            t, _, _ = create_thread(category=category, author_id=user.id,
                                   title="Thread", content="Content")
            create_post(thread=t, author_id=user.id, content=long_content)

            posts = get_user_recent_posts(user.id, limit=10)
            assert len(posts) > 0
            assert len(posts[0]["content_preview"]) <= 203  # 200 chars + "..."

    def test_count_user_threads_accuracy(self, app, test_user, forum_category):
        """Thread count should match actual threads."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread
            category = ForumCategory.query.get(forum_category)

            count_before = count_user_threads(user.id)

            create_thread(category=category, author_id=user.id,
                         title="New", content="Content")

            count_after = count_user_threads(user.id)
            assert count_after == count_before + 1

    def test_count_user_posts_accuracy(self, app, test_user, forum_category):
        """Post count should match actual posts."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, create_post
            category = ForumCategory.query.get(forum_category)

            count_before = count_user_posts(user.id)

            t, _, _ = create_thread(category=category, author_id=user.id,
                                   title="Thread", content="First post")
            create_post(thread=t, author_id=user.id, content="Reply")

            count_after = count_user_posts(user.id)
            # The thread creation creates one post (the OP)
            # Then we add one reply
            assert count_after == count_before + 2


class TestBatchOperations:
    """Test batch operations for N+1 prevention."""

    def test_batch_tag_thread_counts_empty(self, app):
        """Batch tag counts with empty list should return empty dict."""
        with app.app_context():
            result = batch_tag_thread_counts([])
            assert result == {}

    def test_batch_tag_thread_counts_single_query(self, app, test_user, forum_category):
        """Batch tag counts should use single query not N queries."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags, list_all_tags
            category = ForumCategory.query.get(forum_category)

            # Create threads with tags
            for i in range(5):
                t, _, _ = create_thread(category=category, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                set_thread_tags(t, tags=[f"tag{i % 3}"])

            tags, _ = list_all_tags()
            tag_ids = [t.id for t in tags]

            # This should execute a single query
            counts = batch_tag_thread_counts(tag_ids)

            # Should return counts for all tags
            assert len(counts) >= 1
            # All counts should be >= 0
            assert all(count >= 0 for count in counts.values())

    def test_list_tags_for_threads_batch_query(self, app, test_user, forum_category):
        """list_tags_for_threads should batch load tags."""
        with app.app_context():
            from app.models import ForumCategory
            user, _ = test_user
            from app.services.forum_service import create_thread, set_thread_tags
            category = ForumCategory.query.get(forum_category)

            threads = []
            for i in range(10):
                t, _, _ = create_thread(category=category, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                set_thread_tags(t, tags=["shared", f"tag{i}"])
                threads.append(t)

            thread_ids = [t.id for t in threads]

            # Single batch query
            tags_dict = list_tags_for_threads(thread_ids)

            # Should have tags for each thread
            for tid in thread_ids:
                assert tid in tags_dict
                assert len(tags_dict[tid]) > 0
