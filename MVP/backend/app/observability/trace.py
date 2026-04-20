"""Trace ID system using contextvars for request and non-request contexts."""

import contextvars
import uuid

# Context variable stores trace_id across request and non-request code paths
TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)


def set_trace_id(trace_id: str) -> contextvars.Token:
    """Set trace_id in the current context and return the token for reset."""
    return TRACE_ID.set(trace_id)


def get_trace_id() -> str | None:
    """Get trace_id from the current context, or None if not set."""
    return TRACE_ID.get()


def reset_trace_id(token: contextvars.Token) -> None:
    """Reset trace_id using the token returned by set_trace_id."""
    TRACE_ID.reset(token)


def ensure_trace_id(incoming: str | None) -> str:
    """Idempotent trace_id getter/setter.

    If incoming is provided, set it and return it.
    If incoming is None and contextvar is already set, return existing value.
    If incoming is None and contextvar not set, generate UUIDv4, set it, return it.

    Args:
        incoming: Incoming trace_id from request header (or None)

    Returns:
        trace_id: The trace_id to use for this request/execution
    """
    if incoming:
        # Incoming value takes precedence
        set_trace_id(incoming)
        return incoming

    # Check if already set in contextvar
    existing = get_trace_id()
    if existing:
        return existing

    # Generate new UUID
    new_trace_id = str(uuid.uuid4())
    set_trace_id(new_trace_id)
    return new_trace_id
