from __future__ import annotations

import json

from app.story_runtime.callback_web_store import JsonCallbackWebStore
from story_runtime_core.callbacks import CALLBACK_WEB_RECORD_SCHEMA_VERSION


def _record(callback_web_id: str, session_id: str = "session-1") -> dict:
    return {
        "schema_version": CALLBACK_WEB_RECORD_SCHEMA_VERSION,
        "callback_web_id": callback_web_id,
        "story_session_id": session_id,
        "status": "active",
        "edges": [],
        "observations": [],
        "created_at": "2026-05-15T00:00:00+00:00",
        "updated_at": "2026-05-15T00:00:00+00:00",
    }


def test_callback_web_store_roundtrips_json(tmp_path) -> None:
    store = JsonCallbackWebStore(tmp_path / "callback_webs")
    store.save("callback-web-1", _record("callback-web-1"))

    loaded = store.load("callback-web-1")

    assert loaded["callback_web_id"] == "callback-web-1"
    assert loaded["story_session_id"] == "session-1"
    assert not list((tmp_path / "callback_webs").glob("*.tmp"))
    raw = json.loads((tmp_path / "callback_webs" / "callback-web-1.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == CALLBACK_WEB_RECORD_SCHEMA_VERSION


def test_callback_web_store_filters_by_session_and_skips_corrupt_files(tmp_path) -> None:
    store = JsonCallbackWebStore(tmp_path / "callback_webs")
    store.save("callback-web-1", _record("callback-web-1", "session-1"))
    store.save("callback-web-2", _record("callback-web-2", "session-2"))
    (tmp_path / "callback_webs" / "broken.json").write_text("{broken", encoding="utf-8")

    rows = store.load_for_session("session-1")

    assert [row["callback_web_id"] for row in rows] == ["callback-web-1"]
