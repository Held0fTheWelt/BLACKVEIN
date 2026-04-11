"""JSON audit lines for story runtime paths (no raw secrets or full player text)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            return json.dumps(record.msg)
        return json.dumps({"message": str(record.msg)})


def _logger() -> logging.Logger:
    log = logging.getLogger("wos.world_engine.audit")
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(_JSONFormatter())
        log.addHandler(h)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def log_story_turn_event(
    *,
    trace_id: str | None,
    story_session_id: str,
    module_id: str,
    turn_number: int,
    player_input: str,
    outcome: str,
    error_code: str | None = None,
    graph_error_count: int = 0,
) -> None:
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event": "story.turn.execute",
        "actor": "world_engine_story_runtime",
        "story_session_id": story_session_id,
        "module_id": module_id,
        "turn_number": turn_number,
        "player_input_hash": _hash_text(player_input),
        "player_input_length": len(player_input),
        "outcome": outcome,
        "graph_error_count": graph_error_count,
    }
    if error_code:
        entry["error_code"] = error_code
    _logger().info(entry)


def log_story_runtime_failure(
    *,
    trace_id: str | None,
    story_session_id: str | None,
    operation: str,
    message: str,
    failure_class: str,
) -> None:
    _logger().info(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "event": "story.runtime.failure",
            "actor": "world_engine_story_runtime",
            "story_session_id": story_session_id,
            "operation": operation,
            "failure_class": failure_class,
            "message": message[:500],
        }
    )
