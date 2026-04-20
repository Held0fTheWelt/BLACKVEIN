# Canonical Prompt Catalog API

## Overview

The Canonical Prompt Catalog provides game-specific LLM prompts for AI-driven gameplay decisions. All prompts are immutable after load and validated to prevent exposure of system internals.

**Key Principles:**
- **One Truth:** All AI reasoning uses prompts from this catalog
- **Fail Closed:** Prompts validated for safety (no internal exposure)
- **Immutable:** Prompts cannot be modified after retrieval
- **Composable:** Templates use variable binding for LangGraph nodes

## API Reference

### CanonicalPromptCatalog

```python
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

catalog = CanonicalPromptCatalog()
```

#### Methods

##### `get_prompt(name: str) -> Dict[str, Any]`

Retrieve a prompt by name. Returns a deep copy to ensure immutability.

**Parameters:**
- `name` (str): Prompt identifier (e.g., "decision_context")

**Returns:**
```python
{
    "id": "decision_context",
    "template": "...",
    "description": "...",
    "variables": ["game_state", "player_action", "previous_result"]
}
```

**Raises:**
- `KeyError`: If prompt not found

**Example:**
```python
prompt = catalog.get_prompt("decision_context")
template = prompt["template"].format(
    game_state="...",
    player_action="...",
    previous_result="..."
)
```

##### `list_prompts() -> List[str]`

List all available prompt names.

**Returns:**
```python
["decision_context", "action_selection", "narrative_response", "failure_explanation"]
```

##### `validate() -> bool`

Validate catalog structure and safety constraints.

**Validation Checks:**
- Required fields present (id, template, description)
- Templates are non-empty strings
- ID matches prompt name
- No forbidden terms that expose internals (SessionService, database, secret, password)

**Returns:** `True` if valid, raises `ValueError` if invalid

**Example:**
```python
try:
    catalog.validate()
except ValueError as e:
    print(f"Validation failed: {e}")
```

##### `get_prompt_for_profile(name: str, profile: OperationalProfile) -> Dict[str, Any]`

Get prompt adjusted for operational profile (difficulty, complexity).

**Parameters:**
- `name` (str): Prompt identifier
- `profile`: Operational profile with `difficulty` and `complexity` attributes

**Returns:** Deep copy of prompt (possibly adjusted for profile)

**Example:**
```python
# Hard difficulty: prompts with less guidance
# Simple complexity: shorter templates
prompt = catalog.get_prompt_for_profile("narrative_response", profile)
```

##### `list_prompts_for_profile(profile: OperationalProfile) -> List[str]`

List prompts available for specific operational profile.

**Parameters:**
- `profile`: Operational profile

**Returns:** List of available prompt names for this profile

## Available Prompts

### 1. decision_context

**Purpose:** Analyze game state and player action to generate decision context.

**Template Variables:**
- `game_state` (str): Current world state, player status, nearby objects
- `player_action` (str): Description of player's queued action
- `previous_result` (str): Result from previous turn (if any)

**Output:** Structured analysis of 3-5 possible action outcomes

**Usage:** First node in reasoning chain - AI analyzes what *could* happen

**Example Output:**
```
Possible Outcomes:
1. Attack lands (player has combat advantage) - damage dealt
2. Attack blocked (NPC uses shield ability) - damage reduced
3. Attack misses (NPC dodges) - player loses position
```

### 2. action_selection

**Purpose:** Select the best action outcome from decision analysis.

**Template Variables:**
- `decision_analysis` (str): Output from decision_context prompt

**Output:** Single best action outcome with reason and narrative impact

**Usage:** Second node - narrows down to single chosen outcome

**Example Output:**
```
Selected Outcome: Attack lands with partial damage

Reason: Player has slightly higher attack than NPC defense. Fairness maintained.

Narrative Impact: Enemy health reduced by 15%, shifts from aggressive to defensive stance.
```

### 3. narrative_response

**Purpose:** Generate narrative text describing action outcome to player.

**Template Variables:**
- `action` (str): Player's action description
- `outcome` (str): Chosen outcome from action_selection
- `world_context` (str): Surrounding narrative context

**Output:** 2-3 sentences of immersive narrative

