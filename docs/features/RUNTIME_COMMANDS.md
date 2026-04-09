# Historical Note: `/runtime` Command (Non-Canonical)

This document is preserved for historical reference only.

It describes an external command workflow that is not part of the canonical
World of Shadows runtime architecture. The canonical runtime and AI stack
decision lives in:

- `docs/technical/ai/ai-stack-overview.md`
- `docs/technical/runtime/runtime-authority-and-state-flow.md`

---

# `/runtime` Command - Execution Mode Switcher

Switch ClaudeClockwork execution modes on-demand from Claude Code CLI.

## Quick Start

```
/runtime              # Show interactive menu
/runtime get          # Show current mode
/runtime list         # List all modes
/runtime set adaptive # Switch mode
/runtime info         # Show details
```

## Modes

- **default** - Pure Ollama: Local, fast, no API costs
- **adaptive** - Smart routing: Ollama + Claude, optimal per task
- **claude-min** - Claude only: Highest quality

## Usage Examples

### Check current mode
```
/runtime get
```

Output:
```json
{
  "status": "ok",
  "message": "Current mode: default",
  "mode": "default",
  "description": "Pure Ollama Agent Mode - execute all skills with Ollama agents only"
}
```

### Switch to Adaptive mode
```
/runtime set adaptive
```

Output:
```json
{
  "status": "ok",
  "message": "✅ Runtime set to: adaptive",
  "mode": "adaptive",
  "description": "Adaptive Mode - support both Ollama and Claude agents, choose optimal route"
}
```

### Show all available modes
```
/runtime list
```

Output:
```json
{
  "status": "ok",
  "message": "Available modes: default, adaptive, claude-min. Active: default",
  "modes": {
    "default": "Pure Ollama Agent Mode - execute all skills with Ollama agents only",
    "adaptive": "Adaptive Mode - support both Ollama and Claude agents, choose optimal route",
    "claude-min": "Claude Minimal Mode - execute with Claude API agents (minimized costs)"
  },
  "active_mode": "default"
}
```

### Interactive menu
```
/runtime
```

Shows a menu allowing you to select a mode interactively.

### Show detailed information
```
/runtime info
```

Output includes detailed info about each mode (allows_ollama, allows_claude, allows_hybrid, use_case).

## Use Cases

- **default**: Development, testing, privacy-sensitive work. Uses only local Ollama models.
- **adaptive**: Mixed workloads, automatic optimization. Routes tasks to Ollama or Claude based on complexity.
- **claude-min**: Production, quality-critical tasks. Uses Claude API (higher cost, higher quality).

## Mode Behavior

### default (Pure Ollama)
- **Allows Ollama:** ✅ Yes
- **Allows Claude:** ❌ No
- **Cost:** $0 (local execution)
- **Latency:** Depends on model size
- **Best for:** Development, privacy-focused work, cost-sensitive tasks

### adaptive
- **Allows Ollama:** ✅ Yes
- **Allows Claude:** ✅ Yes
- **Allows Hybrid:** ✅ Yes (both in same task)
- **Cost:** Variable (mostly Ollama, Claude for complex tasks)
- **Best for:** Mixed workloads, automatic optimization

### claude-min
- **Allows Ollama:** ❌ No
- **Allows Claude:** ✅ Yes
- **Cost:** $0.08/1M tokens (Haiku), higher for larger models
- **Latency:** Fast, API-based
- **Best for:** Production, quality-critical work

## Implementation Details

### Mode State Storage
- **Location:** `/mnt/d/ClaudeClockwork/.claude/state/mode_state.json` (ClaudeClockwork) or `.claude/state/mode_state.json` (local)
- **Format:** JSON with `active_mode` field
- **Persistence:** Changes persist across sessions

### Hook Handler
- **File:** `.claude/hooks/input-command.js`
- **Mechanism:** Intercepts `/runtime` commands in Claude Code CLI input
- **Execution:** Spawns Python subprocess running `runtime.py`

### Runtime Manager
- **File:** `runtime.py` in project root
- **Class:** `RuntimeManager`
- **Methods:** `load_mode()`, `save_mode()`, `set_mode()`, `get_current_mode()`, `list_modes()`, `show_menu()`, `show_info()`

## Technical Details

Mode state: `/mnt/d/ClaudeClockwork/.claude/state/mode_state.json`

Changes take effect immediately for all future executions.

### Environment Variables

The mode system respects these env vars if configured:
- `ANTHROPIC_API_KEY`: Required for claude-min mode
- `OLLAMA_HOST`: Ollama server hostname (default: localhost)
- `OLLAMA_PORT`: Ollama server port (default: 11434)
- `OLLAMA_FALLBACK_TO_CLAUDE`: Fallback L1/L2 tasks to Claude when Ollama unavailable

## Troubleshooting

### "Invalid mode" error
Ensure you're using one of: `default`, `adaptive`, or `claude-min`.

### Mode not persisting
Check that `.claude/state/` directory exists and is writable.

### Command not found
Ensure `.claude/config.json` has the `/runtime` command registered and hook handler is present at `.claude/hooks/input-command.js`.

## Related Documentation

- `/mnt/d/ClaudeClockwork/.claude/OLLAMA_AGENT_PATTERNS.md` - Agent execution patterns and best practices
- `/mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/docs/ADR/ADR-004-ollama-first-routing-architecture.md` - Routing architecture decisions
