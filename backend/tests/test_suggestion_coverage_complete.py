"""Comprehensive tests for suggested-discussions feature."""

import pytest
from datetime import datetime, timezone
from app.extensions import db
from app.models import User, Forum, Thread, Tag, News, WikiArticle, Discussion


@pytest.fixture
def suggestion_test_data(app):
    """Create comprehensive test data for suggestions testing."""
    # Create test users
    user1 = User(username="user1", email="user1@test.com", password_hash="hash1")
    user2 = User(username="user2", email="user2@test.com", password_hash="hash2")
    admin_user = User(username="admin", email="admin@test.com", password_hash="hash")
    admin_user.is_admin = True

    # Create forum and threads
    forum = Forum(name="Test Forum", slug="test-forum")
    tag1 = Tag(name="python", slug="python")
    tag2 = Tag(name="javascript", slug="javascript")
    tag3 = Tag(name="api", slug="api")

    # Create threads with various properties
    primary_thread = Thread(
        title="Primary Discussion",
        slug="primary-discussion",
        forum=forum,
        author=user1,
        status="active",
    )
    primary_thread.tags.extend([tag1, tag2])

    suggested_1 = Thread(
        title="Related to Python",
        slug="related-python",
        forum=forum,
        author=user2,
        status="active",
    )
    suggested_1.tags.extend([tag1])

    suggested_2 = Thread(
        title="API Best Practices",
        slug="api-best-practices",
        forum=forum,
        author=user2,
        status="active",
    )
    suggested_2.tags.extend([tag3])

    hidden_thread = Thread(
        title="Hidden Discussion",
        slug="hidden-discussion",
        forum=forum,
        author=user2,
        status="hidden",
    )

    deleted_thread = Thread(
        title="Deleted Discussion",
        slug="deleted-discussion",
        forum=forum,
        author=user2,
        status="deleted",
    )

    # Create news articles
    news1 = News(
        title="Python 3.13 Released",
        slug="python-3-13",
        author=user1,
        content="Content here",
        published=True,
    )
    news1.tags.extend([tag1])

    news2 = News(
        title="JavaScript Frameworks",
        slug="js-frameworks",
        author=user1,
        content="Content here",
        published=True,
    )
    news2.tags.extend([tag2])

    # Create wiki articles
    wiki1 = WikiArticle(
        title="Python Basics",
        slug="python-basics",
        content="Content here",
        author=user1,
    )
    wiki1.tags.extend([tag1])

    # Persist all
    db.session.add_all([
        user1, user2, admin_user,
        forum, tag1, tag2, tag3,
        primary_thread, suggested_1, suggested_2, hidden_thread, deleted_thread,
        news1, news2,
        wiki1,
    ])
    db.session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "admin_user": admin_user,
        "forum": forum,
        "tags": {"python": tag1, "javascript": tag2, "api": tag3},
        "primary_thread": primary_thread,
        "suggested_threads": [suggested_1, suggested_2],
        "hidden_thread": hidden_thread,
        "deleted_thread": deleted_thread,
        "news": [news1, news2],
        "wiki": [wiki1],
    }


