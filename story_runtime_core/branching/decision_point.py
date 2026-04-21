"""
Decision point registry and management for branching scenarios.

A DecisionPoint represents a moment in a turn sequence where player choice diverges into distinct paths.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class DecisionPointType(Enum):
    """Types of decision points in narrative flow."""
    APPROACH = "approach"  # How player responds to situation (e.g., escalate vs de-escalate)
    STRATEGY = "strategy"  # Which tactic to use (e.g., seek help vs handle alone)
    ALIGNMENT = "alignment"  # Which alliance/side to take
    FOCUS = "focus"  # What to focus on (e.g., one character vs group)
    CLOSURE = "closure"  # How to resolve (acceptance vs denial)


@dataclass
class DecisionOption:
    """A single choice at a decision point."""
    id: str  # Unique identifier for this option
    label: str  # Human-readable label
    description: str  # What choosing this means
    consequence_tags: List[str] = field(default_factory=list)  # Tags for consequence filtering
    pressure_delta: Dict[str, int] = field(default_factory=dict)  # How pressure changes
    character_response_template: Optional[str] = None  # How characters might respond


@dataclass
class DecisionPoint:
    """A point where player choice diverges narrative path."""
    id: str
    turn_number: int
    scenario_id: str
    decision_type: DecisionPointType
    prompt: str  # What player is deciding
    options: List[DecisionOption]
    locked_after_turn: Optional[int] = None  # Turn after which this point can't be changed
    consequence_scope: str = "local"  # "local" (affects current scene) or "global" (affects overall arc)

    def validate(self) -> bool:
        """Verify decision point is well-formed."""
        if not self.id or not self.scenario_id:
            return False
        if not self.options or len(self.options) < 2:
            return False
        if len(self.options) > 5:  # Reasonable limit for complexity
            return False
        for opt in self.options:
            if not opt.id or not opt.label:
                return False
        return True

    def get_option(self, option_id: str) -> Optional[DecisionOption]:
        """Retrieve a specific option by ID."""
        for opt in self.options:
            if opt.id == option_id:
                return opt
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for storage/transmission."""
        return {
            'id': self.id,
            'turn_number': self.turn_number,
            'scenario_id': self.scenario_id,
            'decision_type': self.decision_type.value,
            'prompt': self.prompt,
            'options': [
                {
                    'id': opt.id,
                    'label': opt.label,
                    'description': opt.description,
                    'consequence_tags': opt.consequence_tags,
                    'pressure_delta': opt.pressure_delta,
                }
                for opt in self.options
            ],
            'locked_after_turn': self.locked_after_turn,
            'consequence_scope': self.consequence_scope,
        }


class DecisionPointRegistry:
    """Registry of all decision points across scenarios."""

    def __init__(self):
        self.decisions: Dict[str, List[DecisionPoint]] = {}  # scenario_id -> list of decisions
        self.by_turn: Dict[str, Dict[int, DecisionPoint]] = {}  # scenario_id -> turn -> decision

    def register(self, decision: DecisionPoint) -> bool:
        """Register a decision point."""
        if not decision.validate():
            return False

        scenario_id = decision.scenario_id
        if scenario_id not in self.decisions:
            self.decisions[scenario_id] = []
            self.by_turn[scenario_id] = {}

        self.decisions[scenario_id].append(decision)
        self.by_turn[scenario_id][decision.turn_number] = decision
        return True

    def get_for_scenario(self, scenario_id: str) -> List[DecisionPoint]:
        """Get all decision points for a scenario."""
        return self.decisions.get(scenario_id, [])

    def get_for_turn(self, scenario_id: str, turn_number: int) -> Optional[DecisionPoint]:
        """Get decision point at a specific turn."""
        return self.by_turn.get(scenario_id, {}).get(turn_number)

    def get_all_for_scenario_range(self, scenario_id: str, start_turn: int, end_turn: int) -> List[DecisionPoint]:
        """Get all decision points in a turn range."""
        scenario_turns = self.by_turn.get(scenario_id, {})
        return [
            scenario_turns[t] for t in range(start_turn, end_turn + 1)
            if t in scenario_turns
        ]

    def to_json(self) -> str:
        """Serialize registry to JSON."""
        data = {
            scenario_id: [d.to_dict() for d in decisions]
            for scenario_id, decisions in self.decisions.items()
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'DecisionPointRegistry':
        """Deserialize registry from JSON."""
        registry = cls()
        data = json.loads(json_str)
        for scenario_id, decision_dicts in data.items():
            for d in decision_dicts:
                options = [
                    DecisionOption(
                        id=opt['id'],
                        label=opt['label'],
                        description=opt['description'],
                        consequence_tags=opt.get('consequence_tags', []),
                        pressure_delta=opt.get('pressure_delta', {}),
                    )
                    for opt in d['options']
                ]
                decision = DecisionPoint(
                    id=d['id'],
                    turn_number=d['turn_number'],
                    scenario_id=d['scenario_id'],
                    decision_type=DecisionPointType(d['decision_type']),
                    prompt=d['prompt'],
                    options=options,
                    locked_after_turn=d.get('locked_after_turn'),
                    consequence_scope=d.get('consequence_scope', 'local'),
                )
                registry.register(decision)
        return registry
