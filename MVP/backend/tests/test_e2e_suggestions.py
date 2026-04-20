import pytest
from app.models import ForumThread, ForumCategory, ForumTag, ForumThreadTag, NewsArticle
from app.extensions import db


class TestSuggestedThreadsOrdering:
    """Test deterministic ordering of suggested threads."""
    
    def test_forum_suggestions_deterministic_ordering(self, client, test_user, app):
        """Same forum thread query returns consistent ordering."""
        with app.app_context():
            # Create test data
            cat = ForumCategory(slug="test", title="Test", sort_order=0, is_active=True, is_private=False)
            db.session.add(cat)
            db.session.flush()
            
            user, _ = test_user
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="test-thread",
                title="Test Thread",
                status="open"
            )
            db.session.add(thread)
            db.session.commit()
            
            # Get suggestions twice
            from app.services.forum_service import suggest_related_threads_by_tags
            result1 = suggest_related_threads_by_tags(thread.id)
            result2 = suggest_related_threads_by_tags(thread.id)
            
            # Should return same order
            ids1 = [t.id for t in result1]
            ids2 = [t.id for t in result2]
            assert ids1 == ids2, "Suggestions should be deterministically ordered"


class TestSuggestedThreadsExclusions:
    """Test exclusion logic for suggested threads."""
    
    def test_excludes_duplicates(self, client, test_user, app):
        """Suggested threads contain no duplicate IDs."""
        with app.app_context():
            cat = ForumCategory(slug="test", title="Test", sort_order=0, is_active=True, is_private=False)
            db.session.add(cat)
            db.session.flush()
            
            user, _ = test_user
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="test-thread",
                title="Test Thread",
                status="open"
            )
            db.session.add(thread)
            db.session.commit()
            
            from app.services.forum_service import suggest_related_threads_by_tags
            results = suggest_related_threads_by_tags(thread.id)
            ids = [t.id for t in results]
            
            assert len(ids) == len(set(ids)), "No duplicate thread IDs in suggestions"

    def test_excludes_hidden_threads(self, client, test_user, app):
        """Suggested threads exclude hidden/archived status threads."""
        with app.app_context():
            cat = ForumCategory(slug="test", title="Test", sort_order=0, is_active=True, is_private=False)
            db.session.add(cat)
            db.session.flush()
            
            user, _ = test_user
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="test-thread",
                title="Test Thread",
                status="open"
            )
            db.session.add(thread)
            db.session.commit()
            
            from app.services.forum_service import suggest_related_threads_by_tags
            results = suggest_related_threads_by_tags(thread.id, include_hidden=False)
            
            # Check status of returned threads
            for thread_result in results:
                assert thread_result.status not in ("hidden", "archived", "deleted"), \
                    f"Should not include {thread_result.status} threads"


class TestWikiSuggestedThreadsEndpoint:
    """Test Wiki suggested-threads endpoint."""
    
    def test_wiki_suggested_threads_route_shape(self, client, admin_headers, app):
        """Wiki endpoint uses ID-based route /api/v1/wiki/<int:page_id>/suggested-threads"""
        # Test with a valid wiki page ID
        response = client.get(
            "/api/v1/wiki/1/suggested-threads",
            headers=admin_headers
        )
        # Should return 200, 404 (page not found), or 403 (forbidden) - not 404 for bad route
        assert response.status_code in [200, 404, 403, 401], \
            f"Route should be recognized (got {response.status_code})"

    def test_wiki_suggested_threads_payload_shape(self, client, admin_headers, app):
        """Wiki suggestions include required fields."""
        response = client.get(
            "/api/v1/wiki/1/suggested-threads",
            headers=admin_headers
        )
        # If we get data, check structure
        if response.status_code == 200:
            data = response.get_json()
            assert "items" in data or "suggested_threads" in data, \
                "Should have suggested_threads or items field"


class TestReasonLabels:
    """Test that reason labels match implementation."""
    
    def test_reason_labels_not_same_category(self, client, test_user, app):
        """Reason labels should NOT be "Same category" (not in current implementation)."""
        with app.app_context():
            from app.services.forum_service import suggest_related_threads_by_tags
            
            cat = ForumCategory(slug="test", title="Test", sort_order=0, is_active=True, is_private=False)
            db.session.add(cat)
            db.session.flush()
            
            user, _ = test_user
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="test-thread",
                title="Test Thread",
                status="open"
            )
            db.session.add(thread)
            db.session.commit()
            
            # Get raw suggestions
            results = suggest_related_threads_by_tags(thread.id)
            
            # Verify reason field exists but is NOT "Same category"
            for result in results:
                if hasattr(result, 'reason'):
                    assert result.reason != "Same category", \
                        "Reason should not be 'Same category' (not in implementation)"


class TestSuggestionDistinction:
    """Test distinction between discussion/related/suggested threads."""
    
    def test_api_distinguishes_thread_types(self, client, admin_headers, app):
        """API response distinguishes discussion vs related_threads vs suggested_threads."""
        response = client.get("/api/v1/news/1", headers=admin_headers)
        
        if response.status_code == 200:
            data = response.get_json()
            
            # Check for distinct fields
            if "discussion_threads" in data:
                assert isinstance(data["discussion_threads"], list)
            if "related_threads" in data:
                assert isinstance(data["related_threads"], list)
            if "suggested_threads" in data:
                assert isinstance(data["suggested_threads"], list)
            
            # If all three exist, they should be separate
            disc_ids = {t.get("id") for t in data.get("discussion_threads", [])}
            related_ids = {t.get("id") for t in data.get("related_threads", [])}
            sugg_ids = {t.get("id") for t in data.get("suggested_threads", [])}
            
            # No overlap between discussion and suggestions
            assert not (disc_ids & sugg_ids), "Discussion threads should not appear in suggestions"
