"""
Multi-layer security decorator for admin endpoints.

Implements comprehensive security checks:
1. JWT and admin role verification
2. Role level verification (SuperAdmin for sensitive operations)
3. IP whitelist enforcement (if configured)
4. Per-admin rate limiting
5. 2FA verification for sensitive operations
6. Comprehensive audit logging
"""

import hmac
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable, Optional, List

from flask import current_app, g, jsonify, request
from flask_jwt_extended import jwt_required

from app.auth.permissions import get_current_user, current_user_is_super_admin
from app.extensions import db, limiter
from app.models.user import SUPERADMIN_THRESHOLD

logger = logging.getLogger(__name__)


# Simple in-memory rate limiter for admin operations
_rate_limit_cache = {}


def _check_rate_limit(key: str, limit_string: str) -> bool:
    """
    Check if a rate limit has been exceeded.
    limit_string format: "10/minute" or "100/hour"
    Returns True if limit is NOT exceeded (request is allowed)
    Returns False if limit IS exceeded (request should be rejected)

    Note: Rate limiting is disabled in TESTING mode.
    """
    # Disable rate limiting in test mode
    if current_app.config.get("TESTING"):
        return True  # Always allow in test mode

    try:
        parts = limit_string.split("/")
        if len(parts) != 2:
            return True  # Invalid format, allow request

        limit_count = int(parts[0])
        time_unit = parts[1].lower()

        # Determine window in seconds
        if "second" in time_unit:
            window = 1
        elif "minute" in time_unit:
            window = 60
        elif "hour" in time_unit:
            window = 3600
        elif "day" in time_unit:
            window = 86400
        else:
            return True  # Invalid time unit, allow request

        now = datetime.now(timezone.utc).timestamp()

        # Clean old entries and get current count
        if key not in _rate_limit_cache:
            _rate_limit_cache[key] = []

        # Remove entries outside the window
        _rate_limit_cache[key] = [t for t in _rate_limit_cache[key] if now - t < window]

        # Check if limit exceeded
        if len(_rate_limit_cache[key]) >= limit_count:
            return False  # Limit exceeded

        # Record this request
        _rate_limit_cache[key].append(now)
        return True  # Limit not exceeded

    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True  # On error, allow request


class AdminSecurityConfig:
    """Configuration for admin security checks."""

    def __init__(
        self,
        require_2fa: bool = False,
        require_super_admin: bool = False,
        rate_limit: Optional[str] = None,
        audit_log: bool = True,
        check_ip_whitelist: bool = True,
    ):
        """
        Args:
            require_2fa: Require 2FA verification for this operation.
            require_super_admin: Require SuperAdmin role level (>= 100).
            rate_limit: Rate limit string (e.g., "10/min", "100/hour").
            audit_log: Log the action to audit log (default True).
            check_ip_whitelist: Check IP whitelist if configured (default True).
        """
        self.require_2fa = require_2fa
        self.require_super_admin = require_super_admin
        self.rate_limit = rate_limit or "10/minute"  # Default: 10 per minute
        self.audit_log = audit_log
        self.check_ip_whitelist = check_ip_whitelist


