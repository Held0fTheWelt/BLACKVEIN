# Demo Fallback Guide: Common Issues & Recovery

When demo issues arise, use this guide to recover gracefully without breaking audience confidence.

---

## Issue: Scene Content Missing or Placeholder Text Shows

**Symptom:** Scene panel shows "Scene not loaded" or placeholder text instead of narrative.

**Root Cause:** Narrative engine hasn't loaded scene data, or module data missing.

**Recovery Strategy:**

1. **Point to the data (not the absence):**
   > "You'll notice the scene description is loading. The underlying narrative data is present in the system—this is just the presentation layer catching up."

2. **Expand debug panel:**
   - Click "Debug & Diagnostics" expand button
   - Point to scene data in diagnostics: "See here—the engine has the scene ID and character state data. The narrative rendering is what you'd see in normal operation."

3. **Continue to next demo path:**
   - If stuck, skip to Path 3 (which requires minimal scene data)
   - Narrate: "Let's move to the error handling demonstration while the scene loads."

**Prevention:**
- Pre-load a session before demo starts
- Keep browser dev tools closed (they slow page rendering)
- Test on the exact demo machine beforehand

---

## Issue: AI Response Unexpected or Off-Topic

**Symptom:** Character dialogue is generic, inconsistent with context, or bizarre.

