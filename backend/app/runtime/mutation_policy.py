"""Field-level mutation permission policy for AI proposals.

Enforces deny-by-default whitelist of mutable story-state fields.
Protects engine-owned, runtime-owned, and internal technical state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MutationPolicyDecision:
    """Result of evaluating a path against the mutation policy.

    Attributes:
        allowed: Whether the path is allowed to be mutated by AI
        reason_code: Machine-readable reason code if blocked (e.g., "blocked_root_domain")
        reason_message: Human-readable reason message if blocked
    """

    allowed: bool
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None


class MutationPolicy:
    """Canonical mutation permission policy for AI proposals.

    Deny-by-default: only explicitly whitelisted paths are allowed.
    Protected domains cannot be mutated under any circumstances.
    Blocked patterns are checked first and always win.
    """

    # ===== Semantic Domains =====

    ALLOWED_DOMAINS = {
        "characters",      # Character emotional state, stance, tension
        "relationships",   # Relationship axis values
        "scene_state",     # Scene-level conflict/pressure markers
        "conflict_state",  # Escalation/intensity trackers (global, not per-scene)
    }

    PROTECTED_DOMAINS = {
        "metadata",        # Internal metadata
        "runtime",         # Execution state, mode, adapter config
        "system",          # Engine bookkeeping
        "logs",            # Event/decision logs
        "decision",        # AI decision artifacts
        "session",         # Session identity (session_id, created_at, module_id)
        "turn",            # Turn metadata (turn_number, session_id)
        "cache",           # Derived/computed fields
    }

    # ===== Whitelist Patterns =====
    # Patterns allowed within allowed domains.
    # Component-by-component matching: split by ".", "*" matches one component.

    WHITELIST_PATTERNS = [
        # Characters: emotional state, stance, tension
        "characters.*.emotional_state",
        "characters.*.stance",
        "characters.*.tension",
        # Relationships: axis values
        "relationships.*.value",
        # Scene state: pressure and conflict markers
        "scene_state.*.pressure",
        "scene_state.*.conflict",
        # Conflict state: escalation and intensity (global, not per-scene)
        "conflict_state.escalation",
        "conflict_state.intensity",
    ]

    # ===== Blocked Patterns =====
    # Patterns that always block mutations (checked first).
    # Component-by-component matching.

    BLOCKED_PATTERNS = [
        # Protected root domains
        "metadata.*",
        "runtime.*",
        "system.*",
        "logs.*",
        "decision.*",
        "session.*",
        "turn.*",
        "cache.*",
        # Internal/technical fields (any nesting level)
        "*._*",            # Fields starting with underscore
        "*.__*",           # Fields starting with double underscore
        "*_internal",      # Fields ending with _internal
        "*_derived",       # Fields ending with _derived
        "*.cache",         # Any .cache field
        "*.cached_*",      # Any .cached_* field
    ]
