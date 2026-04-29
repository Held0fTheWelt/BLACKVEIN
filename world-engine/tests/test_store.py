from __future__ import annotations

import json

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.store import JsonRunStore, build_run_store



def test_json_store_roundtrip_persists_runtime_instances(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:solo", display_name="Solo")

    store = JsonRunStore(tmp_path)
    loaded = store.load_all()

    assert any(instance.id == run.id for instance in loaded)
    assert store.describe()["backend"] == "json"



def test_json_store_skips_invalid_documents(tmp_path):
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{not valid json", encoding="utf-8")

    store = JsonRunStore(tmp_path)

    assert store.load_all() == []



def test_build_run_store_supports_json_backend(tmp_path):
    store = build_run_store(root=tmp_path, backend="json")
    assert isinstance(store, JsonRunStore)



def test_build_run_store_rejects_unknown_backend(tmp_path):
    with pytest.raises(ValueError, match="Unsupported run store backend"):
        build_run_store(root=tmp_path, backend="redis")


@pytest.mark.skipif(not __import__("importlib").util.find_spec("sqlalchemy"), reason="sqlalchemy not installed")
def test_build_run_store_sqlalchemy_requires_url(tmp_path):
    with pytest.raises(ValueError, match="RUN_STORE_URL is required"):
        build_run_store(root=tmp_path, backend="sqlalchemy")
