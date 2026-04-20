"""Trace ID propagation for World Engine HTTP requests (aligned with backend X-WoS-Trace-Id)."""

from __future__ import annotations

import contextvars
import uuid
from contextvars import Token

TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("wos_we_trace_id", default=None)


def set_trace_id(trace_id: str) -> Token:
    return TRACE_ID.set(trace_id)


def get_trace_id() -> str | None:
    return TRACE_ID.get()


def reset_trace_id(token: Token) -> None:
    TRACE_ID.reset(token)


def ensure_trace_id(incoming: str | None) -> str:
    if incoming:
        set_trace_id(incoming)
        return incoming
    existing = get_trace_id()
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    set_trace_id(new_id)
    return new_id