def _get_client_ip() -> str:
    """Extract client IP from request, handling proxies."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_ip_whitelisted(client_ip: str) -> bool:
    """Check if client IP is in whitelist (if configured)."""
    whitelist = current_app.config.get("ADMIN_IP_WHITELIST", [])
    if not whitelist:
        return True  # No whitelist configured = allow all
    return client_ip in whitelist


def _verify_2fa(user) -> bool:
    """
    Verify 2FA for user. Returns True if 2FA is verified or not required.
    Checks 2fa_verified_at timestamp to ensure recent verification.

    Note: Until 2FA is fully implemented in the User model, this checks
    for the optional attributes and allows access if they're not present.
    """
    # Check if user has 2FA attributes (graceful fallback for now)
    if not hasattr(user, "two_factor_enabled"):
        # 2FA not yet implemented for this user
        return True

    if not user.two_factor_enabled:
        return True  # 2FA not enabled for this user

    if not hasattr(user, "two_factor_verified_at") or user.two_factor_verified_at is None:
        return False  # 2FA required but not verified

    # Check if 2FA verification is recent (within 1 hour)
    verified_at = user.two_factor_verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)

    time_since_verification = datetime.now(timezone.utc) - verified_at
    return time_since_verification < timedelta(hours=1)


def _log_admin_action(
    user,
    action: str,
    resource: str,
    status: str = "success",
    details: Optional[dict] = None,
):
    """Log admin action to audit log."""
    from app.services import log_activity

    metadata = {
        "security_level": "admin",
        "resource": resource,
        **(details or {}),
    }

    log_activity(
        actor=user,
        category="admin_security",
        action=action,
        status=status,
        message=f"Admin action: {action} on {resource}",
        route=request.path,
        method=request.method,
        metadata=metadata,
        tags=["admin", "security"],
    )


def _log_security_violation(
    user,
    violation_type: str,
    reason: str,
    details: Optional[dict] = None,
):
    """Log security violation for alerting."""
    from app.services import log_activity

    metadata = {
        "violation_type": violation_type,
        "reason": reason,
        "client_ip": _get_client_ip(),
        **(details or {}),
    }

    # Use CRITICAL for serious violations
    log_activity(
        actor=user,
        category="security",
        action="admin_security_violation",
        status="critical",
        message=f"Admin security violation: {violation_type} - {reason}",
        route=request.path,
        method=request.method,
        metadata=metadata,
        tags=["admin", "security", "violation"],
    )

    # Also log to application logger
    logger.critical(
        f"Admin security violation: {violation_type}",
        extra={
            "event_type": "admin_security_violation",
            "violation_type": violation_type,
            "reason": reason,
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "client_ip": _get_client_ip(),
            **metadata,
        },
    )


def admin_security(
    require_2fa: bool = False,
    require_super_admin: bool = False,
    rate_limit: Optional[str] = None,
    audit_log: bool = True,
    check_ip_whitelist: bool = True,
) -> Callable:
    """
    Multi-layer security decorator for admin endpoints.

    Usage:
        @api_v1_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
        @admin_security(require_2fa=True, require_super_admin=True, rate_limit="5/minute")
        def sensitive_admin_operation(user_id):
            ...

    Args:
        require_2fa: Require 2FA verification (sensitive operations).
        require_super_admin: Require SuperAdmin role level (>= 100).
        rate_limit: Rate limit per user (e.g., "10/minute", "100/hour").
        audit_log: Log all successful operations (default True).
        check_ip_whitelist: Enforce IP whitelist if configured (default True).

    Returns:
        Decorated function with multi-layer security checks.
    """
    config = AdminSecurityConfig(
        require_2fa=require_2fa,
        require_super_admin=require_super_admin,
        rate_limit=rate_limit,
        audit_log=audit_log,
        check_ip_whitelist=check_ip_whitelist,
    )

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # 1. JWT and admin role verification (via @jwt_required decorator)
            user = get_current_user()
            if user is None or user.is_banned:
                return jsonify({"error": "Unauthorized"}), 401

            if not user.is_admin:
                _log_security_violation(
                    user,
                    "non_admin_access_attempt",
                    "Non-admin user attempted admin operation",
                )
                return jsonify({"error": "Forbidden"}), 403

            # 2. Role level verification
            if config.require_super_admin:
                if not current_user_is_super_admin():
                    user_level = getattr(user, "role_level", 0) or 0
                    _log_security_violation(
                        user,
                        "insufficient_role_level",
                        f"Insufficient role level: {user_level} < {SUPERADMIN_THRESHOLD}",
                        {"required_level": SUPERADMIN_THRESHOLD, "user_level": user_level},
                    )
                    return jsonify({
                        "error": "Forbidden",
                        "code": "INSUFFICIENT_PRIVILEGE"
                    }), 403

            # 3. IP whitelist check
            if config.check_ip_whitelist:
                client_ip = _get_client_ip()
                if not _is_ip_whitelisted(client_ip):
                    _log_security_violation(
                        user,
                        "ip_whitelist_violation",
                        f"IP not whitelisted: {client_ip}",
                        {"client_ip": client_ip},
                    )
                    return jsonify({
                        "error": "Forbidden",
                        "code": "IP_NOT_WHITELISTED"
                    }), 403

            # 4. Per-admin rate limiting
            if config.rate_limit:
                rate_limit_key = f"admin_action:{user.id}"
                if not _check_rate_limit(rate_limit_key, config.rate_limit):
                    # Rate limit exceeded
                    _log_security_violation(
                        user,
                        "rate_limit_exceeded",
                        f"Admin rate limit exceeded for user {user.id}",
                    )
                    logger.warning(f"Rate limit exceeded for admin {user.id}")
                    return jsonify({
                        "error": "Too many admin requests",
                        "code": "RATE_LIMIT_EXCEEDED"
                    }), 429

            # 5. 2FA verification
            if config.require_2fa:
                if not _verify_2fa(user):
                    _log_security_violation(
                        user,
                        "2fa_verification_failed",
                        "2FA verification required but not verified",
                    )
                    return jsonify({
                        "error": "Two-factor authentication required",
                        "code": "2FA_REQUIRED"
                    }), 403

            # Store security context in g for audit logging
            g.admin_security_user = user
            g.admin_security_config = config

            # Call the actual endpoint
            try:
                result = f(*args, **kwargs)

                # 6. Audit log successful operation
                if config.audit_log:
                    resource = f"{request.path}:{request.method}"
                    _log_admin_action(
                        user,
                        action=f.__name__,
                        resource=resource,
                        status="success",
                    )

                return result
            except Exception as e:
                # Log unexpected errors
                _log_security_violation(
                    user,
                    "admin_operation_error",
                    f"Error during admin operation: {str(e)}",
                )
                logger.exception(f"Error in admin operation {f.__name__}")
                raise

        # Apply JWT requirement first (base requirement)
        wrapped = jwt_required()(wrapped)
        return wrapped

    return decorator


def admin_security_sensitive(
    operation_name: str = "sensitive_operation",
    require_super_admin: bool = True,
) -> Callable:
    """
    Convenience decorator for highly sensitive operations.

    Automatically enables:
    - 2FA requirement
    - SuperAdmin role requirement
    - Stricter rate limiting (5/minute)
    - IP whitelist check
    - Comprehensive audit logging

    Usage:
        @api_v1_bp.route("/users/<int:user_id>", methods=["DELETE"])
        @admin_security_sensitive("user_deletion")
        def users_delete(user_id):
            ...
    """
    return admin_security(
        require_2fa=True,
        require_super_admin=require_super_admin,
        rate_limit="5/minute",
        audit_log=True,
        check_ip_whitelist=True,
    )


def get_admin_security_context() -> Optional[AdminSecurityConfig]:
    """Get the security context for the current admin request."""
    return getattr(g, "admin_security_config", None)


def get_admin_security_user():
    """Get the admin user that triggered the security check."""
    return getattr(g, "admin_security_user", None)
