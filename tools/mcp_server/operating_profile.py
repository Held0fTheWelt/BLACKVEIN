"""Operating profile enforcement for MCP tools."""

from enum import Enum
from typing import Dict, List, Optional


class OperatingProfile(Enum):
    """MCP operating profiles control tool access."""
    READ_ONLY = "read_only"
    EXECUTE = "execute"
    ADMIN = "admin"


# Which tools are available in each profile
PROFILE_TOOL_ACCESS: Dict[OperatingProfile, List[str]] = {
    OperatingProfile.READ_ONLY: ["get", "state", "logs", "diag"],
    OperatingProfile.EXECUTE: ["get", "state", "logs", "diag", "execute_turn"],
    OperatingProfile.ADMIN: ["get", "state", "logs", "diag", "execute_turn"],
}


def check_tool_access(profile: OperatingProfile, tool_name: str) -> bool:
    """Check if tool is available in profile."""
    allowed_tools = PROFILE_TOOL_ACCESS.get(profile, [])
    return tool_name in allowed_tools


def check_session_binding(profile: OperatingProfile, player_bound: bool) -> bool:
    """Check if player binding requirement is met."""
    if profile == OperatingProfile.READ_ONLY:
        return True  # Read-only doesn't require binding
    if profile == OperatingProfile.EXECUTE:
        return player_bound  # Execute requires binding
    if profile == OperatingProfile.ADMIN:
        return True  # Admin can access without binding
    return False
