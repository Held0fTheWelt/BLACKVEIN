# GOC Phase 2 — Maturity, Breadth, and Quality Closure Report

## 1. Summary

Phase 2 hardens the **God of Carnage** vertical slice under frozen Phase 0 contracts by adding **bounded carry-forward continuity** (`prior_continuity_impacts`), **YAML-fed director policy** (characters, character voice, scene guidance), **validation-time dramatic alignment / anti-seductive rejection**, **multi-pressure resolution diagnostics**, **expanded continuity-on-commit** (up to two frozen classes per turn), and a **test-backed suite of multiple non-preview scenario paths**. No freeze documents were changed; canonical YAML under `content/modules/god_of_carnage/` remains the authoritative content surface.

## 2. Implemented maturity gains

- **Seam discipline preserved** with stronger **validation** input: `run_validation_seam` now receives director context and rejects proposals that fail deterministic **dramatic alignment** checks (`ai_stack/goc_dramatic_alignment.py`), mapped to `validation_outcome.reason` values prefixed with `dramatic_alignment_`.
- **Continuity on commit** is no longer a single special case: `build_goc_continuity_impacts_on_commit` emits the primary frozen class from `selected_scene_function` plus at most one additional class from effect text keywords (`ai_stack/goc_turn_seams.py`).
- **Carry-forward continuity** is explicit: `RuntimeTurnGraphExecutor.run(..., prior_continuity_impacts=...)` and `StorySession.prior_continuity_impacts` (world-engine) maintain a **capped rolling list** (last 12 entries) — not a second narrative memory system.
- **Visible render** can append a **YAML-derived phase context line** for thin-edge / withheld moves when the committed proposal is short or silence-led, with **`bounded_ambiguity`** visibility marking when that supplement is used (`run_visible_render` + `thin_edge_staging_line_from_guidance`).
- **Diagnostics for dramatic review**: `graph_diagnostics["dramatic_review"]` and extended `gate_review_hints` (including `dramatic_quality`, `slice_boundary`) surface scene function, pacing, silence decision, prior continuity classes, multi-pressure resolution, validation reason, and alignment summary (`ai_stack/langgraph_runtime.py`).

## 3. Implemented breadth gains

- **Four distinct non-preview executable paths** are covered in automated tests (see §5); they differ by **player move shape** (escalation, thin-edge silence, multi-pressure, out-of-scope containment), not by cosmetic rewording alone.
- **YAML-backed surfaces now exercised at runtime** (beyond Phase 1 `module.yaml` setting/scope only):
  - `content/modules/god_of_carnage/characters.yaml` (indirectly via bundle load; asymmetry uses `direction/character_voice.yaml`).
  - `content/modules/god_of_carnage/direction/character_voice.yaml` (default responder asymmetry under carry-forward).
  - `content/modules/god_of_carnage/direction/scene_guidance.yaml` (phase hints in `scene_assessment`, thin-edge staging line).
- **Pacing vocabulary usage**: `thin_edge`, `containment`, and `multi_pressure` are now **reachable** from deterministic director rules (`ai_stack/scene_director_goc.py`).

## 4. Implemented quality gains

- **Anti-seductive rejection**: fluent, atmospheric prose with **no support tokens** for the director-selected `selected_scene_function` is **rejected at validation** with `dramatic_quality_gate: alignment_reject` (contract-aligned gate family: `dramatic_quality`).
- **Character asymmetry**: under **unnamed** moves, **Michel** is preferred when `blame_pressure` is carried forward; **Annette** when `revealed_fact` is carried forward — reasons cite YAML voice roles (`yaml_voice_bias:...`).
- **Multi-pressure legibility**: `scene_assessment.multi_pressure_resolution` records **candidates**, implied continuity map, **chosen** function, and a **deterministic rationale** string referencing the canonical contract section 3.5 tie-break.

## 5. Scenario evidence table

| scenario id | scenario type | preview or non-preview | selected scene function | selected responder set | pacing mode | continuity impacts (this turn) | visibility markers | gate families activated | gate outcome | key evidence | weakness if any |
|-------------|---------------|------------------------|-------------------------|------------------------|-------------|----------------------------------|--------------------|-------------------------|--------------|--------------|-----------------|
| `s-p2-escalate` | standard conflict escalation | non-preview | `escalate_conflict` | `annette_reille` (named) | `standard` | `situational_pressure` (from commit) | `truth_aligned` | turn_integrity, diagnostic_sufficiency, dramatic_quality, slice_boundary | pass / pass / pass / pass | `guidance_phase_key` populated from YAML | Relies on keyword heuristics for escalation |
| `s-p2-thin` | thin-edge / silence | non-preview | `withhold_or_evade` | `annette_reille` | `thin_edge` | `silent_carry` | `truth_aligned`, `bounded_ambiguity` | same | all pass | YAML staging line + withheld silence | Director still keyword-driven |
| `s-p2-multi` | multi-pressure prioritization | non-preview | `reveal_surface` | default / unnamed bias | `multi_pressure` | `revealed_fact` (+ optional second) | `truth_aligned` | same | all pass | `multi_pressure_resolution` explains winner | Competing functions still finite set |
| `s-p2-contain` | out-of-scope containment | non-preview | `scene_pivot` | default | `containment` | `refused_cooperation` | `truth_aligned` | same | all pass | Off-topic keywords route to containment | Heuristic keyword list for off-scope |
| `s-p2-anti` | anti-seductive negative | non-preview (run is preview-safe: validation fails) | `escalate_conflict` | n/a | `standard` | none (no commit) | `non_factual_staging` | dramatic_quality (primary), turn_integrity | dramatic_quality **fail**, seams still executed | `dramatic_alignment_*` rejection reason | Does not exhaust all empty-fluency patterns |
| `s-p2-c1`→`s-p2-c2` | continuity carry-forward | non-preview (when approved) | turn1 `redirect_blame`, turn2 `redirect_blame` | turn2 `michel_longstreet` vs turn3 baseline `annette_reille` | `standard` | `blame_pressure` carried | `truth_aligned` | same | pass | Same input shape diverges with/without prior | Carry-forward capped; no long arc memory |
| `trace-goc-phase1` (regression) | Phase 1 integrity path | non-preview | `reveal_surface` (typical) | named target | `standard` | from commit map | `truth_aligned` | same | pass | Phase 1 seam order unchanged | Single baseline path |

