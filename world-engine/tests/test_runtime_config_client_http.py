"""Integration-style tests for ``runtime_config_client`` using a real local HTTP server."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from app.runtime.runtime_config_client import fetch_hf_hub_token_from_backend, fetch_resolved_runtime_config


class _RuntimeConfigHandler(BaseHTTPRequestHandler):
    expected_token: str = ""
    runtime_payload: dict[str, Any] = {}
    hf_payload: dict[str, Any] = {}

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or "0")
        return self.rfile.read(length) if length else b""

    def do_GET(self) -> None:  # noqa: N802
        token = self.headers.get("X-Internal-Config-Token") or ""
        if token != self.expected_token:
            self.send_response(401)
            self.end_headers()
            return
        if self.path.rstrip("/").endswith("/api/v1/internal/runtime-config"):
            body = json.dumps(self.runtime_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.rstrip("/").endswith("/api/v1/internal/hf-hub/token"):
            body = json.dumps(self.hf_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


@pytest.fixture
def config_http_server() -> str:
    _RuntimeConfigHandler.expected_token = "cfg-test-token"
    _RuntimeConfigHandler.runtime_payload = {
        "ok": True,
        "data": {"config_version": "v-test", "generation_execution_mode": "mock_only"},
    }
    _RuntimeConfigHandler.hf_payload = {"ok": True, "data": {"token": " hf-secret "}}

    server = HTTPServer(("127.0.0.1", 0), _RuntimeConfigHandler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.contract
def test_fetch_resolved_runtime_config_happy_path(config_http_server: str) -> None:
    data = fetch_resolved_runtime_config(
        base_url=config_http_server,
        token="cfg-test-token",
        timeout_seconds=5.0,
    )
    assert isinstance(data, dict)
    assert data.get("config_version") == "v-test"


@pytest.mark.contract
def test_fetch_resolved_runtime_config_rejects_non_ok_payload(config_http_server: str) -> None:
    _RuntimeConfigHandler.runtime_payload = {"ok": False, "data": {}}
    assert (
        fetch_resolved_runtime_config(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_hf_hub_token_from_backend_trims_value(config_http_server: str) -> None:
    tok = fetch_hf_hub_token_from_backend(
        base_url=config_http_server,
        token="cfg-test-token",
        timeout_seconds=5.0,
    )
    assert tok == "hf-secret"


@pytest.mark.contract
def test_fetch_clients_return_none_when_missing_params() -> None:
    assert fetch_resolved_runtime_config(base_url="  ", token="x", timeout_seconds=1.0) is None
    assert fetch_hf_hub_token_from_backend(base_url="http://127.0.0.1:9", token="  ", timeout_seconds=1.0) is None


@pytest.mark.contract
def test_fetch_resolved_runtime_config_wrong_token(config_http_server: str) -> None:
    assert (
        fetch_resolved_runtime_config(
            base_url=config_http_server,
            token="wrong-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_resolved_runtime_config_non_envelope_payload(config_http_server: str) -> None:
    _RuntimeConfigHandler.runtime_payload = {"status": "ok"}
    assert (
        fetch_resolved_runtime_config(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_hf_hub_token_missing_token_field(config_http_server: str) -> None:
    _RuntimeConfigHandler.hf_payload = {"ok": True, "data": {}}
    assert (
        fetch_hf_hub_token_from_backend(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_resolved_runtime_config_connection_failure() -> None:
    assert (
        fetch_resolved_runtime_config(
            base_url="http://127.0.0.1:1",
            token="cfg-test-token",
            timeout_seconds=0.001,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_hf_hub_token_connection_failure() -> None:
    assert (
        fetch_hf_hub_token_from_backend(
            base_url="http://127.0.0.1:1",
            token="cfg-test-token",
            timeout_seconds=0.001,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_resolved_runtime_config_non_dict_json(config_http_server: str) -> None:
    _RuntimeConfigHandler.runtime_payload = ["not-a-dict"]
    assert (
        fetch_resolved_runtime_config(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_hf_hub_token_non_dict_json(config_http_server: str) -> None:
    _RuntimeConfigHandler.hf_payload = "not-a-dict"
    assert (
        fetch_hf_hub_token_from_backend(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )


@pytest.mark.contract
def test_fetch_hf_hub_token_rejects_non_ok_envelope(config_http_server: str) -> None:
    _RuntimeConfigHandler.hf_payload = {"ok": False, "data": {"token": "x"}}
    assert (
        fetch_hf_hub_token_from_backend(
            base_url=config_http_server,
            token="cfg-test-token",
            timeout_seconds=5.0,
        )
        is None
    )
