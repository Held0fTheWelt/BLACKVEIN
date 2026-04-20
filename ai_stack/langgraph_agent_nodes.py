"""
LangGraph Agent Nodes - Individual reasoning steps for game decision-making.

Each node is a pure function that takes state and returns updated state.
Nodes are designed to be composable and fail-closed.

Constitutional Laws:
- Law 1: One truth boundary - nodes read mirrors, don't mutate directly
- Law 10: Runtime catastrophic failure - node errors handled gracefully
"""

from typing import Any, Dict, Optional
from ai_stack.langgraph_agent_state import AgentState
from ai_stack.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog


def initialize_state(
    session_id: str,
    player_id: int,
    mcp_interface: MCPAgentInterface,
    operational_profile: Optional[Dict[str, Any]] = None
) -> AgentState:
    """Node 0: Initialize state by fetching session and world state.

    Args:
        session_id: Session identifier
        player_id: Player identifier
        mcp_interface: MCP interface for tool calls
        operational_profile: Optional operational profile

    Returns:
        Initialized AgentState

    Error Handling:
        - Session not found: returns error state
        - MCP timeout: returns error state with degraded flag
    """
    try:
        # Get session info
        session_result = mcp_interface.call_session_get(session_id)
        if not session_result.get("success"):
            state = AgentState(
                session_id=session_id,
                player_id=player_id,
                current_state={}
            )
            state.add_error(f"Session init failed: {session_result.get('error')}")
            return state

        # Get world state
        state_result = mcp_interface.call_session_state(session_id)
        if not state_result.get("success"):
            state = AgentState(
                session_id=session_id,
                player_id=player_id,
                current_state={}
            )
            state.add_error(f"State fetch failed: {state_result.get('error')}")
            return state

        # Create initialized state
        state = AgentState(
            session_id=session_id,
            player_id=player_id,
            current_state=state_result.get("data", {}),
            operational_profile=operational_profile or {}
        )
        return state

    except Exception as e:
        # Catastrophic error - return degraded state
        state = AgentState(
            session_id=session_id,
            player_id=player_id,
            current_state={}
        )
        state.add_error(f"Initialization error: {str(e)}")
        return state


def reason_decision(
    state: AgentState,
    mcp_interface: MCPAgentInterface,
    prompt_catalog: CanonicalPromptCatalog
) -> AgentState:
    """Node 1: Analyze game state and player action to generate reasoning.

    Args:
        state: Current agent state
        mcp_interface: MCP interface for diagnostics
        prompt_catalog: Canonical prompts for reasoning

    Returns:
        Updated state with reasoning_steps

    Error Handling:
        - LLM error: adds error, marks degraded
        - Prompt not found: returns state unchanged
    """
    try:
        if state.is_degraded:
            # Skip if already degraded
            return state

        # Get prompt
        prompt = prompt_catalog.get_prompt("decision_context")
        template = prompt["template"]

        # Note: In production, this would call LLM via structured output
        # For MVP, we add placeholder reasoning
        reasoning = [
            "Analyzing current game state and player queued action",
            f"World context: {str(state.current_state)[:100]}...",
            "Generating 3-5 possible outcomes for AI to choose from"
        ]

        state.add_reasoning_step("\n".join(reasoning))
        return state

    except Exception as e:
        state.add_error(f"Reasoning error: {str(e)}")
        return state


def select_action(
    state: AgentState,
    prompt_catalog: CanonicalPromptCatalog
) -> AgentState:
    """Node 2: Select best action from reasoning analysis.

    Args:
        state: Current agent state with reasoning_steps
        prompt_catalog: Canonical prompts for selection

    Returns:
        Updated state with decision

    Error Handling:
        - Invalid reasoning: falls back to safe default action
        - Prompt error: returns state with degraded flag
    """
    try:
        if state.is_degraded:
            state.decision = "move_forward"  # Safe default
            return state

        if not state.reasoning_steps:
            state.decision = "move_forward"  # Safe default
            return state

        # Get prompt
        prompt = prompt_catalog.get_prompt("action_selection")

        # In production: call LLM with reasoning_steps
        # For MVP: select from safe defaults
        safe_actions = ["move_forward", "look_around", "wait"]
        state.decision = safe_actions[0]

        return state

    except Exception as e:
        state.add_error(f"Action selection error: {str(e)}")
        state.decision = "move_forward"  # Safe default
        return state


def execute_turn(
    state: AgentState,
    mcp_interface: MCPAgentInterface
) -> AgentState:
    """Node 3: Execute the chosen action via SessionService.

    Args:
        state: Current agent state with decision
        mcp_interface: MCP interface for execute_turn

    Returns:
        Updated state with turn result

    Error Handling:
        - Invalid action: caught and returned as error
        - MCP timeout: marks degraded, preserves state
        - Unknown session: returns error state
    """
    try:
        if not state.decision:
            state.add_error("No decision made")
            return state

        # Execute turn via MCP
        result = mcp_interface.call_execute_turn(
            state.session_id,
            state.player_id,
            state.decision
        )

        if not result.get("success"):
            state.add_error(f"Turn execution failed: {result.get('error')}")
            return state

        # Update state with result
        turn_data = result.get("data", {})
        state.turn_number = turn_data.get("turn_number", state.turn_number + 1)
        state.current_state = turn_data.get("world_state", state.current_state)
        state.previous_action = state.decision
        state.previous_result = turn_data.get("narrative", "")

        return state

    except Exception as e:
        state.add_error(f"Turn execution error: {str(e)}")
        return state


def interpret_result(
    state: AgentState,
    prompt_catalog: CanonicalPromptCatalog
) -> AgentState:
    """Node 4: Interpret turn result for next decision.

    Args:
        state: Current agent state with turn result
        prompt_catalog: Canonical prompts for interpretation

    Returns:
        Updated state ready for next turn

    Error Handling:
        - LLM error: uses fallback interpretation
        - Missing result: uses state unchanged
    """
    try:
        if state.is_degraded and not state.previous_result:
            # Cannot interpret without result
            return state

        # Get prompt
        prompt = prompt_catalog.get_prompt("narrative_response")

        # In production: call LLM to generate narrative
        # For MVP: use result from execute_turn
        if state.previous_result:
            state.add_reasoning_step(f"Turn result: {state.previous_result}")

        return state

    except Exception as e:
        state.add_error(f"Result interpretation error: {str(e)}")
        return state
