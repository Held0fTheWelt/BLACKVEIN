# GOC Phase 3 — Experience, Richness, and Reviewability Closure Report

## 1. Summary

Phase 3 materially extends the God of Carnage vertical slice beyond Phase 2 single-turn maturity into executable short-run experience quality. The implementation preserves canonical YAML authority, frozen vocabularies, named Scene Director node decomposition, proposal/validation/commit/visible seam boundaries, and preview-vs-non-preview discipline. No freeze artifact was reopened and no second truth surface was introduced.

## 2. Experience gains

- Multi-turn runs now show stronger dramatic texture over consecutive turns, not only isolated proof turns.
- Visible output is less skeletal in thin-edge, multi-pressure, and continuity-heavy turns via YAML-backed staging/register supplements that remain commit-aligned or bounded-ambiguity aligned.
- Dramatic review now includes explicit explanations for responder choice, scene-function choice, pacing rationale, continuity role, and dramatic quality status.

## 3. Breadth gains

Phase 3 run evidence now includes credible primary paths for:

- `repair_or_stabilize`
- `probe_motive`
- `redirect_blame`
- `withhold_or_evade`
- `escalate_conflict`

This breadth is exercised through real graph output and validation/commit/render flow, not test-only labels.

## 4. Character richness / asymmetry gains

- Unnamed pressure handling now varies across at least three major characters under different continuity and scene contexts.
- Continuity-aware default responder policy now distinguishes:
  - `michel_longstreet` under carried `blame_pressure`
  - `alain_reille` under carried `repair_attempt` and repair-led scene function
  - `annette_reille` under `revealed_fact` and motive-probe pressure
- Visible output now includes responder role/tone/phase-arc register hints from canonical YAML where applicable, without introducing new world facts.

## 5. Multi-turn run evidence

| run id | turn count | preview or non-preview | main scene functions exercised | main responders involved | continuity classes carried | dramatic-quality status | turn-integrity status | diagnostic-sufficiency status | notable gain | notable weakness |
|---|---:|---|---|---|---|---|---|---|---|---|
| `s-p3-a` | 3 | non-preview | `escalate_conflict`, `withhold_or_evade`, `probe_motive` | `annette_reille` (probe), others by move | `situational_pressure`, `silent_carry` | pass across run | pass across run | pass/conditional_pass per turn | Strong scene-shape variation in one mini-run | Deterministic keyword rules still drive function candidate set |
| `s-p3-b` | 4 | non-preview | `redirect_blame`, `repair_or_stabilize`, `redirect_blame` | `michel_longstreet`, `alain_reille` | `blame_pressure` then `repair_attempt` carry-forward | pass across run | pass across run | pass/conditional_pass per turn | Continuity changes later-turn responder behavior more than once | No long-horizon memory system by design (bounded carry only) |
| `s-p3-c` | 3 | mixed (turn 1 non-preview pass; turns 2–3 rejected/degraded) | `probe_motive`, failed `escalate_conflict`, degraded generation path | varies | limited due rejection/degraded turns | pass/fail/degraded in one run | pass across run | pass/conditional_pass per turn | Honest fail + degraded evidence with explicit diagnostics | Failing/degraded turns reduce experiential coherence (expected for evidence run) |

## 6. Continuity evidence

- In run `s-p3-b`, turn 2 and turn 4 use comparable player moves ("watch the table without naming anyone") but produce different responder handling because continuity state changed from carried `blame_pressure` alone to `blame_pressure + repair_attempt`.
- The run shows more than one continuity-driven behavioral shift:
  1. Turn 1 -> Turn 2: carry-forward keeps blame pressure active.
  2. Turn 2 -> Turn 3: repair move introduces `repair_attempt`.
  3. Turn 3 -> Turn 4: same move shape routes to a different responder due to new continuity mix.

## 7. Anti-repetition evidence

- A dedicated comparison path validates that similar player moves produce non-identical handling under different continuity states.
- Runtime diagnostics now emit deterministic `dramatic_signature` and `pattern_repetition_risk`/`pattern_repetition_note`.
- Variation is explainable and contract-compliant; no randomization-only strategy is used.

## 8. Diagnostics usability gains

`graph_diagnostics.dramatic_review` now includes:

- selected responder object and reason
- selected scene function and multi-pressure rationale
- pacing mode and silence rationale context
- prior continuity class summary
- dramatic quality status (`pass`, `fail`, `degraded_explainable`)
- pattern fatigue indicators
- `review_explanations` fields answering:
  - why this responder
  - why this scene function
  - why this pacing mode
  - why this continuity impact
  - why this turn passed/failed/degraded

All of this is produced from one shared diagnostics basis in runtime state/package output; no second diagnostics truth surface was created.

## 9. YAML coverage expansion

Newly exercised canonical YAML-backed surfaces (beyond Phase 2 baseline) include:

- `content/modules/god_of_carnage/module.yaml`
  - continued use in `scene_assessment` (`canonical_setting`, `narrative_scope`)
- `content/modules/god_of_carnage/characters.yaml`
  - loaded in slice bundle and used for character-profile snippets in render context plumbing
- `content/modules/god_of_carnage/direction/character_voice.yaml`
  - formal-role/tone/phase-arc snippets used for responder asymmetry and visible register supplements
- `content/modules/god_of_carnage/direction/scene_guidance.yaml`
  - phase hints for assessment, `ai_guidance`/`exit_signal` snippets for diagnostics and bounded staging cues

These influences remain read-only, YAML-authoritative, and non-competing with committed truth.

## 10. Pass / fail / degraded scenario table

| scenario id | status class | expected behavior | observed behavior | diagnostic evidence |
|---|---|---|---|---|
| `trace-p3-a1..a3` | pass | Multi-turn non-preview quality with scene-shape variation | All turns pass `dramatic_quality`, seams intact | `dramatic_quality_status=pass`, `review_explanations` present |
| `trace-p3-b1..b4` | pass | Continuity should alter later behavior more than once | Responder/function pressure handling changes across carried classes | continuity classes + responder differences recorded in outputs |
| `trace-p3-c2` | fail | Fluent-but-empty high-stakes turn should be rejected | Rejected with dramatic alignment reason | `dramatic_alignment_summary` shows `alignment_reject:*` |
| `trace-p3-c3` | degraded / explainable | Generation failure should degrade honestly, not fake pass | Validation rejects due model generation failure; gate is conditional | `dramatic_quality_status=degraded_explainable`, validation reason records failure path |

## 11. Residual weaknesses

- Director decisioning is still deterministic heuristic logic; it is more expressive than Phase 2 but not equivalent to deep semantic planner behavior.
- Pattern-fatigue detection currently uses previous-signature comparison; broader n-turn recurrence detection is not yet implemented.
- Experience richness improved in short runs, but long-run stability beyond bounded carry-forward remains intentionally out of scope.

## 12. Readiness statement

Phase 3 is complete for the requested closure scope: executable evidence shows materially improved richness, broader scene-function coverage, stronger continuity-sensitive behavior, improved anti-repetition observability, and more useful reviewer diagnostics, while preserving all required contract boundaries and authority constraints. Remaining weaknesses are explicit and do not invalidate the achieved Phase 3 quality uplift.

---

## Tests run

Executed and passed:

- `python -m pytest "ai_stack/tests/test_goc_phase3_experience_richness.py" -q`
- `python -m pytest "ai_stack/tests/test_goc_phase2_scenarios.py" -q`
- `python -m pytest "ai_stack/tests/test_langgraph_runtime.py" -q`
