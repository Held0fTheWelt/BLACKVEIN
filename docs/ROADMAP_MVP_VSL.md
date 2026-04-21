# ROADMAP_MVP_VSL

## 1. Purpose

This document defines the **MVP target state** for the World of Shadows vertical slice.

It is the product-level target document for the slice.  
It is **not** the freeze rulebook and **not** the execution task series.

Its purpose is to make the intended slice stable enough that:

- freeze artifacts can be written against a concrete target,
- the current codebase can be compared against a real end state,
- later execution tasks can be derived without drifting into generic AI-roleplay, prose-generation, or architecture-only work.

The MVP targets a **guided interactive drama runtime**.

It is not intended to be:
- a chatbot,
- a script-echo system,
- a generic narrative sandbox,
- or a “strong model + nice prompts” prototype.

The player must be able to act through free input inside a dramatically coherent authored situation.  
The AI must propose bounded dramatic behavior.  
The engine must validate, commit, and preserve canonical truth.  
The visible result must feel like a scene being led, not like a summary being generated.

---

## 2. MVP product thesis

The MVP exists to prove that World of Shadows can turn authored dramatic material into a **credible, truth-aligned, scene-led interactive dramatic experience**.

The slice is not successful if it merely:

- produces polished prose,
- imitates a voice,
- echoes source material,
- chats plausibly,
- or creates individually strong turns without sustained scene pressure and consequence continuity.

The slice is successful only if it demonstrates:

- source-aware dramatic steering,
- stable character identity,
- explicit scene direction,
- truth-aligned visible output,
- consequence continuity,
- credible live interaction,
- and a runtime structure that can later be exposed safely through MCP.

---

## 3. Intended player experience

The intended player experience is:

1. The player enters an authored dramatic situation through free input.
2. The runtime interprets the move as part of a live dramatic scene rather than as a command string or generic chat turn.
3. A scene-appropriate responder and response mode are selected.
4. The AI proposes bounded dramatic content within runtime semantics.
5. The engine validates and commits canonical consequences.
6. The player receives visible output that is supported by committed truth and shaped for dramatic legibility.
7. The consequences of the turn remain active across later turns.

The player should feel they are inside a living scene with pressure, asymmetry, and consequences.

---

## 4. Canonical MVP pillars

### 4.1 Source-to-game transformation

The slice must transform dramatic source into **playable dramatic machinery**, not preserve it merely as text.

At minimum, the slice must derive or structure:

- scene cores,
- pressure ladders,
- move families,
- relationship fault lines,
- reveal surfaces,
- escalation / de-escalation routes,
- repair possibilities,
- continuity hooks,
- and scene-guidance material strong enough to drive play rather than commentary.

### 4.2 Character minds

Important characters must remain stable over time, not merely in wording but in tactic, pressure response, relationship posture, and motive protection.

A character must not degrade into a generic model voice with cosmetic phrasing changes.

### 4.3 Scene direction

The slice must treat scene direction as a first-class runtime concern.

The runtime must not collapse into:
- disconnected local turns,
- summary-heavy output,
- generic Q&A,
- or repeated dramatic patterns without meaningful scene progression.

### 4.4 World truth

The engine remains the canonical owner of truth.

AI may propose.  
Validation shapes.  
Commit authorizes.  
Visible output must remain aligned with committed truth.

### 4.5 Live viability

The slice must be viable under live or near-live interaction conditions for its intended play style.

Latency, graceful scope handling, fallback behavior, and operator-visible diagnostics are product concerns, not secondary engineering details.

---

## 5. Canonical target layers

The MVP targets the following runtime layers.

### 5.1 Dramatic Source Layer
Owns transformation of authored material into playable slice structures.

### 5.2 Character Mind Layer
Owns stable character constraints, asymmetry, pressure response, and tactic plausibility.

### 5.3 Scene Director Layer
Owns scene-level shaping decisions such as responder choice, scene function, pacing mode, silence/brevity, and fallback shaping.

### 5.4 World Truth Layer
Owns validation, canonical consequences, committed state, continuity retention, and truth-aligned visible output.

These are **target responsibilities**, not yet implementation commitments.  
They are not claims that the current codebase already represents them explicitly, and they do not by themselves settle the final representation decision.  
Freeze work must convert these target responsibilities into explicit contracts, seams, and representation choices.

---

## 6. Slice scope

The first MVP slice is **God of Carnage**.

This slice is chosen because it offers:

- strong authored dramatic material,
- high relational pressure,
- constrained scene geometry,
- clear asymmetry among characters,
- and a good proving ground for turning source material into playable dramatic runtime.

The MVP must explicitly distinguish:

- what already exists as authored material,
- what is only source material,
- what already exists as structured slice-relevant material,
- and what must still be built for the slice.

---

## 7. Canonical scene behavior goals

