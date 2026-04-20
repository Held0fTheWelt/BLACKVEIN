"""Error codes and JSON-RPC error envelope."""

from dataclasses import dataclass
from typing import Any, Optional

# JSON-RPC standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Application error codes (use -32000 to -32099 range)
TOOL_NOT_FOUND = -32000
INVALID_INPUT = -32001
RATE_LIMITED = -32002
PERMISSION_DENIED = -32003


@dataclass
class JsonRpcError(Exception):
    """JSON-RPC 2.0 error envelope."""
    code: int
    message: str
    data: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to JSON-RPC error dict."""
        result = {"code": self.code, "message": self.message}
        if self.data:
            result["data"] = self.data
        return result


class ToolNotFoundError(Exception):
    """Raised when tool is not in registry."""
    pass


class RateLimitedError(Exception):
    """Raised when rate limit exceeded."""
    pass


class PermissionDeniedError(Exception):
    """Raised when tool permission check fails."""
    pass


class InvalidInputError(Exception):
    """Raised when input validation fails."""
    pass
