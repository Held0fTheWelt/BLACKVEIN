"""Unit tests for Langfuse adapter payload helpers (sanitization, trace id)."""

from __future__ import annotations

import logging
import os

import pytest

from app.observability import langfuse_adapter as lf_mod
from app.observability.langfuse_adapter import (
    LangfuseAdapter,
    _langfuse_sanitize_value,
)


def test_langfuse_sanitize_truncates_long_strings() -> None:
    huge = "x" * 25000
    out = _langfuse_sanitize_value({"prompt": huge}, max_str=5000)
    assert isinstance(out, dict)
    assert len(out["prompt"]) < 5100
    assert out["prompt"].endswith("…")


def test_langfuse_sanitize_truncates_long_lists() -> None:
    out = _langfuse_sanitize_value(list(range(200)), max_list=10)
    assert isinstance(out, list)
    assert len(out) == 10


def test_normalize_trace_id_strips_uuid_hyphens() -> None:
    tid = "ABCDEF01-2345-6789-ABCD-EF0123456789"
    assert LangfuseAdapter._normalize_trace_id_for_score_api(tid) == "abcdef0123456789abcdef0123456789"


def test_normalize_trace_id_preserves_32_hex() -> None:
    tid = "abcdef0123456789abcdef0123456789"
    assert LangfuseAdapter._normalize_trace_id_for_score_api(tid) == tid


def test_normalize_trace_id_rejects_non_w3c_strings() -> None:
    assert LangfuseAdapter._normalize_trace_id_for_score_api("trace-child-session") is None
    assert LangfuseAdapter._normalize_trace_id_for_score_api("not-a-valid-uuid-at-all") is None


def test_align_langfuse_otel_sets_live_when_backend_staging(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability import langfuse_adapter as lf_mod

    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    try:
        assert lf_mod._align_langfuse_otel_resource_environment("staging") is True
        assert os.environ.get("LANGFUSE_TRACING_ENVIRONMENT") == "live"
    finally:
        monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)


def test_align_langfuse_otel_noop_when_tracing_env_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability import langfuse_adapter as lf_mod

    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "production")
    assert lf_mod._align_langfuse_otel_resource_environment("staging") is False


def test_ingestion_error_bridge_patches_score_consumer_handle_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """score_ingestion_consumer binds handle_exception at import; bridge must replace that binding."""
    from langfuse._task_manager import score_ingestion_consumer as sic
    from langfuse._utils import parse_error as pe

    monkeypatch.setenv("WOS_LANGFUSE_INGESTION_ERROR_DETAIL", "1")
    lf_mod._LANGFUSE_INGESTION_ERROR_BRIDGE = False
    orig_pe = pe.handle_exception
    orig_sic = sic.handle_exception
    try:
        lf_mod._install_langfuse_ingestion_error_bridge()
        assert lf_mod._LANGFUSE_INGESTION_ERROR_BRIDGE is True
        assert sic.handle_exception is not orig_sic
        assert pe.handle_exception is not orig_pe
    finally:
        lf_mod._LANGFUSE_INGESTION_ERROR_BRIDGE = False
        sic.handle_exception = orig_sic
        pe.handle_exception = orig_pe
        monkeypatch.delenv("WOS_LANGFUSE_INGESTION_ERROR_DETAIL", raising=False)


def test_wos_langfuse_debug_installs_stream_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """WOS_LANGFUSE_DEBUG must attach a handler; otherwise uvicorn root INFO drops SDK DEBUG lines."""
    monkeypatch.setenv("WOS_LANGFUSE_DEBUG", "1")
    lf_mod._LANGFUSE_DEBUG_APPLIED = False
    for name in ("langfuse", "langfuse.api"):
        lg = logging.getLogger(name)
        lg.handlers = [h for h in lg.handlers if not getattr(h, lf_mod._LANGFUSE_DEBUG_HANDLER_ATTR, False)]
        lg.propagate = True
    try:
        lf_mod._apply_langfuse_debug_env()
        for name in ("langfuse", "langfuse.api"):
            lg = logging.getLogger(name)
            assert any(getattr(h, lf_mod._LANGFUSE_DEBUG_HANDLER_ATTR, False) for h in lg.handlers)
            assert lg.propagate is False
    finally:
        for name in ("langfuse", "langfuse.api"):
            lg = logging.getLogger(name)
            lg.handlers = [h for h in lg.handlers if not getattr(h, lf_mod._LANGFUSE_DEBUG_HANDLER_ATTR, False)]
            lg.propagate = True
        lf_mod._LANGFUSE_DEBUG_APPLIED = False
