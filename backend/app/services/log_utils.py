"""
Logging utilities for safe, redacted logging of sensitive data.

This module provides helper functions to ensure sensitive fields
(passwords, tokens, API keys, PII) are never logged in plaintext.

Usage:
    from app.services.log_utils import safe_log_dict, is_sensitive_field

    # Automatically redact sensitive fields before logging
    context = {'user_id': 123, 'password': 'secret123', 'email': 'user@example.com'}
    safe_context = {k: v for k, v in context.items() if not is_sensitive_field(k)}
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Fields that should never be logged in plaintext
SENSITIVE_FIELD_PATTERNS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "api_key",
    "apikey",
    "api_secret",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "bearer",
    "api_token",
    "service_token",
    "shared_secret",
    "signing_key",
    "private_key",
    "public_key",
    "encryption_key",
    "decrypt",
    "encrypt",
    "hash",
    "credit_card",
    "cc_number",
    "card_number",
    "cvv",
    "cvc",
    "ssn",
    "social_security",
    "tax_id",
    "phone",
    "phone_number",
    "cell",
    "mobile",
    "pii",
}


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name indicates sensitive data.

    Args:
        field_name: The field name to check (case-insensitive)

    Returns:
        True if the field should not be logged, False otherwise
    """
    if not isinstance(field_name, str):
        return False

    field_lower = field_name.lower()

    # Check for exact matches or partial matches
    for pattern in SENSITIVE_FIELD_PATTERNS:
        if pattern in field_lower:
            return True

    return False


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a copy of a dictionary with sensitive fields redacted.

    Sensitive fields are replaced with "***REDACTED***".

    Args:
        data: Dictionary to redact

    Returns:
        New dictionary with sensitive values replaced
    """
    if not isinstance(data, dict):
        return data

    redacted = {}
    for key, value in data.items():
        if is_sensitive_field(key):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        else:
            redacted[key] = value

    return redacted


def safe_log_dict(message: str, data: Dict[str, Any], level: str = "info") -> None:
    """
    Log a message with automatic redaction of sensitive fields in metadata.

    Args:
        message: The log message
        data: Dictionary with context data (sensitive fields will be redacted)
        level: Log level ("debug", "info", "warning", "error", "critical")
    """
    redacted = redact_dict(data)
    log_func = getattr(logger, level, logger.info)
    log_func(message, extra=redacted)


def safe_log_user(message: str, user: Any) -> None:
    """
    Log a message with user information (redacted).

    Only logs user ID and username, not sensitive user fields.

    Args:
        message: The log message
        user: User object (or None)
    """
    if user is None:
        user_info = {"user_id": None, "username": None}
    else:
        user_info = {
            "user_id": getattr(user, "id", None),
            "username": getattr(user, "username", None),
        }

    logger.info(message, extra=user_info)


def safe_log_request(message: str, request_obj: Any, include_method: bool = True) -> None:
    """
    Log request information without sensitive headers/payload.

    Args:
        message: The log message
        request_obj: Flask request object
        include_method: Whether to include HTTP method
    """
    context = {
        "path": getattr(request_obj, "path", None),
        "remote_addr": getattr(request_obj, "remote_addr", None),
    }

    if include_method:
        context["method"] = getattr(request_obj, "method", None)

    # Note: We deliberately exclude headers and body to prevent logging
    # Authorization headers, request payloads, etc.

    logger.info(message, extra=context)


# Usage examples (for documentation)
"""
EXAMPLE 1: Redacting user update context
    user_data = {
        'user_id': 123,
        'username': 'john_doe',
        'email': 'john@example.com',
        'password': 'MyPassword123!'
    }
    safe_user_data = redact_dict(user_data)
    # Result: {'user_id': 123, 'username': 'john_doe', 'email': 'john@example.com', 'password': '***REDACTED***'}

EXAMPLE 2: Safe logging with sensitive context
    safe_log_dict(
        "User registration attempted",
        {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': request.json.get('password'),
            'api_key_used': request.headers.get('X-API-Key')
        }
    )
    # Logs with password and api_key_used redacted

EXAMPLE 3: Checking if field is sensitive
    if not is_sensitive_field('user_id'):
        log_data['user_id'] = user.id
    if not is_sensitive_field('password'):
        # Will be True, skip logging password
        pass
"""
