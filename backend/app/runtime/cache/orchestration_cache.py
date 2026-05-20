"""Bounded per-turn cache primitives for orchestration-safe read reuse."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any


class OrchestrationTurnCache:
    """Small deterministic LRU cache scoped to one orchestrated turn."""

    def __init__(self, *, max_entries: int = 16) -> None:
        self.max_entries = max(1, int(max_entries))
        self._data: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.bypasses = 0

    @staticmethod
    def make_tool_key(tool_name: str, arguments: dict[str, Any]) -> str:
        encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        return f"{tool_name}:{encoded}"

    def get(self, key: str) -> dict[str, Any] | None:
        value = self._data.get(key)
        if value is None:
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)
            self.evictions += 1

    def mark_bypass(self) -> None:
        self.bypasses += 1

    def summary(self) -> dict[str, Any]:
        return {
            "scope": "turn",
            "max_entries": self.max_entries,
            "size": len(self._data),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "bypasses": self.bypasses,
        }