## 6. Continuity carry-forward evidence

- **Test**: `test_continuity_changes_later_turn_behavior` in `ai_stack/tests/test_goc_phase2_scenarios.py`.
- Turn 1 commits **`blame_pressure`** via `redirect_blame`.
- Turn 2 with **`prior_continuity_impacts`** reproduces **`redirect_blame`** and selects **`michel_longstreet`** without naming.
- Turn 3 without prior selects **`establish_pressure`** and **`annette_reille`** for the same player text — proving **later-turn behavior change** from carry-forward only.

## 7. Anti-seductive evidence

- **Test**: `test_anti_seductive_fluent_empty_rejected`.
- **Mechanism**: `dramatic_alignment_violation` detects **generic boilerplate phrases** and missing **function-support substrings** for high-stakes `selected_scene_function` values (`GATE_SCORING_POLICY_GOC.md` dramatic_quality intent).
- **vs Phase 1**: Phase 1 validation was **structural only**; Phase 2 adds **explicit dramatic rejection** at the validation seam with stable `reason` codes for diagnostics and CI.

## 8. Diagnostics usefulness evidence

- **Degraded dramatic example**: rejected anti-seductive run surfaces `graph_diagnostics.dramatic_review.dramatic_alignment_summary` = `alignment_reject:<reason>` and `validation_outcome.reason` without hiding the failure behind preview staging alone.
- **Multi-pressure example**: `dramatic_review.multi_pressure_candidates`, `multi_pressure_chosen`, and `multi_pressure_rationale` answer “why this scene function won.”

## 9. YAML coverage expansion

| YAML surface | Phase 1 use | Phase 2 use |
|--------------|-------------|-------------|
| `module.yaml` | setting, scope in `scene_assessment` | unchanged |
| `characters.yaml` | not read by ai_stack | loaded in `load_goc_yaml_slice_bundle` (bundle integrity / future hooks) |
| `direction/character_voice.yaml` | not read | default responder asymmetry (`formal_role` in responder `reason`) |
| `direction/scene_guidance.yaml` | not read | `guidance_phase_*` fields + thin-edge staging line |

## 10. Non-preview vs preview evidence separation

- **Non-preview evidence** is taken only from runs with `experiment_preview is False` and `validation_outcome.status == approved` (Phase 2 scenario tests + Phase 1 regression).
- **Preview-only** runs (e.g. scope breach / title mismatch) are **not** counted toward non-preview breadth; the anti-seductive scenario is **non-preview in intent** (full graph, GoC module, correct host template) but **fails validation** — it is classified in §5 as a **dramatic_quality failure case**, not a shipping-quality pass.

## 11. Residual weaknesses

- Director selection remains **deterministic keyword / heuristic** — not ML classification.
- **Off-scope containment** uses a **small explicit keyword set**; exotic off-topic inputs may still route like in-scene moves.
- **Dramatic alignment** uses **substring tokens and phrase bans** — tuned defaults, not human literary judgment.
- **Continuity** is **class-labeled and capped**; no rich episodic memory (by design).
- **world-engine** persistence of `prior_continuity_impacts` is **session-local**; restart does not replay unless re-injected.

## 12. Readiness statement

- **Task derivation / CI closure**: The slice now has **multiple credible non-preview paths**, stronger **dramatic_quality enforcement at validation**, **observable multi-pressure explanations**, and **continuity that changes later-turn director output** in tests. This is **stronger than Phase 1** on breadth and quality gates, with honest limits above.
- **Shipping readiness**: Not claimed here — anti-seductive and alignment rules are **necessary but not sufficient** for full production literary quality; preview vs non-preview separation must be preserved in any external report.

---

## Tests executed (evidence)

```text
python -m pytest ai_stack/tests/test_goc_phase1_runtime_gate.py \
  ai_stack/tests/test_goc_phase2_scenarios.py \
  ai_stack/tests/test_goc_frozen_vocab.py \
  ai_stack/tests/test_langgraph_runtime.py -q

python -m pytest world-engine/tests/test_runtime_manager.py \
  world-engine/tests/test_story_runtime_api.py -q
```

All of the above passed in the development run used to author this report.
