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
            },
            "runtime_turn_system": {
                "id": "runtime_turn_system",
                "template": """You are the World of Shadows runtime turn model. Generate actor behavior first, prose projection second.

PRIMARY TASK — Actor Realization:
Your job is to determine and output:
1. **Who responds in this turn** (primary_responder_id)
2. **What they say** (spoken_lines with speaker_id and text)
3. **What they do** (action_lines with actor_id and physical action)
4. **Who else reacts** (secondary_responder_ids, initiative_events for interruptions/escalations)
5. **What pressure/state changes** (state_effects capturing social/emotional/scene shifts)

SECONDARY OUTPUT — Prose Narration:
After actor lanes are complete, synthesize narration_summary: a prose narrative that projects the actor choices you made above. Narration is a view of actor realization, not the source of truth.

MECHANICS:
- spoken_lines entries MUST have speaker_id (the actor whose words these are)
- action_lines entries MUST have actor_id (the actor performing the action)
- initiative_events capture turn seizure/loss/escalation/deflection between actors
- state_effects document what world-state changes result from actor choices
- narration_summary describes what happened (derived from actor output above)
- narrative_response MUST be a copy of narration_summary only

Return valid JSON. Prioritize actor lanes over prose beauty.""",
                "description": "System prompt for World of Shadows runtime turn generation.",
                "variables": []
            },
            "runtime_turn_human": {
                "id": "runtime_turn_human",
                "template": """{full_context}{correction_block}ACTOR REALIZATION TASK:
1. Identify the primary responder (the actor who responds to this move/input).
2. Determine what they say (if speech is present: populate spoken_lines with speaker_id).
3. Determine what they do (if physical action: populate action_lines with actor_id).
4. Capture secondary reactions (secondary_responder_ids and initiative_events if others respond/interrupt/escalate).
5. Identify state changes (state_effects for pressure shifts, relationship changes, scene shifts).

PROSE PROJECTION:
After completing actor realization above, write narration_summary that expresses the scene from the actor choices you determined. Think of this as a narrative view of the actor output, not a separate prose invention. Narration should be grounded in actor behavior.

COHERENCE CHECK:
- Does narration_summary reflect the actor choices (responder, spoken/action lines, initiative)?
- Does it avoid inventing actors or dialogue not in the actor lanes?
- Does it ground state_effects in visible narrative consequence?

COPY INSTRUCTION:
Copy narration_summary content exactly to narrative_response (no separate prose).

Format instructions:
{format_instructions}""",
                "description": "Human message template for World of Shadows runtime turn generation.",
                "variables": ["full_context", "correction_block", "format_instructions"]
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

    def get_prompt_for_profile(self, name: str, profile: Any) -> Dict[str, Any]:
        """Get prompt adjusted for operational profile.

        For now, returns base prompt. In future, can vary based on
        profile.difficulty, profile.complexity, etc.

        Args:
            name: Prompt name
            profile: Operational profile with difficulty/complexity attributes

        Returns:
            Deep copy of prompt (possibly adjusted for profile)
        """
        # Get base prompt
        prompt = self.get_prompt(name)

        # For MVP: return base prompt for all difficulty levels
        # Future: adjust prompt verbosity/depth based on profile
        # - difficulty="easy": more guidance, simpler language
        # - difficulty="hard": less guidance, complex scenarios
        # - complexity="simple": shorter templates
        # - complexity="complex": detailed templates

        return prompt

    def list_prompts_for_profile(self, profile: Any) -> List[str]:
        """List prompts available for an operational profile.

        Args:
            profile: Operational profile

        Returns:
            List of available prompt names for this profile
        """
        # For MVP: all prompts available for all profiles
        return self.list_prompts()

    def get_runtime_turn_template(self):
        """Get ChatPromptTemplate for World of Shadows runtime turn generation.

        Returns:
            ChatPromptTemplate with system and human messages from catalog

        Raises:
            ImportError: If langchain_core not available
            KeyError: If runtime turn prompts not in catalog
        """
        from langchain_core.prompts import ChatPromptTemplate

        system_prompt = self.get_prompt("runtime_turn_system")["template"]
        human_prompt = self.get_prompt("runtime_turn_human")["template"]

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )
