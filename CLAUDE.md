# World of Shadows — Claude Code Discipline & Conventions

Project-specific instructions for Claude Code working in this repository. Overrides default behaviors where specified.

---

## Test Runner — "tests/run_tests.py" is canonical, do not create alternates

**Rule:** `tests/run_tests.py` is the single canonical test runner for this project. Do not create wrapper scripts, aliases, or alternate test entry points.

**Why:** Multiple test runners cause:

- Inconsistent test discovery and execution order
- Hidden dependencies in documentation and workflows
- Friction when different parts of the codebase reference different runners
- CI/CD pipeline ambiguity (which runner does the workflow actually use?)

**How to apply:**

- Always invoke tests via: `python tests/run_tests.py [args]`
- Use suite flags for scoped runs: `--suite mvp1`, `--suite backend`, `--suite engine`
- Use MVP presets for focused work: `--mvp1`, `--mvp2`, `--mvp3`, `--mvp4`
- If a test runner is missing or broken, fix `tests/run_tests.py` itself, never create a wrapper
- When documentation refers to "run tests," link to `tests/run_tests.py --help`
- GitHub workflows should invoke: `python tests/run_tests.py --suite <name>`

**Scope:** Applied across all test execution contexts—local dev, CI/CD workflows, documentation examples, debugging sessions.

---

## Root Cause Discipline — Diagnose environment first (venv, deps, container files) before fixing code

**Rule:** When a test fails or a command errors, diagnose the execution environment *before* modifying application code. Check in this order:

1. **Virtual environment**: Is venv activated? Is it using the right Python version?
2. **Dependencies**: Are all required packages installed? Run `pip list` or check lock files.
3. **Container state**: Are Docker containers running? Do they have the right images? Check `docker ps`, `docker images`.
4. **Working directory**: Is the command run from the right directory? Some pytest commands require `cd backend/` or `cd world-engine/`.
5. **Environment variables**: Are required vars set (API keys, config paths, database URLs)?
6. **File permissions**: Do test fixtures have the right file access?

Only after ruling out environment issues should you:

- Modify test code
- Change application logic
- Update dependencies

**Why:** 90% of "test failures" are environment misconfigurations, not code bugs. Fixing code when the issue is a missing venv wastes time and introduces false fixes.

**How to apply:**

- Always start with: "What environment is this test running in?"
- Ask questions: "Is the venv active?" "Are all deps installed?" "Is Docker running?"
- Verify before coding: `pip list | grep <package>`, `docker ps`, `python --version`
- Document what you find: "Test failed because X was misconfigured, fixed by Y"
- Only commit code fixes if the code is actually the root cause

**Scope:** Applied when investigating test failures, CI pipeline breaks, import errors, or unexpected command behavior.

---

## Test Debugging Discipline — Diagnose root cause, not surface symptoms; use semantic search to understand test intent

**Rule:** When a test fails diagnose the root cause before modifying test code.

**Root causes for repeated test failures:**

1. **Instance/Data State**: Test creates object with wrong initial state (e.g., `RunStatus.LOBBY` when `RUNNING` is required)
2. **Template Mismatch**: Test uses template name A but asserts resources from template B (e.g., testing "apartment_confrontation_group" but checking for rooms/props from "god_of_carnage_solo")
3. **Missing Prerequisites**: Test skips setup steps (e.g., setting instance status before applying commands)
4. **Stale Assertions**: Test was copied from one template but not updated when template changed

**How to diagnose (before touching test code):**

1. **Understand test intent**: Use `mcp__claude-context__search_code` with query like "test_X what is it testing" or look at test name and structure
2. **Identify what template/objects are used**: Check what `_runtime_instance_for()` or `load_builtin_templates()` returns
3. **Verify resources exist**: Search for "template_name rooms/props/actions definitions" to confirm test assertions match actual template
4. **Check object state**: Understand required states (LOBBY vs RUNNING, initial beat_id, participant status)
5. **Read related tests**: Look for similar tests that work—see how they handle the same template

**How to apply:**

- When test fails: "What environment state does this test need?"
- Not: "How do I make this assertion pass?"
- Search for: template definitions, action names, prop IDs, room layouts
- Compare against: working tests with same template, recent template changes, template documentation
- Only then: modify test to match actual template behavior

