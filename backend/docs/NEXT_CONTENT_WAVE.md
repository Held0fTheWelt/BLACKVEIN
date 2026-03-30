# Next Content Wave: Readiness Checklist

## Prerequisites for W5+ Content Work

### W4 Completion Gates

All of the following must be true before starting W5:

- [x] **Gate 1 closed:** System tests pass (6/6 E2E tests, all scenarios)
- [x] **Gate 2 closed:** Persistence verified (8/8 tests, save/load/resume works)
- [x] **Gate 3 closed:** UI usability improved (4 questions answered by UI)
- [x] **Gate 4 closed:** Demo paths reproducible (3 paths, operator-ready)
- [x] **Gate 5 closed:** MVP boundary locked (scope audit complete)

### Testing Baseline

Before new content work begins:

- **Minimum:** 2865+ tests passing (W4 baseline)
- **Coverage:** 78.54%+ (W4 baseline)
- **Regressions:** Zero known critical issues
- **E2E suite:** 100% pass rate
- **Demo paths:** All 3 paths reproducible

### System Stability Signals

- No crashes on valid operator input
- No data loss on session save/load
- No memory leaks in multi-turn execution
- No silent failures in validation
- Error handling works as designed

---

## What W5+ Can Safely Build On

### 1. **Session Persistence Foundation**

W4 delivered:
- ✅ JSON file-based persistence (works)
- ✅ Full state recovery on resume (verified)
- ✅ Metadata preservation (tested)
- ✅ Turn counter tracking (working)

W5+ can:
- Build session list/browser (uses existing save/load)
- Add session archive functionality (uses existing load)
- Implement session branching (creates new session files)
- Build admin tools (reads existing session structure)

