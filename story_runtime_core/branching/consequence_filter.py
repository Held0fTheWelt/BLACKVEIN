"""
Consequence filtering - ensures only path-relevant facts are visible to player.
"""

from dataclasses import dataclass
from typing import List, Set, Dict, Any, Optional


@dataclass
class ConsequenceFact:
    """A single consequence/fact in the narrative."""
    id: str
    text: str
    consequence_tags: List[str]  # Tags determining which paths see this fact
    turn_introduced: int
    scope: str  # "local" (one character) or "global" (whole scene)
    visibility: str  # "player_visible", "operator_only", "internal"

    def applies_to_path(self, active_tags: Set[str]) -> bool:
        """Check if this fact applies to a path (all its tags must be present)."""
        if not self.consequence_tags:
            return True  # No tags = applies everywhere
        return all(tag in active_tags for tag in self.consequence_tags)


class ConsequenceFilter:
    """Filters consequences based on player's branch path."""

    def __init__(self):
        self.all_facts: Dict[str, ConsequenceFact] = {}  # fact_id -> ConsequenceFact
        self.facts_by_turn: Dict[int, List[ConsequenceFact]] = {}  # turn -> list of facts

    def register_fact(self, fact: ConsequenceFact) -> bool:
        """Register a consequence fact."""
        if not fact.id or not fact.text:
            return False

        self.all_facts[fact.id] = fact

        if fact.turn_introduced not in self.facts_by_turn:
            self.facts_by_turn[fact.turn_introduced] = []
        self.facts_by_turn[fact.turn_introduced].append(fact)
        return True

    def get_visible_facts(self, active_tags: Set[str], max_turn: Optional[int] = None,
                         visibility_filter: Optional[str] = None) -> List[ConsequenceFact]:
        """Get all visible facts for a path up to given turn."""
        visible = []

        for fact in self.all_facts.values():
            # Check turn bound
            if max_turn is not None and fact.turn_introduced > max_turn:
                continue

            # Check visibility filter
            if visibility_filter and fact.visibility != visibility_filter:
                continue

            # Check if fact applies to this path
            if fact.applies_to_path(active_tags):
                visible.append(fact)

        return sorted(visible, key=lambda f: f.turn_introduced)

    def get_facts_by_turn(self, turn: int, active_tags: Set[str]) -> List[ConsequenceFact]:
        """Get facts introduced at specific turn that apply to path."""
        if turn not in self.facts_by_turn:
            return []

        return [f for f in self.facts_by_turn[turn] if f.applies_to_path(active_tags)]

    def get_path_divergent_facts(self, active_tags_a: Set[str], active_tags_b: Set[str]) -> Dict[str, List[ConsequenceFact]]:
        """Get facts that differ between two paths."""
        facts_a = self.get_visible_facts(active_tags_a)
        facts_b = self.get_visible_facts(active_tags_b)

        facts_a_ids = {f.id for f in facts_a}
        facts_b_ids = {f.id for f in facts_b}

        unique_to_a = [f for f in facts_a if f.id not in facts_b_ids]
        unique_to_b = [f for f in facts_b if f.id not in facts_a_ids]

        return {
            'unique_to_a': unique_to_a,
            'unique_to_b': unique_to_b,
            'shared': [f for f in facts_a if f.id in facts_b_ids],
        }

    def calculate_divergence_percentage(self, active_tags_a: Set[str], active_tags_b: Set[str]) -> float:
        """Calculate percentage of facts that differ between paths (0-100)."""
        facts_a = self.get_visible_facts(active_tags_a)
        facts_b = self.get_visible_facts(active_tags_b)

        if not facts_a or not facts_b:
            return 0.0

        facts_a_ids = {f.id for f in facts_a}
        facts_b_ids = {f.id for f in facts_b}

        total_unique = len(facts_a_ids ^ facts_b_ids)  # Symmetric difference
        total_facts = len(facts_a_ids | facts_b_ids)  # Union

        if total_facts == 0:
            return 0.0

        return (total_unique / total_facts) * 100.0

    def filter_turn_output(self, turn_result: Dict[str, Any], active_tags: Set[str]) -> Dict[str, Any]:
        """Filter a turn's output to only include path-relevant facts."""
        if 'consequences' not in turn_result or not isinstance(turn_result['consequences'], list):
            return turn_result

        filtered_consequences = []
        for consequence in turn_result['consequences']:
            if isinstance(consequence, str):
                # Simple string consequence - pass through
                filtered_consequences.append(consequence)
            elif isinstance(consequence, dict):
                # Consequence dict with tags
                tags = set(consequence.get('tags', []))
                if not tags or all(tag in active_tags for tag in tags):
                    filtered_consequences.append(consequence)

        result = turn_result.copy()
        result['consequences'] = filtered_consequences
        return result
