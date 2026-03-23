"""
Safe error handling utilities for API responses.

Prevents information disclosure by:
- Logging full errors server-side with context
- Returning generic errors to clients
- Sanitizing exception messages in responses
"""
import logging
import traceback
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def safe_error_response(
    exception: Exception,
    generic_message: str = "An error occurred",
    log_level: str = "error",
    context: Optional[dict] = None,
) -> Tuple[str, int]:
    """
    Safely handle an exception by logging details server-side and returning a generic error.

    Args:
        exception: The exception that occurred
        generic_message: Generic message to return to client (no details leaked)
        log_level: Logging level (error, warning, exception)
        context: Additional context dict to include in server logs

    Returns:
        Tuple of (generic_error_message, status_code)

    Example:
        try:
            db_query()
        except Exception as e:
            error_msg, status = safe_error_response(
                e,
                generic_message="Database operation failed",
                context={"operation": "user_lookup"}
            )
            return jsonify({"error": error_msg}), status
    """
    log_data = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "traceback": traceback.format_exc(),
    }

    if context:
        log_data["context"] = context

    if log_level == "warning":
        logger.warning("Handled exception", extra=log_data)
    elif log_level == "exception":
        logger.exception(generic_message, extra=log_data)
    else:  # error (default)
        logger.error(generic_message, extra=log_data)

    return generic_message, 500


def sanitize_exception_message(exc: Exception) -> str:
    """
    Extract a safe message from an exception without leaking internals.

    Filters out dangerous details like SQL, file paths, config values.

    Args:
        exc: Exception to sanitize

    Returns:
        Safe message string
    """
    message = str(exc)

    # Filter out common sensitive patterns
    sensitive_patterns = [
        "Column",
        "table",
        "schema",
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "/",
        "\\",
        ".py",
        "config",
        "SECRET",
        "DATABASE",
    ]

    for pattern in sensitive_patterns:
        if pattern.lower() in message.lower():
            return "Invalid request"

    return message


def log_full_error(
    exception: Exception,
    message: str = "Error occurred",
    user_id: Optional[int] = None,
    route: Optional[str] = None,
    method: Optional[str] = None,
) -> None:
    """
    Log full error details server-side for debugging.

    Args:
        exception: The exception that occurred
        message: Context message
        user_id: Authenticated user ID (if available)
        route: API route that failed
        method: HTTP method
    """
    context = {
        "user_id": user_id,
        "route": route,
        "method": method,
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }

    logger.exception(message, extra=context)


# Common generic error messages for different scenarios
ERROR_MESSAGES = {
    "invalid_token": "Invalid or expired token",
    "database_error": "A database operation failed",
    "validation_error": "Invalid request parameters",
    "not_found": "Resource not found",
    "unauthorized": "Unauthorized access",
    "forbidden": "Access forbidden",
    "conflict": "Resource conflict",
    "internal_error": "An unexpected error occurred",
}
