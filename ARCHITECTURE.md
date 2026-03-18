# Architecture: Clean Separation

## System vs Project

### ClaudeClockwork (SYSTEM)
The autonomous agent framework and management system.

**Location**: `/mnt/d/ClaudeClockwork/`

**Contains**:
- `.ollama/` — 70+ autonomous agent scripts
- `.claude/` — Unified session memory (master)
- `claudeclockwork/` — BaseAgent framework & orchestrator
- `KNOWLEDGE/` — Patterns, best practices, documentation
- `AGENTS_CATALOG.md` — Agent reference
- `DEVELOPMENT.md` — Development guide
- `.DEPRECATED/` — Obsolete but preserved items

**Manages**:
- Agent development and improvement
- Framework patterns and best practices
- Knowledge base for autonomous agents

### WorldOfShadows (PROJECT)
The actual application being developed.

**Location**: `/mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/`

**Contains**:
- `backend/` — REST API, database, business logic
- `administration-tool/` — Public website, admin interface
- `docs/` — Project-specific documentation
- `CLAUDE.md` — Project-specific Claude Code guidelines
- Project code, tests, configs

**Does NOT contain**:
- ✗ Agent framework files
- ✗ `.ollama/` folder
- ✗ ClaudeClockwork system files
- ✗ Framework documentation

## How They Work Together

```
ClaudeClockwork (Framework/System)
        ↓
    Agents & Tools
        ↓
WorldOfShadows (Project)
```

### Workflow

1. **Need to fix/improve WorldOfShadows**?
   - Create or use an agent from ClaudeClockwork
   - Agent runs in ClaudeClockwork context
   - Agent modifies WorldOfShadows files directly
   - Changes committed to WorldOfShadows repo

2. **Need to improve the agent framework**?
   - Work in ClaudeClockwork
   - Update agents, patterns, documentation
   - Available for all projects using the framework

3. **Session Memory** (`.claude`)?
   - Stored in ClaudeClockwork (master)
   - Tracks framework development
   - Accessible to agents working on any project

## Benefits

✓ **Clean separation of concerns**
- System code separate from project code
- Framework improvements don't pollute projects
- Each project stays focused on business logic

✓ **Reusable framework**
- ClaudeClockwork agents work on any project
- Patterns and practices documented in one place
- Framework improvements benefit all projects

✓ **Simplified project repos**
- WorldOfShadows contains only project files
- No framework clutter
- Easier to understand project structure
- Cleaner git history

✓ **Independent evolution**
- ClaudeClockwork can improve independently
- Projects can update framework version when ready
- No tight coupling

## For Developers

**Working on WorldOfShadows**?
→ Use agents from ClaudeClockwork

**Improving the agent framework**?
→ Work in ClaudeClockwork

**Adding project-specific agents**?
→ Create in ClaudeClockwork, tagged for this project

**Questions about patterns**?
→ See ClaudeClockwork/KNOWLEDGE/

---

This clean architecture enables:
- Autonomous agent framework (ClaudeClockwork)
- Multiple projects using the framework (WorldOfShadows, others)
- Clear separation of system vs application code
- Reusable, improvable framework
