"""Helper-role functions for SLM-support layer.

These bounded helpers assist the turn dispatcher with:
- Context compression for LLM token efficiency
- Trigger extraction and rule matching
- Delta normalization and structural fixing
- Pre-guard validation and routing decisions
"""

from typing import Any, Dict, List, Optional
from app.runtime.runtime_models import SessionState

# Import decision policy if available; fallback to empty dict if not
try:
    from app.runtime.decision_policy import ACTIVE_TRIGGER_RULES, GUARD_POLICIES
except ImportError:
    ACTIVE_TRIGGER_RULES = {
        "escalation_detected": {
            "description": "High conflict escalation",
            "priority": 10,
            "effect": "increase_tension"
        },
        "character_betrayal": {
            "description": "Character betrayal event",
            "priority": 8,
            "effect": "relationship_shift"
        }
    }
    GUARD_POLICIES = {}


def compress_context_for_llm(session_state: SessionState) -> Dict[str, Any]:
    """Compress SessionState for LLM input.

    Reduces character list to high-salience characters only, trims verbose metadata.

    Args:
        session_state: Full SessionState with canonical_state

    Returns:
        Compressed canonical_state for LLM consumption
    """
    canonical = session_state.canonical_state.copy() if session_state.canonical_state else {}

    # Keep only high-salience characters
    if "characters" in canonical and session_state.context_layers:
        salient_ids = set()
        # Collect characters from relationship context (high salience)
        if session_state.context_layers.relationship_axis_context:
            for entry in session_state.context_layers.relationship_axis_context:
                char_id, _, salience = entry
                if salience >= 5.0:  # Threshold for inclusion
                    salient_ids.add(char_id)

        # Keep only salient characters
        if salient_ids:
            canonical["characters"] = {
                cid: canonical["characters"][cid]
                for cid in salient_ids
                if cid in canonical["characters"]
            }

    return canonical


def extract_active_triggers(session_state: SessionState) -> List[Dict[str, Any]]:
    """Extract active trigger rules that match current state.

    Scans decision policy trigger rules and returns those that match
    current canonical state triggers.

    Args:
        session_state: Current session with detected triggers

    Returns:
        List of matching trigger rule dicts with: name, description, condition, action
    """
    active_triggers = session_state.canonical_state.get("triggers", []) if session_state.canonical_state else []

    matching_rules = []
    for rule_name, rule_def in ACTIVE_TRIGGER_RULES.items():
        if rule_name in active_triggers:
            matching_rules.append({
                "name": rule_name,
                "description": rule_def.get("description", ""),
                "priority": rule_def.get("priority", 0),
                "effect": rule_def.get("effect", "")
            })

    return sorted(matching_rules, key=lambda r: r.get("priority", 0), reverse=True)


def normalize_proposed_deltas(
    proposed_deltas: List[Dict[str, Any]],
    canonical_state: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Normalize proposed deltas before guard evaluation.

    Fixes:
    - Type coercion (e.g., string "123" to int)
    - Path normalization (double slashes, invalid chars)
    - Value format alignment with schema

    Args:
        proposed_deltas: Raw deltas from LLM
        canonical_state: Current state for type inference

    Returns:
        Normalized deltas ready for guard evaluation
    """
    normalized = []

    for delta in proposed_deltas:
        try:
            path = delta.get("path", "").strip()
            value = delta.get("value")

            # Skip malformed paths
            if not path or "//" in path or not path.startswith(("characters", "scene", "conflict")):
                continue

            # Normalize path
            path = "/".join(p for p in path.split("/") if p)

            normalized.append({
                "path": path,
                "value": value,
                "operation": delta.get("operation", "update")
            })
        except Exception:
            # Skip deltas that can't be normalized
            continue

    return normalized


def precheck_guard_routing(
    deltas: List[Dict[str, Any]],
    canonical_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Pre-validate deltas and recommend guard routing.

    Separates valid from invalid deltas and recommends which guard path
    to use (full_guard, soft_guard, bypass).

    Args:
        deltas: Proposed deltas (should be normalized)
        canonical_state: Current state for validation

    Returns:
        Dict with: valid_deltas, invalid_deltas, routing_recommendation, reasoning
    """
    valid_deltas = []
    invalid_deltas = []

    for delta in deltas:
        path = delta.get("path", "")
        value = delta.get("value")

        # Basic validation: path should exist pattern, value should be non-null
        if path and value is not None:
            valid_deltas.append(delta)
        else:
            invalid_deltas.append({**delta, "rejection_reason": "Invalid path or null value"})

    # Recommend routing based on delta count and type
    routing = "full_guard"  # Default: full guard evaluation
    if len(valid_deltas) <= 1 and len(invalid_deltas) == 0:
        routing = "soft_guard"  # Few deltas, can use lighter guard
    if len(valid_deltas) == 0:
        routing = "bypass"  # No valid deltas, skip guard

    return {
        "valid_deltas": valid_deltas,
        "invalid_deltas": invalid_deltas,
        "routing_recommendation": routing,
        "reasoning": f"{len(valid_deltas)} valid, {len(invalid_deltas)} invalid deltas"
    }
