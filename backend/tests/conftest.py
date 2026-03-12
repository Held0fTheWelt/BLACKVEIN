"""Pytest fixtures for World of Shadows."""
from datetime import datetime, timezone
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Role, User
from app.models.role import ensure_roles_seeded
from app.models.area import ensure_areas_seeded
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Application with testing config and in-memory DB."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
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
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="testuser",
            password_hash=generate_password_hash("Testpass1"),
            role_id=role.id,
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
        ensure_roles_seeded()
        ensure_areas_seeded()
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
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="emailuser",
            email="emailuser@example.com",
            password_hash=generate_password_hash("Testpass1"),
            email_verified_at=datetime.now(timezone.utc),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Testpass1"


@pytest.fixture
def moderator_user(app):
    """Create a user with moderator role; returns (user, password). Used for news write API tests."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_MODERATOR).first()
        user = User(
            username="moderatoruser",
            password_hash=generate_password_hash("Modpass1"),
            role_id=role.id,
            role_level=getattr(role, "default_role_level", None) or 10,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Modpass1"


@pytest.fixture
def moderator_headers(moderator_user, client):
    """Return headers with valid JWT for moderator_user (for API write requests)."""
    user, password = moderator_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": "Bearer " + data["access_token"]}


@pytest.fixture
def admin_user(app):
    """Create a user with admin role and role_level 50 so they may edit users with lower level (e.g. test_user with 0)."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        user = User(
            username="adminuser",
            password_hash=generate_password_hash("Adminpass1"),
            role_id=role.id,
            role_level=getattr(role, "default_role_level", None) or 50,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Adminpass1"


@pytest.fixture
def admin_headers(admin_user, client):
    """Return headers with valid JWT for admin_user (for admin API requests)."""
    user, password = admin_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": "Bearer " + data["access_token"]}


@pytest.fixture
def super_admin_user(app):
    """Admin with role_level 100 (SuperAdmin). Used for hierarchy tests."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        user = User(
            username="superadminuser",
            password_hash=generate_password_hash("Superadmin1"),
            role_id=role.id,
            role_level=100,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Superadmin1"


@pytest.fixture
def super_admin_headers(super_admin_user, client):
    """JWT headers for super_admin_user."""
    user, password = super_admin_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": "Bearer " + data["access_token"]}


@pytest.fixture
def admin_user_same_level(app):
    """Second admin with role_level 50 (same as admin_user). For 'cannot edit equal level' test."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        user = User(
            username="admin2user",
            password_hash=generate_password_hash("Admin2pass1"),
            role_id=role.id,
            role_level=50,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Admin2pass1"


@pytest.fixture
def banned_user(app):
    """Create a user with is_banned=True (role=user, no email so login would otherwise succeed)."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="banneduser",
            password_hash=generate_password_hash("Bannedpass1"),
            role_id=role.id,
            is_banned=True,
            banned_at=datetime.now(timezone.utc),
            ban_reason="Test ban",
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Bannedpass1"


@pytest.fixture
def sample_news(app, test_user):
    """Create sample published and draft news for list/detail/search/sort tests.
    Returns (published_article_1, published_article_2, draft_article) – two published, one draft."""
    from app.models import NewsArticle, NewsArticleTranslation
    from datetime import datetime, timezone

    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        pub1_article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            category="Updates",
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(pub1_article)
        db.session.flush()
        pub1 = NewsArticleTranslation(
            article_id=pub1_article.id,
            language_code="de",
            title="Published Article",
            slug="published-article",
            summary="A published summary",
            content="Published body with unique word searchable.",
            translation_status="published",
            source_language="de",
            translated_at=now,
        )
        db.session.add(pub1)

        pub2_article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            category="Updates",
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(pub2_article)
        db.session.flush()
        pub2 = NewsArticleTranslation(
            article_id=pub2_article.id,
            language_code="de",
            title="Another Published",
            slug="another-published",
            summary="Second published.",
            content="Second body.",
            translation_status="published",
            source_language="de",
            translated_at=now,
        )
        db.session.add(pub2)

        draft_article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            category="Drafts",
            created_at=now,
            updated_at=now,
            published_at=None,
        )
        db.session.add(draft_article)
        db.session.flush()
        draft = NewsArticleTranslation(
            article_id=draft_article.id,
            language_code="de",
            title="Draft Article",
            slug="draft-article",
            summary="Draft summary",
            content="Draft body.",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(draft)
        db.session.commit()
        db.session.refresh(pub1_article)
        db.session.refresh(pub2_article)
        db.session.refresh(draft_article)
        return pub1_article, pub2_article, draft_article
