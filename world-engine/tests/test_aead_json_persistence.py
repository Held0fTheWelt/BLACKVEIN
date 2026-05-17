from __future__ import annotations

import json

import pytest

pytest.importorskip("cryptography.hazmat.primitives.ciphers.aead")

from app.runtime.json_at_rest import JsonAtRestCodec, generate_aead_key
from app.runtime.models import RuntimeInstance
from app.runtime.store import JsonRunStore, build_run_store
from app.story_runtime.story_session_store import JsonStorySessionStore


def _runtime_instance(run_id: str = "run-aead") -> RuntimeInstance:
    return RuntimeInstance(
        id=run_id,
        template_id="test-template",
        template_title="AEAD Test Template",
        kind="solo_story",
        join_policy="owner_only",
        beat_id="opening",
        owner_account_id="acct:encrypted",
    )


def test_json_aead_run_store_writes_encrypted_envelope_and_roundtrips(tmp_path):
    codec = JsonAtRestCodec.from_key_string(generate_aead_key())
    store = JsonRunStore(tmp_path, codec=codec)
    instance = _runtime_instance()

    store.save(instance)

    saved_file = tmp_path / "run-aead.json.enc"
    assert saved_file.exists()
    raw = saved_file.read_text(encoding="utf-8")
    envelope = json.loads(raw)
    assert envelope["format"] == "wos.aead-json.v1"
    assert envelope["algorithm"] == "AES-256-GCM"
    assert "AEAD Test Template" not in raw
    assert "acct:encrypted" not in raw

    loaded = JsonRunStore(tmp_path, codec=codec).load_all()
    assert [item.id for item in loaded] == ["run-aead"]
    assert loaded[0].owner_account_id == "acct:encrypted"
    assert store.describe()["backend"] == "json_aead"
    assert store.describe()["encrypted_at_rest"] == "yes"


def test_build_run_store_supports_json_aead_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_ENGINE_JSON_AEAD_KEY", generate_aead_key())

    store = build_run_store(root=tmp_path, backend="json_aead")

    assert isinstance(store, JsonRunStore)
    assert store.describe()["backend"] == "json_aead"


def test_build_run_store_json_aead_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("WORLD_ENGINE_JSON_AEAD_KEY", raising=False)
    monkeypatch.delenv("RUN_STORE_JSON_AEAD_KEY", raising=False)

    with pytest.raises(ValueError, match="AEAD JSON persistence"):
        build_run_store(root=tmp_path, backend="json_aead")


def test_aead_env_placeholders_are_treated_as_unconfigured(monkeypatch):
    monkeypatch.setenv("WORLD_ENGINE_JSON_AEAD_KEY", "__AUTO_GENERATED_DO_NOT_EDIT__")
    monkeypatch.delenv("RUN_STORE_JSON_AEAD_KEY", raising=False)

    assert JsonAtRestCodec.from_env().encrypted is False


def test_story_session_store_uses_aead_codec(tmp_path):
    codec = JsonAtRestCodec.from_key_string(generate_aead_key())
    store = JsonStorySessionStore(tmp_path / "story_sessions", codec=codec)
    payload = {
        "session_id": "session-aead",
        "module_id": "m",
        "history": [{"player_input": "secret move"}],
    }

    store.save("session-aead", payload)

    saved_file = tmp_path / "story_sessions" / "session-aead.json.enc"
    raw = saved_file.read_text(encoding="utf-8")
    assert "secret move" not in raw
    assert store.load_all_raw()["session-aead"] == payload
