# AI Stack Integration Guide

## Overview

The AI stack integrates LangGraph-based reasoning with the World of Shadows backend. The orchestrator manages multi-turn reasoning flows, while the decorator pattern integrates AI with player routes.

## Architecture

```
Player Route
    ↓
@with_ai_reasoning Decorator
    ↓
AIReasoningDiagnostics Collection
    ↓
GameOrchestrator.run()
    ↓
LangGraph: initialize → reason → select → execute → interpret
    ↓
MCP Interface (tools, session queries)
    ↓
SessionService (world-engine authority)
    ↓
Response + AI Diagnostics
```

## Core Components

### 1. GameOrchestrator

Compiles and runs the LangGraph reasoning pipeline.

```python
from ai_stack.langgraph_orchestrator import GameOrchestrator
from ai_stack.mcp_agent_interface import MCPAgentInterface
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

# Initialize
mcp_interface = MCPAgentInterface()
catalog = CanonicalPromptCatalog()
orchestrator = GameOrchestrator(mcp_interface, catalog)

# Run reasoning for a session
state = orchestrator.run(session_id="abc123", player_id=1)

# Check result
if state.is_degraded:
    print(f"AI degraded: {state.errors}")
else:
    print(f"Decision: {state.action_selected}")
```

### 2. Turn Execution Decorator

Wraps player routes with AI reasoning.

```python
from ai_stack.with_ai_reasoning_decorator import (
    with_ai_reasoning,
    enable_ai_for_player,
    disable_ai_for_player,
    set_orchestrator
)

# Configure orchestrator
set_orchestrator(mcp_interface, catalog)

# Enable AI for specific player
enable_ai_for_player("player123")

# Decorate route
@api_v1_bp.route("/player/execute_action", methods=["POST"])
@with_ai_reasoning
def execute_action():
    # ... route implementation
    return {"message": "success"}, 200

# Response automatically includes ai_diagnostics:
# {
#     "message": "success",
#     "ai_diagnostics": {
#         "ai_enabled": true,
#         "reasoning_duration_ms": 450,
#         "reasoning_degraded": false,
#         "decision_made": "attack"
#     }
# }
```

### 3. AI Configuration

Configure AI behavior with operational profiles.

```python
from ai_stack.ai_config import AIConfig, set_default_config

# Use difficulty-based profiles
easy_config = AIConfig.for_difficulty("easy")      # Uses claude-3-haiku
normal_config = AIConfig.for_difficulty("normal")  # Uses claude-3.5-sonnet
hard_config = AIConfig.for_difficulty("hard")      # Enhanced sonnet

# Or create custom config
config = AIConfig(
    model="claude-3.5-sonnet",
    temperature=0.7,
    max_tokens=2048,
    reasoning_depth="standard",
    difficulty_mode="normal"
)

# Load from environment
config = AIConfig.from_environment()
# Reads: WOS_AI_MODEL, WOS_AI_TEMPERATURE, WOS_AI_MAX_TOKENS, WOS_AI_DIFFICULTY

# Load from file
config = AIConfig.from_file("/path/to/config.json")

# Set as default
set_default_config(config)
```

## Integration Patterns

### Pattern 1: Basic Route Integration

```python
from flask import request, jsonify
from app.api.v1 import api_v1_bp
from ai_stack.with_ai_reasoning_decorator import with_ai_reasoning, enable_ai_for_player

# Enable AI before using
enable_ai_for_player("player123")

@api_v1_bp.route("/player/execute_action", methods=["POST"])
@with_ai_reasoning
def execute_action():
    """Execute player action with AI reasoning."""
    data = request.get_json()
    session_id = data.get("session_id")
    action = data.get("action")
    
    # ... call session_service.execute_turn(session_id, player_id, action)
    
    return jsonify({
        "success": True,
        "new_turn_number": 5,
        "state_delta": {}
    }), 200
```

### Pattern 2: Conditional AI Enablement

```python
from ai_stack.with_ai_reasoning_decorator import is_ai_enabled_for_player

def handle_player_action(player_id, action):
    """Handle action, using AI if enabled for player."""
    
    if is_ai_enabled_for_player(player_id):
        # AI will run via decorator
        return execute_action_with_ai(player_id, action)
    else:
        # Direct execution
        return execute_action(player_id, action)
```

### Pattern 3: Custom Configuration per Difficulty

```python
from ai_stack.ai_config import AIConfig

def setup_world(difficulty):
    """Setup world with difficulty-appropriate AI."""
    
    # Get difficulty-specific config
    config = AIConfig.for_difficulty(difficulty)
    
    # Use config in orchestrator setup
    orchestrator = GameOrchestrator(mcp_interface, catalog)
    
    # Configuration affects reasoning depth, model selection, etc.
    return orchestrator
```

## Configuration Reference

### AIConfig Parameters

| Parameter | Type | Default | Range/Options | Description |
|-----------|------|---------|---------------|-------------|
| model | str | claude-3.5-sonnet | claude-3.5-sonnet, claude-3-haiku, claude-3-opus | Model to use for reasoning |
| temperature | float | 0.7 | 0.0 - 2.0 | Creativity/randomness (0=deterministic, 2=very creative) |
| max_tokens | int | 2048 | > 0 | Maximum tokens in response |
| reasoning_depth | str | standard | shallow, standard, deep | Amount of reasoning before action |
| max_reasoning_tokens | int | 4096 | > 0 | Maximum tokens for internal reasoning |
| difficulty_mode | str | normal | easy, normal, hard | Operational profile |
| use_extended_context | bool | False | true/false | Include extended context in reasoning |

