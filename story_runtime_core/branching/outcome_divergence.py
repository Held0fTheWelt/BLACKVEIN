"""
Outcome divergence measurement - quantifies how different two branch paths are.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Any
from enum import Enum


class DivergenceMetric(Enum):
    """Types of divergence to measure."""
    DECISION_POINTS = "decision_points"  # How many decisions differ
    CONSEQUENCE_FACTS = "consequence_facts"  # How many facts differ
    CHARACTER_ARCS = "character_arcs"  # How different are character growth arcs
    PRESSURE_TRAJECTORY = "pressure_trajectory"  # How different is pressure over time
    DIALOGUE_CONTENT = "dialogue_content"  # How much dialogue differs
    ENDING_STATE = "ending_state"  # How different is final state


@dataclass
class DivergenceScore:
    """Quantified divergence between two paths."""
    metric: DivergenceMetric
    percentage: float  # 0-100
    detail: Dict[str, Any]  # Metric-specific details

    def __repr__(self) -> str:
        return f"Divergence({self.metric.value}: {self.percentage:.1f}%)"


class OutcomeDivergence:
    """Measures and tracks outcome divergence between branch paths."""

    def __init__(self):
        self.divergence_scores: Dict[str, List[DivergenceScore]] = {}  # pair_id -> scores

    def measure_decision_divergence(self, decisions_a: List[str], decisions_b: List[str]) -> DivergenceScore:
        """Measure divergence based on decision choices."""
        if not decisions_a or not decisions_b:
            return DivergenceScore(DivergenceMetric.DECISION_POINTS, 0.0, {})

        # decisions are formatted as "decision_id:option_id"
        identical = sum(1 for a, b in zip(decisions_a, decisions_b) if a == b)
        total = max(len(decisions_a), len(decisions_b))

        if total == 0:
            percentage = 0.0
        else:
            percentage = ((total - identical) / total) * 100.0

        return DivergenceScore(
            DivergenceMetric.DECISION_POINTS,
            percentage,
            {
                'identical_decisions': identical,
                'divergent_decisions': total - identical,
                'total_decisions': total,
            }
        )

    def measure_consequence_divergence(self, facts_a: Set[str], facts_b: Set[str]) -> DivergenceScore:
        """Measure divergence based on visible consequences."""
        union = facts_a | facts_b
        intersection = facts_a & facts_b

        if not union:
            return DivergenceScore(DivergenceMetric.CONSEQUENCE_FACTS, 0.0, {})

        shared = len(intersection)
        unique_a = len(facts_a - facts_b)
        unique_b = len(facts_b - facts_a)
        unique_total = unique_a + unique_b

        percentage = (unique_total / len(union)) * 100.0

        return DivergenceScore(
            DivergenceMetric.CONSEQUENCE_FACTS,
            percentage,
            {
                'shared_facts': shared,
                'unique_to_a': unique_a,
                'unique_to_b': unique_b,
                'total_union': len(union),
            }
        )

    def measure_pressure_divergence(self, pressure_trajectory_a: List[float],
                                   pressure_trajectory_b: List[float]) -> DivergenceScore:
        """Measure divergence in pressure curves."""
        if not pressure_trajectory_a or not pressure_trajectory_b:
            return DivergenceScore(DivergenceMetric.PRESSURE_TRAJECTORY, 0.0, {})

        # Calculate average difference in pressure across trajectory
        min_len = min(len(pressure_trajectory_a), len(pressure_trajectory_b))
        differences = [abs(a - b) for a, b in zip(pressure_trajectory_a[:min_len], pressure_trajectory_b[:min_len])]

        avg_diff = sum(differences) / len(differences) if differences else 0.0
        max_pressure = max(max(pressure_trajectory_a), max(pressure_trajectory_b))

        if max_pressure == 0:
            percentage = 0.0
        else:
            percentage = (avg_diff / max_pressure) * 100.0

        return DivergenceScore(
            DivergenceMetric.PRESSURE_TRAJECTORY,
            percentage,
            {
                'avg_pressure_difference': avg_diff,
                'max_pressure': max_pressure,
                'turns_compared': min_len,
            }
        )

    def measure_ending_divergence(self, ending_a: Dict[str, Any], ending_b: Dict[str, Any]) -> DivergenceScore:
        """Measure divergence in final states."""
        # Simple approach: check key differences in ending state
        keys = set(ending_a.keys()) | set(ending_b.keys())
        differences = 0

        for key in keys:
            if ending_a.get(key) != ending_b.get(key):
                differences += 1

        percentage = (differences / len(keys)) * 100.0 if keys else 0.0

        return DivergenceScore(
            DivergenceMetric.ENDING_STATE,
            percentage,
            {
                'different_fields': differences,
                'total_fields': len(keys),
                'ending_a': ending_a,
                'ending_b': ending_b,
            }
        )

    def calculate_overall_divergence(self, scores: List[DivergenceScore]) -> float:
        """Calculate weighted average divergence."""
        if not scores:
            return 0.0

        weights = {
            DivergenceMetric.DECISION_POINTS: 0.25,
            DivergenceMetric.CONSEQUENCE_FACTS: 0.35,
            DivergenceMetric.PRESSURE_TRAJECTORY: 0.15,
            DivergenceMetric.ENDING_STATE: 0.25,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for score in scores:
            weight = weights.get(score.metric, 0.2)
            weighted_sum += score.percentage * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def store_divergence(self, pair_id: str, scores: List[DivergenceScore]) -> None:
        """Store divergence measurement for a path pair."""
        self.divergence_scores[pair_id] = scores

    def get_divergence_report(self, pair_id: str) -> Dict[str, Any]:
        """Get complete divergence report for a path pair."""
        scores = self.divergence_scores.get(pair_id, [])

        if not scores:
            return {'error': 'No divergence data found'}

        overall = self.calculate_overall_divergence(scores)

        return {
            'pair_id': pair_id,
            'overall_divergence_percentage': overall,
            'metric_scores': [asdict(s) for s in scores],
            'divergence_assessment': self._assess_divergence(overall),
        }

    @staticmethod
    def _assess_divergence(percentage: float) -> str:
        """Qualitative assessment of divergence percentage."""
        if percentage < 20:
            return "minimal (paths very similar)"
        elif percentage < 40:
            return "low (paths mostly aligned)"
        elif percentage < 60:
            return "moderate (paths noticeably different)"
        elif percentage < 80:
            return "high (paths significantly divergent)"
        else:
            return "very_high (paths almost completely different)"
