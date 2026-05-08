"""Tests for Langfuse MCP tracing (MCP observability)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.mcp_server.langfuse_tracing import (
    McpLangfuseTracer,
    _extract_parent_trace_id,
    _sanitize_arguments,
    _sanitize_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tracer_with_mock_client(monkeypatch) -> tuple[McpLangfuseTracer, MagicMock]:
    """Return an enabled tracer with a pre-wired mock Langfuse client."""
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    tracer = McpLangfuseTracer()
    mock_span = MagicMock()
    mock_trace = MagicMock()
    mock_trace.span.return_value = mock_span
    mock_lf = MagicMock()
    mock_lf.trace.return_value = mock_trace
    tracer._lf = mock_lf
    tracer._credentials_fetched = True
    return tracer, mock_lf


# ---------------------------------------------------------------------------
# is_enabled — flag only
# ---------------------------------------------------------------------------


def test_tracer_disabled_by_default():
    tracer = McpLangfuseTracer()
    assert not tracer.is_enabled()


def test_tracer_enabled_when_flag_set(monkeypatch):
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    tracer = McpLangfuseTracer()
    assert tracer.is_enabled()


# ---------------------------------------------------------------------------
# _get_client — credential resolution order
# ---------------------------------------------------------------------------


def test_get_client_returns_none_when_disabled():
    tracer = McpLangfuseTracer()
    assert tracer._get_client() is None


def test_get_client_uses_direct_env_keys(monkeypatch):
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-direct")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-direct")
    tracer = McpLangfuseTracer()
    mock_lf = MagicMock()
    with patch("tools.mcp_server.langfuse_tracing.Langfuse", mock_lf, create=True):
        # patch the import inside _get_client
        import tools.mcp_server.langfuse_tracing as mod
        orig = getattr(mod, "Langfuse", None)
        try:
            setattr(mod, "_langfuse_class_override", None)
            tracer._lf = mock_lf()
            tracer._credentials_fetched = True
            client = tracer._get_client()
            assert client is not None
        finally:
            pass


def test_get_client_fetches_from_backend_when_no_direct_keys(monkeypatch):
    """When no direct keys, _fetch_credentials_from_backend is called once."""
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    tracer = McpLangfuseTracer()
    tracer._enabled_flag = True
    tracer._public_key = ""
    tracer._secret_key = ""
    calls = []

    def _track_fetch():
        calls.append(1)
        # don't set keys → client init will silently fail, which is fine

    tracer._fetch_credentials_from_backend = _track_fetch
    # _lf is None; _credentials_fetched is False → fetch must be triggered
    tracer._get_client()

    assert calls, "_fetch_credentials_from_backend was not called"


def test_get_client_fetches_from_backend_only_once(monkeypatch):
    """Backend fetch is cached after the first call."""
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    tracer = McpLangfuseTracer()
    tracer._enabled_flag = True
    tracer._public_key = ""
    tracer._secret_key = ""
    calls = []

    def _track_fetch():
        calls.append(1)

    tracer._fetch_credentials_from_backend = _track_fetch
    tracer._get_client()
    tracer._get_client()
    tracer._get_client()

    assert len(calls) == 1, f"Expected 1 fetch call, got {len(calls)}"


# ---------------------------------------------------------------------------
# _fetch_credentials_from_backend (unit)
# ---------------------------------------------------------------------------


def test_fetch_credentials_skipped_without_token(monkeypatch):
    monkeypatch.delenv("INTERNAL_RUNTIME_CONFIG_TOKEN", raising=False)
    tracer = McpLangfuseTracer()
    tracer._fetch_credentials_from_backend()  # must not raise
    assert tracer._public_key == ""


def test_fetch_credentials_populates_keys_on_200(monkeypatch):
    monkeypatch.setenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "tok-abc")
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:8000")
    tracer = McpLangfuseTracer()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "enabled": True,
            "public_key": "pk-backend",
            "secret_key": "sk-backend",
            "base_url": "https://cloud.langfuse.com",
        }
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        tracer._fetch_credentials_from_backend()

    assert tracer._public_key == "pk-backend"
    assert tracer._secret_key == "sk-backend"


def test_fetch_credentials_ignores_disabled_config(monkeypatch):
    monkeypatch.setenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "tok-abc")
    tracer = McpLangfuseTracer()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"enabled": False}}
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        tracer._fetch_credentials_from_backend()

    assert tracer._public_key == ""


def test_fetch_credentials_suppresses_network_error(monkeypatch):
    monkeypatch.setenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "tok-abc")
    tracer = McpLangfuseTracer()
    with patch("httpx.Client", side_effect=Exception("connection refused")):
        tracer._fetch_credentials_from_backend()  # must not raise


def test_fetch_credentials_uses_runtime_backend_url_env(monkeypatch):
    monkeypatch.setenv("INTERNAL_RUNTIME_CONFIG_TOKEN", "tok-abc")
    monkeypatch.setenv("BACKEND_RUNTIME_CONFIG_URL", "http://backend-runtime:8000")
    tracer = McpLangfuseTracer()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "enabled": True,
            "public_key": "pk-runtime",
            "secret_key": "sk-runtime",
            "base_url": "https://cloud.langfuse.com",
        }
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        tracer._fetch_credentials_from_backend()

    endpoint = mock_client.get.call_args.args[0]
    assert endpoint.startswith("http://backend-runtime:8000/")
    assert tracer._public_key == "pk-runtime"
    assert tracer._secret_key == "sk-runtime"


def test_fetch_credentials_uses_token_alias_env(monkeypatch):
    monkeypatch.delenv("INTERNAL_RUNTIME_CONFIG_TOKEN", raising=False)
    monkeypatch.setenv("BACKEND_INTERNAL_RUNTIME_CONFIG_TOKEN", "tok-alias")
    tracer = McpLangfuseTracer()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "enabled": True,
            "public_key": "pk-alias",
            "secret_key": "sk-alias",
            "base_url": "https://cloud.langfuse.com",
        }
    }
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client):
        tracer._fetch_credentials_from_backend()

    assert mock_client.get.call_args.kwargs["headers"]["X-Internal-Config-Token"] == "tok-alias"
    assert tracer._public_key == "pk-alias"
    assert tracer._secret_key == "sk-alias"


# ---------------------------------------------------------------------------
# _sanitize_arguments
# ---------------------------------------------------------------------------


def test_sanitize_arguments_redacts_sensitive_keys():
    args = {"query": "carnage", "api_key": "secret", "token": "abc", "bearer": "xyz"}
    out = _sanitize_arguments(args)
    assert out["query"] == "carnage"
    assert out["api_key"] == "[redacted]"
    assert out["token"] == "[redacted]"
    assert out["bearer"] == "[redacted]"


def test_sanitize_arguments_truncates_long_strings():
    args = {"text": "x" * 1000}
    out = _sanitize_arguments(args)
    assert out["text"].endswith("…")
    assert len(out["text"]) <= 502


def test_sanitize_arguments_passes_normal_values():
    args = {"module_id": "god_of_carnage", "limit": 10}
    assert _sanitize_arguments(args) == args


# ---------------------------------------------------------------------------
# _sanitize_result
# ---------------------------------------------------------------------------


def test_sanitize_result_none():
    assert _sanitize_result(None) is None


def test_sanitize_result_small_dict_unchanged():
    result = {"status": "ok", "hits": 3}
    assert _sanitize_result(result) == result


def test_sanitize_result_truncates_large_payload():
    result = {"text": "y" * 5000}
    out = _sanitize_result(result)
    assert isinstance(out, str)
    assert out.endswith("…")


# ---------------------------------------------------------------------------
# _extract_parent_trace_id
# ---------------------------------------------------------------------------


def test_extract_parent_trace_id_none_input():
    assert _extract_parent_trace_id(None) is None
    assert _extract_parent_trace_id({}) is None


def test_extract_parent_trace_id_langfuse_field():
    assert _extract_parent_trace_id({"langfuse_trace_id": "lf-abc"}) == "lf-abc"


def test_extract_parent_trace_id_w3c_traceparent():
    trace_id = "a" * 32
    span_id = "b" * 16
    assert _extract_parent_trace_id({"traceparent": f"00-{trace_id}-{span_id}-01"}) == trace_id


def test_extract_parent_trace_id_prefers_langfuse_over_traceparent():
    trace_id = "c" * 32
    span_id = "d" * 16
    meta = {"langfuse_trace_id": "explicit", "traceparent": f"00-{trace_id}-{span_id}-01"}
    assert _extract_parent_trace_id(meta) == "explicit"


# ---------------------------------------------------------------------------
# trace_tool_call — disabled path
# ---------------------------------------------------------------------------


def test_trace_tool_call_noop_when_disabled():
    tracer = McpLangfuseTracer()
    tracer.trace_tool_call(
        wos_trace_id="t1", tool_name="wos.system.health",
        arguments={}, result={"status": "ok"}, duration_ms=12.5, status="success",
    )


# ---------------------------------------------------------------------------
# trace_tool_call — standalone mode
# ---------------------------------------------------------------------------


def test_trace_tool_call_standalone_creates_new_trace(monkeypatch):
    tracer, mock_lf = _tracer_with_mock_client(monkeypatch)
    tracer.trace_tool_call(
        wos_trace_id="wos-123", tool_name="wos.content.search",
        arguments={"pattern": "god_of_carnage"}, result={"hits": 3},
        duration_ms=42.0, status="success", suite="wos-ai",
    )
    call_kwargs = mock_lf.trace.call_args.kwargs
    assert call_kwargs.get("name") == "mcp.wos.content.search"
    assert "id" not in call_kwargs
    assert call_kwargs["metadata"]["trace_origin"] == "mcp"
    assert call_kwargs["metadata"]["execution_tier"] == "diagnostic"
    assert call_kwargs["metadata"]["canonical_player_flow"] is False
    assert call_kwargs["metadata"]["tool_name"] == "wos.content.search"
    span_kwargs = mock_lf.trace.return_value.span.call_args.kwargs
    assert span_kwargs["name"] == "mcp.tool.wos.content.search"
    assert span_kwargs["input"] == {"pattern": "god_of_carnage"}
    mock_lf.trace.return_value.span.return_value.end.assert_called_once()
    mock_lf.flush.assert_called_once()


# ---------------------------------------------------------------------------
# trace_tool_call — linked mode
# ---------------------------------------------------------------------------


def test_trace_tool_call_linked_mode(monkeypatch):
    tracer, mock_lf = _tracer_with_mock_client(monkeypatch)
    tracer.trace_tool_call(
        wos_trace_id="wos-999", tool_name="wos.session.create",
        arguments={"module_id": "god_of_carnage"}, result={"session_id": "s1"},
        duration_ms=55.0, status="success",
        meta={"langfuse_trace_id": "upstream-trace-xyz"},
    )
    mock_lf.trace.assert_called_once_with(id="upstream-trace-xyz")


# ---------------------------------------------------------------------------
# trace_tool_call — error path
# ---------------------------------------------------------------------------


def test_trace_tool_call_error_sets_error_level(monkeypatch):
    tracer, mock_lf = _tracer_with_mock_client(monkeypatch)
    tracer.trace_tool_call(
        wos_trace_id="wos-err", tool_name="wos.goc.get_module",
        arguments={"module_id": "missing"}, result=None,
        duration_ms=8.0, status="error", error="Module not found",
    )
    end_kwargs = mock_lf.trace.return_value.span.return_value.end.call_args.kwargs
    assert end_kwargs["level"] == "ERROR"
    assert end_kwargs["output"] is None


def test_trace_tool_call_error_metadata_includes_error_string(monkeypatch):
    tracer, mock_lf = _tracer_with_mock_client(monkeypatch)
    tracer.trace_tool_call(
        wos_trace_id="wos-err2", tool_name="wos.system.health",
        arguments={}, result=None, duration_ms=5.0,
        status="error", error="Connection refused",
    )
    span_kwargs = mock_lf.trace.return_value.span.call_args.kwargs
    assert span_kwargs["metadata"]["error"] == "Connection refused"
    assert span_kwargs["metadata"]["status"] == "error"


# ---------------------------------------------------------------------------
# Span metadata
# ---------------------------------------------------------------------------


def test_trace_tool_call_metadata_includes_wos_trace_id_and_suite(monkeypatch):
    tracer, mock_lf = _tracer_with_mock_client(monkeypatch)
    tracer.trace_tool_call(
        wos_trace_id="wos-meta", tool_name="wos.goc.list_modules",
        arguments={}, result={"modules": ["god_of_carnage"]},
        duration_ms=7.0, status="success", suite="wos-author",
    )
    meta = mock_lf.trace.return_value.span.call_args.kwargs["metadata"]
    assert meta["wos_trace_id"] == "wos-meta"
    assert meta["suite"] == "wos-author"
    assert meta["duration_ms"] == 7.0
    assert meta["span_origin"] == "mcp_tool"
    assert meta["trace_origin"] == "mcp"
    assert meta["execution_tier"] == "diagnostic"
    assert meta["canonical_player_flow"] is False
    assert meta["tool_name"] == "wos.goc.list_modules"


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_trace_tool_call_suppresses_internal_langfuse_errors(monkeypatch):
    monkeypatch.setenv("LANGFUSE_MCP_ENABLED", "1")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    tracer = McpLangfuseTracer()
    mock_lf = MagicMock()
    mock_lf.trace.side_effect = RuntimeError("Langfuse exploded")
    tracer._lf = mock_lf
    tracer._credentials_fetched = True
    tracer.trace_tool_call(
        wos_trace_id="wos-boom", tool_name="wos.system.health",
        arguments={}, result=None, duration_ms=1.0, status="success",
    )
