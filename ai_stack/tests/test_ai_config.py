"""
Tests for AI configuration system.

Tests:
- Configuration validation (temperature, tokens)
- Operational profile awareness (easy/normal/hard)
- Configuration loading from environment
- Configuration loading from JSON file
- Configuration serialization
- Default configuration management

Constitutional Laws:
- Law 1: Clarity of truth - explicit configuration validation
- Law 8: Explicit errors - all validation failures clear
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

from ai_stack.ai_config import (
    AIConfig,
    get_default_config,
    set_default_config,
    reset_default_config,
)


class TestAIConfigInitialization:
    """Test basic configuration initialization."""

    def test_config_initializes_with_defaults(self):
        """Test config initializes with default values."""
        config = AIConfig()
        assert config.model == "claude-3.5-sonnet"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.reasoning_depth == "standard"
        assert config.difficulty_mode == "normal"

    def test_config_initializes_with_custom_values(self):
        """Test config initializes with custom values."""
        config = AIConfig(
            model="claude-3-haiku",
            temperature=0.5,
            max_tokens=1024,
            reasoning_depth="shallow"
        )
        assert config.model == "claude-3-haiku"
        assert config.temperature == 0.5
        assert config.max_tokens == 1024
        assert config.reasoning_depth == "shallow"

    def test_config_string_representation(self):
        """Test configuration string representation."""
        config = AIConfig()
        repr_str = repr(config)
        assert "AIConfig" in repr_str
        assert "claude-3.5-sonnet" in repr_str


class TestAIConfigValidation:
    """Test configuration validation (Law 1, 8)."""

    def test_temperature_validation_range(self):
        """Test temperature must be between 0 and 2."""
        # Valid boundaries
        AIConfig(temperature=0.0)
        AIConfig(temperature=1.0)
        AIConfig(temperature=2.0)

        # Invalid - too low
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            AIConfig(temperature=-0.1)

        # Invalid - too high
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            AIConfig(temperature=2.1)

    def test_temperature_validation_type(self):
        """Test temperature must be numeric."""
        with pytest.raises(ValueError, match="temperature must be a number"):
            AIConfig(temperature="high")

    def test_max_tokens_validation_positive(self):
        """Test max_tokens must be positive."""
        AIConfig(max_tokens=1)
        AIConfig(max_tokens=10000)

        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            AIConfig(max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be greater than 0"):
            AIConfig(max_tokens=-100)

    def test_max_tokens_validation_type(self):
        """Test max_tokens must be integer."""
        with pytest.raises(ValueError, match="max_tokens must be an integer"):
            AIConfig(max_tokens=1024.5)

    def test_reasoning_tokens_validation(self):
        """Test max_reasoning_tokens must be positive."""
        AIConfig(max_reasoning_tokens=1)

        with pytest.raises(ValueError, match="max_reasoning_tokens must be greater than 0"):
            AIConfig(max_reasoning_tokens=0)

    def test_response_length_validation(self):
        """Test response length bounds are valid."""
        AIConfig(min_response_length=50, max_response_length=1000)

        with pytest.raises(ValueError, match="max_response_length.*must be >="):
            AIConfig(min_response_length=100, max_response_length=50)

    def test_cache_ttl_validation(self):
        """Test cache TTL must be non-negative."""
        AIConfig(cache_ttl_seconds=0)
        AIConfig(cache_ttl_seconds=3600)

        with pytest.raises(ValueError, match="cache_ttl_seconds must be non-negative"):
            AIConfig(cache_ttl_seconds=-1)


class TestOperationalProfiles:
    """Test operational profile awareness (difficulty modes)."""

    def test_easy_profile(self):
        """Test easy difficulty profile configuration."""
        config = AIConfig.for_difficulty("easy")

        assert config.model == "claude-3-haiku"
        assert config.temperature == 0.5
        assert config.max_tokens == 1024
        assert config.reasoning_depth == "shallow"
        assert config.max_reasoning_tokens == 2048
        assert config.difficulty_mode == "easy"
        assert config.use_extended_context is False

    def test_normal_profile(self):
        """Test normal difficulty profile configuration."""
        config = AIConfig.for_difficulty("normal")

        assert config.model == "claude-3.5-sonnet"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.reasoning_depth == "standard"
        assert config.max_reasoning_tokens == 4096
        assert config.difficulty_mode == "normal"
        assert config.use_extended_context is True

    def test_hard_profile(self):
        """Test hard difficulty profile configuration."""
        config = AIConfig.for_difficulty("hard")

        assert config.model == "claude-3.5-sonnet"
        assert config.temperature == 0.9
        assert config.max_tokens == 3072
        assert config.reasoning_depth == "deep"
        assert config.max_reasoning_tokens == 8000
        assert config.difficulty_mode == "hard"
        assert config.use_extended_context is True

    def test_invalid_difficulty_mode(self):
        """Test invalid difficulty mode raises error."""
        with pytest.raises(ValueError, match="Unknown difficulty mode"):
            AIConfig.for_difficulty("extreme")


class TestEnvironmentLoading:
    """Test configuration loading from environment."""

    def test_load_from_environment_defaults(self):
        """Test loading from environment with no env vars set."""
        # Clear environment
        for key in ["WOS_AI_MODEL", "WOS_AI_TEMPERATURE", "WOS_AI_MAX_TOKENS",
                    "WOS_AI_REASONING_DEPTH", "WOS_AI_DIFFICULTY"]:
            os.environ.pop(key, None)

        config = AIConfig.from_environment()

        assert config.model == "claude-3.5-sonnet"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_load_from_environment_custom_values(self):
        """Test loading from environment with custom values."""
        os.environ["WOS_AI_MODEL"] = "claude-3-haiku"
        os.environ["WOS_AI_TEMPERATURE"] = "0.5"
        os.environ["WOS_AI_MAX_TOKENS"] = "1024"
        os.environ["WOS_AI_REASONING_DEPTH"] = "shallow"
        os.environ["WOS_AI_DIFFICULTY"] = "easy"

        try:
            config = AIConfig.from_environment()

            assert config.model == "claude-3-haiku"
            assert config.temperature == 0.5
            assert config.max_tokens == 1024
            assert config.reasoning_depth == "shallow"
            assert config.difficulty_mode == "easy"

        finally:
            # Clean up
            for key in ["WOS_AI_MODEL", "WOS_AI_TEMPERATURE", "WOS_AI_MAX_TOKENS",
                        "WOS_AI_REASONING_DEPTH", "WOS_AI_DIFFICULTY"]:
                os.environ.pop(key, None)

    def test_load_from_environment_invalid_temperature(self):
        """Test loading from environment with invalid temperature."""
        os.environ["WOS_AI_TEMPERATURE"] = "not_a_number"

        try:
            with pytest.raises(ValueError, match="WOS_AI_TEMPERATURE must be a valid float"):
                AIConfig.from_environment()
        finally:
            os.environ.pop("WOS_AI_TEMPERATURE", None)

    def test_load_from_environment_invalid_max_tokens(self):
        """Test loading from environment with invalid max_tokens."""
        os.environ["WOS_AI_MAX_TOKENS"] = "not_an_int"

        try:
            with pytest.raises(ValueError, match="WOS_AI_MAX_TOKENS must be a valid integer"):
                AIConfig.from_environment()
        finally:
            os.environ.pop("WOS_AI_MAX_TOKENS", None)


class TestFileLoading:
    """Test configuration loading from JSON file."""

    def test_load_from_file_valid(self):
        """Test loading valid configuration from file."""
        config_data = {
            "model": "claude-3-haiku",
            "temperature": 0.5,
            "max_tokens": 1024,
            "reasoning_depth": "shallow",
            "difficulty_mode": "easy"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = AIConfig.from_file(temp_file)

            assert config.model == "claude-3-haiku"
            assert config.temperature == 0.5
            assert config.max_tokens == 1024
            assert config.reasoning_depth == "shallow"

        finally:
            os.unlink(temp_file)

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            AIConfig.from_file("/nonexistent/path/config.json")

    def test_load_from_file_invalid_json(self):
        """Test loading from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json")
            temp_file = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                AIConfig.from_file(temp_file)

        finally:
            os.unlink(temp_file)

    def test_load_from_file_unknown_fields(self):
        """Test loading from file ignores unknown fields."""
        config_data = {
            "model": "claude-3-haiku",
            "temperature": 0.5,
            "unknown_field": "should_be_ignored"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = AIConfig.from_file(temp_file)

            assert config.model == "claude-3-haiku"
            assert config.temperature == 0.5
            # Unknown field should not exist
            assert not hasattr(config, 'unknown_field')

        finally:
            os.unlink(temp_file)


class TestConfigurationSerialization:
    """Test configuration serialization."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = AIConfig(
            model="claude-3-haiku",
            temperature=0.5,
            max_tokens=1024
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["model"] == "claude-3-haiku"
        assert config_dict["temperature"] == 0.5
        assert config_dict["max_tokens"] == 1024

    def test_to_json(self):
        """Test conversion to JSON string."""
        config = AIConfig(
            model="claude-3-haiku",
            temperature=0.5
        )

        json_str = config.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["model"] == "claude-3-haiku"
        assert data["temperature"] == 0.5


class TestDefaultConfiguration:
    """Test module-level default configuration."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()

        assert isinstance(config, AIConfig)
        assert config.model == "claude-3.5-sonnet"

    def test_set_default_config(self):
        """Test setting default configuration."""
        original = get_default_config()

        custom = AIConfig(model="claude-3-haiku")
        set_default_config(custom)

        current = get_default_config()
        assert current.model == "claude-3-haiku"

        # Reset to original
        set_default_config(original)

    def test_set_default_config_invalid_type(self):
        """Test setting invalid default configuration."""
        with pytest.raises(ValueError, match="Expected AIConfig"):
            set_default_config("not a config")

    def test_reset_default_config(self):
        """Test resetting default configuration."""
        custom = AIConfig(model="claude-3-haiku")
        set_default_config(custom)

        reset_default_config()

        config = get_default_config()
        assert config.model == "claude-3.5-sonnet"
