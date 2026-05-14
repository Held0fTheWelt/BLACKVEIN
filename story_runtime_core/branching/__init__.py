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
from .branch_tree import (
    BRANCHING_TREE_RECORD_SCHEMA_VERSION,
    BRANCHING_TREE_RECORD_SOURCE,
    BRANCHING_TREE_STATUS_COMMITTED,
    BRANCHING_TREE_STATUS_EXPIRED,
    BRANCHING_TREE_STATUS_NOT_APPLICABLE,
    BRANCHING_TREE_STATUS_SIMULATED,
    BRANCHING_TREE_STATUS_STALE,
    branch_tree_is_fresh,
    branch_tree_path_nodes,
    find_branch_tree_node,
    make_branch_tree_record,
    mark_branch_tree_committed,
    mark_branch_tree_expired,
    mark_branch_tree_stale,
    selectable_simulation_nodes,
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
    'BRANCHING_TREE_RECORD_SCHEMA_VERSION',
    'BRANCHING_TREE_RECORD_SOURCE',
    'BRANCHING_TREE_STATUS_COMMITTED',
    'BRANCHING_TREE_STATUS_EXPIRED',
    'BRANCHING_TREE_STATUS_NOT_APPLICABLE',
    'BRANCHING_TREE_STATUS_SIMULATED',
    'BRANCHING_TREE_STATUS_STALE',
    'branch_tree_is_fresh',
    'branch_tree_path_nodes',
    'find_branch_tree_node',
    'make_branch_tree_record',
    'mark_branch_tree_committed',
    'mark_branch_tree_expired',
    'mark_branch_tree_stale',
    'selectable_simulation_nodes',
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
