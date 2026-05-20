"""Shared typing protocol for handler bundles (avoid circular imports with ToolRegistry)."""

from __future__ import annotations

from typing import Protocol


class RegistryListToolNames(Protocol):
    def list_tool_names(self) -> list[str]: ...
