"""Database test fixtures and configuration."""
import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from flask import Flask
from app.extensions import db as _db
from run import app as create_app


@pytest.fixture(scope="session", autouse=True)
def change_to_backend_dir():
    """Change to backend directory for tests that need alembic."""
    original_cwd = os.getcwd()
    os.chdir(str(backend_path))
    yield
    os.chdir(original_cwd)


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Database fixture."""
    return _db


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()
