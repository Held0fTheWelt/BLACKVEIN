"""
Path state tracking - maintains which branch a player is on throughout a session.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set
import json
from datetime import datetime


@dataclass
class PathNode:
    """A single decision node in a player's branch path."""
    turn_number: int
    decision_point_id: str
    chosen_option_id: str
    consequence_tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PathState:
    """Complete branch path state for a session."""
    session_id: str
    scenario_id: str
    path_nodes: List[PathNode] = field(default_factory=list)
    current_turn: int = 0
    active_consequence_tags: Set[str] = field(default_factory=set)
    path_hash: Optional[str] = None  # Hash for quick path comparison

    def add_decision(self, turn: int, decision_id: str, option_id: str, consequence_tags: List[str]) -> None:
        """Record a decision made by player."""
        node = PathNode(
            turn_number=turn,
            decision_point_id=decision_id,
            chosen_option_id=option_id,
            consequence_tags=consequence_tags,
        )
        self.path_nodes.append(node)
        self.active_consequence_tags.update(consequence_tags)
        self._update_hash()

    def get_decision_at_turn(self, turn: int) -> Optional[PathNode]:
        """Retrieve decision made at specific turn."""
        for node in self.path_nodes:
            if node.turn_number == turn:
                return node
        return None

    def get_all_decisions(self) -> List[PathNode]:
        """Get complete decision sequence."""
        return sorted(self.path_nodes, key=lambda n: n.turn_number)

    def is_on_path(self, consequence_tag: str) -> bool:
        """Check if consequence tag applies to this path."""
        return consequence_tag in self.active_consequence_tags

    def get_path_signature(self) -> str:
        """Get unique signature for this path (for divergence comparison)."""
        if self.path_hash:
            return self.path_hash

        decisions = [f"{n.decision_point_id}:{n.chosen_option_id}" for n in self.get_all_decisions()]
        import hashlib
        sig = hashlib.sha256('|'.join(decisions).encode()).hexdigest()[:16]
        return sig

    def _update_hash(self) -> None:
        """Update path hash after decisions change."""
        decisions = [f"{n.decision_point_id}:{n.chosen_option_id}" for n in self.get_all_decisions()]
        import hashlib
        self.path_hash = hashlib.sha256('|'.join(decisions).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        """Serialize to dict."""
        return {
            'session_id': self.session_id,
            'scenario_id': self.scenario_id,
            'path_nodes': [n.to_dict() for n in self.path_nodes],
            'current_turn': self.current_turn,
            'active_consequence_tags': list(self.active_consequence_tags),
            'path_hash': self.path_hash,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PathState':
        """Deserialize from dict."""
        path_nodes = [PathNode(**node) for node in data.get('path_nodes', [])]
        return cls(
            session_id=data['session_id'],
            scenario_id=data['scenario_id'],
            path_nodes=path_nodes,
            current_turn=data.get('current_turn', 0),
            active_consequence_tags=set(data.get('active_consequence_tags', [])),
            path_hash=data.get('path_hash'),
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'PathState':
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))


class PathStateManager:
    """Manages path state for multiple concurrent sessions."""

    def __init__(self):
        self.paths: Dict[str, PathState] = {}  # session_id -> PathState

    def create_path(self, session_id: str, scenario_id: str) -> PathState:
        """Create new path state for session."""
        path = PathState(session_id=session_id, scenario_id=scenario_id)
        self.paths[session_id] = path
        return path

    def get_path(self, session_id: str) -> Optional[PathState]:
        """Retrieve path state for session."""
        return self.paths.get(session_id)

    def record_decision(self, session_id: str, turn: int, decision_id: str,
                       option_id: str, consequence_tags: List[str]) -> bool:
        """Record a decision for a session."""
        path = self.paths.get(session_id)
        if not path:
            return False
        path.add_decision(turn, decision_id, option_id, consequence_tags)
        path.current_turn = turn
        return True

    def get_consequence_tags(self, session_id: str) -> Set[str]:
        """Get all active consequence tags for a session."""
        path = self.paths.get(session_id)
        return path.active_consequence_tags if path else set()

    def is_consequence_active(self, session_id: str, tag: str) -> bool:
        """Check if consequence applies to session's path."""
        path = self.paths.get(session_id)
        return path.is_on_path(tag) if path else False

    def compare_paths(self, session_id_a: str, session_id_b: str) -> Dict:
        """Compare two paths for divergence."""
        path_a = self.paths.get(session_id_a)
        path_b = self.paths.get(session_id_b)

        if not path_a or not path_b:
            return {'error': 'Path not found'}

        decisions_a = path_a.get_all_decisions()
        decisions_b = path_b.get_all_decisions()

        divergence_points = []
        for node_a, node_b in zip(decisions_a, decisions_b):
            if node_a.chosen_option_id != node_b.chosen_option_id:
                divergence_points.append({
                    'turn': node_a.turn_number,
                    'decision_id': node_a.decision_point_id,
                    'option_a': node_a.chosen_option_id,
                    'option_b': node_b.chosen_option_id,
                })

        divergent_tags_a = path_a.active_consequence_tags - path_b.active_consequence_tags
        divergent_tags_b = path_b.active_consequence_tags - path_a.active_consequence_tags

        return {
            'divergence_points': divergence_points,
            'unique_tags_a': list(divergent_tags_a),
            'unique_tags_b': list(divergent_tags_b),
            'total_divergence': len(divergence_points),
        }

    def remove_path(self, session_id: str) -> bool:
        """Clean up path state when session ends."""
        if session_id in self.paths:
            del self.paths[session_id]
            return True
        return False
