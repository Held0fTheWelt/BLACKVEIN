"""
AI configuration system with operational profile awareness.

Manages:
- Model selection (claude-3.5-sonnet, claude-3-haiku, etc.)
- Temperature control (0-2 range)
- Token limits (max_tokens > 0)
- Reasoning depth (shallow/standard/deep)
- Operational profile mapping (easy/normal/hard modes)
- Configuration loading from environment/file

Constitutional Laws:
- Law 1: Clarity of truth - explicit configuration validation
- Law 8: Explicit errors - all validation failures clear and loud
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Literal
import os
import json
import logging

logger = logging.getLogger(__name__)


# Type aliases for clarity
ModelType = Literal["claude-3.5-sonnet", "claude-3-haiku", "claude-3-opus"]
DifficultyMode = Literal["easy", "normal", "hard"]
ReasoningDepth = Literal["shallow", "standard", "deep"]


@dataclass
class AIConfig:
    """AI configuration with validation and operational profiles."""

    # Model configuration
    model: ModelType = "claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 2048

    # Reasoning configuration
    reasoning_depth: ReasoningDepth = "standard"
    max_reasoning_tokens: int = 4096

    # Operational awareness
    difficulty_mode: DifficultyMode = "normal"
    use_extended_context: bool = False

    # Response characteristics
    min_response_length: int = 50
    max_response_length: int = 1000

    # Caching and optimization
    enable_prompt_caching: bool = True
    cache_ttl_seconds: int = 3600

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate all configuration values.

        Raises:
            ValueError: If any configuration is invalid
        """
        # Validate temperature (Law 1: clarity, Law 8: explicit errors)
        if not isinstance(self.temperature, (int, float)):
            raise ValueError(
                f"temperature must be a number, got {type(self.temperature).__name__}"
            )
        if not 0 <= self.temperature <= 2:
            raise ValueError(
                f"temperature must be between 0 and 2, got {self.temperature}"
            )

        # Validate max_tokens
        if not isinstance(self.max_tokens, int):
            raise ValueError(
                f"max_tokens must be an integer, got {type(self.max_tokens).__name__}"
            )
        if self.max_tokens <= 0:
            raise ValueError(
                f"max_tokens must be greater than 0, got {self.max_tokens}"
            )

        # Validate max_reasoning_tokens
        if self.max_reasoning_tokens <= 0:
            raise ValueError(
                f"max_reasoning_tokens must be greater than 0, got {self.max_reasoning_tokens}"
            )

        # Validate response length bounds
        if self.max_response_length < self.min_response_length:
            raise ValueError(
                f"max_response_length ({self.max_response_length}) must be >= "
                f"min_response_length ({self.min_response_length})"
            )

        if self.cache_ttl_seconds < 0:
            raise ValueError(
                f"cache_ttl_seconds must be non-negative, got {self.cache_ttl_seconds}"
            )

    @classmethod
    def for_difficulty(cls, difficulty: DifficultyMode) -> "AIConfig":
        """Create AIConfig optimized for difficulty level (operational profile).

        Args:
            difficulty: "easy", "normal", or "hard"

        Returns:
            Configured AIConfig instance

        Law 1: Clear mapping between difficulty and AI behavior
        """
        if difficulty == "easy":
            return cls(
                model="claude-3-haiku",
                temperature=0.5,
                max_tokens=1024,
                reasoning_depth="shallow",
                max_reasoning_tokens=2048,
                difficulty_mode="easy",
                use_extended_context=False,
                enable_prompt_caching=True
            )
        elif difficulty == "normal":
            return cls(
                model="claude-3.5-sonnet",
                temperature=0.7,
                max_tokens=2048,
                reasoning_depth="standard",
                max_reasoning_tokens=4096,
                difficulty_mode="normal",
                use_extended_context=True,
                enable_prompt_caching=True
            )
        elif difficulty == "hard":
            return cls(
                model="claude-3.5-sonnet",
                temperature=0.9,
                max_tokens=3072,
                reasoning_depth="deep",
                max_reasoning_tokens=8000,
                difficulty_mode="hard",
                use_extended_context=True,
                enable_prompt_caching=True
            )
        else:
            raise ValueError(
                f"Unknown difficulty mode: {difficulty}. "
                f"Must be 'easy', 'normal', or 'hard'"
            )

    @classmethod
    def from_environment(cls) -> "AIConfig":
        """Load configuration from environment variables.

        Reads from:
        - WOS_AI_MODEL: Model name
        - WOS_AI_TEMPERATURE: Temperature (0-2)
        - WOS_AI_MAX_TOKENS: Max tokens
        - WOS_AI_REASONING_DEPTH: Reasoning depth
        - WOS_AI_DIFFICULTY: Difficulty mode (easy/normal/hard)

        Returns:
            AIConfig loaded from environment

        Law 8: Explicit errors if environment vars are invalid
        """
        model = os.getenv("WOS_AI_MODEL", "claude-3.5-sonnet")
        temperature_str = os.getenv("WOS_AI_TEMPERATURE", "0.7")
        max_tokens_str = os.getenv("WOS_AI_MAX_TOKENS", "2048")
        reasoning_depth = os.getenv("WOS_AI_REASONING_DEPTH", "standard")
        difficulty = os.getenv("WOS_AI_DIFFICULTY", "normal")

        try:
            temperature = float(temperature_str)
        except ValueError:
            raise ValueError(
                f"WOS_AI_TEMPERATURE must be a valid float, got '{temperature_str}'"
            )

        try:
            max_tokens = int(max_tokens_str)
        except ValueError:
            raise ValueError(
                f"WOS_AI_MAX_TOKENS must be a valid integer, got '{max_tokens_str}'"
            )

        config = cls(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_depth=reasoning_depth,
            difficulty_mode=difficulty
        )

        logger.info(
            f"Loaded AI config from environment: "
            f"model={model}, temperature={temperature}, max_tokens={max_tokens}"
        )

        return config

    @classmethod
    def from_file(cls, filepath: str) -> "AIConfig":
        """Load configuration from JSON file.

        File format:
        {
            "model": "claude-3.5-sonnet",
            "temperature": 0.7,
            "max_tokens": 2048,
            "reasoning_depth": "standard",
            "difficulty_mode": "normal"
        }

        Args:
            filepath: Path to JSON config file

        Returns:
            AIConfig loaded from file

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
            ValueError: If configuration values are invalid
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        # Filter to only known fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        config = cls(**filtered_data)

        logger.info(f"Loaded AI config from file: {filepath}")

        return config

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "reasoning_depth": self.reasoning_depth,
            "max_reasoning_tokens": self.max_reasoning_tokens,
            "difficulty_mode": self.difficulty_mode,
            "use_extended_context": self.use_extended_context,
            "min_response_length": self.min_response_length,
            "max_response_length": self.max_response_length,
            "enable_prompt_caching": self.enable_prompt_caching,
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    def to_json(self) -> str:
        """Convert configuration to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"AIConfig(model={self.model}, temperature={self.temperature}, "
            f"max_tokens={self.max_tokens}, difficulty={self.difficulty_mode})"
        )


# Module-level default configuration
_default_config = AIConfig()


def get_default_config() -> AIConfig:
    """Get the default AI configuration.

    Returns:
        Default AIConfig instance
    """
    return _default_config


def set_default_config(config: AIConfig):
    """Set the default AI configuration.

    Args:
        config: AIConfig to use as default

    Raises:
        ValueError: If config is invalid
    """
    global _default_config
    if not isinstance(config, AIConfig):
        raise ValueError(f"Expected AIConfig, got {type(config).__name__}")
    _default_config = config


def reset_default_config():
    """Reset default configuration to hardcoded defaults."""
    global _default_config
    _default_config = AIConfig()
