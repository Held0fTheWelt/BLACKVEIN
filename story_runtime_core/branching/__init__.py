"""
Branching system for World of Shadows.

Provides decision point management, path state tracking, and outcome divergence measurement.
"""

from .decision_point import (
    DecisionPoint, DecisionPointType, DecisionOption, DecisionPointRegistry
)
from .path_state import PathState, PathNode, PathStateManager
from .consequence_filter import ConsequenceFilter, ConsequenceFact
from .outcome_divergence import OutcomeDivergence, DivergenceMetric, DivergenceScore
from .forecast import (
    BRANCHING_FORECAST_SCHEMA_VERSION,
    BRANCHING_FORECAST_SOURCE,
    build_branching_forecast,
)
from .simulation_tree import (
    BRANCHING_SIMULATION_TREE_SCHEMA_VERSION,
    BRANCHING_SIMULATION_TREE_SOURCE,
    append_simulation_node,
    clamp_simulation_limits,
    finalize_simulation_tree,
    forecast_has_options,
    make_simulated_turn_node,
    make_simulation_tree,
    simulated_input_for_branch_option,
)

__all__ = [
    'DecisionPoint',
    'DecisionPointType',
    'DecisionOption',
    'DecisionPointRegistry',
    'PathState',
    'PathNode',
    'PathStateManager',
    'ConsequenceFilter',
    'ConsequenceFact',
    'OutcomeDivergence',
    'DivergenceMetric',
    'DivergenceScore',
    'BRANCHING_FORECAST_SCHEMA_VERSION',
    'BRANCHING_FORECAST_SOURCE',
    'build_branching_forecast',
    'BRANCHING_SIMULATION_TREE_SCHEMA_VERSION',
    'BRANCHING_SIMULATION_TREE_SOURCE',
    'append_simulation_node',
    'clamp_simulation_limits',
    'finalize_simulation_tree',
    'forecast_has_options',
    'make_simulated_turn_node',
    'make_simulation_tree',
    'simulated_input_for_branch_option',
]
