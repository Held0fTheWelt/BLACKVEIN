# PLAN_G9_S4_Misinterpretation_Correction_Closure

**Governing references:** [docs/ROADMAP_MVP_GoC.md](../ROADMAP_MVP_GoC.md) (§6.9, §8.2 Scenario S4, §8.5); [docs/GoC_Gate_Baseline_Audit_Plan.md](../GoC_Gate_Baseline_Audit_Plan.md) (G9 phase); [docs/audit/gate_G9_experience_acceptance_baseline.md](../audit/gate_G9_experience_acceptance_baseline.md); [docs/audit/gate_G9B_evaluator_independence_baseline.md](../audit/gate_G9B_evaluator_independence_baseline.md); [docs/goc_evidence_templates/](../goc_evidence_templates/) (matrix schema/template); [scripts/g9_threshold_validator.py](../../scripts/g9_threshold_validator.py).

---

## 1. Scope

**In scope:** Roadmap experience-acceptance **scenario S4** only — *Misunderstanding / correction* as defined in [docs/ROADMAP_MVP_GoC.md](../ROADMAP_MVP_GoC.md) §8.2 (runtime initially interprets imperfectly; player corrects; correction incorporated plausibly; truth stable; exchange dramatically alive). Work is limited to planning how a **later** execution task will produce a truthful S4 anchor and evidence package aligned with frozen scenario id `goc_roadmap_s4_misinterpretation_correction` ([ai_stack/goc_g9_roadmap_scenarios.py](../../ai_stack/goc_g9_roadmap_scenarios.py)).

**Out of scope:** Full G9 re-run orchestration, full G9B re-run, full G10 re-run, global closure aggregation, updating audit matrix statuses, threshold arithmetic execution, assigning numeric rubric scores, and any code or test changes.

---

## 2. Re-check objective

This planning artifact exists solely to **re-check** the current S4 evidence and anchor mapping **before** any implementation, scenario rewrite, or audit-status update is approved. No repository state is assumed sufficient for S4 until a later execution task completes the re-evaluation steps in Section 5 and produces the evidence package in Section 8.

---

## 3. Current S4 insufficiency summary

Per [docs/audit/gate_G9_experience_acceptance_baseline.md](../audit/gate_G9_experience_acceptance_baseline.md), the primary automated anchor mapped to S4 is `test_phase3_run_b_continuity_changes_later_behavior_more_than_once` in [ai_stack/tests/test_goc_phase3_experience_richness.py](../../ai_stack/tests/test_goc_phase3_experience_richness.py). The same baseline and [scripts/g9_level_a_evidence_capture.py](../../scripts/g9_level_a_evidence_capture.py) (`assess_roadmap_s4`) document that this chain demonstrates **continuity-driven re-staging** (same surface player line, different primary responder under carry-forward), **not** an explicit imperfect interpretation of player intent followed by a **player-led correction turn**.

Therefore:

- **Continuity or restaging evidence alone does not prove misunderstanding/correction** under the roadmap S4 standard.
- **Responder variation or generic behavior shift** without a legible misread–correction–incorporation arc does not satisfy S4.
- The Level A bundle `tests/reports/evidence/g9_level_a_20260408/` recorded S4 as insufficiently evidenced; the score matrix left S4 cells null; [scripts/g9_threshold_validator.py](../../scripts/g9_threshold_validator.py) correctly reports an incomplete grid (`complete: false`, thresholds not computed). That state **does not** constitute a roadmap-compliant S4 anchor.

---

## 4. S4 success definition

A valid S4 anchor for later G9 consumption exists **only if** reproducible artifacts clearly support **all** of the following, traceable to concrete fields (transcript, structured output, dramatic turn excerpts, routing/interpretation metadata as available):

1. **Initial imperfect interpretation:** The runtime (or a documented interpretation seam) attributes meaning, intent, or facts that a neutral reader can compare against the player’s stated move and classify as **wrong, partial, or misaligned** — not merely a different dramatic staging choice under continuity.
2. **Correction or clarification:** A **distinct** player turn (or formally equivalent player-authored correction signal in the harness) explicitly repairs the misread target (who/what/whether), without collapsing into generic continuation.
3. **Incorporation of correction:** Subsequent runtime output **responds to the correction** in a way that shows the corrected reading is operative (e.g., updated entity focus, retracted wrong claim, aligned responder stance), not only a fresh narrative beat.
4. **Stable truth after correction:** Committed or visible truth layers remain **consistent** with module/authored constraints after correction; no silent reversion that contradicts the corrected reading without a new dramatic justification.
5. **Dramatic liveliness after correction:** The post-correction exchange remains **theatrically engaged** (tension, interpersonal reactivity, non-generic pacing) — stronger than flat acknowledgement or template de-escalation unless the rubric explicitly documents why that still meets “alive” for this scenario.

