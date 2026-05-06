"""
LangGraph Orchestrator - Builds and runs multi-turn reasoning graph.

The orchestrator compiles LangGraph nodes into a complete reasoning pipeline
for game decision-making. Graph flows: init -> reason -> select -> execute -> interpret.

Constitutional Laws:
- Law 9: AI composition bounds - orchestrator uses only MCP interface
- Law 10: Runtime catastrophic failure - graph errors don't crash system
"""

from typing import Any, Dict, Optional

try:
    from ai_stack.langgraph_imports import StateGraph
except ImportError:
    # Fallback for testing
    StateGraph = None

from ai_stack.langgraph_agent_state import AgentState, create_initial_state
from ai_stack.langgraph_agent_nodes import (
    initialize_state,
    reason_decision,
    select_action,
    execute_turn,
    interpret_result
)
from ai_stack.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog


class GameOrchestrator:
    """Orchestrates LangGraph AI reasoning for game decisions.

    Graph structure (linear for MVP):
    initialize_state -> reason_decision -> select_action -> execute_turn -> interpret_result

    Each node:
    - Takes AgentState
    - Returns updated AgentState
    - Never raises exceptions
    - Tracks errors and degradation
    """

    def __init__(
        self,
        mcp_interface: MCPAgentInterface,
        prompt_catalog: CanonicalPromptCatalog
    ):
        """Initialize orchestrator.

        Args:
            mcp_interface: MCP agent interface for tool calls
            prompt_catalog: Canonical prompt catalog
        """
        self.mcp_interface = mcp_interface
        self.prompt_catalog = prompt_catalog
        self._graph = None

    def build_graph(self) -> Any:
        """Build the LangGraph computation graph.

        Returns:
            Compiled langgraph.Graph or mock graph for testing

        Raises:
            ImportError: If langgraph not available and required
        """
        if self._graph is not None:
            return self._graph

        if StateGraph is None:
            # Return mock graph for testing without langgraph
            return self._build_mock_graph()

        # Build real LangGraph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node(
            "initialize",
            self._node_initialize_state
        )
        graph.add_node(
            "reason",
            self._node_reason_decision
        )
        graph.add_node(
            "select",
            self._node_select_action
        )
        graph.add_node(
            "execute",
            self._node_execute_turn
        )
        graph.add_node(
            "interpret",
            self._node_interpret_result
        )

        # Add edges (linear pipeline)
        graph.add_edge("initialize", "reason")
        graph.add_edge("reason", "select")
        graph.add_edge("select", "execute")
        graph.add_edge("execute", "interpret")

        # Set entry and exit points
        graph.set_entry_point("initialize")
        graph.set_finish_point("interpret")

        # Compile
        self._graph = graph.compile()
        return self._graph

    def _node_initialize_state(self, state: AgentState) -> AgentState:
        """Wrapper for initialize_state node."""
        initialized = initialize_state(
            state.session_id,
            state.player_id,
            self.mcp_interface,
            state.operational_profile
        )
        # Preserve operational profile from input state
        if state.operational_profile:
            initialized.operational_profile = state.operational_profile
        return initialized

    def _node_reason_decision(self, state: AgentState) -> AgentState:
        """Wrapper for reason_decision node."""
        return reason_decision(
            state,
            self.mcp_interface,
            self.prompt_catalog
        )

    def _node_select_action(self, state: AgentState) -> AgentState:
        """Wrapper for select_action node."""
        return select_action(state, self.prompt_catalog)

    def _node_execute_turn(self, state: AgentState) -> AgentState:
        """Wrapper for execute_turn node."""
        return execute_turn(state, self.mcp_interface)

    def _node_interpret_result(self, state: AgentState) -> AgentState:
        """Wrapper for interpret_result node."""
        return interpret_result(state, self.prompt_catalog)

    def _build_mock_graph(self) -> "MockGraph":
        """Build mock graph for testing without langgraph."""
        return MockGraph(self)

    def run(
        self,
        session_id: str,
        player_id: int,
        operational_profile: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """Execute reasoning pipeline for single turn.

        Args:
            session_id: Session identifier
            player_id: Player identifier
            operational_profile: Optional operational profile

        Returns:
            Final AgentState with decision and execution result

        Error Handling:
            - Session errors: returns degraded state
            - MCP errors: returns degraded state
            - LLM errors: uses safe defaults
        """
        try:
            graph = self.build_graph()

            # Create initial state
            initial_state = AgentState(
                session_id=session_id,
                player_id=player_id,
                operational_profile=operational_profile or {}
            )

            # Run graph
            if isinstance(graph, MockGraph):
                # Mock execution
                final_state = graph.invoke(initial_state)
            else:
                # Real LangGraph execution
                final_result = graph.invoke(initial_state)
                # Convert dict to AgentState if needed
                if isinstance(final_result, dict):
                    final_state = AgentState.from_dict(final_result)
                else:
                    final_state = final_result

            return final_state

        except Exception as e:
            # Catastrophic error - return degraded state
            state = AgentState(
                session_id=session_id,
                player_id=player_id
            )
            state.add_error(f"Orchestration error: {str(e)}")
            return state


class MockGraph:
    """Mock LangGraph for testing without langgraph library.

    Executes nodes sequentially to simulate graph execution.
    """

    def __init__(self, orchestrator: GameOrchestrator):
        """Initialize mock graph.

        Args:
            orchestrator: Parent GameOrchestrator
        """
        self.orchestrator = orchestrator

    def invoke(self, initial_state: AgentState) -> AgentState:
        """Execute mock graph sequentially.

        Args:
            initial_state: Initial AgentState

        Returns:
            Final AgentState after all nodes executed
        """
        state = initial_state

        # Execute nodes in sequence
        state = self.orchestrator._node_initialize_state(state)
        state = self.orchestrator._node_reason_decision(state)
        state = self.orchestrator._node_select_action(state)
        state = self.orchestrator._node_execute_turn(state)
        state = self.orchestrator._node_interpret_result(state)

        return state
