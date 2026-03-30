# Demo Scripts: Three Reproducible Paths

## Overview

Three complete demo paths demonstrating different aspects of the system:
1. **Good Run** — Coherent story progression, clean execution (5-7 turns, ~30-45 seconds)
2. **Stressed Run** — Pressure escalation and recovery (8-12 turns, ~1-1.5 minutes)
3. **Failure/Recovery** — Error handling and graceful degradation (3-4 turns, ~20-30 seconds)

All paths use the God of Carnage module. Operator delivers calm narration while system executes turns.

---

## Path 1: Good Run (Coherent Progression)

**Objective:** Show clean story progression, character consistency, escalation within bounds.

**Setup:** Fresh session, mock execution mode (deterministic turns)

### Operator Script

```
Turn 1: "Everyone settles in. I acknowledge the tension and try to establish common ground."
Turn 2: "I ask Annette about her concerns. I listen carefully and nod."
Turn 3: "I propose we discuss this calmly, focusing on what we agree on."
Turn 4: "I suggest a way forward that respects everyone's needs."
Turn 5: "I make a final plea for civility and shared understanding."
```

### Expected Checkpoints

| Checkpoint | Expectation |
|-----------|-------------|
| **Turn 1** | Scene loads, characters visible, initial tension established |
| **Turn 3** | Dialogue reflects operator input, characters respond in character |
| **Turn 5** | Situation moves toward resolution or escalation (narratively coherent) |

### Timing

- **Total duration:** ~30-45 seconds
- **Turn execution:** ~6-8 seconds per turn (mock mode)
- **Key moments to highlight:** Turn 1 (setup), Turn 3 (engagement), Turn 5 (climax)

### Demo Narration

> "This session demonstrates the core narrative loop. Operator input flows through the system—the engine updates character state, detects triggers, and produces coherent narrative output. Notice how the characters respond to what the operator says."

---

## Path 2: Stressed Run (Pressure + Recovery)

**Objective:** Show system's handling of escalation, coalition shifts, pressure dynamics, and recovery moments.

**Setup:** Fresh session, mock execution mode

### Operator Script

```
Turn 1: "I notice the room is getting more tense. I try to defuse it."
Turn 2: "I push back on a particularly harsh comment."
Turn 3: "The situation is escalating. I escalate pressure, trying to break the stalemate."
Turn 4: "I notice Michel and Alain are aligning against me. I try to split the coalition."
Turn 5: "I appeal to Annette directly, trying to shift the dynamic."
Turn 6: "The pressure is building. I push harder."
Turn 7: "I step back and try a different approach—appealing to their better instincts."
Turn 8: "I propose a genuine compromise that addresses the core issues."
Turn 9: "I reinforce the compromise and ask for their commitment."
Turn 10: "I check in: is everyone willing to move forward?"
```

### Expected Checkpoints

| Checkpoint | Expectation |
|-----------|-------------|
| **Turn 1-3** | Initial escalation, pressure visible in scene description |
| **Turn 4-6** | Coalition shifts, character relationships update, pressure peaks |
| **Turn 7-9** | Recovery moments, alternative approaches shown, pressure moderates |
| **Turn 10** | Session stable, narrative coherent, resolution visible |

### Timing

- **Total duration:** ~1-1.5 minutes (mock turns faster)
- **Key moments to highlight:** Turn 3 (pressure peak), Turn 7 (recovery start), Turn 10 (resolution)

### Demo Narration

> "This path shows the system's richness. Beyond simple turns, we see relationship dynamics, coalition shifts, and pressure escalation. The operator can steer the narrative through different tensions, and the engine maintains character consistency throughout."

---

## Path 3: Failure/Recovery (Error Handling)

**Objective:** Show graceful error handling and diagnostic visibility without system crash.

**Setup:** Fresh session, mock execution mode

### Operator Script

```
Turn 1: "I take a breath and speak calmly: everyone needs to listen."
Turn 2: [Trigger invalid input] ""  (empty string)
  OR: "xyzabc123garbage" (gibberish)
  OR: (submit without text)
Turn 3: "Let me try again. I apologize and ask for a moment of silence."
Turn 4: "I acknowledge everyone's feelings and propose a path forward."
```

### Expected Checkpoints

| Checkpoint | Expectation |
|-----------|-------------|
| **Turn 1** | Session initializes, scene loads |
| **Turn 2** | Error handled gracefully (validation fails, feedback shown) |
| **Debug panel** | Shows guard outcome, diagnostic info visible |
| **Turn 3** | Session continues (error doesn't crash system) |
| **Turn 4** | Normal execution resumes |

### Timing

- **Total duration:** ~20-30 seconds
- **Key moments to highlight:** Turn 2 (error trigger), Debug expansion (diagnostics), Turn 3 (recovery)

### Demo Narration

> "Even with invalid input, the system handles gracefully. The validation layer rejects the malformed decision, the debug panel shows why, and the session continues. This is critical for production readiness—we don't crash on bad input."

---

## Quick Execution Checklist

```markdown
## Before Demo

- [ ] System running (Flask server ready, God of Carnage module loaded)
- [ ] Fresh session created
- [ ] Mock execution mode confirmed (deterministic turns)
- [ ] Browser zoomed to readable size
- [ ] Demo scripts printed or visible in second window

## Path 1 Execution

- [ ] Input Turn 1 action → verify scene loads
- [ ] Input Turn 3 action → verify dialogue update
- [ ] Input Turn 5 action → verify escalation/resolution
- [ ] Total time < 45 seconds

## Path 2 Execution

- [ ] Input turns 1-3 → escalation visible
- [ ] Input turns 4-6 → coalition shift visible
- [ ] Input turns 7-9 → recovery visible
- [ ] Input turns 9-10 → resolution visible
- [ ] Total time < 90 seconds

## Path 3 Execution

- [ ] Turn 1 → normal execution
- [ ] Turn 2 → empty/invalid input → error handling shown
- [ ] Expand debug panel → diagnostics visible
- [ ] Turn 3 → session continues (proves no crash)
- [ ] Total time < 30 seconds

## Success Criteria

- [ ] All 3 paths complete without crashes
- [ ] Operator can narrate each path without cue cards
- [ ] Timing acceptable for presentation
- [ ] Demo transitions smooth between paths
```

---

## Common Issues & Recovery

See [DEMO_FALLBACK_GUIDE.md](./DEMO_FALLBACK_GUIDE.md) for handling common demo issues.
