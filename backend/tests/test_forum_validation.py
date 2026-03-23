"""Forum Input Validation Tests: Comprehensive coverage of content length validation."""
import pytest

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
)


# ============= THREAD TITLE VALIDATION TESTS =============

def test_thread_create_title_too_short(app, client, auth_headers):
    """Thread creation should fail with title < 5 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test", title="Test Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 4 characters - too short
    resp = client.post(
        "/api/v1/forum/categories/test/threads",
        json={"title": "Test", "content": "This is a valid post content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be at least 5 characters" in data["error"]


def test_thread_create_title_valid_min(app, client, auth_headers):
    """Thread creation should succeed with title exactly 5 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test2", title="Test Category 2", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 5 characters - exactly at minimum
    resp = client.post(
        "/api/v1/forum/categories/test2/threads",
        json={"title": "Title", "content": "This is a valid post content"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Title"


def test_thread_create_title_too_long(app, client, auth_headers):
    """Thread creation should fail with title > 500 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test3", title="Test Category 3", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 501 characters - too long
    long_title = "A" * 501
    resp = client.post(
        "/api/v1/forum/categories/test3/threads",
        json={"title": long_title, "content": "This is a valid post content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must not exceed 500 characters" in data["error"]


def test_thread_create_title_valid_max(app, client, auth_headers):
    """Thread creation should succeed with title exactly 500 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test4", title="Test Category 4", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 500 characters - exactly at maximum
    title = "A" * 500
    resp = client.post(
        "/api/v1/forum/categories/test4/threads",
        json={"title": title, "content": "This is a valid post content"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert len(data["title"]) == 500


# ============= THREAD CONTENT VALIDATION TESTS =============

def test_thread_create_content_too_short(app, client, auth_headers):
    """Thread creation should fail with content < 10 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test5", title="Test Category 5", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 9 characters - too short
    resp = client.post(
        "/api/v1/forum/categories/test5/threads",
        json={"title": "Valid Title", "content": "123456789"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must be at least 10 characters" in data["error"]


def test_thread_create_content_too_long(app, client, auth_headers):
    """Thread creation should fail with content > 50000 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test7", title="Test Category 7", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 50001 characters - too long
    long_content = "A" * 50001
    resp = client.post(
        "/api/v1/forum/categories/test7/threads",
        json={"title": "Valid Title", "content": long_content},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must not exceed 50000 characters" in data["error"]


def test_thread_create_content_valid_max(app, client, auth_headers):
    """Thread creation should succeed with content exactly 50000 characters."""
    with app.app_context():
        cat = ForumCategory(slug="test8", title="Test Category 8", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # 50000 characters - exactly at maximum
    content = "A" * 50000
    resp = client.post(
        "/api/v1/forum/categories/test8/threads",
        json={"title": "Valid Title", "content": content},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    # Verify creation succeeded - response may not include full content
    assert "id" in data
    assert data["title"] == "Valid Title"


# ============= CATEGORY TITLE VALIDATION TESTS =============

def test_category_create_title_too_short(app, client, admin_headers):
    """Category creation should fail with title < 5 characters."""
    # 4 characters - too short
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={
            "slug": "cat1",
            "title": "Test",  # 4 characters
            "is_active": True,
            "is_private": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be at least 5 characters" in data["error"]


def test_category_create_title_valid_min(app, client, admin_headers):
    """Category creation should succeed with title exactly 5 characters."""
    # 5 characters - exactly at minimum
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={
            "slug": "cat2",
            "title": "Title",  # 5 characters
            "is_active": True,
            "is_private": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Title"


def test_category_create_title_too_long(app, client, admin_headers):
    """Category creation should fail with title > 200 characters."""
    # 201 characters - too long
    long_title = "A" * 201
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={
            "slug": "cat3",
            "title": long_title,
            "is_active": True,
            "is_private": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must not exceed 200 characters" in data["error"]


def test_category_create_title_valid_max(app, client, admin_headers):
    """Category creation should succeed with title exactly 200 characters."""
    # 200 characters - exactly at maximum
    title = "A" * 200
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={
            "slug": "cat4",
            "title": title,
            "is_active": True,
            "is_private": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert len(data["title"]) == 200


def test_category_update_title_too_short(app, client, admin_headers):
    """Category update should fail with title < 5 characters."""
    with app.app_context():
        cat = ForumCategory(slug="cat5", title="Original Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Try to update to 4 characters
    resp = client.put(
        f"/api/v1/forum/admin/categories/{cat_id}",
        json={"title": "Test"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be at least 5 characters" in data["error"]


def test_category_update_title_too_long(app, client, admin_headers):
    """Category update should fail with title > 200 characters."""
    with app.app_context():
        cat = ForumCategory(slug="cat6", title="Original Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Try to update to 201 characters
    long_title = "B" * 201
    resp = client.put(
        f"/api/v1/forum/admin/categories/{cat_id}",
        json={"title": long_title},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must not exceed 200 characters" in data["error"]


def test_category_update_title_valid(app, client, admin_headers):
    """Category update should succeed with valid title length."""
    with app.app_context():
        cat = ForumCategory(slug="cat7", title="Original Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Update with valid title
    resp = client.put(
        f"/api/v1/forum/admin/categories/{cat_id}",
        json={"title": "Updated Category Title"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Updated Category Title"


# ============= WHITESPACE HANDLING TESTS =============

def test_thread_create_title_with_leading_trailing_whitespace(app, client, auth_headers):
    """Thread creation should trim whitespace and validate length."""
    with app.app_context():
        cat = ForumCategory(slug="test19", title="Test Category 19", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Title with whitespace that becomes too short after trimming
    resp = client.post(
        "/api/v1/forum/categories/test19/threads",
        json={"title": "   AB   ", "content": "This is a valid post content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be at least 5 characters" in data["error"]


# ============= TYPE-CHECK BYPASS PREVENTION TESTS =============
# CRITICAL: Validate that non-string types are rejected to prevent bypass

def test_thread_create_title_as_object_rejected(app, client, auth_headers):
    """Thread creation should reject title as JSON object (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="test20", title="Test Category 20", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Send title as object instead of string
    resp = client.post(
        "/api/v1/forum/categories/test20/threads",
        json={"title": {"text": "Valid Title"}, "content": "This is valid content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"]


def test_thread_create_title_as_array_rejected(app, client, auth_headers):
    """Thread creation should reject title as array (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="test21", title="Test Category 21", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Send title as array instead of string
    resp = client.post(
        "/api/v1/forum/categories/test21/threads",
        json={"title": ["Valid", "Title"], "content": "This is valid content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"]


def test_thread_create_title_as_number_rejected(app, client, auth_headers):
    """Thread creation should reject title as number (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="test22", title="Test Category 22", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Send title as number instead of string
    resp = client.post(
        "/api/v1/forum/categories/test22/threads",
        json={"title": 12345, "content": "This is valid content"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"]


def test_thread_create_content_as_object_rejected(app, client, auth_headers):
    """Thread creation should reject content as JSON object (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="test23", title="Test Category 23", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Send content as object instead of string
    resp = client.post(
        "/api/v1/forum/categories/test23/threads",
        json={"title": "Valid Title", "content": {"text": "This is valid content"}},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must be a string" in data["error"]


def test_thread_create_content_as_array_rejected(app, client, auth_headers):
    """Thread creation should reject content as array (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="test24", title="Test Category 24", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()

    # Send content as array instead of string
    resp = client.post(
        "/api/v1/forum/categories/test24/threads",
        json={"title": "Valid Title", "content": ["This", "is", "valid", "content"]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must be a string" in data["error"]


def test_post_create_content_as_object_rejected(app, client, auth_headers):
    """Post creation should reject content as JSON object (type bypass attack)."""
    with app.app_context():
        from app.models import User, ForumThread, ForumPost
        user = User.query.first()
        cat = ForumCategory(slug="test25", title="Test Category 25", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            title="Test Thread",
            slug="test-thread-25"
        )
        db.session.add(thread)
        db.session.commit()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="Initial post content")
        db.session.add(post)
        db.session.commit()
        thread_id = thread.id

    # Send content as object instead of string
    resp = client.post(
        f"/api/v1/forum/threads/{thread_id}/posts",
        json={"content": {"text": "This is a long enough comment"}},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must be a string" in data["error"]


def test_post_update_content_as_object_rejected(app, client, auth_headers):
    """Post update should reject content as JSON object (type bypass attack)."""
    with app.app_context():
        from app.models import User
        user = User.query.first()
        cat = ForumCategory(slug="test26", title="Test Category 26", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            title="Test Thread",
            slug="test-thread-26"
        )
        db.session.add(thread)
        db.session.commit()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="Initial post content here")
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Send content as object instead of string
    resp = client.put(
        f"/api/v1/forum/posts/{post_id}",
        json={"content": {"text": "Updated post content"}},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Content must be a string" in data["error"]


def test_thread_update_title_as_object_rejected(app, client, auth_headers):
    """Thread update should reject title as JSON object (type bypass attack)."""
    with app.app_context():
        from app.models import User
        user = User.query.first()
        cat = ForumCategory(slug="test27", title="Test Category 27", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            title="Original Title",
            slug="test-thread-27"
        )
        db.session.add(thread)
        db.session.commit()
        post = ForumPost(thread_id=thread.id, author_id=user.id, content="Initial post content")
        db.session.add(post)
        db.session.commit()
        thread_id = thread.id

    # Send title as object instead of string
    resp = client.put(
        f"/api/v1/forum/threads/{thread_id}",
        json={"title": {"text": "New Title"}},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"]


def test_category_create_title_as_object_rejected(app, client, admin_headers):
    """Category creation should reject title as JSON object (type bypass attack)."""
    # Send title as object instead of string
    resp = client.post(
        "/api/v1/forum/admin/categories",
        json={
            "slug": "cat_type_test",
            "title": {"text": "Valid Title"},
            "is_active": True,
            "is_private": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"]


def test_category_update_title_as_object_rejected(app, client, admin_headers):
    """Category update should reject title as JSON object (type bypass attack)."""
    with app.app_context():
        cat = ForumCategory(slug="cat_update_test", title="Original Category", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Send title as object instead of string
    resp = client.put(
        f"/api/v1/forum/admin/categories/{cat_id}",
        json={"title": {"text": "New Title"}},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title must be a string" in data["error"] or "must be a string" in data.get("error", "")
