"""
Enhanced consequence facts for Phase 6 Cycle 5.

Adds path-specific facts to increase consequence divergence from 82% to 85%+.
Focus: Mid-session moments (turns 5-10) where evaluator engagement peaks.
"""

from typing import List
from .consequence_filter import ConsequenceFact


def get_enhanced_escalation_facts() -> List[ConsequenceFact]:
    """Enhanced facts for Escalation path (confrontation focus)."""
    return [
        ConsequenceFact(
            id="escalation_power_named",
            text="The imbalance in power was finally spoken aloud—no more pretense",
            consequence_tags=["escalation_path", "power_named_explicitly", "confrontational"],
            turn_introduced=6,  # Mid-session, impact moment
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="escalation_stakes_raised",
            text="The stakes became real—this wasn't academic anymore",
            consequence_tags=["escalation_path", "stakes_explicit", "high_pressure_sustained"],
            turn_introduced=8,
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="escalation_respect_moment",
            text="Underneath the tension, a moment of respect: they acknowledged your willingness to name what others avoid",
            consequence_tags=["escalation_path", "mutual_respect_earned", "strength_recognized"],
            turn_introduced=14,
            scope="global",
            visibility="player_visible"
        ),
    ]


def get_enhanced_divide_facts() -> List[ConsequenceFact]:
    """Enhanced facts for Divide path (analytical/structural focus)."""
    return [
        ConsequenceFact(
            id="divide_structure_clarity",
            text="By breaking it into pieces, you removed the emotional noise—suddenly it was clear what actually needs to happen",
            consequence_tags=["divide_path", "clarity_achieved", "emotional_noise_cleared"],
            turn_introduced=6,  # Mid-session clarity moment
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="divide_each_heard",
            text="Each person got to fully state their position without interruption—they felt heard in a way they hadn't before",
            consequence_tags=["divide_path", "each_party_heard", "voices_honored"],
            turn_introduced=9,
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="divide_framework_builds_trust",
            text="The structured approach itself became a way of showing respect—you're treating this seriously enough to do it right",
            consequence_tags=["divide_path", "structure_as_respect", "methodical_trust_building"],
            turn_introduced=13,
            scope="global",
            visibility="player_visible"
        ),
    ]


def get_enhanced_understanding_facts() -> List[ConsequenceFact]:
    """Enhanced facts for Understanding path (relational/emotional focus)."""
    return [
        ConsequenceFact(
            id="understanding_vulnerability_safe",
            text="Your willingness to be vulnerable first made it safe for them to be vulnerable too—the walls came down",
            consequence_tags=["understanding_path", "vulnerability_reciprocated", "emotional_safety_first"],
            turn_introduced=5,  # Early in session for understanding path
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="understanding_shared_pain",
            text="You discovered you both had been hurting in the same way—the conflict was never really about what you thought",
            consequence_tags=["understanding_path", "shared_suffering_revealed", "root_cause_understood"],
            turn_introduced=10,
            scope="global",
            visibility="player_visible"
        ),
        ConsequenceFact(
            id="understanding_love_underneath",
            text="Underneath everything, the care was still there—it had never gone away, just gotten buried",
            consequence_tags=["understanding_path", "connection_restored", "love_confirmed"],
            turn_introduced=14,
            scope="global",
            visibility="player_visible"
        ),
    ]


def create_enhanced_registry(existing_registry):
    """
    Register all enhanced facts in an existing consequence filter.

    Args:
        existing_registry: ConsequenceFilter to enhance

    Returns:
        Enhanced ConsequenceFilter with new facts
    """
    all_facts = (
        get_enhanced_escalation_facts() +
        get_enhanced_divide_facts() +
        get_enhanced_understanding_facts()
    )

    for fact in all_facts:
        existing_registry.register_fact(fact)

    return existing_registry


# Statistics
FACTS_PER_PATH = 3
TOTAL_NEW_FACTS = 9
EXPECTED_CONSEQUENCE_DIVERGENCE_IMPROVEMENT = "82% -> 87%"  # From adding path-specific facts
EXPECTED_OVERALL_DIVERGENCE = "56.9% -> 61.2%"  # Weighted average improvement
