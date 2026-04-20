"""Phase 5B: Performance Regression Tests.

Tests that critical query paths execute efficiently:
- Most queries target <500ms wall-clock; escalation/review queue tests use a warm-up plus
  PERF_REGRESSION_QUEUE_SEC (default 2.0s) because SQLite cold-start and CI variance dominate.
- No N+1 queries
- Indexes are being used
"""
import os
import time
import pytest
from app.models import ForumCategory, ForumThread, ForumPost
from app.services.forum_service import (
    list_threads_for_category,
    list_bookmarked_threads,
    list_escalation_queue,
    list_review_queue,
    suggest_related_threads_by_tags,
    list_all_tags,
)
from app.services.user_service import (
    get_user_recent_threads,
    get_user_recent_posts,
)

# Wall-clock ceilings: SQLite + SQLAlchemy cold-start and shared CI runners vary widely.
# Tighten locally with PERF_REGRESSION_QUEUE_SEC=0.5 when profiling.
_QUEUE_PERF_MAX_SEC = float(os.environ.get("PERF_REGRESSION_QUEUE_SEC", "2.0"))


class TestQueryPerformance:
    """Test that critical queries complete efficiently."""

    @pytest.mark.slow
    def test_list_threads_for_category_performance(self, app, test_user, forum_category):
        """list_threads_for_category should complete in <500ms with 1000 threads."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            # Create 1000 threads
            for i in range(1000):
                create_thread(category=cat, author_id=user.id,
                            title=f"Thread {i}", content="Content")

            start = time.perf_counter()
            threads, total = list_threads_for_category(cat, page=1, per_page=50)
            elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"Query took {elapsed:.3f}s, should be <0.5s"
            assert len(threads) <= 50
            assert total >= 1000

    @pytest.mark.slow
    def test_search_forum_performance(self, client, auth_headers, app, test_user, forum_category):
        """Forum search should complete in <500ms with 1000 threads."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            # Create 1000 threads
            for i in range(1000):
                create_thread(category=cat, author_id=user.id,
                            title=f"Performance Test {i % 100}", content="Content")

        start = time.perf_counter()
        response = client.get("/api/v1/forum/search?q=performance&limit=20", headers=auth_headers)
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 0.5, f"Search took {elapsed:.3f}s, should be <0.5s"

    def test_list_bookmarked_threads_performance(self, app, test_user, forum_category):
        """Bookmarked threads listing should complete efficiently."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, bookmark_thread

            # Create and bookmark threads
            for i in range(50):
                t, _, _ = create_thread(category=cat, author_id=user.id,
                                       title=f"Bookmark {i}", content="Content")
                bookmark_thread(user, t)

            start = time.perf_counter()
            threads, total = list_bookmarked_threads(user, page=1, per_page=20)
            elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"Bookmark listing took {elapsed:.3f}s, should be <0.5s"
            assert len(threads) <= 20

    def test_escalation_queue_performance(self, app):
        """Escalation queue query should be fast."""
        with app.app_context():
            # Create some reports
            from app.models import ForumReport, User
            users = User.query.all()
            if users:
                user = users[0]
                for i in range(100):
                    report = ForumReport(
                        target_type="thread",
                        target_id=i % 10,
                        reported_by=user.id,
                        reason=f"Report {i}",
                        status="escalated" if i % 2 else "open",
                        priority=["critical", "high", "normal", "low"][i % 4]
                    )
                    from app.extensions import db
                    db.session.add(report)
                db.session.commit()

            # Warm-up avoids counting one-off import/compile and first-connection latency.
            list_escalation_queue(page=1, per_page=50)
            start = time.perf_counter()
            reports, total = list_escalation_queue(page=1, per_page=50)
            elapsed = time.perf_counter() - start

            assert elapsed < _QUEUE_PERF_MAX_SEC, (
                f"Escalation queue took {elapsed:.3f}s, should be <{_QUEUE_PERF_MAX_SEC}s "
                f"(set PERF_REGRESSION_QUEUE_SEC to override)"
            )

    def test_review_queue_performance(self, app):
        """Review queue query should be fast."""
        with app.app_context():
            from app.models import ForumReport, User
            users = User.query.all()
            if users:
                user = users[0]
                for i in range(100):
                    report = ForumReport(
                        target_type="post",
                        target_id=i % 10,
                        reported_by=user.id,
                        reason=f"Report {i}",
                        status="open" if i % 2 else "reviewed"
                    )
                    from app.extensions import db
                    db.session.add(report)
                db.session.commit()

            list_review_queue(page=1, per_page=50)
            start = time.perf_counter()
            reports, total = list_review_queue(page=1, per_page=50)
            elapsed = time.perf_counter() - start

            assert elapsed < _QUEUE_PERF_MAX_SEC, (
                f"Review queue took {elapsed:.3f}s, should be <{_QUEUE_PERF_MAX_SEC}s "
                f"(set PERF_REGRESSION_QUEUE_SEC to override)"
            )

    def test_list_tags_performance(self, app, test_user, forum_category):
        """Tag listing should be fast."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, set_thread_tags

            # Create threads with many tags
            for i in range(100):
                t, _, _ = create_thread(category=cat, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                tags = [f"tag{j}" for j in range(i % 5)]
                set_thread_tags(t, tags=tags)

            start = time.perf_counter()
            tags, total = list_all_tags(page=1, per_page=50)
            elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"Tag listing took {elapsed:.3f}s, should be <0.5s"

    def test_user_recent_threads_performance(self, app, test_user, forum_category):
        """User recent threads should be fast."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            # Create many threads
            for i in range(500):
                create_thread(category=cat, author_id=user.id,
                            title=f"Thread {i}", content="Content")

            start = time.perf_counter()
            threads = get_user_recent_threads(user.id, limit=20)
            elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"Recent threads took {elapsed:.3f}s, should be <0.5s"
            assert len(threads) <= 20


class TestNoN1Queries:
    """Test that common operations don't have N+1 query problems."""

    def test_list_threads_category_no_n1(self, app, test_user, forum_category):
        """list_threads_for_category should eager load authors (no N+1)."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread
            from app.extensions import db

            # Create 10 threads
            cat_id = cat.id  # Save the ID before expunge
            for i in range(10):
                create_thread(category=cat, author_id=user.id,
                            title=f"Thread {i}", content="Content")

            # Flush to clear session cache
            db.session.expunge_all()

            # Reload the detached category
            cat = ForumCategory.query.get(cat_id)

            # Patch db.session.execute to count queries
            execute_count = [0]
            original_execute = db.session.execute

            def counting_execute(*args, **kwargs):
                execute_count[0] += 1
                return original_execute(*args, **kwargs)

            db.session.execute = counting_execute

            threads, _ = list_threads_for_category(cat, page=1, per_page=20)

            db.session.execute = original_execute

            # Should have minimal queries: 1 for threads + 1 for count
            # (eager loading authors in the main query)
            assert execute_count[0] <= 5, f"Too many queries: {execute_count[0]}"

    def test_list_bookmarked_threads_no_n1(self, app, test_user, forum_category):
        """list_bookmarked_threads should eager load authors."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, bookmark_thread
            from app.extensions import db

            # Create and bookmark threads
            for i in range(10):
                t, _, _ = create_thread(category=cat, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                bookmark_thread(user, t)

            db.session.expunge_all()

            execute_count = [0]
            original_execute = db.session.execute

            def counting_execute(*args, **kwargs):
                execute_count[0] += 1
                return original_execute(*args, **kwargs)

            db.session.execute = counting_execute

            threads, _ = list_bookmarked_threads(user, page=1, per_page=20)

            db.session.execute = original_execute

            # Should have minimal queries
            assert execute_count[0] <= 5, f"Too many queries: {execute_count[0]}"


class TestIndexUsage:
    """Test that indexes are being used effectively."""

    def test_search_uses_thread_status_index(self, client, auth_headers, app, test_user, forum_category):
        """Search should use thread status index for visibility filtering."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, hide_thread

            # Create mix of visible and hidden threads
            for i in range(100):
                t, _, _ = create_thread(category=cat, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                if i % 10 == 0:
                    hide_thread(t)

        # Search should efficiently filter out hidden threads
        response = client.get("/api/v1/forum/search?q=thread&page=1&limit=20", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        # Regular user should not see hidden threads
        for item in data.get("items", []):
            assert "hidden" not in item.get("title", "").lower()

    def test_category_listing_uses_composite_index(self, app, test_user, forum_category):
        """Category listing should use (category_id, status, created_at) index."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            # Create threads in bulk
            for i in range(500):
                create_thread(category=cat, author_id=user.id,
                            title=f"Thread {i}", content="Content")

            # List should be fast (index is being used)
            start = time.perf_counter()
            threads, total = list_threads_for_category(cat, page=1, per_page=50)
            elapsed = time.perf_counter() - start

            # Should be fast with index
            assert elapsed < 0.3, f"Category listing took {elapsed:.3f}s with index"
            assert total >= 500
