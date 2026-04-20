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

    @staticmethod
    def evaluate(target_path: str) -> MutationPolicyDecision:
        """Evaluate whether a target path is allowed to be mutated.

        Algorithm (deny-by-default):
        1. Check if path matches ANY blocked pattern → REJECT immediately
        2. Check if path matches ANY whitelist pattern → ALLOW
        3. Otherwise → REJECT (deny by default)

        Matching: component-by-component (split by ".", "*" = one component).
        Blocked patterns checked first and always win.

        Args:
            target_path: Dot-notation path (e.g., "characters.veronique.emotional_state")

        Returns:
            MutationPolicyDecision with allowed flag and reason codes
        """
        if not target_path or not isinstance(target_path, str):
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_internal_field",
                reason_message="Invalid target_path: must be non-empty string"
            )

        # Split path into components
        path_parts = target_path.split(".")
        if not path_parts:
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_internal_field",
                reason_message="Invalid target_path: empty after split"
            )

        root_domain = path_parts[0]

        # ===== Step 1: Check Blocked Patterns (fail-fast) =====
        for pattern in MutationPolicy.BLOCKED_PATTERNS:
            if MutationPolicy._matches_pattern(target_path, pattern):
                return MutationPolicy._blocked_decision(pattern, target_path)

        # ===== Step 2: Check Whitelist Patterns =====
        for pattern in MutationPolicy.WHITELIST_PATTERNS:
            if MutationPolicy._matches_pattern(target_path, pattern):
                return MutationPolicyDecision(allowed=True)

        # ===== Step 3: Deny by Default =====
        # Check if root domain is in allowed domains (helps with error message)
        if root_domain in MutationPolicy.ALLOWED_DOMAINS:
            # Root is allowed, but leaf is not whitelisted
            return MutationPolicyDecision(
                allowed=False,
                reason_code="not_whitelisted",
                reason_message=(
                    f"Target path '{target_path}' is not in the mutation whitelist. "
                    f"Root domain '{root_domain}' is allowed, but only specific leaves are mutable."
                )
            )
        elif root_domain in MutationPolicy.PROTECTED_DOMAINS:
            # Root is explicitly protected
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_root_domain",
                reason_message=(
                    f"Target path '{target_path}' is in protected domain '{root_domain}'. "
                    f"Protected domains cannot be mutated by AI proposals."
                )
            )
        else:
            # Root is neither allowed nor protected - out of scope
            return MutationPolicyDecision(
                allowed=False,
                reason_code="out_of_scope_root",
                reason_message=(
                    f"Target path '{target_path}' has unknown root domain '{root_domain}'. "
                    f"Allowed domains: {sorted(MutationPolicy.ALLOWED_DOMAINS)}"
                )
            )

    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        """Check if path matches pattern using component-by-component matching.

        Matching rules:
        - Split both path and pattern by "."
        - "*" in pattern matches exactly one path component
        - All other components must match exactly
        - Special: "*._*", "*.__*" match ANY component starting with underscore at any depth
        - If pattern has fewer components than path, no match (except wildcards)

        Args:
            path: Target path (e.g., "characters.veronique.emotional_state")
            pattern: Pattern (e.g., "characters.*.emotional_state")

        Returns:
            True if path matches pattern, False otherwise
        """
        path_parts = path.split(".")
        pattern_parts = pattern.split(".")

        # Special case: *._* matches any component starting with underscore (at any depth)
        if pattern == "*._*":
            return any(comp.startswith("_") and not comp.startswith("__") for comp in path_parts)

        # Special case: *.__* matches any component starting with __
        if pattern == "*.__*":
            return any(comp.startswith("__") for comp in path_parts)

        # Special case: *.cache matches any component exactly "cache"
        if pattern == "*.cache":
            return "cache" in path_parts

        # Special case: *.cached_* matches any component starting with "cached_"
        if pattern == "*.cached_*":
            return any(comp.startswith("cached_") for comp in path_parts)

        # Standard component-by-component matching
        # Pattern must have same number of components as path
        if len(pattern_parts) != len(path_parts):
            return False

        # Match component by component
        for path_comp, pattern_comp in zip(path_parts, pattern_parts):
            if pattern_comp == "*":
                # Wildcard matches any single component
                continue
            elif path_comp == pattern_comp:
                # Exact match
                continue
            else:
                # No match
                return False

        return True

    @staticmethod
    def _blocked_decision(pattern: str, path: str) -> MutationPolicyDecision:
        """Create a decision for a path blocked by a pattern.

        Determines the appropriate reason code based on which pattern blocked it.
        """
        # Categorize the reason based on pattern type
        # Check for cache/cached patterns first (more specific)
        if "cached" in pattern or ".cache" == pattern[-6:]:  # .cache at end
            reason_code = "blocked_technical_field"
        # Check for field-level underscore patterns
        elif pattern in ["*._*", "*.__*"]:
            reason_code = "blocked_internal_field"
        # Check for named underscore patterns
        elif "_internal" in pattern or "_derived" in pattern:
            reason_code = "blocked_technical_field"
        # Check for domain patterns
        elif any(pat in pattern for pat in [".*", "system", "logs", "decision", "session", "turn", "metadata", "runtime"]):
            reason_code = "blocked_root_domain"
        else:
            reason_code = "blocked_technical_field"

        return MutationPolicyDecision(
            allowed=False,
            reason_code=reason_code,
            reason_message=(
                f"Target path '{path}' matches blocked pattern '{pattern}' "
                f"and is protected from mutation by AI proposals."
            )
        )
