# W4 MVP Boundary Lock

**Status:** CLOSED (as of 2026-03-30)

This document locks the W4 MVP scope. All features below this line are production-ready. Features deferred to W5+ are explicitly listed.

---

## Included in W4 MVP ✅

### Core Session Engine

- ✅ Session lifecycle (create, execute turns, conclude)
- ✅ Multi-turn turn execution with state management
- ✅ Turn dispatcher with mock/AI mode selection
- ✅ Mock decision mode for deterministic testing
- ✅ Real runtime path (dispatch_turn with actual module/adapter)
- ✅ Error handling and graceful degradation
- ✅ Session store with module references

### State Management

- ✅ Canonical state (character data, relationships, scene)
- ✅ Context layers (short-term, history, progression, relationships, lore)
- ✅ State deltas and change tracking
- ✅ Guard validation (structural + domain)
- ✅ Degraded state markers for recovery

### Persistence Layer

- ✅ Session serialization to JSON
- ✅ Session deserialization from disk
- ✅ Full state recovery on resume
- ✅ Turn counter preservation
- ✅ Metadata preservation
- ✅ Independent session file management

### Content Module

- ✅ God of Carnage module (complete)
- ✅ Scene definitions (6 phases)
- ✅ Character data (4 characters: Véronique, Michel, Annette, Alain)
- ✅ Escalation paths and trigger system
- ✅ Dialogue generation (via AI or mock)
- ✅ Coalition dynamics and relationship tracking

### Web Interface

- ✅ Session creation flow (`/play`, `/play/start`)
- ✅ Session shell view (`/play/<session_id>`)
- ✅ Session metadata display (module, turn, status, scene)
- ✅ Scene narrative display (placeholder + data-driven)
- ✅ Interaction input form (textarea + submit)
- ✅ Turn history panel (table view)
- ✅ Character sidebar (relationship summary)
- ✅ Conflict & escalation panel (pressure, trends)
- ✅ Debug & diagnostics panel (collapsible)
- ✅ Quick-action helper buttons (Observe, Interact, Move)
- ✅ Error display (validation failures shown gracefully)

### Testing & Verification

- ✅ E2E lifecycle tests (6 tests, all scenario types)
- ✅ Session persistence tests (8 tests, all persistence paths)
- ✅ Regression test suite (2865+ tests baseline)
- ✅ 78.54% code coverage maintained
- ✅ No test regressions from W4 additions

### Documentation

- ✅ UI Usability Guide (4 questions, visual hierarchy)
- ✅ Demo Scripts (3 paths, operator-ready)
- ✅ Demo Fallback Guide (10+ issue recovery strategies)
- ✅ MVP Boundary Document (this file)
- ✅ Next Content Wave Readiness (planning document)

### Deployment-Ready

- ✅ All core features tested and working
- ✅ Error paths handled gracefully (no crashes)
- ✅ Persistence working (save/load verified)
- ✅ Web routes accessible and functional
- ✅ Demo paths reproducible and stable
- ✅ Code quality maintained (no regressions)

---

## Deferred from W4 → W5+

### Additional Content Modules

- ❌ New story modules (beyond God of Carnage)
- ❌ Additional character types/archetypes
- ❌ New scene types or narrative styles
- ❌ Advanced character generation

**When:** W5+ (content expansion phase)
**Why:** God of Carnage demonstrates system capability. Additional modules should follow same proven pattern.

### Relationship & Coalition Fine-Tuning

- ❌ Coalition balancing (weights, triggers)
- ❌ Relationship arc optimization
- ❌ Escalation curve tuning
- ❌ De-escalation mechanics refinement

**When:** W5+ (balancing phase)
**Why:** System works, needs gameplay iteration with user feedback.

### AI Quality Improvements

- ❌ Prompt engineering optimization
- ❌ Response filtering/validation enhancements
- ❌ Context window tuning
- ❌ Hallucination prevention measures

**When:** W5+ (AI quality phase)
**Why:** Current AI path works; improvements are iterative, not foundational.

### Advanced UI Features

- ❌ Real-time scene updates (WebSockets)
- ❌ Rich text formatting in scene panel
- ❌ Session list / history browser
- ❌ Drag-and-drop quick action templates
- ❌ Keyboard shortcuts (operators)

**When:** W5+ (UI polish phase)
**Why:** Current Jinja template shell is functional. Enhancements after MVP validation.

### Advanced Persistence

- ❌ Database backend (currently file-based JSON)
- ❌ Batch export/import (currently single file)
- ❌ Session replay with branching
- ❌ Session archive/cleanup automation

**When:** W5+ (persistence hardening phase)
**Why:** File persistence is sufficient for MVP. Database/scaling comes later.

### Production Ops Features

- ❌ Admin dashboard for session management
- ❌ Telemetry/logging aggregation
- ❌ Performance monitoring (APM)
- ❌ Multi-user session sharing
- ❌ Usage analytics

**When:** W5+ (operations phase)
**Why:** Not required for single-operator MVP validation.

---

## Scope Lock Rules

The following rules govern what can be added to W4 after this gate closes:

1. **No new features** without explicit scope revision
2. **Bug fixes only** for critical path issues (crashes, data loss)
3. **Documentation updates** for clarity (no functional changes)
4. **Performance optimizations** if they improve baseline (no architectural changes)
5. **Test additions** that validate existing features (no new features tested)

**Exceptions require:** Scope change proposal + stakeholder approval

---

## Quality Gates: Closure Verification

### Testing

- [x] E2E tests pass (6/6 tests, all scenarios)
- [x] Persistence tests pass (8/8 tests, all paths)
- [x] Regression baseline maintained (2865+ tests, 78.54% coverage)
- [x] No known critical bugs in core paths

### Functionality

- [x] Session creation works (API + web)
- [x] Turn execution works (real runtime, deterministic)
- [x] Session persistence works (save/load verified)
- [x] Web shell renders without errors
- [x] Demo paths reproducible (tested 3 times each)

### Documentation

- [x] MVP boundary clear and explicit
- [x] Deferred features listed with rationale
- [x] Demo paths documented with operator scripts
- [x] UI usability guide complete
- [x] Fallback strategies documented

### Sign-Off

| Role | Status | Date |
|------|--------|------|
| **Engineering** | ✅ Ready for review | 2026-03-30 |
| **Product** | ⏳ Awaiting review | — |
| **QA** | ⏳ Awaiting verification | — |

---

## Next Steps: Content Wave Readiness

See [NEXT_CONTENT_WAVE.md](./NEXT_CONTENT_WAVE.md) for prerequisites and what the next wave can safely build on.

## Historical Note

This boundary was set at the conclusion of W4. Prior wave boundaries:
- **W1 (complete):** Content module authoring, schema design
- **W2 (complete):** Session API foundation, turn executor
- **W3 (complete):** Web UI shell, debug routing, session storage prep
- **W4 (complete):** System tests, persistence, UI clarity, demos, boundary lock

W5 planning depends on this boundary holding stable.
