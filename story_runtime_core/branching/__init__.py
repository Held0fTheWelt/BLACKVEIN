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
]
