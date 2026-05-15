"""Tests for trace ID context helpers (no network)."""

from __future__ import annotations

import pytest

from app.observability import trace as trace_mod


@pytest.fixture(autouse=True)
def _reset_trace_context() -> None:
    trace_mod.TRACE_ID.set(None)
    trace_mod.LANGFUSE_TRACE_ID.set(None)
    yield
    trace_mod.TRACE_ID.set(None)
    trace_mod.LANGFUSE_TRACE_ID.set(None)


@pytest.mark.contract
def test_ensure_trace_id_reuses_and_generates() -> None:
    first = trace_mod.ensure_trace_id(None)
    assert len(first) > 8
    assert trace_mod.ensure_trace_id(None) == first
    incoming = trace_mod.ensure_trace_id("fixed-trace")
    assert incoming == "fixed-trace"
    assert trace_mod.get_trace_id() == "fixed-trace"


@pytest.mark.contract
def test_reset_trace_id_restores_prior() -> None:
    tok_a = trace_mod.set_trace_id("a")
    tok_b = trace_mod.set_trace_id("b")
    trace_mod.reset_trace_id(tok_b)
    assert trace_mod.get_trace_id() == "a"
    trace_mod.reset_trace_id(tok_a)
    assert trace_mod.get_trace_id() is None


@pytest.mark.contract
def test_ensure_langfuse_trace_id_hex_and_seed_paths() -> None:
    lf = "a" * 32
    assert trace_mod.ensure_langfuse_trace_id(lf) == lf
    trace_mod.LANGFUSE_TRACE_ID.set(None)
    seeded = trace_mod.ensure_langfuse_trace_id(None, seed="unit-seed")
    assert len(seeded) == 32
    trace_mod.LANGFUSE_TRACE_ID.set(None)
    random_id = trace_mod.ensure_langfuse_trace_id(None)
    assert len(random_id) == 32
