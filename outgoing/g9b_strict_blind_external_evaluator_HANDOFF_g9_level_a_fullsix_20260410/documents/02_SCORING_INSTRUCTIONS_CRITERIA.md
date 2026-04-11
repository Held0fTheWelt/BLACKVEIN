# Scoring instructions — Evaluator B (G9 criteria)

This document expands the five roadmap criteria (**§6.9**) for the **fixed six-scenario** bundle. It does **not** add criteria or replace the roadmap. Use the **scenario JSON fields** as primary evidence; optional GoC script / module grounding only if your handoff authorizes it.

## Shared scale (1–5)

Use the **same** integer scale for every criterion:

- **5 — Strong:** Clearly meets the criterion for this scenario slice; issues are negligible.  
- **4 — Solid:** Meets the criterion with minor gaps or narrow limitations visible in the JSON.  
- **3 — Adequate:** Acceptable but uneven; meaningful limitations.  
- **2 — Weak:** Frequent misses or contradictions relative to the scenario’s intent.  
- **1 — Fails:**Criterion largely unmet or undermined by the recorded run.

Anchor rationales to **named JSON paths** (e.g. `dramatic_review`, `validation_outcome`, `visible_output_bundle`, `roadmap_s4_evidence`) and short quotes or paraphrases of **recorded** strings—do not invent transcript lines not present in the artifact.

---

## 1. `dramatic_responsiveness`

**Question:** Does the committed player-facing output **respond** to the dramatic pressure encoded in the scenario—pacing, scene function, and the table-conflict beat appropriate to *God of Carnage* (civility under strain, status threat, rapid escalation)?

**GoC dramatic lens:** Bourgeois couples in a living-room confrontation; provocation, silence, and pressure should **land** as theatre-of-manners turning sharp—not generic RPG filler.

**Per scenario anchors:**

- **S1 (direct provocation):** Does escalation (e.g. conflict-intent → `escalate_conflict` or equivalent) show up in committed narration and diagnostics? Does the response **match** a fight provocation rather than deflecting irrelevantly?  
- **S2 (deflection / brevity):** Does thin-edge / brevity handling (`pacing_mode`, `silence_brevity_decision`, withhold patterns) produce a **credible** minimal or evasive beat?  
- **S3 (pressure escalation):** Under multi-pressure input, does resolution (`multi_pressure_resolution`, scene assessment) pick a **dramatically intelligible** lane (e.g. reveal vs deflect) consistent with the fixture?  
- **S4 (misinterpretation / correction):** Across the **chain** (misroute → correction → incorporation), does each turn’s narration reflect the **current** dramatic state? Pay attention to `roadmap_s4_evidence` and trace ids if present.  
- **S5 (failure + fallback):** After primary failure, does **recovered** committed output still deliver a **sustained** table-conflict beat (not only a dry error stub)? Use `failure_turn` / `visible_output_bundle` / `routing` fields.  
- **S6 (retrieval-heavy):** Does narration **use** retrieved context in a way the player can feel (governance-visible retrieval), not ignore it?

---

## 2. `truth_consistency`

**Question:** Are **staging**, **validation**, and **committed** outcomes **coherent**—no silent contradictions between what the graph claims and what is approved for the player?

**Look for:**

- `validation_outcome` (or equivalent) vs committed narration.  
- Routing and fallback flags (`fallback_stage_reached`, `graph_fallback_executed`, `generation.fallback_used`) **matching** the story told in the JSON.  
- S4: `stable_truth_after_correction` / correction evidence—does the addressee or dramatic fact **stay** fixed after correction?  
- S5: explicit **failure** then **recovery** without pretending the primary path succeeded.

Lower scores when the JSON shows **approved** content that **contradicts** earlier stable facts without a documented correction path.

---

## 3. `character_credibility`

**Question:** Do responder choices, voice, and beats fit **GoC** characters and relationships **as staged in the fixture** (e.g. host vs guest, defensive Michel, sharp Veronique)?

**Use:**

- `dramatic_signature`, responder id, and fixture `gm_narration` / player-visible lines in the scenario JSON.  
- Optional: module YAML under `content/modules/god_of_carnage/` **only if** included in your handoff.

Penalize generic or interchangeable dialogue that **ignores** who is speaking and the social stakes, **when** the JSON gives enough structure to judge.

---

## 4. `conflict_continuity`

**Question:** Does conflict **state** evolve sensibly across the recorded turn(s)—pressure, blame, continuity markers—not a random reset?

**Look for:**

- `continuity_impacts`, scene function, pressure axes, blame routing.  
- S4: evidence that **misread → correction → incorporation** is reflected in **who** speaks and **what** tension persists (`correction_incorporation_evidence`, etc.).  
- S5: fallback narration **continues** the conflict thread (e.g. blame redirect) rather than abandoning structure.

Single-turn slices (S1–S3, S6) may have **narrower** continuity scope; score relative to what the scenario asserts, not a full-play arc.

---

## 5. `graceful_degradation`

**Question:** When the system is **stressed**, does behavior remain **safe, honest, and playable**?

- **All scenarios:** You still score this column 1–5. For **non-failure** rows, high scores usually mean clean primary-path behavior and honest diagnostics **without** unnecessary collapse.  
- **S5 (`failure_oriented: true`):** This is the **primary** graceful-degradation scenario. Weight **recovery**: fallback path reached, committed output quality after failure, `dramatic_review.run_classification` if present, and whether the player would get a **usable** dramatic beat—not only a technical OK.

**Do not** conflate “model failed once” with automatic low degradation: a **successful** fallback with strong narration can score high if the JSON supports it.

---

## Completeness

Every scenario row must have **five** integers and **five** non-empty `cell_rationale` strings. If you cannot score a cell, document why in the declaration and discuss with the package owner—**incomplete** grids are not valid for ingestion as complete G9B evidence.
