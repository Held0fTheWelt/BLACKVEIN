"""Pytest fixtures for World of Shadows."""
from datetime import datetime, timezone
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Application with testing config and in-memory DB."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner for flask commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user in the DB; returns (user, password)."""
    with app.app_context():
        user = User(
            username="testuser",
            password_hash=generate_password_hash("Testpass1"),
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Testpass1"


@pytest.fixture
def auth_headers(test_user, client):
    """Return headers with valid JWT for test_user (for API requests)."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestingConfigWithCSRF(TestingConfig):
    """Testing config with CSRF enabled for security tests."""
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app_csrf():
    """Application with CSRF enabled (for testing CSRF protection)."""
    application = create_app(TestingConfigWithCSRF)
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client_csrf(app_csrf):
    """Test client for app with CSRF enabled."""
    return app_csrf.test_client()


@pytest.fixture
def db_session(app):
    """Run test in a clean session; rollback after test for isolation."""
    yield db.session
    db.session.rollback()
    db.session.remove()


@pytest.fixture
def test_user_with_email(app):
    """Test user with email set (verified); returns (user, password)."""
    with app.app_context():
        user = User(
            username="emailuser",
            email="emailuser@example.com",
            password_hash=generate_password_hash("Testpass1"),
            email_verified_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Testpass1"


@pytest.fixture
def editor_user(app):
    """Create a user with editor role; returns (user, password). Used for news write API tests."""
    with app.app_context():
        user = User(
            username="editoruser",
            password_hash=generate_password_hash("Editorpass1"),
            role=User.ROLE_EDITOR,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Editorpass1"


@pytest.fixture
def editor_headers(editor_user, client):
    """Return headers with valid JWT for editor_user (for API write requests)."""
    user, password = editor_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": "Bearer " + data["access_token"]}


@pytest.fixture
def sample_news(app, test_user):
    """Create sample published and draft news for list/detail/search/sort tests.
    Returns (published_news, published_news_2, draft_news) – two published (different title/sort), one draft."""
    from app.models import News
    from datetime import datetime, timezone

    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        pub1 = News(
            title="Published Article",
            slug="published-article",
            summary="A published summary",
            content="Published body with unique word searchable.",
            author_id=user.id,
            is_published=True,
            published_at=now,
            created_at=now,
            updated_at=now,
            category="Updates",
        )
        pub2 = News(
            title="Another Published",
            slug="another-published",
            summary="Second published.",
            content="Second body.",
            author_id=user.id,
            is_published=True,
            published_at=now,
            created_at=now,
            updated_at=now,
            category="Updates",
        )
        draft = News(
            title="Draft Article",
            slug="draft-article",
            summary="Draft summary",
            content="Draft body.",
            author_id=user.id,
            is_published=False,
            published_at=None,
            created_at=now,
            updated_at=now,
            category="Drafts",
        )
        db.session.add(pub1)
        db.session.add(pub2)
        db.session.add(draft)
        db.session.commit()
        db.session.refresh(pub1)
        db.session.refresh(pub2)
        db.session.refresh(draft)
        return pub1, pub2, draft