**Usage:** Third node - generates player-facing text

**Example Output:**
```
You swing your blade at the guardian's shield. The impact rings through the hall, 
and cracks spider-web across its magical surface. Sparks of defensive magic 
scatter as the guardian staggers back, reassessing you with new wariness.
```

### 4. failure_explanation

**Purpose:** Explain action failure in narrative terms (degraded mode).

**Template Variables:**
- `action` (str): What player tried to do
- `reason` (str): Technical reason for failure (simplified)
- `game_state` (str): Current world state

**Output:** 1-2 sentences explaining failure in-world, never punitive

**Usage:** Error path - when AI cannot complete normal reasoning

**Example Output:**
```
Your action requires you to be on solid ground. The bridge beneath you 
crumbles further—you need to find stable footing before trying that move.
```

## Safety Guarantees

### Immutability

Prompts are returned as deep copies to prevent modification:

```python
prompt = catalog.get_prompt("decision_context")
prompt["template"] = "HACKED"  # Does NOT affect catalog

new_prompt = catalog.get_prompt("decision_context")
# Returns original, unmodified template
```

### No Internal Exposure

Prompts validated to exclude:
- `SessionService` references
- `database` calls or details
- `secret` or `password` mentions
- SQLAlchemy or ORM internals

All prompts describe game-world state only, never system architecture.

### Fail-Closed Template Validation

Every prompt template is validated:
- Required variables present
- No forbidden keywords
- Non-empty and well-formed

Invalid prompts raise `ValueError` on validation, preventing corruption.

## Integration with LangGraph

### Usage Pattern

```python
from ai_stack.langgraph_agent_nodes import initialize_state, reason_decision
from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog

catalog = CanonicalPromptCatalog()

# Node 1: Reasoning
def reason_decision(state, mcp_interface, prompt_catalog):
    prompt = prompt_catalog.get_prompt("decision_context")
    template = prompt["template"]
    
    analysis = llm.generate(
        template.format(
            game_state=state["current_state"],
            player_action=state["queued_action"],
            previous_result=state.get("previous_result", "")
        )
    )
    
    return {"reasoning_steps": analysis}

# Node 2: Action selection
def select_action(state, prompt_catalog):
    prompt = prompt_catalog.get_prompt("action_selection")
    template = prompt["template"]
    
    decision = llm.generate(
        template.format(decision_analysis=state["reasoning_steps"])
    )
    
    return {"decision": decision}
```

## Operational Profile Integration

Prompts can vary based on game difficulty/complexity:

```python
# Easy mode: more guidance, simpler language
easy_profile = OperationalProfile(difficulty="easy", complexity="simple")
prompt = catalog.get_prompt_for_profile("narrative_response", easy_profile)

# Hard mode: less guidance, complex scenarios
hard_profile = OperationalProfile(difficulty="hard", complexity="complex")
prompt = catalog.get_prompt_for_profile("narrative_response", hard_profile)
```

## Adding New Prompts

To extend the catalog:

1. Add prompt definition to `_initialize_prompts()` in `canonical_prompt_catalog.py`
2. Include required fields: `id`, `template`, `description`, `variables`
3. Add tests to `test_canonical_prompt_catalog.py`
4. Document in this file
5. Validate using `catalog.validate()`

## Error Handling

### Missing Prompt

```python
try:
    prompt = catalog.get_prompt("nonexistent")
except KeyError as e:
    print(f"Prompt not found: {e}")
    # Fallback to default prompt
```

### Validation Failure

```python
try:
    catalog.validate()
except ValueError as e:
    print(f"Catalog invalid: {e}")
    # Log and alert operators
```

## Performance

- Catalog initialization: O(1) - prompts pre-loaded
- `get_prompt()`: O(1) dictionary lookup + O(n) deep copy
- `validate()`: O(n) where n = number of prompts
- All operations: <1ms on typical hardware

## References

- **Implementation:** `ai_stack/canonical_prompt_catalog.py`
- **Tests:** `ai_stack/tests/test_canonical_prompt_catalog.py`
- **LangGraph Integration:** `ai_stack/langgraph_agent_nodes.py`
- **Orchestrator:** `ai_stack/langgraph_orchestrator.py`