**Why:** A test that patches around mismatch teaches false confidence. A test aligned with actual template structure:

- Documents how the template actually works
- Catches regressions when template changes
- Prevents copy-paste errors in future tests
- Provides a reference implementation for template usage

**Example:** A test using "apartment_confrontation_group" but testing for "living_room" (not in template) means either:

- Test was copied from "god_of_carnage_solo" and not updated → fix by using actual rooms (foyer, parlor)
- Template recently changed → fix by updating assertions OR reverting template
- Test was written against wrong template → fix by switching to correct template

**Scope:** Applied to any test that fails or with cascading errors. Use semantic search to understand context before patching.

---

## Execution vs Exploration — When given a prepared plan, execute directly; cap discovery at 3 tool calls

**Rule:** Execution mode (when you have a written plan or user has specified exactly what to do) is fundamentally different from exploration mode (when you're investigating or designing).

**Execution Mode — Do not explore:**

- User has provided a plan or detailed instructions
- Plan includes specific file paths, function names, line numbers
- You know what to change and why
- **Action:** Execute directly. Make the changes. Do not run discovery searches first.

**Exploration Mode — Capped at 3 tool calls:**

- User asks an open question: "What files handle X?" "Where is the bug?"
- You need to understand the codebase before making changes
- **Action:** Run up to 3 Glob/Grep/Read calls to gather context. If you need more, use Agent with `subagent_type=Explore` instead of self-executing 10+ searches.

**Why:** 

- **Execution mode:** Planning already consumed the discovery cost. Searching again delays implementation and wastes context on redundant lookups.
- **Exploration mode cap:** Self-executing many searches floods the conversation with tool results and context. Agent delegates efficiently; you keep working.

**How to apply:**

- **When starting work:** Ask yourself: "Do I have a specific plan, or am I exploring?"
- **If you have a plan:** Open the files mentioned, make changes, test. Do not search.
- **If you're exploring:** Ask yourself after 3 tool calls: "Do I have enough context?" If no, spawn `Agent(subagent_type=Explore, ...)` instead of continuing.
- **When user says "check why this failed":** That's exploration. Use it to gather 1-2 clues, then either execute a fix or delegate deeper investigation to Agent.

**Scope:** Applied to all implementation work, debugging sessions, and feature additions. Helps maintain velocity and prevent context bloat.

---

## Indexing for Search & Diagnostics — Use semantic codebase search for exploration and problem-solving

**Rule:** Use semantic codebase indexing (`mcp__claude-context__search_code`) for **almost everything** where you need to find out what is happening and why. The codebase is semantically indexed and ready for natural language queries. This is your default tool for understanding code behavior, dependencies, and root causes.

**When to use indexing:**

- "Where is X defined?" (function, class, constant, symbol)
- "What files reference Y?" (searching for usages)
- "Find all places where Z happens" (logic search)
- "Diagnose why this is failing" (understand codebase context before fixing)
- "Legacy content audit" (find all instances of old patterns)
- "Scope analysis" (what code is affected by this change?)
- "Test reference audit" (find all tests that import or reference a deleted module)
- "Cross-file consistency" (find all docs that reference deleted/renamed code)

**When NOT to use indexing:**

- Just always use claude-index, when possible. you always gain knowledge

**How to use:**

```bash
# Search the indexed codebase
mcp__claude-context__search_code(
  path: "D:\WorldOfShadows",
  query: "runtime profile resolver for MVP1",
  limit: 10
)

# If codebase isn't indexed yet, index it first
mcp__claude-context__index_codebase(
  path: "D:\WorldOfShadows",
  splitter: "ast",  # Use AST splitter for Python
  force: false
)

# Check indexing status
mcp__claude-context__get_indexing_status(
  path: "D:\WorldOfShadows"
)
```

**Example queries:**


| Task                                | Query                                     |
| ----------------------------------- | ----------------------------------------- |
| Find runtime profile implementation | "runtime profile resolver implementation" |
| Locate actor lane enforcement       | "actor lane validation and enforcement"   |
| Find visitor prohibition logic      | "visitor removal prohibition GLOBAL"      |
| Understand passivity validation     | "passivity validation scene block"        |
| Diagnose legacy Area 2 references   | "Area 2 Task 4 closure validation"        |
| Audit capability evidence usage     | "capability evidence source anchor"       |


**Why use indexing:**

- **Semantic search:** Finds code by meaning, not just text matching (understands "role selection" finds both "validate_selected_player_role" and "build_actor_ownership")
- **Large codebase:** 6400+ files indexed efficiently; naive grep is slow and loses context
- **Context-aware:** Results include surrounding code, not just matching lines
- **Exploration:** Enables quick 3-tool-call discovery (search → read → understand) without manual grep iterations
- **Diagnostic:** Understand what code is affected before making changes

**Workflow:**

1. **Explore:** Use `search_code` for natural language queries
2. **Understand:** `Read` the top 2-3 results to get context
3. **Diagnose:** Identify root cause before modifying code
4. **Execute:** Only then make changes (see Execution vs Exploration discipline)

**Scope:** Applied to all search, diagnostic, and exploration work. Codebase is pre-indexed; queries are fast and semantically aware.

---

## Gate & Status Reporting — Report exact pass/fail counts + command output; required ADRs before MVP completion

**Rule:** When reporting gate verification results or MVP completion status, always include exact test counts and command evidence. ADRs are required before any MVP can be marked complete.

**Gate Verification Format (never vague):**

❌ Bad:

- "tests pass"
- "all gate requirements met"
- "verified successfully"

✅ Good:

- "19 passed, 0 failed, 0 skipped, 0 errors"
- "Gate: mvp1-operational-evidence PASS [19/19 tests]"
- Include command used: `python tests/run_tests.py --suite mvp1`
- Include actual test names if tests fail

**Status Report Format:**

```
MVP Verification: {mvp_name}
Status: COMPLETE | BLOCKED
Test Results: {exact counts}
- Passed: {n}
- Failed: {n}
- Skipped: {n}
- Total: {n}

Evidence:
- Source Locator: docs/ADR/{mvp_name}-source-locator.md (✓ exists | ✗ missing)
- Operational Evidence: docs/ADR/{mvp_name}-operational-evidence.md (✓ exists | ✗ missing)
- Handoff: docs/ADR/{mvp_name}-handoff.md (✓ exists | ✗ missing)

Required ADRs: {count} present
- adr-{mvp_name}-001-{title}.md (✓ exists | ✗ missing)
- ...

Command Evidence:
\`\`\`bash
cd D:\WorldOfShadows
python tests/run_tests.py --suite {suite}
# Output: {last 10 lines of results}
\`\`\`
```

**ADR Requirements:**

Before marking any MVP complete:

1. All required ADRs must exist in `docs/ADR/MVP_Live_Runtime_Completion/`
2. Each ADR must include: context, decision, consequences, test evidence, operational gate impact
3. Each ADR must be marked `ACCEPTED` (status frontmatter)
4. Source Locator matrix must have zero unresolved placeholders
5. Operational Evidence must have zero "todo" or "fill during implementation" entries
6. Handoff must specify contracts consumed by next MVP

**How to apply:**

- When you complete a gate, use `/gate-check {gate-name}` to auto-generate ADR
- Report numbers, not opinions: show `pytest --tb=short` output, not interpretations
- Before declaring MVP complete, verify all 3 artifact files exist and are populated
- If ADR is missing, do not proceed to next MVP—create it first
- Include actual command output in status reports (redacted for secrets only)

**Scope:** Applied to all gate verifications, MVP completion reports, and status updates. Enables clear handoff between MVPs and prevents silent failures.

---

## Additional Context

- **Project:** World of Shadows interactive text adventure engine
- **MVP System:** MVP1 (Experience Identity) → MVP2 (Runtime State) → MVP3 (LDSS) → MVP4 (E2E)
- **Key Files:** `tests/run_tests.py`, `docker-up.py`, `docs/ADR/`, `docs/MVPs/`
- **Test Suites:** `--suite mvp1` | `--suite mvp2` | `--suite mvp3` | `--suite mvp4` | `--suite backend` | `--suite engine`
- **Memory Location:** `C:\Users\YvesT\.claude\projects\D--WorldOfShadows\memory\`

Last updated: 2026-04-29