"""Pytest fixtures for World of Shadows."""
from datetime import datetime, timezone
import pytest

# Enable pytest-asyncio for async test support
pytest_plugins = ("pytest_asyncio",)

from app import create_app
from app.config import TestingConfig
from app.extensions import db, limiter
from app.services.play_service_control_service import bootstrap_play_service_control
from app.models import Role, User
from app.models.role import ensure_roles_seeded
from app.models.area import ensure_areas_seeded
from werkzeug.security import generate_password_hash


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Clear rate limiter state before each test to prevent cross-test contamination."""
    # Reset the limiter's storage to clear all rate limit tracking
    # Only reset if the limiter has been initialized (has a _storage attribute)
    try:
        if hasattr(limiter, '_storage') and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass
    yield
    # Clean up after test
    try:
        if hasattr(limiter, '_storage') and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass


@pytest.fixture
def app():
    """Application with testing config and in-memory DB."""
    application = create_app(TestingConfig)
    with application.app_context():
        # Enable foreign key constraints for SQLite (required for constraint violation tests)
        db.session.execute(db.text('PRAGMA foreign_keys = ON'))
        db.session.commit()
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        bootstrap_play_service_control(application)
        yield application
        # Clean up after test: drop all tables to isolate test state
        db.session.remove()
        db.drop_all()
        db.session.commit()
        db.session.remove()


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def app_bootstrap_on():
    """Application with ``ROUTING_REGISTRY_BOOTSTRAP=True`` for Area 2 final-gate HTTP proofs."""
    application = create_app(TestingConfigWithRoutingBootstrap)
    with application.app_context():
        db.session.execute(db.text("PRAGMA foreign_keys = ON"))
        db.session.commit()
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        bootstrap_play_service_control(application)
        yield application
        db.session.remove()
        db.drop_all()
        db.session.commit()
        db.session.remove()


@pytest.fixture
def client_bootstrap_on(app_bootstrap_on):
    """Test client for bootstrap-on app (isolated DB lifecycle from default ``app``)."""
    return app_bootstrap_on.test_client()


@pytest.fixture
def test_user_bootstrap(app_bootstrap_on):
    """Test user in bootstrap-on app database."""
    with app_bootstrap_on.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="testuser_bootstrap",
            password_hash=generate_password_hash("Testpass1"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Testpass1"


@pytest.fixture
def auth_headers_bootstrap_on(test_user_bootstrap, client_bootstrap_on):
    """JWT headers for ``test_user_bootstrap`` on bootstrap-on client."""
    user, password = test_user_bootstrap
    response = client_bootstrap_on.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    return {"Authorization": f"Bearer {data['access_token']}"}


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
def auth_user(test_user):
    """Return the test user tuple (user, password) for authenticated tests."""
    return test_user


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


class TestingConfigWithRoutingBootstrap(TestingConfig):
    """Testing config with routing registry bootstrap enabled (production-like global specs)."""

    ROUTING_REGISTRY_BOOTSTRAP = True


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
    """Admin with role_level 100 (SuperAdmin threshold). Used for hierarchy tests."""
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
def high_privilege_admin_user(app):
    """Admin with role_level 10000 for tests requiring high privilege level assignment."""
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        user = User(
            username="highprivilegeadmin",
            password_hash=generate_password_hash("HighPriv1"),
            role_id=role.id,
            role_level=10000,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "HighPriv1"


@pytest.fixture
def high_privilege_admin_headers(high_privilege_admin_user, client):
    """JWT headers for high_privilege_admin_user."""
    user, password = high_privilege_admin_user
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


@pytest.fixture
def forum_category(app):
    """Create a default forum category for tests.

    Returns the category ID (integer) to avoid DetachedInstanceError.
    Tests should reload the category from the database with:
        category = ForumCategory.query.get(forum_category)
    within an app context when they need the full object.
    """
    with app.app_context():
        from app.models import ForumCategory
        cat = ForumCategory.query.filter_by(slug="general").first()
        if not cat:
            cat = ForumCategory(
                slug="general",
                title="General Discussion",
                description="General discussion forum",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.commit()
        return cat.id


@pytest.fixture
def forum_locked_thread(app, test_user):
    """Create a locked forum thread for testing lock constraints.

    Returns the thread ID (integer) to avoid DetachedInstanceError.
    Tests should reload the thread from the database with:
        thread = ForumThread.query.get(forum_locked_thread)
    within an app context when they need the full object.
    """
    with app.app_context():
        from app.models import ForumCategory, ForumThread

        # Ensure a category exists
        cat = ForumCategory.query.filter_by(slug="general").first()
        if not cat:
            cat = ForumCategory(
                slug="general",
                title="General Discussion",
                description="General discussion forum",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

        # Get the test user
        user, _ = test_user

        # Create a locked thread
        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            title="Locked Thread",
            slug="locked-thread-fixture",
            is_locked=True,
            status="open"
        )
        db.session.add(thread)
        db.session.commit()
        return thread.id


@pytest.fixture
def forum_archived_category(app):
    """Create an archived/inactive forum category for testing category constraints.

    Returns the category ID (integer) to avoid DetachedInstanceError.
    Tests should reload the category from the database with:
        category = ForumCategory.query.get(forum_archived_category)
    within an app context when they need the full object.
    """
    with app.app_context():
        from app.models import ForumCategory

        cat = ForumCategory(
            slug="archived-category-fixture",
            title="Archived Category",
            description="This category is archived",
            sort_order=100,
            is_active=False,  # Mark as inactive/archived
            is_private=False
        )
        db.session.add(cat)
        db.session.commit()
        return cat.id


@pytest.fixture
def app_without_alembic_version(app):
    """Create app without alembic_version table for testing fallback behavior.

    This fixture returns an app where the alembic_version table may not exist,
    allowing tests to verify fallback behavior when the migration table is missing.
    """
    with app.app_context():
        from sqlalchemy import text
        # Drop alembic_version table if it exists to test fallback behavior
        try:
            db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
            db.session.commit()
        except Exception:
            pass
    return app


@pytest.fixture
def app_with_alembic_version(app):
    """Create alembic_version table for tests that need schema revision info.

    This fixture creates a test alembic_version table and returns the app.
    Tests that depend on schema_revision can use this fixture instead of 'app'.
    """
    with app.app_context():
        from sqlalchemy import text
        # Create alembic_version table if it doesn't exist
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    PRIMARY KEY (version_num)
                )
            """))
            db.session.commit()

            # Check if version already exists
            result = db.session.execute(text("SELECT version_num FROM alembic_version")).first()
            if not result:
                # Insert a test version
                db.session.execute(text(
                    "INSERT INTO alembic_version (version_num) VALUES ('test_version_001')"
                ))
                db.session.commit()
        except Exception:
            # If table creation fails, just proceed (table might already exist)
            pass

    return app


