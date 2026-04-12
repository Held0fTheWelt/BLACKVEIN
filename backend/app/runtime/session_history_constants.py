"""Named bounds for session history shaping (DS-003 / C5 clarity)."""

from __future__ import annotations

from typing import Final

# Per-entry cap when copying canonical_consequences from short-term context.
MAX_HISTORY_CONSEQUENCES_PER_ENTRY: Final[int] = 16

# Authoritative reason string cap (JSON-safe row size); truncation keeps room for ellipsis.
MAX_HISTORY_REASON_CHAR_LIMIT: Final[int] = 200

# Default FIFO cap for SessionHistory.entries before oldest trims.
SESSION_HISTORY_DEFAULT_MAX_ENTRIES: Final[int] = 100
