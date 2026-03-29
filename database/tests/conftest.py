"""Database test fixtures and helpers for the current backend schema."""
from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db, limiter
from app.models import (
    ForumCategory,
    ForumPost,
    ForumThread,
    Role,
    User,
)
from app.models.area import ensure_areas_seeded
from app.models.role import ensure_roles_seeded


@pytest.fixture(scope="session", autouse=True)
def change_to_backend_dir():
    """Change to backend directory so alembic.ini resolves correctly."""
    original_cwd = os.getcwd()
    os.chdir(str(backend_path))
    try:
        yield
    finally:
        os.chdir(original_cwd)


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Reset in-memory rate limiter state between tests."""
    try:
        if hasattr(limiter, "_storage") and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass

    yield

    try:
        if hasattr(limiter, "_storage") and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass


@pytest.fixture
def app():
    """Application with isolated in-memory database."""
    application = create_app(TestingConfig)
    with application.app_context():
        _db.session.execute(_db.text("PRAGMA foreign_keys = ON"))
        _db.session.commit()
        _db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Database fixture."""
    return _db


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def user_factory(db):
    """Create persisted users with sane defaults and unique identities."""
    counter = itertools.count(1)

    def make_user(*, role_name: str = Role.NAME_USER, username: str | None = None, email: str | None = None, **kwargs):
        index = next(counter)
        role = Role.query.filter_by(name=role_name).first()
        assert role is not None, f"role {role_name!r} must exist"

        user = User(
            username=username or f"user_{index}",
            email=email,
            password_hash=kwargs.pop("password_hash", generate_password_hash(f"Password{index}!")),
            role_id=kwargs.pop("role_id", role.id),
            role_level=kwargs.pop("role_level", role.default_role_level or 0),
            **kwargs,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user

    return make_user


@pytest.fixture
def category_factory(db):
    """Create persisted forum categories."""
    counter = itertools.count(1)

    def make_category(**kwargs):
        index = next(counter)
        category = ForumCategory(
            slug=kwargs.pop("slug", f"category-{index}"),
            title=kwargs.pop("title", f"Category {index}"),
            **kwargs,
        )
        db.session.add(category)
        db.session.commit()
        db.session.refresh(category)
        return category

    return make_category


@pytest.fixture
def thread_factory(db, category_factory, user_factory):
    """Create persisted forum threads with defaults."""
    counter = itertools.count(1)

    def make_thread(**kwargs):
        index = next(counter)
        category = kwargs.pop("category", None) or category_factory()
        author = kwargs.pop("author", None)
        if author is None and kwargs.get("author_id", "__missing__") == "__missing__":
            author = user_factory()

        thread = ForumThread(
            category_id=kwargs.pop("category_id", category.id),
            author_id=kwargs.pop("author_id", author.id if author else None),
            slug=kwargs.pop("slug", f"thread-{index}"),
            title=kwargs.pop("title", f"Thread {index}"),
            **kwargs,
        )
        db.session.add(thread)
        db.session.commit()
        db.session.refresh(thread)
        return thread

    return make_thread


@pytest.fixture
def post_factory(db, thread_factory, user_factory):
    """Create persisted forum posts with defaults."""
    counter = itertools.count(1)

    def make_post(**kwargs):
        index = next(counter)
        thread = kwargs.pop("thread", None) or thread_factory()
        author = kwargs.pop("author", None)
        if author is None and kwargs.get("author_id", "__missing__") == "__missing__":
            author = user_factory()

        post = ForumPost(
            thread_id=kwargs.pop("thread_id", thread.id),
            author_id=kwargs.pop("author_id", author.id if author else None),
            content=kwargs.pop("content", f"Post content {index}"),
            **kwargs,
        )
        db.session.add(post)
        db.session.commit()
        db.session.refresh(post)
        return post

    return make_post
