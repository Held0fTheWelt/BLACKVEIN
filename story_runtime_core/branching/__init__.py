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
]