class TestNewsSuggestionsRanking:

    def test_rank_by_tag_matches(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that news suggestions are ranked higher when they match user's tag interests. Create a user, add tags to their reading history, create news with those tags, verify ranking order."""
        user_id = suggestion_test_data['user_id']
        tags = suggestion_test_data['tags']
        news_items = suggestion_test_data['news_items']
    
        # Create user
        response = client.post('/users', headers=admin_headers)
        assert response.status_code == 201
        user_data = response.json
        user_id = user_data['id']
    
        # Add tags to user
        response = client.post(f'/users/{user_id}/tags', headers=admin_headers, json=tags)
        assert response.status_code == 200
    
        # Create news items
        news_data = []
        for item in news_items:
            news_data.append(client.post('/news', headers=admin_headers, json=item).json)
    
        # Fetch suggestions
        response = client.get(f'/users/{user_id}/suggestions', headers=admin_headers)
        assert response.status_code == 200
        suggestions = response.json
    
        # Verify ranking
        ranked_suggestions = sorted(suggestions, key=lambda x: x['rank'])
        for i, suggestion in enumerate(ranked_suggestions):
            assert suggestion['user_id'] == user_id
            assert suggestion['tags'] == tags
            assert suggestion['rank'] == i + 1
    

class TestWikiSuggestionsRanking:

    def test_rank_by_tag_matches(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that wiki suggestions are ranked by tag relevance. Create wiki articles with tags, verify they rank based on user's tag profile."""
        article1 = suggestion_test_data["article1"]
        article2 = suggestion_test_data["article2"]
        user_tags = suggestion_test_data["user_tags"]
    
        # Create articles with tags
        client.post("/articles", json=article1, headers=admin_headers)
        client.post("/articles", json=article2, headers=admin_headers)
    
        # Get suggestions
        response = client.get("/suggestions", params={"tag": user_tags[0]}, headers=admin_headers)
    
        assert response.status_code == 200
        suggestions = response.json()
    
        assert len(suggestions) == 2
        assert article1["title"] in suggestions
        assert article2["title"] in suggestions
    
        # Verify ranking based on tag relevance
        rank1 = suggestions.index(article1["title"])
        rank2 = suggestions.index(article2["title"])
    
        assert rank1 == 0  # Article 1 should be ranked higher
        assert rank2 == 1
    

class TestSuggestionExclusions:

    def test_exclude_primary_thread(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that the primary discussion thread itself is not included in suggestions. Create a thread, fetch its suggestions, verify the primary thread ID is not in results."""
        thread_id = suggestion_test_data['thread_id']
        thread_name = suggestion_test_data['thread_name']
        
        try:
            response = client.post(
                f"/threads/{thread_id}/suggest",
                json={"limit": 10},
                headers=admin_headers
            )
            response.raise_for_status()
            data = response.json()
            suggestions = data.get("suggestions", [])
            
            assert len(suggestions) == 0, f"Unexpected suggestions for thread {thread_id}: {suggestions}"
            
        except Exception as e:
            self.fail(f"An unexpected error occurred: {e}")
    
    def test_exclude_related_threads(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that manually related threads are excluded from suggestions. Create threads with manual relatio..."""
        thread1_id = suggestion_test_data.create_thread(name="Thread 1")
        thread2_id = suggestion_test_data.create_thread(name="Thread 2")
        suggestion_test_data.set_manual_relationship(thread1_id, thread2_id)
        
        suggestions = client.get_suggestions(thread1_id, admin_headers=admin_headers)
        
        assert suggestions["status_code"] == 200
        assert len(suggestions["suggestions"]) == 0
        
        suggestion_test_data.delete_thread(thread1_id)
        suggestion_test_data.delete_thread(thread2_id)
    
    def test_exclude_hidden_threads(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that hidden threads are excluded from suggestions. Create hidden threads, fetch suggestions, verify hidden threads don't appear (unless user is moderator)."""
        thread1_id = suggestion_test_data.create_thread(is_hidden=True)
        thread2_id = suggestion_test_data.create_thread()
        
        suggestions = client.get_suggestions()
        
        assert len(suggestions) == 2
        assert thread1_id in [s['thread_id'] for s in suggestions]
        assert thread2_id not in [s['thread_id'] for s in suggestions]
        
        suggestion_test_data.delete_thread(thread1_id)
        suggestion_test_data.delete_thread(thread2_id)
    

class TestSuggestionDeterminism:

    def test_deterministic_ordering(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that suggestions are deterministic. Call the same suggestion endpoint twice with same inputs, v..."""
        
        input_data = suggestion_test_data['input_data']
        expected_output = suggestion_test_data['expected_output']
        
        response1 = client.get(f"/suggestions", params=input_data, headers=admin_headers)
        response1.assert_status(200)
        actual_output1 = response1.json()
        
        response2 = client.get(f"/suggestions", params=input_data, headers=admin_headers)
        response2.assert_status(200)
        actual_output2 = response2.json()
        
        assert actual_output1 == actual_output2
        assert actual_output1 == expected_output
    

class TestSuggestionLabels:

    def test_grounded_reason_labels(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test that reason labels are grounded in actual data. Verify labels like 'Matched 2 tags' correspond ..."""
        for data in suggestion_test_data:
            response = client.post('/suggestions', json=data, headers=admin_headers)
            assert response.status_code == 200
            json_response = response.json
            reason_label = json_response.get('reason_label')
            if reason_label:
                if "Matched" in reason_label:
                    try:
                        num_matches = int(reason_label.split("Matched ")[1].split(" tags")[0])
                        if num_matches > 0:
                            assert len(data['tags']) == num_matches
                        else:
                            assert False, "Matched label with 0 matches"
                    except (IndexError, ValueError):
                        assert False, "Invalid format for matched label"
                else:
                    assert False, "Reason label should start with 'Matched'"
            else:
                assert False, "Reason label should be present"
    

class TestThreadTypeDistinction:

    def test_primary_vs_related_vs_suggested(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test three distinct thread categories: primary (the main discussion), related (manually linked), suggested (algorithmic). Verify they're returned in appropriate sections."""
        thread_id = suggestion_test_data['thread_id']
        thread = client.get_thread(thread_id, admin_headers=admin_headers)
    
        assert thread is not None
        assert thread['type'] == 'thread'
    
        primary = None
        related = None
        suggested = None
    
        for item in thread['items']:
            if item['type'] == 'thread':
                if item['is_primary']:
                    primary = item
                elif item['is_related']:
                    related = item
                elif item['is_suggested']:
                    suggested = item
    
        assert primary is not None, "Primary thread not found"
        assert related is not None, "Related thread not found"
        assert suggested is not None, "Suggested thread not found"
    
        assert primary['id'] == thread_id, "Primary thread ID mismatch"
        assert related['id'] == thread_id, "Related thread ID mismatch"
        assert suggested['id'] == thread_id, "Suggested thread ID mismatch"
    
        assert primary['title'] == 'Main Discussion', "Primary thread title mismatch"
        assert related['title'] == 'Related Thread', "Related thread title mismatch"
        assert suggested['title'] == 'Algorithmic Suggestion', "Suggested thread title mismatch"


class TestManagementAPI:

    def test_admin_fetch_suggestions(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test admin endpoint for suggestions management. Admin GET /api/v1/admin/forums/threads/<id>/management should return suggestions data with ability to view/modify."""
        thread_id = suggestion_test_data["thread_id"]
        
        # Test successful retrieval with valid thread ID
        response = client.get(f"/api/v1/admin/forums/threads/{thread_id}/management", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for suggestion in data:
            assert "id" in suggestion
            assert "text" in suggestion
            assert "is_visible" in suggestion
            assert "is_editable" in suggestion
            
        # Test edge case: thread ID not found
        response = client.get(f"/api/v1/admin/forums/threads/{9999}/management", headers=admin_headers)
        assert response.status_code == 404
        
        # Test edge case: Invalid admin headers
        response = client.get(f"/api/v1/admin/forums/threads/{thread_id}/management", headers={})
        assert response.status_code == 401
    

class TestPublicAPI:

    def test_api_endpoint_response(self, client, suggestion_test_data, admin_headers=None):
        """Test requirement: Test public API endpoint GET /api/v1/forums/threads/<id>/suggestions returns 200 with proper pagination (limit, offset), response schema validation."""
        thread_id = suggestion_test_data["thread_id"]
        limit = 10
        offset = 0
    
        response = client.get(f"/api/v1/forums/threads/{thread_id}/suggestions?limit={limit}&offset={offset}", headers=admin_headers)
    
        assert response.status_code == 200
        response_data = response.json()
    
        assert isinstance(response_data, dict)
        assert "suggestions" in response_data
        assert isinstance(response_data["suggestions"], list)
        assert len(response_data["suggestions"]) == limit
    
        for suggestion in response_data["suggestions"]:
            assert isinstance(suggestion, dict)
            assert "id" in suggestion
            assert "text" in suggestion
            assert "created_at" in suggestion
    
        assert response_data["total"] == suggestion_test_data["total_suggestions"]
        assert response_data["limit"] == limit
        assert response_data["offset"] == offset
    