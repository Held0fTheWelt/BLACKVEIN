"""
LangGraph Agent State Schema - Game-aware state for multi-turn reasoning.

This module defines the state passed through LangGraph nodes. State is
immutable after locking and serializable to JSON for auditing.

Constitutional Laws:
- Law 1: One truth boundary - state is read-only mirror of game world
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class AgentState:
    """Immutable game state for LangGraph reasoning.

    Fields represent:
    - Session/player identity (read-only)
    - Current game state (mirror from SessionService)
    - Player's queued action
    - AI reasoning steps and decision
    - Error tracking and diagnostics
    """

    # Session and player identity
    session_id: str
    player_id: int
    turn_number: int = 0

    # Game state mirrors (read-only)
    current_state: Dict[str, Any] = field(default_factory=dict)
    previous_action: Optional[str] = None
    previous_result: Optional[str] = None

    # AI reasoning
    reasoning_steps: Optional[List[str]] = field(default_factory=list)
    decision: Optional[str] = None

    # MCP diagnostics and logs
    mcp_logs: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    # Operational profile
    operational_profile: Dict[str, Any] = field(default_factory=dict)

    # Error tracking
    errors: List[str] = field(default_factory=list)
    is_degraded: bool = False

    # Internal state - not part of dataclass init
    locked: bool = field(default=False, repr=False, compare=False)

    def lock(self) -> None:
        """Lock state to prevent further modifications."""
        # Use object.__setattr__ to bypass __setattr__ override
        object.__setattr__(self, "locked", True)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent modification after lock."""
        if name != "locked":
            # Check if locked (allow setting during __init__)
            if hasattr(self, "locked") and self.locked:
                raise ValueError(f"Cannot modify locked state field: {name}")
        super().__setattr__(name, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to JSON-serializable dict.

        Returns:
            Dictionary representation of state (excludes locked)
        """
        data = asdict(self)
        # Remove internal locked field
        data.pop("locked", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create state from dictionary.

        Args:
            data: Dictionary with state fields

        Returns:
            New AgentState instance
        """
        return cls(**data)

    def to_json(self) -> str:
        """Serialize state to JSON.

        Returns:
            JSON string representation
        """
        # Handle datetime fields
        data = self.to_dict()
        return json.dumps(data, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentState":
        """Deserialize state from JSON.

        Args:
            json_str: JSON string representation

        Returns:
            New AgentState instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_reasoning_step(self, step: str) -> None:
        """Add a reasoning step (before lock).

        Args:
            step: Reasoning text to add
        """
        if self.locked:
            raise ValueError("Cannot modify locked state")
        self.reasoning_steps.append(step)

    def set_decision(self, decision: str) -> None:
        """Set AI decision (before lock).

        Args:
            decision: Decision text
        """
        if self.locked:
            raise ValueError("Cannot modify locked state")
        self.decision = decision

    def add_error(self, error: str) -> None:
        """Add error message and mark degraded.

        Args:
            error: Error description
        """
        if self.locked:
            raise ValueError("Cannot modify locked state")
        self.errors.append(error)
        self.is_degraded = True

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"AgentState(session={self.session_id}, player={self.player_id}, "
            f"turn={self.turn_number}, decision={self.decision}, "
            f"degraded={self.is_degraded})"
        )


def create_initial_state(
    session_id: str,
    player_id: int,
    current_state: Dict[str, Any],
    operational_profile: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Create initial state for reasoning.

    Args:
        session_id: Session identifier
        player_id: Player identifier
        current_state: Current game world state (from SessionService)
        operational_profile: Operational profile for difficulty/complexity

    Returns:
        Initialized AgentState
    """
    return AgentState(
        session_id=session_id,
        player_id=player_id,
        turn_number=0,
        current_state=current_state,
        operational_profile=operational_profile or {},
    )