Generic continuity change, generic behavior shift, and generic responder variation **do not** satisfy items 1–5 without the explicit misread–correction–incorporation arc.

---

## 5. Existing-anchor re-evaluation plan

The **later** S4 closure execution task must **start** by re-checking **all** candidate anchors already referenced or mappable in-repo, including at minimum:

| Candidate | Where documented | Re-check action |
|-----------|------------------|-----------------|
| `test_phase3_run_b_continuity_changes_later_behavior_more_than_once` | G9 baseline, `g9_level_a_evidence_capture.py` | Re-read pytest assertions, turn inputs, `trace-p3-b1`–`b4`, dramatic review / interpreted move fields; document verbatim what is proven vs. not proven for §8.2 S4 |
| Any other phase-2/phase-3/phase-5 test that could be argued as S4 | [docs/GoC_Gate_Baseline_Audit_Plan.md](../GoC_Gate_Baseline_Audit_Plan.md) G9 targets, grep for multi-turn “correction” semantics | Same documentation discipline: one table row per candidate: **proves / does not prove** each of the five bullets in Section 4 |
| Structured capture output `scenario_goc_roadmap_s4_misinterpretation_correction.json` pattern | Evidence bundle convention | If re-run under a new `audit_run_id`, same `roadmap_s4_evidence` structure must either affirm S4 or remain explicit `insufficiently_evidenced_for_roadmap_s4` — no silent upgrade |

**Mandatory rule:** Reject any anchor that does not **clearly** meet the Section 4 definition, even if pytest succeeds technically or traces exist. Document the rejection rationale with pointers to specific turns and fields.

---

## 6. Possible closure paths

**A. Accept an existing anchor** only if the re-check in Section 5 proves it satisfies Section 4 with no ambiguity. Update capture mapping so the accepted test id is the single authoritative pytest anchor for `goc_roadmap_s4_misinterpretation_correction`.

**B. Strengthen an existing scenario/test** so it becomes a **genuine** misunderstanding/correction scenario: add or reshape turns, fixtures, and assertions so that items 1–5 in Section 4 are **asserted or structurally required** (not narrated only in prose). Keep frozen scenario id `goc_roadmap_s4_misinterpretation_correction` in [ai_stack/goc_g9_roadmap_scenarios.py](../../ai_stack/goc_g9_roadmap_scenarios.py).

**C. Add one new explicit S4 scenario/test** if no existing anchor can **truthfully** satisfy S4 after re-check. The new test becomes the pytest anchor; evidence capture ([scripts/g9_level_a_evidence_capture.py](../../scripts/g9_level_a_evidence_capture.py)) must emit one JSON artifact for this scenario id with full turn chain excerpts.

**Selection principle:** Choose the **smallest truthful path**, not the path of least engineering effort. If Path A is false after honest re-check, prefer Path B **only** when it adds the minimum structural delta while preserving reproducibility; otherwise use Path C.

---

## 7. Preferred later execution path

**Preferred path (conditional, after Section 5):**

1. **Execute Section 5 completely.** If any existing anchor satisfies Section 4, prefer **Path A** — **roadmap truthfulness** and **minimal drift** (no new scenario surface area).
2. If no anchor qualifies, prefer **Path B** when a **small, bounded** extension to an existing multi-turn harness (e.g., the phase-3 richness module) can introduce: (a) an explicit misread signal in structured diagnostics or narrative that the test asserts, (b) a distinct correction turn, (c) a post-correction assertion on interpretation/responder/truth fields — without conflating “same line restaged” with “correction.” This preserves **testability** and **compatibility** with the existing six-test pytest bundle pattern documented in the G9 baseline. **Path B is admissible only when the change semantically sharpens the scenario** (inputs, fixtures, or observable runtime semantics), **not** when it merely forces the desired S4 reading through assertions on an otherwise weak trace; the latter would **overfit** a frail anchor and must be rejected in favor of Path C or a deeper scenario redesign.
3. If Path B would require contorted continuity semantics or would blur S4 with S3 (pressure escalation), use **Path C**: one dedicated pytest + capture path for S4 only, still keyed to `goc_roadmap_s4_misinterpretation_correction`.

**Rationale bundle:** Roadmap alignment (§8.2), minimal unnecessary new vocabulary (frozen ids in [ai_stack/goc_g9_roadmap_scenarios.py](../../ai_stack/goc_g9_roadmap_scenarios.py)), reproducible commands, explicit linkage for a **later** full G9 bundle re-run and matrix fill per [docs/goc_evidence_templates/schemas/g9_experience_score_matrix.schema.json](../goc_evidence_templates/schemas/g9_experience_score_matrix.schema.json).