### Environment Variables

```bash
# Model selection
export WOS_AI_MODEL=claude-3.5-sonnet

# Temperature control
export WOS_AI_TEMPERATURE=0.7

# Token limits
export WOS_AI_MAX_TOKENS=2048

# Reasoning depth
export WOS_AI_REASONING_DEPTH=standard

# Difficulty mode
export WOS_AI_DIFFICULTY=normal
```

### JSON Configuration File

```json
{
  "model": "claude-3.5-sonnet",
  "temperature": 0.7,
  "max_tokens": 2048,
  "reasoning_depth": "standard",
  "max_reasoning_tokens": 4096,
  "difficulty_mode": "normal",
  "use_extended_context": true,
  "enable_prompt_caching": true,
  "cache_ttl_seconds": 3600
}
```

## Error Handling

### Graceful Degradation (Law 6, Law 10)

All AI failures are handled gracefully:

```python
# Orchestrator failures
result = orchestrator.run(session_id, player_id)
if result.is_degraded:
    # AI failed but turn still executes
    print(f"AI degraded: {result.errors}")
    # Route proceeds without AI

# Decorator catches orchestrator exceptions
@with_ai_reasoning
def execute_action():
    # Even if orchestrator raises, turn still executes
    # Diagnostics will show reasoning_error
    return {"success": True}, 200
```

### Diagnostics Collection

Every decorated route includes diagnostics:

```python
{
    "success": True,
    "new_turn_number": 5,
    "ai_diagnostics": {
        "ai_enabled": true,
        "reasoning_duration_ms": 450,
        "reasoning_error": null,
        "reasoning_degraded": false,
        "decision_made": "move_forward"
    }
}
```

## Validation

### Configuration Validation

All parameters are validated on initialization:

```python
from ai_stack.ai_config import AIConfig

try:
    config = AIConfig(temperature=2.5)  # Too high
except ValueError as e:
    print(f"Invalid config: {e}")
    # ValueError: temperature must be between 0 and 2

try:
    config = AIConfig(max_tokens=0)  # Too low
except ValueError as e:
    print(f"Invalid config: {e}")
    # ValueError: max_tokens must be greater than 0
```

## Testing

### Unit Tests

```bash
# Test orchestrator
pytest ai_stack/tests/test_langgraph_orchestrator.py -v

# Test decorator
pytest ai_stack/tests/test_with_ai_reasoning_decorator.py -v

# Test configuration
pytest ai_stack/tests/test_ai_config.py -v

# Test integration
pytest ai_stack/tests/test_ai_integration_with_session.py -v
```

### Integration Testing

```python
from ai_stack.tests.test_ai_integration_with_session import MockSessionService
from ai_stack.langgraph_orchestrator import GameOrchestrator

# Create mock session
mock_session = MockSessionService()
mock_session.create_mock_session(
    session_id="test",
    world_id="world1",
    state={"location": "forest"}
)

# Test orchestrator against mock
orchestrator = GameOrchestrator(mock_interface, catalog)
state = orchestrator.run("test", 1)

assert state.session_id == "test"
```

## Constitutional Laws

### Law 1: One Truth
- AI state mirrors session state from world-engine
- No divergence between AI reasoning and authoritative state

### Law 6: Fail Closed
- AI errors never break turn execution
- Decorator catches orchestrator failures gracefully
- Routes complete even if AI unavailable

### Law 8: Explicit Errors
- All validation failures are explicit and loud
- Configuration errors raised immediately
- No silent degradation

### Law 9: AI Composition Bounds
- Orchestrator uses only MCP interface
- No direct database access
- No side effects outside MCP protocol

### Law 10: Catastrophic Failure
- AI reasoning marked as degraded on failure
- Turn execution continues with or without AI
- Diagnostics indicate degradation to client

## Troubleshooting

### AI Reasoning Not Running

Check if AI is enabled:
```python
from ai_stack.with_ai_reasoning_decorator import is_ai_enabled_for_player

if not is_ai_enabled_for_player("player123"):
    enable_ai_for_player("player123")
```

### Configuration Load Failures

Check environment variables:
```bash
# List AI config env vars
env | grep WOS_AI
```

Check file syntax:
```bash
# Validate JSON config
python -m json.tool /path/to/config.json
```

### High Reasoning Latency

Check configuration:
```python
config = AIConfig.for_difficulty("easy")  # Faster: uses haiku
config = AIConfig(temperature=0.5)  # Lower: faster reasoning
config = AIConfig(max_tokens=1024)  # Smaller: faster response
config = AIConfig(reasoning_depth="shallow")  # Less thinking
```

## Future Enhancements

1. **Caching**: Implement prompt caching for common queries
2. **Batch Processing**: Queue reasoning jobs for peak hours
3. **Model Selection**: Dynamic model routing based on complexity
4. **Multi-Turn History**: Longer context windows for narrative continuity
5. **Feedback Loop**: Learn from player decisions
6. **Monitoring**: Track reasoning quality and player satisfaction

## References

- LangGraph Documentation: https://python.langchain.com/docs/langgraph
- Constitutional AI: https://arxiv.org/abs/2310.11111
- World of Shadows Architecture: /docs/architecture.md
- SessionService API: /backend/app/services/session_service.py
