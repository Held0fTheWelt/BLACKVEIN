"""Pure policy decisions for admin security checks (no Flask responses)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.auth.admin_security_helpers import _check_rate_limit, _is_ip_whitelisted, _verify_2fa
from app.auth.permissions import current_user_is_super_admin
from app.models.backend.user import SUPERADMIN_THRESHOLD


@dataclass
class AdminSecurityConfig:
    """Configuration for admin security checks."""

    require_2fa: bool = False
    require_super_admin: bool = False
    rate_limit: Optional[str] = None
    audit_log: bool = True
    check_ip_whitelist: bool = True

    def __post_init__(self) -> None:
        if self.rate_limit is None:
            object.__setattr__(self, "rate_limit", "10/minute")


@dataclass(frozen=True)
class AdminSecurityDenial:
    """Structured denial when a gate fails (mapped to HTTP in the decorator)."""

    http_status: int
    json_body: dict
    violation_type: Optional[str]
    violation_reason: str
    violation_details: Optional[dict] = None


def evaluate_admin_security_gate(
    user: Any,
    config: AdminSecurityConfig,
    *,
    client_ip: str,
) -> AdminSecurityDenial | None:
    """Return a denial if any gate fails; otherwise None (caller proceeds)."""
    if user is None or user.is_banned:
        return AdminSecurityDenial(
            http_status=401,
            json_body={"error": "Unauthorized"},
            violation_type=None,
            violation_reason="",
        )

    if not user.is_admin:
        return AdminSecurityDenial(
            http_status=403,
            json_body={"error": "Forbidden"},
            violation_type="non_admin_access_attempt",
            violation_reason="Non-admin user attempted admin operation",
        )

    if config.require_super_admin:
        if not current_user_is_super_admin():
            user_level = getattr(user, "role_level", 0) or 0
            return AdminSecurityDenial(
                http_status=403,
                json_body={"error": "Forbidden", "code": "INSUFFICIENT_PRIVILEGE"},
                violation_type="insufficient_role_level",
                violation_reason=f"Insufficient role level: {user_level} < {SUPERADMIN_THRESHOLD}",
                violation_details={"required_level": SUPERADMIN_THRESHOLD, "user_level": user_level},
            )

    if config.check_ip_whitelist:
        if not _is_ip_whitelisted(client_ip):
            return AdminSecurityDenial(
                http_status=403,
                json_body={"error": "Forbidden", "code": "IP_NOT_WHITELISTED"},
                violation_type="ip_whitelist_violation",
                violation_reason=f"IP not whitelisted: {client_ip}",
                violation_details={"client_ip": client_ip},
            )

    if config.rate_limit:
        rate_limit_key = f"admin_action:{user.id}"
        if not _check_rate_limit(rate_limit_key, config.rate_limit):
            return AdminSecurityDenial(
                http_status=429,
                json_body={"error": "Too many admin requests", "code": "RATE_LIMIT_EXCEEDED"},
                violation_type="rate_limit_exceeded",
                violation_reason=f"Admin rate limit exceeded for user {user.id}",
            )

    if config.require_2fa:
        if not _verify_2fa(user):
            return AdminSecurityDenial(
                http_status=403,
                json_body={"error": "Two-factor authentication required", "code": "2FA_REQUIRED"},
                violation_type="2fa_verification_failed",
                violation_reason="2FA verification required but not verified",
            )

    return None
