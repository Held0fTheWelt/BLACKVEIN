# MVP Definition

## Purpose

This document defines the scope, boundaries, authority model, and quality principles of the World of Shadows MVP. It is the canonical source for understanding what the MVP is, what it explicitly is not, and the principles that govern MVP development.

---

## What the MVP Is

The MVP is a **formally secured AI-story vertical slice**. It includes:

1. **One content module**: *God of Carnage* (reference implementation for story content)
2. **One playable run** of that module
3. **One usable UI** for session start, scene display, character/conflict tracking, turn execution, and diagnostics
4. **One controlled AI story loop** with validation gates and error recovery
5. **One hybrid AI execution model** with role-separated SLMs and LLMs
6. **A World Engine** with: session state, turn state, event log, state deltas, rule/validation layer
7. **Test coverage** for contracts, content, runtime, AI integration, and end-to-end flows

---

## What the MVP is NOT

The MVP **explicitly excludes**:

- A generic authoring tool for arbitrary story modules
- An open multi-module ecosystem
- Free lore invention by the AI
- Autonomous AI with write rights to canon
- Unlimited free character or scene generation
- A real large multi-agent system as a mandatory component
- Complex cinematic or presentation features before functional stability
- A complex player-choice economy outside the core loop
- A broad content wave beyond *God of Carnage*
- Any scope expansion not directly required for MVP function
- A sprawling model landscape with many specialized models without clear roles
- Replacement of the actual story core by pure SLM logic

---

## System Authority Model

The MVP defines four boundaries of responsibility:

### Engine (World Engine)
Responsible for: canonical states, state transitions, rule validation, delta application, session progress, error handling, logging, reproducibility.

**Authority**: The Engine is the **authoritative instance**. Only the Engine commits canonical state.

### AI (Story Models)
Responsible for: scene interpretation, conflict dynamics, trigger detection, reaction impulses, proposals for permissible state changes.

**Authority**: The AI is **not authoritative**. It may only make **structured proposals** that the Engine must validate before committing.

**Core Rule**: *"The AI may be creative, but never sovereign. The Engine remains sovereign, but never blind."*

### SLM Helper Roles
SLMs assist with narrow, fast, strictly limited tasks:
- Context compression
- Trigger extraction
- Pre-normalization of structured output
- Cheap routing
- Pre-check for obvious contract violations
- Debug/diagnostic summaries

**Authority**: SLMs are **auxiliary models, not story sovereigns**. They prepare the canon flow; they do not lead it.

### UI (User Interface)
Responsible for: visibility, operation, diagnostics, history insight, debug support.

**Authority**: The UI makes no canon decisions.

### Content (Modules)
Content defines: characters, relationships, scenes, transitions, triggers, escalation axes, end states, interpretation spaces.

**Authority**: Content delivers the **formally permitted possibility space** that constrains the Engine and informs the AI.

---

## Wave Structure W0–W4

| Wave | Focus | Primary Deliverables | Gate Criteria |
|------|-------|----------------------|---------------|
| **W0** | **Foundation & Contract** | 4 canonical docs, schema skeletons, test skeletons, SLM/LLM role definitions, folder structure | Core terms defined, contracts documented, SLM/LLM roles separated |
| **W1** | **God of Carnage as Real Module** | Full module.yaml, characters.yaml, relationships.yaml, scenes.yaml, triggers.yaml, endings.yaml, content validator | Module loads stably, at least one run formally possible |
| **W2** | **Dynamic AI Story Core** | Story loop skeleton (W2.0), real AI adapter with JSON (W2.1), guard/validation layer (W2.2), context/memory logic (W2.3), internal SLM/LLM roles (W2.4), recovery/stability (W2.5) | Story loop stable, guard layer enforced, recovery working |
| **W3** | **Playable UI with Diagnostics** | Session start view, scene display, character panel, conflict panel, debug panel, minimum API endpoints (start session, get session, execute turn, get logs, get state) | Minimum playable, diagnostics discoverable |
| **W4** | **MVP Hardening & First Playable** | System tests, E2E tests, balancing, AI quality, session persistence, UI usability, demo script | MVP-ready for demonstration |

---

## Quality Principles

1. **No implicit truth**: Everything central must be defined in content, contract, or state — not in engine code or undocumented AI behavior.

2. **No special logic for God of Carnage**: It is the reference module, not an exception. All engine logic must work generically.

3. **No free AI canon**: The AI may propose meaning and conflict movement, but it may not set new world truth.

4. **Validation before application**: Every AI proposal is checked against the contract before it changes state.

5. **Diagnostics is mandatory**: Every turn generates logs (event log, AI decision log, validation log, state delta log, recovery log).

6. **SLMs as tools, not sovereigns**: Narrow helper roles are better than many diffuse specialized models.

7. **Keep the hybrid architecture small**: Few clearly defined auxiliary roles instead of a scattered model landscape.

---

## Anti-Scope-Creep Policy

The MVP is **strictly bounded**. Features requested during W0–W4 that fall outside these categories must be deferred:

- ❌ **New content modules** beyond God of Carnage
- ❌ **New AI roles** beyond SLM helpers + story LLM + Engine
- ❌ **Presentation enhancements** beyond functional diagnostics
- ❌ **Ecosystem features** (authoring tools, module repositories, multiplayer beyond a single run)
- ❌ **Advanced choice economies** (faction systems, resource trading, multi-branch narratives)

**Scope expansion is a W5+ decision**, not a W0–W4 task. Requests must be documented in open questions for later waves, not implemented.

---

## Related Documents

- [God of Carnage Module Contract](./god_of_carnage_module_contract.md) — Content structure and validation expectations
- [AI Story Contract](./ai_story_contract.md) — AI output format, SLM/LLM roles, guard validation
- [Session Runtime Contract](./session_runtime_contract.md) — Session state, turn pipeline, recovery behavior

---

**Version**: W0 (2026-03-26)