---

## 8. Evidence package requirements

The **later** S4 execution task must capture, under a dedicated `audit_run_id` directory (convention: `tests/reports/evidence/<audit_run_id>/`):

- **audit_run_id:** The bundle directory name and the same identifier recorded in `run_metadata.json` (or equivalent) so G9, G9B, and audit text can reference one unambiguous run.
- **Git provenance:** Git commit identifier (per project convention, typically full hash) and an explicit **clean vs. dirty** working-tree flag, recorded in the same run metadata as existing Level A evidence bundles — required for later reproducibility and cross-run comparison.
- **Scenario id:** `goc_roadmap_s4_misinterpretation_correction` (must match [scripts/g9_threshold_validator.py](../../scripts/g9_threshold_validator.py) canonical row).
- **Command/test anchor:** Exact pytest node id(s) and working directory; archive stdout/stderr log fragment referencing the run.
- **Trace id(s):** All `trace_id` values for the S4 chain (from `graph_diagnostics.repro_metadata` or equivalent).
- **Transcript or structured output excerpt:** Player inputs and primary narrative outputs per turn, plus any `interpreted_move` / intent fields needed to show misread vs. correction.
- **Misunderstanding evidence note:** Short technical note citing which turn/field evidences item 1 (Section 4).
- **Correction evidence note:** Same for item 2.
- **Correction-incorporation evidence note:** Same for item 3, linking pre- and post-correction structured slices.
- **Turn-record or routing evidence references:** Excerpts from dramatic turn record groups (e.g., routing, realization, outcome) that support items 4–5 where applicable.

Align JSON shape with existing `scenario_goc_roadmap_s4_*.json` patterns and templates under [docs/goc_evidence_templates/](../goc_evidence_templates/).

---

## 9. Scoring-readiness rule

This **planning** task does **not** score S4 and does **not** invoke rubric arithmetic. It only defines how S4 can become **truthfully scoreable later**: once Section 8 is complete and Section 4 is satisfied, a later human or process may assign 1–5 scores per [docs/ROADMAP_MVP_GoC.md](../ROADMAP_MVP_GoC.md) §8.3 and fill [docs/goc_evidence_templates/g9_experience_score_matrix.template.json](../goc_evidence_templates/g9_experience_score_matrix.template.json).

**Rule:** No later S4 numeric row is acceptable unless **misunderstanding**, **correction**, and **correction-incorporation** are all **explicitly evidenced** in the package (Section 8). Filling the matrix before that evidence exists is invalid.

---

## 10. Dependencies and downstream impact

Successful S4 closure (in a **later** execution task) unblocks:

- Completion of the **6×5** G9 experience matrix (all six roadmap scenarios scored).
- **Threshold calculation** via [scripts/g9_threshold_validator.py](../../scripts/g9_threshold_validator.py) with `complete: true`.
- **Single-evaluator G9B Level A** raw sheet consistency (matrix no longer has null S4 cells for that run), per [docs/audit/gate_G9B_evaluator_independence_baseline.md](../audit/gate_G9B_evaluator_independence_baseline.md) sequencing.
- **Later G10** step-11 re-evaluation that depends on G9 evidence completeness ([docs/ROADMAP_MVP_GoC.md](../ROADMAP_MVP_GoC.md) §6.11 item 11).

**This planning task** does not change any gate structural status, closure-level status, or matrix cell. It produces no audit delta.

---

## 11. Exit criteria for the later execution task

The **later** S4 closure execution is complete only when:

- Exactly **one** truthful S4 anchor exists (pytest or approved harness) mapped to `goc_roadmap_s4_misinterpretation_correction`.
- The **evidence package** (Section 8) is **complete** and stored under an `audit_run_id` path.
- **No invented transcript text** and **no invented numeric scores** in planning or evidence notes.
- **No ambiguous “close enough” language** in the evidence notes; each Section 4 bullet is addressed with field-level citations.
- The anchor is **reproducible** by documented command(s).
- Outputs are **ready for later G9 bundle consumption** (capture script alignment, matrix row fill, validator input consistency).

---

## 12. Non-goals and disclaimers

- This task does **not** implement S4 fixes in code or tests.
- This task does **not** satisfy or certify G9, G9B, or G10.
- This task does **not** make any closure, compliance, or baseline-status claim.
- This task does **not** substitute for a full gate re-audit; it plans a single-scenario remediation slice only.

---

**Research notes (for authors):** Current baseline explicitly maps S4 to `test_phase3_run_b_continuity_changes_later_behavior_more_than_once` as *closest automated anchor only* and rejects it for roadmap S4 semantics; `g9_level_a_evidence_capture.py` encodes the same insufficiency assessment in `assess_roadmap_s4`.