W5+ should NOT:
- Redesign persistence layer (it works, don't break it)
- Migrate to database (stability risk)
- Change session file format (breaks resume from W4 sessions)
- Add transactional guarantees (scope creep)

---

### 2. **Multi-Module Architecture**

W4 demonstrated:
- ✅ Module loading system (content.module_loader)
- ✅ Module registry (available_modules list)
- ✅ Module-agnostic session/turn execution
- ✅ Character/scene/trigger definitions (God of Carnage proves pattern)

W5+ can:
- Add new story modules (follow God of Carnage pattern)
- Extend character archetypes (use existing schema)
- Add new scenes to existing modules
- Create new trigger/escalation patterns

W5+ must:
- Use same module file structure
- Follow same character attribute schema
- Implement triggers same way
- Preserve session compatibility across modules

---

### 3. **AI Adapter Integration**

W4 confirmed:
- ✅ dispatch_turn routes to mock or AI mode
- ✅ adapter registry system works
- ✅ AI output flows through validation guards
- ✅ Mock mode deterministic (for testing)

W5+ can:
- Switch between different AI adapters (same interface)
- Optimize prompt engineering for new modules
- Add response filtering/validation layers
- Tune context window usage

W5+ should NOT:
- Change adapter interface (breaks compatibility)
- Bypass validation guards (core safety mechanism)
- Add new decision pipeline (unstable, needs testing)
- Remove mock mode (essential for testing/demo)

---

### 4. **Validation & Guard System**

W4 proved:
- ✅ Structural guards catch invalid decisions
- ✅ Domain guards validate narrative consistency
- ✅ Rejected decisions don't corrupt state
- ✅ Partial acceptance works (some deltas apply)

W5+ can:
- Add new guard types (new validation rules)
- Extend delta validation (new character attributes)
- Add narrative consistency checks (new patterns)
- Implement recovery strategies (new fallback paths)

W5+ must:
- Maintain guard pass/fail semantics
- Preserve canonical state consistency
- Keep validation errors explicit
- Never silently drop changes

---

### 5. **UI Shell Framework**

W4 provided:
- ✅ Jinja templates (session_shell.html, base.html)
- ✅ Panel structure (scene, interaction, history, debug)
- ✅ Form submission (operator input → /play/<id>/turn)
- ✅ Session context variables (passed from Flask routes)

W5+ can:
- Enhance panel content (richer scene descriptions)
- Add new panels (player notes, strategy board)
- Extend quick-action helpers
- Add keyboard shortcuts
- Implement real-time updates (if upgrading from Jinja)

W5+ should NOT:
- Change session_id parameter passing
- Remove debug panel (needed for diagnostics)
- Redesign route structure (/play, /play/start, /play/<id>)
- Change session data storage (Flask session dict)

---

### 6. **Test Infrastructure**

W4 established:
- ✅ E2E test framework (test_e2e_god_of_carnage_full_lifecycle.py)
- ✅ Persistence tests (test_session_persistence.py)
- ✅ Session fixtures (test_user, auth fixtures)
- ✅ 2865+ existing tests (regression baseline)

W5+ can:
- Add tests for new modules
- Extend E2E scenarios (new story paths)
- Test new guard types
- Test new adapter implementations

W5+ must:
- Maintain existing test suite (2865+ must still pass)
- Use same pytest framework
- Keep fixtures compatible
- Document new test patterns

---

## Content Wave Readiness: Final Checklist

Use this checklist before starting W5:

```markdown
### W4 Closure Verification

- [ ] All 5 gates closed (signed by Product/Eng)
- [ ] Regression baseline established (git tag: w4-complete)
- [ ] Demo paths tested 3+ times (reproducible)
- [ ] MVP boundary document published
- [ ] Deferred features list reviewed (no surprises)

### System Health Check (Pre-W5)

- [ ] Run full test suite → 2865+ passing
- [ ] Run E2E suite → 6/6 passing
- [ ] Test demo paths → all 3 reproducible
- [ ] Check code coverage → 78%+
- [ ] Review known issues → none blocking W5

### Team Alignment

- [ ] Product confirms scope for W5
- [ ] Engineering confirms technical dependencies
- [ ] QA confirms test coverage baseline
- [ ] Demo participants reviewed fallback guide
- [ ] Timeline agreed (no pressure on stability)

### W5 Planning

- [ ] Module authoring guide documented
- [ ] Character schema documented
- [ ] Scene format documented
- [ ] Trigger/escalation pattern guide
- [ ] New module template created

### Go/No-Go Decision

**Ready for W5?** (confirm below)

- [ ] All checkboxes above are checked
- [ ] No blockers or unknowns remain
- [ ] Team aligned on W5 scope
- [ ] Risk register reviewed

**Decision:** `[ ] GO [ ] NO-GO [ ] HOLD`

```

---

## Example W5 Work (Not Commitments)

### Scenario: "Add a second module"

**Preparation (use W4 boundary):**
1. Load God of Carnage module → understand structure
2. Review character schema → design new characters
3. Review scene format → design new scenes
4. Review trigger system → design new escalation patterns

**Implementation:**
1. Create new module directory (follow pattern)
2. Author characters, scenes, triggers (follow schema)
3. Add to available_modules list
4. Create tests for new module (use E2E framework)
5. Run full regression → verify no breaks

**Rollout:**
1. Session shell works with new module (no changes needed)
2. Persistence works (same schema)
3. Demo paths work (same flow, different content)
4. Tests updated (new module covered)

**Why this works:** W4 boundary is stable. New module reuses all infrastructure.

---

## If W4 Boundary Is Broken

If during W5 work you find that W4 boundary is violated (e.g., persistence doesn't work with new module), **stop and escalate:**

1. Create bug report (reference what broke)
2. Do NOT work around it (don't add hacks)
3. Revert to W4 checkpoint (git tag: w4-complete)
4. Fix root cause (may require W4.1 work)
5. Re-verify boundary
6. Resume W5

This prevents technical debt and keeps boundary honest.

---

## Questions to Ask Before W5

**Q: "Can we add feature X in W4?"**
> A: Only if it's in MVP_BOUNDARY.md "Included" section, OR it fixes a bug, OR it has zero impact on existing features. Otherwise, it's W5+.

**Q: "Do we have all the content tools ready?"**
> A: Not in W4. Module authoring guide is part of W5 planning. God of Carnage proves the technical approach.

**Q: "What's the risk of W5?"**
> A: Technical risk is low (infrastructure proven). Content risk is medium (new stories need playtesting). Team risk is low (process is known).

**Q: "When should W5 start?"**
> A: After W4 sign-off AND team alignment on W5 scope. This document is a gate, not a starting gun.

---

## Ownership & Maintenance

- **MVP Boundary:** Engineering
- **Next Wave Plan:** Product
- **Test Baseline:** QA
- **Demo Readiness:** Operators

Changes to this document require stakeholder discussion (it's part of project contract).
