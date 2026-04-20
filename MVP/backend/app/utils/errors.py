"""
Standardized error response handling for API routes.

All API error responses should use the api_error() helper to return:
{
    "error": "Human-readable error message",
    "code": "MACHINE_READABLE_CODE"
}

This ensures consistency across all endpoints and simplifies client-side error handling.
"""

from flask import jsonify

# Standard error codes for API responses
ERROR_CODES = {
    # 400 Bad Request errors
    "INVALID_INPUT": 400,
    "INVALID_JSON": 400,
    "MISSING_FIELD": 400,
    "INVALID_TYPE": 400,
    "VALIDATION_ERROR": 400,
    "INVALID_PRIORITY": 400,
    "INVALID_STATUS": 400,
    "INVALID_TARGET_TYPE": 400,
    "INVALID_SCOPE": 400,
    "MISSING_TABLE": 400,
    "INVALID_LANGUAGE": 400,
    "SEARCH_QUERY_TOO_SHORT": 400,
    "ARRAY_FORMAT_INVALID": 400,
    "INVALID_PARAMETER": 400,

    # 401 Unauthorized errors
    "UNAUTHORIZED": 401,
    "INVALID_TOKEN": 401,
    "TOKEN_EXPIRED": 401,
    "TOKEN_INVALID": 401,
    "INVALID_CREDENTIALS": 401,
    "MISSING_AUTH": 401,

    # 402 Payment Required (reserved for future use)
    # Not commonly used in most APIs

    # 403 Forbidden errors
    "FORBIDDEN": 403,
    "FEATURE_ACCESS_DENIED": 403,
    "INSUFFICIENT_PERMISSIONS": 403,
    "ADMIN_REQUIRED": 403,
    "MODERATOR_REQUIRED": 403,
    "SUPER_ADMIN_REQUIRED": 403,
    "INSUFFICIENT_ROLE_LEVEL": 403,
    "RESTRICTED_ACCOUNT": 403,
    "EMAIL_NOT_VERIFIED": 403,
    "THREAD_LOCKED": 403,
    "THREAD_NOT_ACCESSIBLE": 403,

    # 404 Not Found errors
    "NOT_FOUND": 404,
    "RESOURCE_NOT_FOUND": 404,
    "USER_NOT_FOUND": 404,
    "THREAD_NOT_FOUND": 404,
    "POST_NOT_FOUND": 404,
    "CATEGORY_NOT_FOUND": 404,
    "AREA_NOT_FOUND": 404,
    "WIKI_PAGE_NOT_FOUND": 404,
    "NEWS_NOT_FOUND": 404,
    "ROLE_NOT_FOUND": 404,
    "TAG_NOT_FOUND": 404,
    "REPORT_NOT_FOUND": 404,
    "FEATURE_NOT_FOUND": 404,
    "SLOGAN_NOT_FOUND": 404,
    "TRANSLATION_NOT_FOUND": 404,
    "DISCUSSION_THREAD_NOT_FOUND": 404,
    "FORUM_THREAD_NOT_FOUND": 404,
    "MAPPING_NOT_FOUND": 404,
    "ROOT_POST_NOT_FOUND": 404,
    "FILE_READ_ERROR": 404,

    # 409 Conflict errors
    "CONFLICT": 409,
    "RESOURCE_EXISTS": 409,
    "DUPLICATE_KEY": 409,
    "KEY_ALREADY_IN_USE": 409,
    "USERNAME_TAKEN": 409,
    "EMAIL_ALREADY_REGISTERED": 409,

    # 429 Too Many Requests
    "RATE_LIMIT_EXCEEDED": 429,
    "ACCOUNT_LOCKED": 429,

    # 500 Internal Server Error
    "INTERNAL_ERROR": 500,
    "SERVER_ERROR": 500,
    "FILE_WRITE_ERROR": 500,

    # Security/Auth specific
    "PASSWORD_WEAK": 400,
    "PASSWORD_CHANGE_RESTRICTED": 400,
    "UNAUTHORIZED_PASSWORD_CHANGE": 403,

    # Service/External errors
    "SERVICE_ERROR": 500,
    "GAME_LAUNCHER_ERROR": 500,
    "ANALYTICS_FETCH_ERROR": 500,
    "TIMELINE_FETCH_ERROR": 500,
}


def api_error(message: str, code: str, status_code: int = None) -> tuple:
    """
    Return a standardized API error response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "NOT_FOUND", "INVALID_INPUT")
        status_code: HTTP status code. If None, inferred from ERROR_CODES dict.

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        >>> return api_error("User not found", "USER_NOT_FOUND", 404)
        ({"error": "User not found", "code": "USER_NOT_FOUND"}, 404)

        >>> return api_error("Invalid input", "INVALID_INPUT")  # Uses default 400
        ({"error": "Invalid input", "code": "INVALID_INPUT"}, 400)
    """
    # If status_code not provided, infer from ERROR_CODES
    if status_code is None:
        status_code = ERROR_CODES.get(code, 400)

    response = {
        "error": message,
        "code": code,
    }
    return jsonify(response), status_code


def api_success(data: dict = None, message: str = None, status_code: int = 200) -> tuple:
    """
    Return a standardized API success response (optional, for consistency).

    Args:
        data: Response data (optional)
        message: Success message (optional)
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        >>> return api_success({"id": 1, "name": "John"}, status_code=201)
        ({"id": 1, "name": "John"}, 201)

        >>> return api_success(message="Deleted successfully")
        ({"message": "Deleted successfully"}, 200)
    """
    if data is not None:
        response = data
        if message:
            response["message"] = message
        return jsonify(response), status_code
    elif message:
        return jsonify({"message": message}), status_code
    else:
        return jsonify({}), status_code
