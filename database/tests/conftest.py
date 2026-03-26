"""Database test fixtures and configuration."""
import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db, limiter
from app.models.role import ensure_roles_seeded
from app.models.area import ensure_areas_seeded


@pytest.fixture(scope="session", autouse=True)
def change_to_backend_dir():
    """Change to backend directory for tests that need alembic."""
    original_cwd = os.getcwd()
    os.chdir(str(backend_path))
    yield
    os.chdir(original_cwd)


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Clear rate limiter state before each test to prevent cross-test contamination."""
    try:
        if hasattr(limiter, '_storage') and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass
    yield
    try:
        if hasattr(limiter, '_storage') and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass


@pytest.fixture
def app():
    """Create Flask app for testing with proper database configuration."""
    application = create_app(TestingConfig)
    with application.app_context():
        # Enable foreign key constraints for SQLite (required for constraint violation tests)
        _db.session.execute(_db.text('PRAGMA foreign_keys = ON'))
        _db.session.commit()
        _db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        yield application


@pytest.fixture
def db(app):
    """Database fixture."""
    return _db


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()
