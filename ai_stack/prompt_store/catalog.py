"""
Canonical prompt catalog - game-specific LLM prompts for AI-driven gameplay.

This module provides immutable, validated prompts for LangGraph nodes to use
when reasoning about game state and generating narrative responses.
"""

from copy import deepcopy
from typing import Any, Dict, List

from ai_stack.prompt_store import list_prompt_definitions


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
        """Initialize all game-specific prompts from the central prompt store.

        Returns:
            Dictionary mapping prompt names to prompt definitions.
        """
        prompts: Dict[str, Dict[str, Any]] = {}
        for prompt in list_prompt_definitions():
            key = str(prompt.get("prompt_key") or prompt.get("id") or "").strip()
            if not key:
                continue
            prompts[key] = {
                "id": key,
                "template": prompt["template"],
                "description": prompt.get("description", ""),
                "variables": list(prompt.get("variables") or []),
                "name": prompt.get("name") or key,
                "category": prompt.get("category") or "uncategorized",
                "source_path": prompt.get("source_path") or "",
                "source_symbol": prompt.get("source_symbol") or "",
            }
        return prompts

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
