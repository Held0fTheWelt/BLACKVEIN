"""
Central feature access resolution (Phase 1.5).

Single decision path for: backend ``@require_feature``, ``/auth/me`` allowed_features,
and administration-tool ``data-feature`` alignment (same checks via API).

Decision order (strict; first match wins):
1. **Explicit override** — ``get_feature_access_override`` returns ``True``/``False`` (reserved; default no override).
2. **Minimum privilege tier** — user's tier must be >= the feature's configured minimum tier.
3. **Area scope** — if the feature has FeatureArea rows, the user must satisfy the same overlap rules as before.

Tiers are ordered integers (higher = more privilege for comparison only):
- ``ACCESS_TIER_NONE`` (0): banned or anonymous
- ``ACCESS_TIER_AUTHENTICATED`` (1): logged-in, non-banned (any primary role)
- ``ACCESS_TIER_MODERATOR`` (2): moderator (not admin)
- ``ACCESS_TIER_ADMIN`` (3): admin

This replaces ad-hoc per-feature role *tuple* checks with one declarative minimum tier per feature while
preserving today's effective access (moderator+admin features → tier 2; admin-only → tier 3;
any authenticated → tier 1).

Future: add per-user/per-feature allow-deny in ``get_feature_access_override`` without changing callers.
"""

from __future__ import annotations

from typing import Any

from app.auth.feature_registry import (
    FEATURE_DASHBOARD_LOGS,
    FEATURE_DASHBOARD_METRICS,
    FEATURE_DASHBOARD_SETTINGS,
    FEATURE_DASHBOARD_USER_SETTINGS,
    FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE,
    FEATURE_MANAGE_AREAS,
    FEATURE_MANAGE_DATA_EXPORT,
    FEATURE_MANAGE_DATA_IMPORT,
    FEATURE_MANAGE_FEATURE_AREAS,
    FEATURE_MANAGE_FORUM,
    FEATURE_MANAGE_GAME_CONTENT,
    FEATURE_MANAGE_GAME_OPERATIONS,
    FEATURE_MANAGE_MCP_OPERATIONS,
    FEATURE_MANAGE_RESEARCH_GOVERNANCE,
    FEATURE_MANAGE_NEWS,
    FEATURE_MANAGE_PLAY_SERVICE_CONTROL,
    FEATURE_MANAGE_ROLES,
    FEATURE_MANAGE_SYSTEM_DIAGNOSIS,
    FEATURE_MANAGE_SLOGANS,
    FEATURE_MANAGE_USERS,
    FEATURE_MANAGE_WIKI,
    FEATURE_MANAGE_WORLD_ENGINE_AUTHOR,
    FEATURE_MANAGE_WORLD_ENGINE_OBSERVE,
    FEATURE_MANAGE_WORLD_ENGINE_OPERATE,
    _user_area_ids,
    _user_has_area_all,
    get_feature_area_ids,
    is_valid_feature_id,
)
from app.models import User

# Ordered privilege tiers (numeric for >= comparisons only).
ACCESS_TIER_NONE = 0
ACCESS_TIER_AUTHENTICATED = 1
ACCESS_TIER_MODERATOR = 2
ACCESS_TIER_ADMIN = 3

# Reasons returned by ``resolve_feature_access`` (machine-readable, stable for tests).
REASON_OVERRIDE_ALLOW = "override_allow"
REASON_OVERRIDE_DENY = "override_deny"
REASON_TIER_MET = "tier_met"
REASON_TIER_DENIED = "tier_denied"
REASON_AREA_DENIED = "area_denied"
REASON_INVALID_FEATURE = "invalid_feature"
REASON_BANNED = "banned"
REASON_NO_USER = "no_user"


def user_privilege_tier(user: User | None) -> int:
    """
    Map primary role to a privilege tier for feature gating.

    Admin always maps to ``ACCESS_TIER_ADMIN``. Moderator maps to ``ACCESS_TIER_MODERATOR``.
    All other roles (user, qa, …) map to ``ACCESS_TIER_AUTHENTICATED`` when the account is usable.
    """
    if user is None or getattr(user, "is_banned", False):
        return ACCESS_TIER_NONE
    if user.has_role(User.ROLE_ADMIN):
        return ACCESS_TIER_ADMIN
    if user.has_role(User.ROLE_MODERATOR):
        return ACCESS_TIER_MODERATOR
    return ACCESS_TIER_AUTHENTICATED


def get_feature_access_override(user: User | None, feature_id: str) -> bool | None:
    """
    Optional explicit allow/deny. Return ``None`` to fall through to tier + area rules.

    Reserved for future per-user or per-tenant overrides; do not weaken defaults here.
    """
    return None


def _feature_minimum_tier(feature_id: str) -> int:
    row = FEATURE_ACCESS_RULES.get(feature_id)
    if not row:
        return ACCESS_TIER_ADMIN
    return int(row["min_tier"])


def _area_allows(user: User | None, feature_id: str) -> bool:
    """Same semantics as legacy ``user_can_access_feature`` area tail."""
    if not user:
        return False
    feature_areas = get_feature_area_ids(feature_id)
    if not feature_areas:
        return True
    if not list(user.areas or []):
        return True
    if _user_has_area_all(user):
        return True
    user_aids = _user_area_ids(user)
    return bool(user_aids & set(feature_areas))


_m = ACCESS_TIER_MODERATOR
_a = ACCESS_TIER_ADMIN
_u = ACCESS_TIER_AUTHENTICATED

