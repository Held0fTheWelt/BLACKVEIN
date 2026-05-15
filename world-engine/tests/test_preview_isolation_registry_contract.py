"""Contract tests for preview session isolation (in-memory, no I/O mocks)."""

from __future__ import annotations

import pytest

from app.narrative.preview_isolation import PreviewIsolationRegistry


@pytest.mark.contract
def test_preview_isolation_load_start_end_lifecycle() -> None:
    reg = PreviewIsolationRegistry()
    reg.load_preview(module_id="m1", preview_id="p1")
    with pytest.raises(ValueError, match="preview_already_loaded"):
        reg.load_preview(module_id="m1", preview_id="p1")

    sess = reg.start_session(module_id="m1", preview_id="p1", session_seed="seed-a")
    assert sess.namespace == "preview:m1:p1:seed-a"
    desc = reg.describe()
    assert desc["preview_session_count"] == 1

    reg.end_session(sess.preview_session_id)
    with pytest.raises(KeyError, match="preview_session_not_found"):
        reg.end_session(sess.preview_session_id)

    reg.unload_preview(module_id="m1", preview_id="p1")
    with pytest.raises(KeyError, match="preview_not_loaded"):
        reg.unload_preview(module_id="m1", preview_id="p1")


@pytest.mark.contract
def test_preview_isolation_namespace_collision() -> None:
    reg = PreviewIsolationRegistry()
    reg.load_preview(module_id="m1", preview_id="p1")
    reg.start_session(module_id="m1", preview_id="p1", session_seed="dup")
    with pytest.raises(ValueError, match="preview_session_collision"):
        reg.start_session(module_id="m1", preview_id="p1", session_seed="dup")
