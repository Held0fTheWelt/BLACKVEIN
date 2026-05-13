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


def test_normalize_create_score_scope_trace_and_observation_strips_session() -> None:
    tid = "a" * 32
    out, scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {
            "name": "n",
            "value": 1.0,
            "trace_id": tid,
            "observation_id": "obs-1",
            "session_id": "sess-1",
            "metadata": {},
        }
    )
    assert scope == "observation"
    assert out is not None
    assert out["trace_id"] == tid
    assert out["observation_id"] == "obs-1"
    assert "session_id" not in out


def test_normalize_create_score_scope_trace_only_strips_session() -> None:
    tid = "b" * 32
    out, scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {"name": "n", "value": 0.0, "trace_id": tid, "session_id": "s", "extra": 1}
    )
    assert scope == "trace"
    assert out is not None
    assert out["trace_id"] == tid
    assert "session_id" not in out
    assert out.get("extra") == 1


def test_normalize_create_score_scope_session_only() -> None:
    out, scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {"name": "n", "value": 1.0, "session_id": "only-session"}
    )
    assert scope == "session"
    assert out is not None
    assert out["session_id"] == "only-session"
    assert "trace_id" not in out


def test_normalize_create_score_scope_dataset_wins_over_trace_and_session() -> None:
    tid = "c" * 32
    out, scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {
            "name": "n",
            "value": 1.0,
            "trace_id": tid,
            "session_id": "s",
            "dataset_run_id": "dr-1",
        }
    )
    assert scope == "dataset"
    assert out is not None
    assert out["dataset_run_id"] == "dr-1"
    assert "trace_id" not in out
    assert "session_id" not in out


def test_normalize_create_score_scope_observation_without_trace_skipped() -> None:
    out, scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {"name": "n", "observation_id": "orphan-obs"}
    )
    assert out is None
    assert scope == "skipped"


def test_add_score_create_score_emits_trace_and_observation_not_session() -> None:
    """Deterministic duplicate create_score must not send session_id when trace_id exists."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    trace_hex = "0123456789abcdef0123456789abcdef"
    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    client = MagicMock()
    adapter._clients = {"development": client}
    span = MagicMock()
    span.trace_id = trace_hex
    span.id = "0102030405060708"
    span.name = "world-engine.turn"
    token = lf_mod._active_span_context.set(span)
    try:
        LangfuseAdapter.add_score(
            adapter,
            name="contract_score",
            value=1.0,
            metadata={"session_id": "story-sid-99"},
        )
    finally:
        lf_mod._active_span_context.reset(token)

    client.create_score.assert_called_once()
    cc_kw = client.create_score.call_args.kwargs
    assert cc_kw["trace_id"] == trace_hex
    assert cc_kw.get("observation_id") == "0102030405060708"
    assert "session_id" not in cc_kw


def test_wos_langfuse_score_scope_debug_emits_info_line(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("WOS_LANGFUSE_SCORE_DEBUG", "1")
    caplog.set_level(logging.INFO, logger="app.observability.langfuse_adapter")
    LangfuseAdapter._log_wos_langfuse_score_scope_debug(
        "score_x",
        has_trace_id=True,
        has_observation_id=False,
        had_session_before_norm=True,
        emitted_scope="trace",
    )
    assert any("score_scope" in r.message for r in caplog.records)
    assert any("emitted_scope=trace" in r.message for r in caplog.records)


def test_wos_langfuse_score_scope_debug_default_on_when_env_unset(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.delenv("WOS_LANGFUSE_SCORE_DEBUG", raising=False)
    caplog.set_level(logging.INFO, logger="app.observability.langfuse_adapter")
    LangfuseAdapter._log_wos_langfuse_score_scope_debug(
        "score_y",
        has_trace_id=True,
        has_observation_id=True,
        had_session_before_norm=False,
        emitted_scope="observation",
    )
    assert any("score_y" in r.message and "score_scope" in r.message for r in caplog.records)


def test_wos_langfuse_score_scope_debug_off_when_zero(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("WOS_LANGFUSE_SCORE_DEBUG", "0")
    caplog.set_level(logging.INFO, logger="app.observability.langfuse_adapter")
    LangfuseAdapter._log_wos_langfuse_score_scope_debug(
        "score_z",
        has_trace_id=True,
        has_observation_id=False,
        had_session_before_norm=False,
        emitted_scope="trace",
    )
    assert not any("score_scope" in r.message for r in caplog.records)


def test_align_langfuse_otel_sets_backend_environment_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.observability import langfuse_adapter as lf_mod

    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    try:
        assert lf_mod._align_langfuse_otel_resource_environment("staging") is True
        assert os.environ.get("LANGFUSE_TRACING_ENVIRONMENT") == "staging"
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
