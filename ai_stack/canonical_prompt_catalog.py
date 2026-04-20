"""
Canonical prompt catalog - game-specific LLM prompts for AI-driven gameplay.

This module provides immutable, validated prompts for LangGraph nodes to use
when reasoning about game state and generating narrative responses.
"""

from typing import Dict, List, Any
from copy import deepcopy


class CanonicalPromptCatalog:
    """Manages canonical prompts for game decision-making and narrative generation.

    Prompts are immutable after load and validated for required structure.
    Each prompt contains: id, template, description, and optional variables.
    """

    def __init__(self):
        """Initialize catalog with game-specific prompts."""
        self._prompts = self._initialize_prompts()
        self._validated = False

    def _initialize_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all game-specific prompts.

        Returns:
            Dictionary mapping prompt names to prompt definitions.
        """
        return {
            "decision_context": {
                "id": "decision_context",
                "template": """You are an AI agent in a game world. Analyze the current game state and the player's queued action.

Current Game State:
{game_state}

Player's Queued Action:
{player_action}

Previous Turn Result:
{previous_result}

Generate a list of 3-5 possible narrative interpretations or outcomes for this action, considering:
1. The game world's rules and physics
2. The player's current abilities and status
3. The narrative consequences
4. Failure modes if applicable

Respond with a structured analysis of possible action outcomes.""",
                "description": "Analyze game state and player action to generate decision context.",
                "variables": ["game_state", "player_action", "previous_result"]
            },
            "action_selection": {
                "id": "action_selection",
                "template": """Based on the decision analysis below, select the single best action outcome for the player.

Decision Analysis:
{decision_analysis}

Consider:
1. Narrative coherence with game world
2. Player intention (what they tried to do)
3. Game rules and balance
4. Fairness and fun factor

Respond with:
- Selected Outcome: [brief description]
- Reason: [1-2 sentences explaining why]
- Narrative Impact: [how this affects game state]""",
                "description": "Select the best action outcome from decision analysis.",
                "variables": ["decision_analysis"]
            },
            "narrative_response": {
                "id": "narrative_response",
                "template": """Generate a short, engaging narrative response to the player's action.

Action Taken: {action}
Outcome: {outcome}
Game World Context: {world_context}

Write 2-3 sentences that:
1. Describe what happened in vivid, game-appropriate language
2. Show consequences of the action
3. Set up the next player choice

Keep it concise and immersive.""",
                "description": "Generate narrative text describing action outcome to player.",
                "variables": ["action", "outcome", "world_context"]
            },
            "failure_explanation": {
                "id": "failure_explanation",
                "template": """The player's action failed. Explain why in narrative terms.

Action Attempted: {action}
Failure Reason: {reason}
Game State: {game_state}

Respond with 1-2 sentences that:
1. Explain in-world why the action failed
2. Preserve player agency (not "you are too weak")
3. Hint at alternative approaches if applicable

Tone: helpful, not punitive.""",
                "description": "Explain action failure in engaging, non-punitive narrative.",
                "variables": ["action", "reason", "game_state"]
            }
        }

    def get_prompt(self, name: str) -> Dict[str, Any]:
        """Get a prompt by name.

        Args:
            name: Prompt name (e.g., 'decision_context')

        Returns:
            Deep copy of prompt definition (immutable)

        Raises:
            KeyError: If prompt not found
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not found in catalog")
        # Return deep copy to ensure immutability
        return deepcopy(self._prompts[name])

    def list_prompts(self) -> List[str]:
        """List all available prompt names.

        Returns:
            List of prompt names.
        """
        return list(self._prompts.keys())

    def validate(self) -> bool:
        """Validate catalog structure and safety.

        Returns:
            True if valid, raises ValueError if invalid.

        Raises:
            ValueError: If any prompt is invalid.
        """
        required_fields = {"id", "template", "description"}

        for name, prompt in self._prompts.items():
            # Check required fields
            if not all(field in prompt for field in required_fields):
                raise ValueError(
                    f"Prompt '{name}' missing required fields. "
                    f"Has: {set(prompt.keys())}, needs: {required_fields}"
                )

            # Check template is non-empty
            if not isinstance(prompt["template"], str) or len(prompt["template"]) == 0:
                raise ValueError(f"Prompt '{name}' has empty or non-string template")

            # Check id matches name
            if prompt["id"] != name:
                raise ValueError(
                    f"Prompt id mismatch: name='{name}', id='{prompt['id']}'"
                )

            # Check no sensitive internals exposed
            forbidden_terms = ["SessionService", "database", "secret", "password"]
            template_lower = prompt["template"].lower()
            for term in forbidden_terms:
                if term.lower() in template_lower:
                    raise ValueError(
                        f"Prompt '{name}' contains forbidden term '{term}' "
                        f"that may expose internals"
                    )

        self._validated = True
        return True
