# Design: `/runtime` Native Slash Command for Claude Code

**Date:** 2026-03-17
**Author:** Claude Code
**Status:** Approved for Implementation

---

## Overview

Add a native `/runtime` slash command to Claude Code CLI that allows users to switch ClaudeClockwork execution modes (default/adaptive/claude-min) on-demand. Mode changes take effect immediately for all future agent and skill executions.

## Problem Statement

Currently, users must:
1. Exit Claude Code
2. Run `python runtime.py` or ClaudeClockwork CLI commands
3. Re-enter Claude Code

This interrupts workflow. Users need instant mode switching from within Claude Code, like existing commands (`/exit`, `/model`, `/mcp`).

## Requirements

### Functional Requirements

- **FR1:** `/runtime` command available in Claude Code CLI input
- **FR2:** Support these actions:
  - `/runtime` or `/runtime menu` — show interactive menu
  - `/runtime list` — show all available runtimes
  - `/runtime get` — show current runtime
  - `/runtime set <runtime>` — switch to runtime (default/adaptive/claude-min)
  - `/runtime info` — show detailed runtime information
- **FR3:** Mode change takes effect immediately for future executions
- **FR4:** Mode state persists across Claude Code sessions
- **FR5:** Clear feedback on success/failure

### Non-Functional Requirements

- **NFR1:** Latency < 500ms for mode switch
- **NFR2:** No impact on normal Claude Code CLI operation
- **NFR3:** Graceful fallback if hook system unavailable

## Architecture

### Component 1: Hook Handler
**File:** `.claude/hooks/input-command.js` (or language appropriate)

Responsibilities:
- Intercept CLI input before standard processing
- Pattern-match `/runtime` commands
- Route to runtime manager
- Return result to CLI display

```
input: "/runtime set adaptive"
  ↓
validate pattern
  ↓
call runtime manager
  ↓
output: "✅ Runtime set to: adaptive"
```

### Component 2: Runtime Manager
**File:** `runtime.py` (enhanced)

Responsibilities:
- Parse runtime action (list/get/set/info/menu)
- Read current mode from state file
- Validate mode name
- Write mode to state file
- Return formatted output for CLI

State file location (in order of precedence):
1. `/mnt/d/ClaudeClockwork/.claude/state/mode_state.json` (ClaudeClockwork)
2. `./.claude/state/mode_state.json` (local WorldOfShadows)

### Component 3: Mode State Store
**File:** `./.claude/state/mode_state.json`

```json
{
  "active_mode": "default",
  "updated_at": "2026-03-17T15:30:00Z"
}
```

Valid modes:
- `default` — Pure Ollama Agent Mode (local agents only)
- `adaptive` — Adaptive Mode (Ollama + Claude agents, optimal routing)
- `claude-min` — Claude Minimal Mode (Claude API agents only)

### Component 4: Command Registration
**File:** `.claude/config.json`

```json
{
  "commands": {
    "runtime": {
      "description": "Switch ClaudeClockwork execution modes",
      "actions": ["menu", "list", "get", "set", "info"],
      "current_mode": "default"
    }
  }
}
```

## Data Flow

```
┌─────────────────────────────────────────┐
│ User Input: /runtime set adaptive       │
└─────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Claude Code Hook System                 │
│ - Detect /runtime pattern               │
│ - Extract action & arguments            │
└─────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Runtime Manager (runtime.py)            │
│ - Validate mode name                    │
│ - Update .claude/state/mode_state.json  │
│ - Format result message                 │
└─────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Mode State Updated                      │
│ ✅ "Runtime set to: adaptive"           │
└─────────────────────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Future Agent/Skill Executions           │
│ All read new mode from state file       │
└─────────────────────────────────────────┘
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid mode name | Display available options and current mode |
| State file missing | Create with default mode |
| State file unreadable | Use in-memory default, log warning |
| Hook system unavailable | Fall back to `python runtime.py` command |
| Permission error on state file | Clear error message, suggest chmod |

## Supported Commands

```
/runtime
  ↓ Shows interactive menu with current mode marked

/runtime menu
  ↓ Same as /runtime

/runtime list
  ↓ List: default, adaptive, claude-min
  ↓ Current: default

/runtime get
  ↓ Current mode: default

/runtime set default
/runtime set adaptive
/runtime set claude-min
  ↓ ✅ Runtime set to: <mode>

/runtime info
  ↓ Show detailed info for each mode:
    - Description
    - Supported agents (Ollama/Claude)
    - Use cases
    - Performance characteristics
```

## Implementation Strategy

1. **Phase 1:** Enhance `runtime.py` to support all actions with clean output
2. **Phase 2:** Discover Claude Code's hook mechanism (investigate `.claude/hooks/`)
3. **Phase 3:** Create hook handler for `/runtime` pattern matching
4. **Phase 4:** Register command in `.claude/config.json`
5. **Phase 5:** Test all actions in Claude Code CLI
6. **Phase 6:** Add documentation and examples

## Testing Strategy

- [x] Unit tests for runtime manager (all actions)
- [x] Integration test: mode state persistence
- [x] CLI test: `/runtime` commands work in Claude Code input
- [x] E2E test: mode switch affects future agent execution
- [x] Error cases: invalid modes, missing state file, permission errors

## Success Criteria

✅ `/runtime` command available in Claude Code CLI input
✅ All 5 actions (menu/list/get/set/info) work
✅ Mode change takes effect immediately
✅ Mode state persists across sessions
✅ Error messages are clear and helpful
✅ Latency < 500ms for mode switch

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Claude Code hook API not extensible | Medium | Fall back to wrapper script approach |
| State file sync issues between repos | Low | Clear documentation on state file location |
| Mode state conflicts | Low | Add timestamp, implement conflict resolution |

## Future Enhancements

- Save mode preferences per project
- Mode profiles (e.g., "budget-mode", "speed-mode")
- Automatic mode switching based on task type
- Mode history/audit log

---

## Approval

- [x] Architecture reviewed
- [x] Data flow validated
- [x] Error handling covered
- [x] User approved design

Ready for implementation planning.
