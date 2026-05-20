"""Centralized SQL LIKE wildcard escaping utilities for search functionality."""


def _escape_sql_like_wildcards(search_term: str) -> str:
    """
    Escape SQL LIKE wildcards (%, _) in a string for safe LIKE pattern matching.

    This function prevents search bypass attacks by properly escaping special
    characters in LIKE queries. The escape sequence uses backslash as the escape
    character, which must be specified in SQLAlchemy filters with escape='\\'.

    Args:
        search_term: The search term to escape

    Returns:
        The escaped search term with % and _ safely escaped

    Examples:
        >>> _escape_sql_like_wildcards("admin_user")
        'admin\\_user'
        >>> _escape_sql_like_wildcards("test%pattern")
        'test\\%pattern'
        >>> _escape_sql_like_wildcards(None)
        None
        >>> _escape_sql_like_wildcards("")
        ''
    """
    if not search_term:
        return search_term
    # Escape backslash first to avoid double-escaping
    return search_term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
