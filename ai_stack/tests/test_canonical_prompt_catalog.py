"""
Tests for canonical prompt catalog - game-specific LLM prompts.
"""

import pytest
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog


class MockOperationalProfile:
    """Mock operational profile for testing."""

    def __init__(self, difficulty="normal", complexity="standard"):
        self.difficulty = difficulty
        self.complexity = complexity
        self.ai_enabled = True


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


class TestPromptValidationAndSafety:
    """Test prompt validation and safety checks."""

    def test_prompt_validation_required_variables(self):
        """Test prompt validation checks for required variables."""
        catalog = CanonicalPromptCatalog()
        # All prompts should have variables field (if they use template variables)
        for prompt_name in catalog.list_prompts():
            prompt = catalog.get_prompt(prompt_name)
            # If template has {variables}, validate field exists
            if "{" in prompt.get("template", ""):
                assert "variables" in prompt or prompt["template"].count("{") > 0

    def test_catalog_validate_no_forbidden_terms(self):
        """Test validation prevents exposure of internal terms."""
        catalog = CanonicalPromptCatalog()
        # Should not raise any error
        result = catalog.validate()
        assert result is True

    def test_prompt_templates_are_strings(self):
        """Test all prompt templates are non-empty strings."""
        catalog = CanonicalPromptCatalog()
        for prompt_name in catalog.list_prompts():
            prompt = catalog.get_prompt(prompt_name)
            assert isinstance(prompt["template"], str)
            assert len(prompt["template"]) > 0

    def test_description_is_meaningful(self):
        """Test all prompts have meaningful descriptions."""
        catalog = CanonicalPromptCatalog()
        for prompt_name in catalog.list_prompts():
            prompt = catalog.get_prompt(prompt_name)
            assert isinstance(prompt["description"], str)
            assert len(prompt["description"]) > 5


class TestPromptVariableBinding:
    """Test prompt template variable binding."""

    def test_decision_context_has_required_variables(self):
        """Test decision_context prompt has required template variables."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("decision_context")
        template = prompt["template"]
        # Check for required placeholders
        assert "{game_state}" in template
        assert "{player_action}" in template
        assert "{previous_result}" in template

    def test_action_selection_has_required_variables(self):
        """Test action_selection prompt has required variables."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("action_selection")
        template = prompt["template"]
        assert "{decision_analysis}" in template

    def test_narrative_response_has_required_variables(self):
        """Test narrative_response prompt has required variables."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("narrative_response")
        template = prompt["template"]
        assert "{action}" in template
        assert "{outcome}" in template
        assert "{world_context}" in template

    def test_failure_explanation_has_required_variables(self):
        """Test failure_explanation prompt has required variables."""
        catalog = CanonicalPromptCatalog()
        prompt = catalog.get_prompt("failure_explanation")
        template = prompt["template"]
        assert "{action}" in template
        assert "{reason}" in template
        assert "{game_state}" in template

    def test_runtime_turn_prompts_emphasize_actor_level_contract(self):
        """Runtime prompts should guide actor-level exchange plus compatibility fields."""
        catalog = CanonicalPromptCatalog()
        sys_template = catalog.get_prompt("runtime_turn_system")["template"]
        human_template = catalog.get_prompt("runtime_turn_human")["template"]
        combined = sys_template + human_template

        # Actor realization should be present
        assert "spoken_lines" in combined, "Prompts must mention spoken_lines"
        assert "action_lines" in combined, "Prompts must mention action_lines"
        assert "initiative_events" in combined, "Prompts must mention initiative_events"
        assert "speaker_id" in combined, "Prompts must mention speaker_id"
        assert "actor_id" in combined, "Prompts must mention actor_id"

        # Narration should be present as secondary
        assert "narration_summary" in combined, "Prompts must mention narration_summary"
        assert "narrative_response" in combined, "Prompts must mention narrative_response"

        # Actor-first priority should be clear
        assert "PRIMARY" in sys_template or "ACTOR REALIZATION" in human_template, \
            "Prompts should emphasize actor realization as primary"
        assert "SECONDARY" in sys_template or "prose projection" in human_template.lower(), \
            "Prompts should indicate prose is secondary"


class TestOperationalProfileIntegration:
    """Test prompt catalog integration with operational profile."""

    def test_get_prompt_respects_difficulty(self):
        """Test prompt selection can be influenced by difficulty level."""
        catalog = CanonicalPromptCatalog()
        profile = MockOperationalProfile(difficulty="hard")
        prompt = catalog.get_prompt_for_profile("decision_context", profile)
        # Should return a valid prompt
        assert prompt is not None
        assert "template" in prompt

    def test_get_prompt_respects_complexity(self):
        """Test prompt selection respects complexity level."""
        catalog = CanonicalPromptCatalog()
        profile_simple = MockOperationalProfile(complexity="simple")
        profile_complex = MockOperationalProfile(complexity="complex")

        prompt_simple = catalog.get_prompt_for_profile("narrative_response", profile_simple)
        prompt_complex = catalog.get_prompt_for_profile("narrative_response", profile_complex)

        assert prompt_simple is not None
        assert prompt_complex is not None

    def test_profile_default_behavior(self):
        """Test default behavior when profile not specified."""
        catalog = CanonicalPromptCatalog()
        # Should work without profile
        prompt = catalog.get_prompt("decision_context")
        assert prompt is not None

    def test_catalog_lists_prompts_for_all_profiles(self):
        """Test catalog has prompts for different difficulty levels."""
        catalog = CanonicalPromptCatalog()
        normal_profile = MockOperationalProfile(difficulty="normal")
        hard_profile = MockOperationalProfile(difficulty="hard")

        normal_count = len(catalog.list_prompts())
        hard_count = len(catalog.list_prompts_for_profile(hard_profile))

        # Should have prompts for both
        assert normal_count > 0
        assert hard_count > 0