@pytest.fixture(autouse=True)
def ensure_schema_revision(app):
    """Ensure alembic_version table exists with a test version.

    This autouse fixture ensures all tests have access to a valid schema revision.
    It creates the alembic_version table during app initialization if it doesn't exist.
    """
    with app.app_context():
        from sqlalchemy import text
        try:
            # Try to create the alembic_version table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    PRIMARY KEY (version_num)
                )
            """))
            db.session.commit()

            # Check if a version exists
            try:
                result = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
                if not result:
                    # Insert a test version for tests to use
                    db.session.execute(text(
                        "INSERT INTO alembic_version (version_num) VALUES ('00001_test')"
                    ))
                    db.session.commit()
            except Exception:
                # If the insert fails (e.g., unique constraint), just continue
                db.session.rollback()
        except Exception:
            # If table creation fails, that's okay - tests can still work with empty revision
            db.session.rollback()
        finally:
            # Ensure the session is clean for the test
            db.session.remove()
    yield
    # Cleanup is handled by the app fixture's session management


# Fixture for patch tests that instantiate models without full Flask context
@pytest.fixture
def isolated_app_context(app):
    """Provide isolated app context for unit tests that import models directly.

    Patch tests that create model instances without database need this fixture
    to ensure proper Flask app context and avoid SQLAlchemy table conflicts.
    """
    with app.app_context():
        yield app


# Known foreign/corrupted test modules accidentally carried into backend/.
# They either target the separate world-engine service or contain incomplete generated text.
collect_ignore = [
    "test_runtime_manager.py",
    "test_narrow_followup.py",
    "test_suggestion_coverage_complete.py",
    "test_task_executor_fallback.py",
]
