# Quick Reference: Using ClaudeClockwork

WorldOfShadows is now a pure project repository.
All autonomous agent work happens in ClaudeClockwork.

## Using Agents

To run an agent on WorldOfShadows:

```bash
cd /mnt/d/ClaudeClockwork
python .ollama/agent_name.py
```

Common agents:
- `master_corrective_agent_v3.py` — Fix bugs, code issues
- `implement_taskexecutor_integration.py` — Add features
- `consolidate_claude_folders.py` — Organize structure
- `validate_claudeclockwork_patterns.py` — Validate patterns

## Viewing Agent Catalog

```bash
cat /mnt/d/ClaudeClockwork/AGENTS_CATALOG.md
```

## Learning Patterns

See patterns and best practices:

```bash
cat /mnt/d/ClaudeClockwork/KNOWLEDGE/README.md
```

## Development Guidelines

For WorldOfShadows specific guidelines:
- See: `CLAUDE.md` (this repo, project-specific)

For agent/framework guidelines:
- See: `ClaudeClockwork/KNOWLEDGE/README.md`

## Creating New Agents

1. Create in: `/mnt/d/ClaudeClockwork/.ollama/`
2. Inherit from: `claudeclockwork.agents.base_agent.BaseAgent`
3. Reference: `ClaudeClockwork/DEVELOPMENT.md`

## File Organization

```
WorldOfShadows/                 # Project only
├── backend/
├── administration-tool/
├── docs/
├── CLAUDE.md                   # Project-specific
├── ARCHITECTURE.md             # This structure
└── QUICK_REFERENCE.md          # This file

ClaudeClockwork/                # System framework
├── .ollama/                    # Agents
├── .claude/                    # Session memory
├── claudeclockwork/            # Framework
├── KNOWLEDGE/                  # Patterns
└── [framework files]
```

## When Files Change

- `WorldOfShadows files` → commit to WorldOfShadows repo
- `ClaudeClockwork files` → agents handle automatically
- `Framework improvements` → available to all projects

---

Clean architecture = cleaner projects + better reusability
