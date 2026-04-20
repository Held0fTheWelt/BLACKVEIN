"""Configuration management for MCP server."""

import os
from pathlib import Path


class Config:
    """Load and provide access to configuration from environment variables.

    MCP M1 operating profile (process-wide policy for write_capable tools) is read separately via
    ``WOS_MCP_OPERATING_PROFILE``: ``healthy`` | ``review_safe`` | ``test_isolated`` | ``degraded``.
    """

    def __init__(self):
        self.backend_url = os.getenv(
            "BACKEND_BASE_URL", "http://localhost:8000"
        )
        self.bearer_token = os.getenv("BACKEND_BEARER_TOKEN") or None
        self.request_timeout_s = 5
        self._repo_root = None

    @property
    def repo_root(self) -> Path:
        """Get repo root by walking up from this file to find content/ folder."""
        if self._repo_root is None:
            self._repo_root = get_repo_root()
        return self._repo_root


def get_repo_root() -> Path:
    """Find repo root by checking REPO_ROOT env var, then walking up to find content/ folder."""
    # Check env override first
    if "REPO_ROOT" in os.environ:
        return Path(os.environ["REPO_ROOT"])

    # Walk up from this file until content/ is found
    current = Path(__file__).resolve().parent
    while current != current.parent:  # Stop at filesystem root
        if (current / "content").is_dir():
            return current
        current = current.parent
    # Fallback to current file's parent
    return Path(__file__).resolve().parent
