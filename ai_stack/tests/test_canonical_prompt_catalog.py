"""
Tests for canonical prompt catalog - game-specific LLM prompts.
"""

import pytest
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog


class TestCanonicalPromptCatalogStructure:
    """Test catalog loads and validates prompt structure."""

    def test_catalog_initializes(self):
        """Test catalog can be initialized."""
        catalog = CanonicalPromptCatalog()
        assert catalog is not None

    def test_catalog_loads_game_specific_prompts(self):
        """Test catalog loads game-specific prompts."""
        catalog = CanonicalPromptCatalog()
        prompts = catalog.list_prompts()
        assert len(prompts) > 0
        assert "decision_context" in prompts
        assert "action_selection" in prompts
        assert "narrative_response" in prompts
        assert "failure_explanation" in prompts

    def test_prompts_have_required_fields(self):
        """Test each prompt has required fields: id, template, description."""
        catalog = CanonicalPromptCatalog()
        for prompt_name in catalog.list_prompts():
            prompt = catalog.get_prompt(prompt_name)
            assert "id" in prompt
            assert "template" in prompt
            assert "description" in prompt
            assert prompt["id"] == prompt_name
            assert isinstance(prompt["template"], str)
            assert len(prompt["template"]) > 0
            assert isinstance(prompt["description"], str)

    def test_get_prompt_by_name(self):
        """Test getting individual prompts by name."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("decision_context")
        assert prompt is not None
        assert prompt["id"] == "decision_context"

    def test_get_nonexistent_prompt_raises_error(self):
        """Test getting nonexistent prompt raises KeyError."""
        catalog = CanonicalPromptCatalog()
        with pytest.raises(KeyError):
            catalog.get_prompt("nonexistent_prompt")

    def test_prompts_are_immutable_after_load(self):
        """Test prompts cannot be modified after load."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("decision_context")
        # Attempt to modify should fail or not affect catalog
        original_template = prompt.get("template", "")
        prompt["template"] = "MODIFIED"
        # Re-fetch should return original
        prompt2 = catalog.get_prompt("decision_context")
        assert prompt2["template"] == original_template

    def test_catalog_validate(self):
        """Test catalog validation."""
        catalog = CanonicalPromptCatalog()
        result = catalog.validate()
        assert result is True or isinstance(result, dict)
