"""HTTP middleware: accept/propagate X-WoS-Trace-Id across World Engine requests."""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from app.observability.trace import TRACE_ID, ensure_trace_id, get_trace_id


def install_trace_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def wos_trace_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
        token = TRACE_ID.set(None)
        try:
            raw = request.headers.get("X-WoS-Trace-Id")
            incoming = raw.strip() if isinstance(raw, str) and raw.strip() else None
            trace_id = ensure_trace_id(incoming)
            request.state.trace_id = trace_id
            response = await call_next(request)
            response.headers["X-WoS-Trace-Id"] = get_trace_id() or trace_id
            return response
        finally:
            TRACE_ID.reset(token)