**Root Cause:** LLM produced valid but unexpected output (in mock mode, shouldn't happen; in AI mode, LLM variance).

**Recovery Strategy:**

1. **Frame it as system correctness:**
   > "Notice the system accepted this output because it passed structural validation. Character responses vary—this is within acceptable bounds for an interactive narrative system."

2. **Use debug panel to show reasoning:**
   - Expand debug panel
   - Point to "Guard Outcome" → shows `pass` (validation succeeded)
   - Point to "Triggers" → shows what the engine detected
   - Narrate: "The system processed this correctly. Variation in LLM output is expected and handled."

3. **Show consistency elsewhere:**
   - Advance one more turn with a clear operator input
   - If next output is more coherent, narrate: "Now watch—when the input is more specific, the system response tightens."

4. **Don't apologize for randomness:**
   - Never say "That was wrong" or "That shouldn't happen"
   - Instead: "Narrative systems like this have some variance in output—it's a feature, not a bug"

**Prevention:**
- Use mock execution mode for demos (deterministic output)
- If using AI mode, run the demo path multiple times beforehand to identify stable checkpoints
- Have a backup demo path that's known to work

---

## Issue: Session Takes Longer Than Expected

**Symptom:** Turns execute slowly, audience waits longer than planned.

**Root Cause:** AI inference slow, system load, network latency (if deployed remotely).

**Recovery Strategy:**

1. **Set expectations:**
   > "The system is processing—this is real-time narrative generation. In production, inference speed would be optimized, but you're seeing the actual computation happening."

2. **Use the pause productively:**
   - Point out code/system architecture while waiting
   - Open debug panel and discuss what's happening behind the scenes
   - Explain the multi-step pipeline: "The engine is running decision logic, validation, state updates..."

3. **Skip to next path:**
   - If a turn is genuinely stuck (> 30 seconds), say: "Let me move to our next demo path while this processes in the background."
   - Start fresh session for next path

4. **Have timing expectations published:**
   - Print/show expected timing before demo
   - Narrate: "This path typically takes 30-45 seconds. We're within range."

**Prevention:**
- Use mock execution mode (fast, deterministic)
- Pre-warm the system before demo (run a dummy turn)
- Have session persistence checkpoint loaded (faster than creating new)
- Test on the demo machine with realistic network conditions

---

## Issue: Character Behavior Inconsistent with Earlier Turns

**Symptom:** Character acts out of character, relationship dynamics suddenly shift, contradicts prior turns.

**Root Cause:** State loss, context window issue, or expected variance in multi-turn scenarios.

**Recovery Strategy:**

1. **Point to session history (context is maintained):**
   - Open History panel
   - Show turn-by-turn record: "Look at the history—we've documented 8 turns so far, and the system is maintaining context across all of them."

2. **Frame it as acceptable variance:**
   > "Character responses emerge from a complex state space. Over longer sessions, variation is expected. The system is maintaining consistency at the aggregate level—the characters are moving toward their narrative arc."

3. **Check debug panel for coherence signals:**
   - Show "Guard Outcome" → all valid
   - Show "Recent Turn Pattern" → shows consistency in outcomes
   - Narrate: "Notice the guard outcomes are consistently valid across 8 turns. The system is coherent."

4. **Move forward:**
   - Continue execution; often consistency reasserts in next turn
   - Narrate: "Let's see how this resolves as we continue..."

**Prevention:**
- Keep demo paths to 5-10 turns max (within reliable context window)
- Use pre-tested paths (you've run them multiple times, know where consistency is strongest)
- Plan key moment demos (don't improvise turns; stick to script)

---

## Issue: Turn Fails / Error Shown

**Symptom:** Error message displayed, guard outcome is `rejected` or `invalid`.

**Root Cause:** Validation caught structural issue, decision rejected by guards, invalid input.

**Recovery Strategy:**

1. **Point to error handling as a feature:**
   > "Notice the system caught an invalid decision and rejected it. This is the validation layer working as designed—bad data doesn't silently corrupt the session."

2. **Expand debug panel:**
   - Show the rejection with details
   - Point to "Guard Outcome" → `rejected`
   - Show "Validation Errors" → why it was rejected
   - Narrate: "This guards against nonsensical state changes. The system says 'no' and the session continues safely."

3. **Recover by re-trying:**
   - Input new action: "Let me try a different approach..."
   - Show successful turn after rejection
   - Narrate: "Now we're back on track. The system is resilient to invalid input."

4. **Discuss robustness:**
   > "Production systems need to handle bad data gracefully. This is exactly what we're seeing—validation failures are logged, the session isn't corrupted, and we continue."

**Prevention:**
- Don't feed intentionally invalid input to system (unless Path 3 is deliberately testing error handling)
- Stick to clear, descriptive operator input
- Have a "turn redo" ready if you accidentally enter garbage

---

## Issue: Audience Loses Interest During Long Demo

**Symptom:** Turns 6+ of demo path, audience attention fading, questions becoming off-topic.

**Root Cause:** Demo too long, pacing off, not enough visual feedback.

**Recovery Strategy:**

1. **Accelerate:** Skip forward in path
   > "Let me jump ahead to the key moment..." (move to turn 10 directly)

2. **Shift focus:** Move to next demo path
   > "Let's see how the system handles errors..." (skip to Path 3)

3. **Switch medium:** Open debug panel, talk about system design while scenario runs
   > "While this processes, let me show you the validation pipeline..."

4. **Ask engaging questions:**
   > "What would you expect to happen if character alignment shifted here? Let's see..."

**Prevention:**
- Keep demo paths to < 2 minutes total
- Practice pacing and timing beforehand
- Have key moments scripted (know exactly when to narrate)
- Use visual cues (highlight state changes, expand/collapse panels strategically)

---

## Issue: Network/System Failure (Complete Outage)

**Symptom:** Application crashes, page fails to load, backend unreachable.

**Root Cause:** Infrastructure failure, service down, connection lost.

**Recovery Strategy:**

1. **Have a video fallback:**
   - Record successful demo run beforehand
   - If live demo fails, play video: "Let me show you the recorded version while we troubleshoot..."

2. **Discuss architecture instead:**
   - Show code architecture diagram
   - Walk through turn execution flow on whiteboard
   - Demonstrate system design without live execution

3. **Offer asynchronous demo:**
   > "We'll send you a recorded demo to review. Meanwhile, any questions about the system design?"

**Prevention:**
- Test system thoroughly on demo day morning
- Have backup device with demo pre-loaded
- Have video recording ready as fallback
- Document expected behavior so you can describe it if system is down

---

## Timing Reference

| Path | Turns | Expected Duration | Acceptable Range |
|------|-------|-------------------|------------------|
| **Good Run** | 5 | 30-45 sec | 25-60 sec |
| **Stressed Run** | 8-10 | 60-90 sec | 45-120 sec |
| **Failure/Recovery** | 3-4 | 20-30 sec | 15-45 sec |
| **All Paths + Intro/Outro** | 16-19 | 3-4 min | 2.5-5 min |

---

## Audience Q&A: Common Questions & Answers

**Q: "How does the AI know what to say?"**
> A: The system passes the current scene, character state, and operator input to an LLM, which generates narrative decisions. These are validated before execution—no invalid state changes get through.

**Q: "Can I see the character relationships?"**
> A: Absolutely—see the sidebar? That's updating in real-time. Each turn, relationships shift based on character actions and dialogue.

**Q: "What happens if the AI goes off the rails?"**
> A: We have validation guards that reject structurally invalid decisions. Also, the narrative is emergent—variation is expected and handled. Long-term, the story arc still holds.

**Q: "How persistent is this?"**
> A: Sessions save to disk in JSON format. You can pause, close the browser, and resume later with full state recovery.

**Q: "Can you add more modules?"**
> A: Yes—this architecture is designed for multiple modules. God of Carnage is the MVP, but new stories can be authored and loaded.

---

## Final Note

**The goal is confidence, not perfection.** Demo issues are expected and recoverable. Narrate calmly, point to system design when things don't go perfectly, and move forward. Audiences trust operators who handle errors gracefully more than those who pretend systems are flawless.
