"""Route-level configuration constants: rate limits, timeouts, pagination, role bounds.

All constants are frozen dataclasses (immutable after creation) to prevent runtime drift.
Importing code uses these as read-only: `from app.config.route_constants import route_auth_config`.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RouteAuthConfig:
    """Authentication endpoint constants."""
    constant_time_delay_seconds: float = 0.5
    """Delay for failed auth attempts to mitigate timing attacks."""
    resend_verification_nonexistent_extra_delay_seconds: float = 0.3
    """Compensating delay for non-existing/invalid email paths to match real resend work."""


@dataclass(frozen=True)
class RouteSessionConfig:
    """Session management endpoint constants."""
    play_operator_diag_max: int = 40
    """Maximum number of diagnostic items per session query."""


@dataclass(frozen=True)
class RouteSiteConfig:
    """Site management endpoint constants."""
    min_rotation_interval: int = 5
    """Minimum rotation interval in seconds."""
    max_rotation_interval: int = 86400
    """Maximum rotation interval in seconds (1 day)."""
    default_rotation_interval: int = 60
    """Default rotation interval in seconds (1 minute)."""


@dataclass(frozen=True)
class RouteUserConfig:
    """User and role management endpoint constants."""
    role_level_min: int = 0
    """Minimum role level (no privilege)."""
    role_level_max: int = 9999
    """Maximum role level (super admin)."""


@dataclass(frozen=True)
class RoutePaginationConfig:
    """Pagination and pagination defaults across all routes."""
    page_size_small: int = 10
    """Small page size (quick lists)."""
    page_size_medium: int = 50
    """Medium page size (default)."""
    page_size_large: int = 100
    """Large page size (bulk operations)."""
    page_size_max: int = 5000
    """Absolute maximum page size."""


@dataclass(frozen=True)
class RouteStatusCodes:
    """HTTP status codes used consistently across routes."""
    ok: int = 200
    created: int = 201
    bad_request: int = 400
    unauthorized: int = 401
    forbidden: int = 403
    not_found: int = 404
    unprocessable_entity: int = 422
    conflict: int = 409
    internal_error: int = 500
    too_many_requests: int = 429


# Singleton instances: frozen and module-level, safe to import everywhere
route_auth_config = RouteAuthConfig()
route_session_config = RouteSessionConfig()
route_site_config = RouteSiteConfig()
route_user_config = RouteUserConfig()
route_pagination_config = RoutePaginationConfig()
route_status_codes = RouteStatusCodes()
