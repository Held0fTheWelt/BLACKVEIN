"""Named defaults for AI turn / adapter policy (no behavior change vs prior literals)."""

from __future__ import annotations

# Session metadata key and fallback (ms) — was inline in execute_turn_with_ai
METADATA_ADAPTER_GENERATE_TIMEOUT_MS = "adapter_generate_timeout_ms"
DEFAULT_ADAPTER_GENERATE_TIMEOUT_MS = 30_000
