"""Bulk forum operation contract tests (split from former test_coverage_expansion)."""

from app.models import ForumPost, ForumThread


class TestBulkOperations:
    """Test bulk operations and batch processing."""

    def test_bulk_thread_lock(self, client, moderator_headers, app):
        """Can lock multiple threads in one operation."""
        with app.app_context():
            threads = ForumThread.query.limit(3).all()
            thread_ids = [t.id for t in threads]

        if thread_ids:
            response = client.post(
                "/api/v1/forum/threads/bulk-lock",
                headers=moderator_headers,
                json={"thread_ids": thread_ids},
            )
            assert response.status_code in [200, 204]

    def test_bulk_post_hide(self, client, moderator_headers, app):
        """Can hide multiple posts in one operation."""
        with app.app_context():
            posts = ForumPost.query.limit(3).all()
            post_ids = [p.id for p in posts]

        if post_ids:
            response = client.post(
                "/api/v1/forum/posts/bulk-hide",
                headers=moderator_headers,
                json={"post_ids": post_ids},
            )
            assert response.status_code in [200, 204]