FEATURE_ACCESS_RULES: dict[str, dict[str, Any]] = {
    FEATURE_MANAGE_NEWS: {"min_tier": _m, "description": "News management"},
    FEATURE_MANAGE_USERS: {"min_tier": _a, "description": "User accounts"},
    FEATURE_MANAGE_ROLES: {"min_tier": _a, "description": "Role assignments"},
    FEATURE_MANAGE_WIKI: {"min_tier": _m, "description": "Wiki"},
    FEATURE_MANAGE_SLOGANS: {"min_tier": _m, "description": "Slogans"},
    FEATURE_MANAGE_AREAS: {"min_tier": _a, "description": "Areas"},
    FEATURE_MANAGE_FEATURE_AREAS: {"min_tier": _a, "description": "Feature ↔ area mapping"},
    FEATURE_MANAGE_DATA_EXPORT: {"min_tier": _a, "description": "Data export"},
    FEATURE_MANAGE_DATA_IMPORT: {"min_tier": _a, "description": "Data import"},
    FEATURE_MANAGE_FORUM: {"min_tier": _m, "description": "Forum"},
    FEATURE_MANAGE_GAME_CONTENT: {"min_tier": _m, "description": "Game content"},
    FEATURE_MANAGE_GAME_OPERATIONS: {"min_tier": _m, "description": "Game operations"},
    FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE: {"min_tier": _a, "description": "AI runtime governance"},
    FEATURE_MANAGE_SYSTEM_DIAGNOSIS: {"min_tier": _m, "description": "System diagnosis"},
    FEATURE_MANAGE_PLAY_SERVICE_CONTROL: {"min_tier": _a, "description": "Play-service control"},
    FEATURE_MANAGE_WORLD_ENGINE_OBSERVE: {"min_tier": _m, "description": "World engine observe"},
    FEATURE_MANAGE_WORLD_ENGINE_OPERATE: {"min_tier": _m, "description": "World engine operate"},
    FEATURE_MANAGE_WORLD_ENGINE_AUTHOR: {"min_tier": _m, "description": "World engine author"},
    FEATURE_MANAGE_MCP_OPERATIONS: {"min_tier": _m, "description": "MCP operations"},
    FEATURE_MANAGE_RESEARCH_GOVERNANCE: {"min_tier": _a, "description": "Research domain strategic governance"},
    FEATURE_DASHBOARD_METRICS: {"min_tier": _a, "description": "Dashboard metrics"},
    FEATURE_DASHBOARD_LOGS: {"min_tier": _a, "description": "Dashboard logs"},
    FEATURE_DASHBOARD_SETTINGS: {"min_tier": _a, "description": "Dashboard settings"},
    FEATURE_DASHBOARD_USER_SETTINGS: {"min_tier": _u, "description": "Per-user dashboard settings"},
}


def _ensure_rule_coverage() -> None:
    """Fail fast in development/tests if a feature id is missing from the access rule table."""
    from app.auth.feature_registry import FEATURE_IDS

    missing = set(FEATURE_IDS) - set(FEATURE_ACCESS_RULES)
    extra = set(FEATURE_ACCESS_RULES) - set(FEATURE_IDS)
    if missing or extra:
        raise RuntimeError(f"FEATURE_ACCESS_RULES out of sync with FEATURE_IDS: missing={missing!r} extra={extra!r}")


_ensure_rule_coverage()


def resolve_feature_access(user: User | None, feature_id: str) -> tuple[bool, dict[str, Any]]:
    """
    Return (allowed, detail) with stable diagnostic keys for tests and future auditing.

    detail keys: allowed (bool), reason (str), feature_id, min_tier, user_tier, override (str|null).
    """
    detail: dict[str, Any] = {
        "allowed": False,
        "reason": REASON_INVALID_FEATURE,
        "feature_id": feature_id,
        "min_tier": None,
        "user_tier": None,
        "override": None,
    }

    if not is_valid_feature_id(feature_id):
        detail["reason"] = REASON_INVALID_FEATURE
        return False, detail

    if user is None:
        detail["reason"] = REASON_NO_USER
        return False, detail

    if getattr(user, "is_banned", False):
        detail["reason"] = REASON_BANNED
        detail["user_tier"] = ACCESS_TIER_NONE
        return False, detail

    ut = user_privilege_tier(user)
    detail["user_tier"] = ut

    override = get_feature_access_override(user, feature_id)
    if override is True:
        detail["override"] = "allow"
        ok = _area_allows(user, feature_id)
        detail["allowed"] = ok
        detail["reason"] = REASON_OVERRIDE_ALLOW if ok else REASON_AREA_DENIED
        return ok, detail

    if override is False:
        detail["override"] = "deny"
        detail["reason"] = REASON_OVERRIDE_DENY
        return False, detail

    min_tier = _feature_minimum_tier(feature_id)
    detail["min_tier"] = min_tier

    if ut < min_tier:
        detail["reason"] = REASON_TIER_DENIED
        return False, detail

    if not _area_allows(user, feature_id):
        detail["reason"] = REASON_AREA_DENIED
        return False, detail

    detail["allowed"] = True
    detail["reason"] = REASON_TIER_MET
    return True, detail


def user_can_access_feature_resolved(user: User | None, feature_id: str) -> bool:
    """Boolean convenience matching legacy ``user_can_access_feature`` call shape."""
    allowed, _ = resolve_feature_access(user, feature_id)
    return allowed
