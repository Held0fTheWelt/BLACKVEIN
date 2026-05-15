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


def test_record_wos_nested_span_observation_uses_active_parent() -> None:
    from types import SimpleNamespace

    class _Child:
        trace_id = "0123456789abcdef0123456789abcdef"
        id = "child-obs"

        def __init__(self) -> None:
            self.ended = False

        def end(self) -> None:
            self.ended = True

    class _Parent:
        trace_id = "0123456789abcdef0123456789abcdef"
        id = "parent-obs"

        def __init__(self) -> None:
            self.child = _Child()
            self.kwargs: dict[str, object] | None = None

        def start_observation(self, **kwargs):
            self.kwargs = kwargs
            return self.child

    parent = _Parent()
    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    adapter._clients = {"development": object()}

    token = lf_mod._active_span_context.set(parent)
    try:
        diag = adapter.record_wos_nested_span_observation(
            name="story.semantic_capability.local_evidence",
            metadata={"proof_level": "local_only"},
            input_data={"turn": 1},
            output_data={"contract_pass": True},
        )
    finally:
        lf_mod._active_span_context.reset(token)

    assert diag["emitted"] is True
    assert diag["proof_level"] == "local_only"
    assert diag["live_or_staging_evidence"] is False
    assert diag["langfuse_trace_id"] == "0123456789abcdef0123456789abcdef"
    assert parent.kwargs is not None
    assert parent.kwargs["as_type"] == "span"
    assert parent.kwargs["name"] == "story.semantic_capability.local_evidence"
    assert parent.child.ended is True


def test_record_adr0041_langfuse_scores_are_local_only_scores() -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    client = MagicMock()
    parent = MagicMock()
    parent.trace_id = "0123456789abcdef0123456789abcdef"
    parent.id = "parent-obs"

    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    adapter._clients = {"development": client}

    token = lf_mod._active_span_context.set(parent)
    try:
        diag = adapter.record_adr0041_langfuse_scores(
            scores=[("npc_agency_contract", 1.0), ("scene_energy_contract", 0.5)],
            comment="local contract evidence",
        )
    finally:
        lf_mod._active_span_context.reset(token)

    assert diag["emitted"] is True
    assert diag["scores_emitted"] == 2
    assert client.create_score.call_count == 2
    for call in client.create_score.call_args_list:
        metadata = call.kwargs["metadata"]
        assert metadata["score_origin"] == "adr0041_runtime_intelligence"
        assert metadata["proof_level"] == "local_only"
        assert metadata["live_or_staging_evidence"] is False
        assert "session_id" not in call.kwargs


def test_trace_metadata_backfill_reports_unsupported_when_sdk_method_missing() -> None:
    from types import SimpleNamespace

    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    # No update surfaces exposed.
    adapter._clients = {"development": object()}

    diag = LangfuseAdapter.backfill_trace_metadata_after_commit(
        adapter,
        trace_id="0123456789abcdef0123456789abcdef",
        canonical_turn_id="story-1:turn:1",
        story_session_id="story-1",
        turn_number=1,
        environment="development",
    )

    assert diag["attempted"] is True
    assert diag["supported"] is False
    assert diag["success"] is False
    assert diag["reason"] == "sdk_method_unavailable"


def test_trace_metadata_backfill_merges_canonical_turn_metadata_when_supported() -> None:
    from types import SimpleNamespace

    class _FakeClient:
        def __init__(self) -> None:
            self.updated: dict[str, object] | None = None

        def get_trace(self, **kwargs):
            assert kwargs["trace_id"] == "0123456789abcdef0123456789abcdef"
            return {"id": kwargs["trace_id"], "metadata": {"existing_key": "existing_value"}}

        def update_trace(self, **kwargs):
            self.updated = kwargs
            return {"ok": True}

    client = _FakeClient()
    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    adapter._clients = {"development": client}

    diag = LangfuseAdapter.backfill_trace_metadata_after_commit(
        adapter,
        trace_id="0123456789abcdef0123456789abcdef",
        canonical_turn_id="story-1:turn:1",
        story_session_id="story-1",
        turn_number=1,
        environment="development",
    )

    assert diag["supported"] is True
    assert diag["success"] is True
    assert client.updated is not None
    merged_md = client.updated["metadata"]
    assert isinstance(merged_md, dict)
    assert merged_md["existing_key"] == "existing_value"
    assert merged_md["canonical_turn_id"] == "story-1:turn:1"
    assert merged_md["story_session_id"] == "story-1"
    assert merged_md["turn_number"] == 1


def test_trace_metadata_backfill_does_not_raise_on_langfuse_error() -> None:
    from types import SimpleNamespace

    class _ExplodingClient:
        def update_trace(self, **kwargs):
            raise RuntimeError("simulated_update_failure")

    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    adapter._clients = {"development": _ExplodingClient()}

    diag = LangfuseAdapter.backfill_trace_metadata_after_commit(
        adapter,
        trace_id="0123456789abcdef0123456789abcdef",
        canonical_turn_id="story-1:turn:2",
        story_session_id="story-1",
        turn_number=2,
        environment="development",
    )

    assert diag["attempted"] is True
    assert diag["supported"] is True
    assert diag["success"] is False
    assert diag["reason"] == "backfill_failed"


def test_trace_metadata_backfill_does_not_change_score_scope_normalization() -> None:
    from types import SimpleNamespace

    baseline, baseline_scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {
            "name": "gate_score",
            "value": 1.0,
            "trace_id": "a" * 32,
            "observation_id": "obs-1",
            "session_id": "sess-1",
        }
    )

    adapter = LangfuseAdapter.__new__(LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    adapter._clients = {"development": object()}
    _ = LangfuseAdapter.backfill_trace_metadata_after_commit(
        adapter,
        trace_id="a" * 32,
        canonical_turn_id="story-1:turn:3",
        story_session_id="story-1",
        turn_number=3,
        environment="development",
    )

    after, after_scope = LangfuseAdapter._normalize_langfuse_create_score_scope_kwargs(
        {
            "name": "gate_score",
            "value": 1.0,
            "trace_id": "a" * 32,
            "observation_id": "obs-1",
            "session_id": "sess-1",
        }
    )

    assert baseline_scope == "observation"
    assert after_scope == baseline_scope
    assert after == baseline


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