The slice must support:

- free player input,
- scene-aware interpretation,
- responder selection,
- scene-function selection,
- bounded dramatic proposal,
- validation and commit,
- player-visible output,
- continuity carry-forward,
- and diagnostic replayability.

The slice must preserve the distinction between:

- what is proposed,
- what is validated,
- what is committed,
- and what becomes visible.

---

## 8. Canonical turn target

The MVP assumes a canonical dramatic turn model with at least these conceptual phases:

1. player move interpretation
2. scene assessment
3. responder selection
4. scene-function selection
5. pacing / silence / brevity shaping
6. proposed state effects
7. validation outcome
8. committed result
9. visible output shaping
10. continuity update
11. diagnostics and provenance capture

This is the product target for turn semantics.  
Freeze work must convert this into a starter contract with concrete field names, ownership, and seams.

---

## 9. Truth-aligned visible output

The MVP follows these core rules:

- Nothing visible without truth support.
- Nothing committed and dramatically relevant remains entirely invisible.
- Partial rejection must not produce stronger visible consequence than committed truth allows.
- Ambiguity may exist, but must not be used to hide missing runtime commitment.
- Constraint handling should remain scene-compatible rather than reading like raw system refusal where possible.

The visible experience must feel dramatically alive without outrunning committed truth.

---

## 10. Continuity and consequence

The slice must preserve consequence over multiple turns.

Continuity is not merely “history exists.”  
Relevant dramatic consequences must remain available to shape later turns.

The slice must preserve and prioritize continuity classes relevant to the dramatic scenario, including:

- situational pressure,
- dignity injury,
- alliance movement,
- revealed information,
- refused cooperation,
- blame pressure,
- repair attempts,
- and other slice-relevant continuity classes defined during freeze.

The runtime must not overload visible turns with too many simultaneous foreground consequences.

---

## 11. Quality goals

### 11.1 Credible scene response
Responses must function as scene moves, not summaries.

### 11.2 Stable character asymmetry
Important characters must behave as distinct dramatic agents, not as paraphrased variants of one engine.

### 11.3 Legible escalation
Pressure and escalation must be perceptible and reconstructable.

### 11.4 Subtext capacity
Responses must be capable of pressure, evasion, accusation, concealment, tactical implication, and socially meaningful ambiguity.

### 11.5 Repair capacity
The runtime must support repair or partial stabilization without resetting the scene.

### 11.6 Under-response protection
The runtime must not become so brief, graceful, or cautious that the scene starves.

### 11.7 Anti-summary behavior
The runtime must not replace scene work with narrative explanation.

### 11.8 Anti-misleading competence
Polished or tense output does not count as success unless it serves actual scene function and truth alignment.

---

## 12. MVP non-goals

The MVP does **not** aim to achieve:

- full script completeness,
- broad multi-module generalization,
- open-world improvisation,
- unconstrained roleplay freedom,
- maximal multi-agent breadth,
- or fully generalized authoring automation.

The MVP also does **not** optimize for:

- generic chatbot quality,
- prose beauty without scene function,
- prompt-only identity control,
- or broad MCP surface before the runtime itself is alive.

---

## 13. Freeze implications already assumed by the MVP

Even at roadmap level, the MVP already assumes that freeze work will define:

- a current-state vs target-state bridge,
- a starter canonical turn schema,
- field ownership,
- a proposal / validation / commit / visible-output seam,
- a God of Carnage asset inventory,
- a scene-director representation choice,
- a dry-run method,
- a minimal review/governance mode,
- dependency and escalation rules,
- and traceability into later execution tasks.

These are not optional refinements.  
They are required to keep the MVP grounded in the real stack.

---

## 14. MCP position in the MVP

MCP belongs in the MVP as the **canonical controlled access layer**, but only after the slice runtime itself is alive enough to expose meaningfully.

For the MVP, MCP should remain deliberately:

- read-heavy,
- diagnostics-heavy,
- review-friendly,
- and runtime-truth-aligned.

The MVP must not introduce a second competing runtime or truth surface through MCP.

---

## 15. Success condition

The MVP is successful if a technically and dramatically informed observer can reasonably say:

- the slice behaves like a guided interactive dramatic scene,
- the AI does not merely chat or summarize,
- the engine truthfully controls what becomes real,
- visible output feels alive without outrunning committed truth,
- important characters remain meaningfully distinct,
- consequences survive across multiple turns,
- diagnostics make weak turns explainable,
- and the slice is grounded enough in the actual system to be extended through disciplined execution work.

---

## 16. Practical conclusion

The MVP is already precise enough as a product target.

What remains is not another larger vision document, but a disciplined conversion of this target into:

- freeze-ready contracts,
- codebase-aware transition logic,
- and execution-ready task derivation.

That is how this MVP becomes buildable.
