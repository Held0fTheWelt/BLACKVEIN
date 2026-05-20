"""
Single canonical envelope for uninitialized G3-projected fields
(CANONICAL_TURN_CONTRACT_GOC.md).
"""

from __future__ import annotations

from typing import Any, Final

GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID: Final[str] = "goc_uninitialized_field_envelope_v1"

SETTER_SURFACE_ADMIN_CONTROL_PLANE: Final[str] = "admin_control_plane"
SETTER_SURFACE_WRITERS_ROOM_AUTHORED: Final[str] = "writers_room_authored"
SETTER_SURFACE_RUNTIME_HOST_SESSION: Final[str] = "runtime_host_session"

ALLOWED_SETTER_SURFACES: Final[frozenset[str]] = frozenset(
    {
        SETTER_SURFACE_ADMIN_CONTROL_PLANE,
        SETTER_SURFACE_WRITERS_ROOM_AUTHORED,
        SETTER_SURFACE_RUNTIME_HOST_SESSION,
    }
)

_ENVELOPE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "envelope_schema_id",
        "initialization_state",
        "initialization_issue_kind",
        "setter_surface",
        "expected_source",
    }
)


def goc_uninitialized_field_envelope(*, setter_surface: str, expected_source: str) -> dict[str, Any]:
    """Build the only valid JSON object for a G3 field that is not
    initialized yet.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        setter_surface: ``setter_surface`` (str); meaning follows the type and call sites.
        expected_source: ``expected_source`` (str); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if setter_surface not in ALLOWED_SETTER_SURFACES:
        raise ValueError(f"setter_surface must be one of {sorted(ALLOWED_SETTER_SURFACES)}, got {setter_surface!r}")
    src = (expected_source or "").strip()
    if not src:
        raise ValueError("expected_source must be a non-empty string")
    return {
        "envelope_schema_id": GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID,
        "initialization_state": "uninitialized",
        "initialization_issue_kind": "pending_initialization",
        "setter_surface": setter_surface,
        "expected_source": src,
    }


def is_goc_uninitialized_field_envelope(obj: Any) -> bool:
    """Return True only if obj matches goc_uninitialized_field_envelope_v1
    exactly (no extra keys).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        obj: ``obj`` (Any); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != _ENVELOPE_KEYS:
        return False
    if obj.get("envelope_schema_id") != GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID:
        return False
    if obj.get("initialization_state") != "uninitialized":
        return False
    if obj.get("initialization_issue_kind") != "pending_initialization":
        return False
    if obj.get("setter_surface") not in ALLOWED_SETTER_SURFACES:
        return False
    exp = obj.get("expected_source")
    if not isinstance(exp, str) or not exp.strip():
        return False
    return True


def assert_goc_uninitialized_field_envelope(obj: Any) -> None:
    """Raise AssertionError if obj is not a valid
    goc_uninitialized_field_envelope_v1.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        obj: ``obj`` (Any); meaning follows the type and call sites.
    """
    if not is_goc_uninitialized_field_envelope(obj):
        raise AssertionError(f"invalid goc_uninitialized_field_envelope_v1: {obj!r}")
