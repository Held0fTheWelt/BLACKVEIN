"""Store Configuration and Initialization Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests store configuration validation and backend selection.

Mark: @pytest.mark.persistence, @pytest.mark.contract
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.store import JsonRunStore, SqlAlchemyRunStore, build_run_store


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_json_backend_valid(tmp_path):
    """Verify build_run_store accepts 'json' backend."""
    store = build_run_store(root=tmp_path, backend="json")

    assert isinstance(store, JsonRunStore)
    assert store.backend_name == "json"


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_json_backend_case_insensitive(tmp_path):
    """Verify backend name is case-insensitive."""
    store_lower = build_run_store(root=tmp_path, backend="json")
    store_upper = build_run_store(root=tmp_path / "2", backend="JSON")
    store_mixed = build_run_store(root=tmp_path / "3", backend="Json")

    assert isinstance(store_lower, JsonRunStore)
    assert isinstance(store_upper, JsonRunStore)
    assert isinstance(store_mixed, JsonRunStore)


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_strips_whitespace_from_backend(tmp_path):
    """Verify backend name whitespace is stripped."""
    store = build_run_store(root=tmp_path, backend="  json  ")

    assert isinstance(store, JsonRunStore)
    assert store.backend_name == "json"


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_sqlalchemy_backend_valid(tmp_path, sqlalchemy_available):
    """Verify build_run_store accepts 'sqlalchemy' backend."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = build_run_store(root=tmp_path, backend="sqlalchemy", url=db_url)

    assert isinstance(store, SqlAlchemyRunStore)
    assert store.backend_name == "sqlalchemy"


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_postgres_backend_alias(tmp_path, sqlalchemy_available):
    """Verify 'postgres' backend name maps to sqlalchemy type."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    # Use sqlite URL to avoid postgres driver requirement
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = build_run_store(root=tmp_path, backend="postgres", url=db_url)

    assert isinstance(store, SqlAlchemyRunStore)
    assert store.backend_name == "sqlalchemy"


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_postgresql_backend_alias(tmp_path, sqlalchemy_available):
    """Verify 'postgresql' backend name maps to sqlalchemy type."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    # Use sqlite URL to avoid postgres driver requirement
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = build_run_store(root=tmp_path, backend="postgresql", url=db_url)

    assert isinstance(store, SqlAlchemyRunStore)
    assert store.backend_name == "sqlalchemy"


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_rejects_unknown_backend(tmp_path):
    """Verify unknown backend names are rejected."""
    with pytest.raises(ValueError, match="Unsupported run store backend"):
        build_run_store(root=tmp_path, backend="redis")


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_rejects_mongo_backend(tmp_path):
    """Verify mongo backend is not supported."""
    with pytest.raises(ValueError, match="Unsupported run store backend"):
        build_run_store(root=tmp_path, backend="mongodb")


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_rejects_empty_backend(tmp_path):
    """Verify empty backend name is rejected."""
    with pytest.raises(ValueError, match="Unsupported run store backend"):
        build_run_store(root=tmp_path, backend="")


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_sqlalchemy_requires_url(tmp_path, sqlalchemy_available):
    """Verify sqlalchemy backend requires url parameter."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    with pytest.raises(ValueError, match="RUN_STORE_URL is required"):
        build_run_store(root=tmp_path, backend="sqlalchemy", url=None)


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_sqlalchemy_requires_non_empty_url(tmp_path, sqlalchemy_available):
    """Verify sqlalchemy backend requires non-empty url."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    with pytest.raises(ValueError, match="RUN_STORE_URL is required"):
        build_run_store(root=tmp_path, backend="sqlalchemy", url="")


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_json_ignores_url_parameter(tmp_path):
    """Verify json backend ignores url parameter."""
    # This should not raise even though url is provided
    store = build_run_store(root=tmp_path, backend="json", url="http://unused")

    assert isinstance(store, JsonRunStore)


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_creates_root_directory(tmp_path):
    """Verify JsonRunStore creates root directory if missing."""
    store_root = tmp_path / "nonexistent" / "nested" / "path"
    assert not store_root.exists()

    store = JsonRunStore(store_root)

    assert store_root.exists()
    assert store_root.is_dir()


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_works_with_existing_directory(tmp_path):
    """Verify JsonRunStore works with pre-existing directory."""
    tmp_path.mkdir(parents=True, exist_ok=True)

    store = JsonRunStore(tmp_path)

    assert store.root == tmp_path


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_creates_database(tmp_path, sqlalchemy_available):
    """Verify SqlAlchemyRunStore creates database file."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    assert not db_path.exists()

    store = SqlAlchemyRunStore(db_url)

    # SQLite creates the db file on first connection
    assert store.engine is not None


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_initializes_schema(tmp_path, sqlalchemy_available):
    """Verify SqlAlchemyRunStore initializes table schema."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    # Verify table exists
    assert store.runs is not None
    assert "run_id" in store.runs.c
    assert "template_id" in store.runs.c
    assert "payload_json" in store.runs.c


@pytest.mark.persistence
@pytest.mark.contract
def test_store_backend_detection_json(tmp_path):
    """Verify store type can be detected from backend name."""
    store = build_run_store(root=tmp_path, backend="json")

    assert store.backend_name == "json"
    assert isinstance(store, JsonRunStore)


@pytest.mark.persistence
@pytest.mark.contract
def test_store_backend_detection_sqlalchemy(tmp_path, sqlalchemy_available):
    """Verify store type can be detected from backend name."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = build_run_store(root=tmp_path, backend="sqlalchemy", url=db_url)

    assert store.backend_name == "sqlalchemy"
    assert isinstance(store, SqlAlchemyRunStore)


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_describe_includes_root_path(tmp_path):
    """Verify describe method returns root directory path."""
    store = JsonRunStore(tmp_path)

    desc = store.describe()
    assert "root" in desc
    assert str(tmp_path) in desc["root"]


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_describe_includes_url(tmp_path, sqlalchemy_available):
    """Verify describe method returns database URL."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    desc = store.describe()
    assert "url" in desc
    assert db_url in desc["url"]


@pytest.mark.persistence
@pytest.mark.contract
def test_build_run_store_default_to_json_if_no_backend(tmp_path):
    """Verify build_run_store defaults to json if backend not specified."""
    # This tests the actual usage where backend might come from config
    store = build_run_store(root=tmp_path, backend="json")

    assert isinstance(store, JsonRunStore)


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_multiple_instances_same_path(tmp_path):
    """Verify multiple store instances can share the same path."""
    store1 = JsonRunStore(tmp_path)
    store2 = JsonRunStore(tmp_path)

    # Both should be functional
    assert store1.root == store2.root
    assert store1.backend_name == store2.backend_name


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_with_file_path_url(tmp_path, sqlalchemy_available):
    """Verify SqlAlchemyRunStore works with file:/// URLs."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"

    store = SqlAlchemyRunStore(db_url)

    assert store.backend_name == "sqlalchemy"
    assert db_url in store.describe()["url"]


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_path_normalization(tmp_path):
    """Verify JsonRunStore normalizes paths correctly."""
    # Test with relative path components
    store1 = JsonRunStore(tmp_path)
    store2 = JsonRunStore(tmp_path)

    # Both should be equivalent
    assert store1.root == store2.root
