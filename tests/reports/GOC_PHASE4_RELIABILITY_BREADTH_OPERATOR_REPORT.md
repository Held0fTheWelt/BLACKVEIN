# GOC Phase 4 - Reliability, Breadth, and Operator Hardening Report

## 1. Summary

Phase 4 hardens the God of Carnage vertical slice from a strong proof vertical into a more reliable MVP play experience with broader non-preview path coverage, longer multi-turn stability, stronger pressure/identity carry, and clearer operator diagnostics for pass/fail/degraded judgments.  
The implementation remains within the frozen contracts: canonical YAML authority, frozen vocabularies, named Scene Director graph-node decomposition, proposal/validation/commit/render seams, and preview-vs-non-preview discipline.

## 2. Reliability gains

- Expanded deterministic move recognition in the Scene Director for humiliation, evasion/deflection, alliance-like repositioning, and stronger escalation cues (`furious`, `attack`) while preserving canonical scene-function outputs.
- Improved continuity extraction on commit for alliance-like movement and dignity injury when textual evidence supports it, still bounded to a capped continuity list (no second memory truth surface).
- Strengthened dramatic-quality filtering against commentary-style generic text so weak turns are more reliably rejected at validation instead of passing as polished prose.

## 3. Breadth gains

Phase 4 now provides at least six distinct non-preview executable path families in one dedicated suite:

1. `s-p4-escalate` (`escalate_conflict`)
2. `s-p4-blame` (`redirect_blame`)
3. `s-p4-probe` (`probe_motive`)
4. `s-p4-repair` (`repair_or_stabilize`)
5. `s-p4-thin` (`withhold_or_evade`)
6. `s-p4-contain` (`scene_pivot`)

These are not cosmetic variants; they cover escalation, accusation/blame redirection, motive probing, repair attempts, thin-edge silence handling, and containment behavior.

## 4. Character consistency gains

- Pressure-conditioned defaults now remain character-distinguishable across continuity states:
  - `veronique_vallon` as default host pressure bearer in early/courtesy baseline.
  - `michel_longstreet` under carried `blame_pressure`.
  - `annette_reille` under carried `revealed_fact` and motive-probe pressure.
  - `alain_reille` under carried `repair_attempt`.
- Under dignity-injury carry, responder bias can shift toward host-protection behavior rather than generic re-assignment.
- Character behavior remains continuity-sensitive without collapsing into identity interchangeability.

## 5. Multi-turn evidence

Three Phase 4 runs at 5+ turns were executed:

- `s-p4-run-a` (5 turns): credible across full run, with pressure escalation, humiliation carry, repair pressure, and later motive pressure.
- `s-p4-run-b` (5 turns): credible across full run, includes alliance-like movement plus later pressure continuity impact.
- `s-p4-run-c` (5 turns): mixed by design (pass + fail + degraded), used as explicit weak-run operator evidence.

Result vs requirement:

- 3 runs with 5+ turns: satisfied.
- At least 2 credible across full run: satisfied (`run-a`, `run-b`).
- At least one run with escalation -> bend -> partial restabilization: satisfied (`run-b` and `run-a` show this pattern in different forms).

## 6. Scene-feel evidence

- Validation now rejects additional commentary-like generic phrasing patterns that read as narration-about-scene rather than scene happening now.
- Credible runs use immediate social action language (accuse, deny, blame, apology/truce, silence pressure) rather than abstract summary-only responses.
- Thin-edge and silence turns remain legible as social events in present-time interaction, not only analytical explanation.

## 7. Pressure / alliance movement evidence

- In `s-p4-run-b`, turn 2 carries explicit alliance-like repositioning (`scene_pivot` + continuity including `alliance_shift`) and this movement remains visible in subsequent behavior and diagnostics.
- Earlier blame/humiliation pressure affects later turn selection and responder shaping multiple times in `run-a` and `run-b`.
- Continuity remains bounded and contract-safe (no unbounded memory surface; capped carry-forward semantics preserved).

## 8. Operator / reviewer usability gains

`graph_diagnostics.dramatic_review` now includes additional operator-facing fields:

- `run_classification` (`pass`, `fail`, `degraded_explainable`)
- `current_continuity_classes`
- `alliance_shift_detected`, `dignity_injury_detected`, `pressure_shift_detected`
- `pressure_shift_explanation`
- `weak_run_explanation` (structured textual explanation for degraded/fail turns)

This makes weak runs explainable from diagnostics directly, without prompt-guessing.

## 9. Regression hardening evidence

Regression hardening was expanded and verified across Phase 1-4 path families:

| family | status in Phase 4 | evidence |
|---|---|---|
| Phase 1 seam integrity baseline | preserved | phase-1 runtime gate suite passes |
| Phase 2 breadth scenarios | preserved | phase-2 scenarios suite passes |
| Phase 3 richness/continuity behavior | preserved | phase-3 richness suite passes |
| Phase 4 added breadth and long-run reliability | new strength | dedicated phase-4 suite passes |

Preserved strengths, new strengths, and weak spots are now visible in one regression-aware closure surface.

## 10. Scenario table

| scenario or run id | turn count | preview or non-preview | main scene functions exercised | main responders involved | main continuity classes carried | dramatic-quality status | turn-integrity status | diagnostic-sufficiency status | notable strength | notable weakness |
|---|---:|---|---|---|---|---|---|---|---|---|
| `s-p4-escalate` | 1 | non-preview | `escalate_conflict` | `michel_longstreet` | `situational_pressure` | pass | pass | pass/conditional_pass | Immediate escalation remains scene-anchored | Heuristic triggering remains lexical |
| `s-p4-blame` | 1 | non-preview | `redirect_blame` | `annette_reille` | `blame_pressure` | pass | pass | pass/conditional_pass | Blame redirection is legible and committed | Still keyword-sensitive |
| `s-p4-probe` | 1 | non-preview | `probe_motive` | `annette_reille` | `situational_pressure` | pass | pass | pass/conditional_pass | Motive pressure reads as in-scene interrogation | Probe detection is deterministic |
| `s-p4-repair` | 1 | non-preview | `repair_or_stabilize` | `alain_reille` | `repair_attempt` | pass | pass | pass/conditional_pass | Repair attempt does not erase prior pressure | Repair remains text-triggered |
| `s-p4-thin` | 1 | non-preview | `withhold_or_evade` | continuity-shaped default | `silent_carry` | pass | pass | pass/conditional_pass | Silence is preserved as playable social move | Thin-edge quality still heuristic |
| `s-p4-contain` | 1 | non-preview | `scene_pivot` | continuity-shaped default | `refused_cooperation` | pass | pass | pass/conditional_pass | Containment remains scope-safe and in-world | Off-scope detection still lexical |
| `s-p4-run-a` | 5 | non-preview | escalation, blame redirect, repair, motive probe | multiple (Michel/Annette/Alain + continuity-shaped) | `situational_pressure`, `blame_pressure`, `dignity_injury`, `repair_attempt` | pass across run | pass across run | pass/conditional_pass across run | Pressure evolves and remains coherent across 5 turns | No deep semantic planner |
| `s-p4-run-b` | 5 | non-preview | blame redirect, scene pivot, silence, repair/blame mix | multiple with alliance repositioning | includes `alliance_shift` plus blame/repair/silence classes | pass across run | pass across run | pass/conditional_pass across run | Alliance-like movement is explicit and diagnosable | Relational movement still inferred from lexical evidence |
| `s-p4-run-c` | 5 | mixed quality (contains degraded/fail turns) | probe, high-stakes rejection, degraded generation path, silence, containment | multiple | mixed; some turns no commit by rejection | pass/fail/degraded mix | pass across run | pass/conditional_pass across run | Honest weak-run evidence with explainable diagnostics | Not a fully credible run by design |

## 11. Residual weaknesses

- Director logic remains deterministic/heuristic (lexical and rule-based), not a learned semantic planner.
- Dramatic alignment checks are stronger than Phase 3 but still rule-driven (token and phrase logic), not full dramaturgical understanding.
- Continuity is bounded and intentionally compact; long-horizon narrative memory is still out of scope for this slice.
- Alliance/pressure movement detection is explicit and testable, but still relies on textual support rather than richer latent social-state inference.

## 12. Readiness statement

Phase 4 is closed for the requested hardening scope.

- Credible MVP behavior: improved and evidenced (6+ distinct non-preview paths, 3 runs at 5+ turns, 2 fully credible long runs, alliance/pressure movement evidence, 4-character pressure distinction, stronger operator diagnostics).
- Degraded but explainable behavior: present and intentionally documented (`s-p4-run-c`) with explicit diagnostic fields.
- Known weak behavior: still heuristic-driven in selection/alignment layers; no overclaim of full production dramaturgy.

Net result: the GoC slice is materially more reliable, broader, and easier to review than Phase 3 in executable evidence, while remaining contract-safe and freeze-compliant.

---

## Tests run

```text
python -m pytest ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py -q
python -m pytest ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py \
  ai_stack/tests/test_goc_phase3_experience_richness.py \
  ai_stack/tests/test_goc_phase2_scenarios.py \
  ai_stack/tests/test_goc_phase1_runtime_gate.py \
  ai_stack/tests/test_goc_frozen_vocab.py \
  ai_stack/tests/test_langgraph_runtime.py -q
```

All listed commands passed in the Phase 4 closure run.
