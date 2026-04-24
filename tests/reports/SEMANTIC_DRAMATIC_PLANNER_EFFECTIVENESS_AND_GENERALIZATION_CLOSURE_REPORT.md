# Semantic Dramatic Planner — Phases 5–6 Closure Report

## 1. Executive summary

This closure implements **Phase 5 (Dramatic Effect Gate)** and **Phase 6 (Controlled Generalization)** on the existing God of Carnage (GoC) LangGraph runtime: a **bounded, serializable** `DramaticEffectGateOutcome`, a **planner-signal-aware** primary evaluation path (scene-function effect tags derived from semantic move + social/continuity context, not a single token list per function), **explicit legacy structural fallback** (`dramatic_alignment_legacy_fallback_only`) for documented edge cases only, **typed** `DramaticEffectEvaluationContext` at the validation seam, a **minimal** `semantic_planner_effect_surface` with **Non-GoC = `gate_result: not_supported` only**, and **diagnostics/operator** exposure of gate outcomes. **Validation remains authoritative** for rejection; **commit** unchanged; **no second runtime graph** was added.

## 2. Implemented files and responsibilities

| File | Responsibility |
|------|----------------|
| [`ai_stack/dramatic_effect_contract.py`](../../ai_stack/dramatic_effect_contract.py) | `DramaticEffectGateResult` (includes `not_supported`, `accepted`, `accepted_with_weak_signal`, four hard-reject results), postures, `DramaticEffectGateOutcome`, `DramaticEffectEvaluationContext` (Pydantic, `extra=forbid`), `SemanticPlannerSupportLevel` metadata |
| [`ai_stack/dramatic_effect_gate.py`](../../ai_stack/dramatic_effect_gate.py) | `evaluate_dramatic_effect_gate`, effect-tag clusters, scene-function OR-groups, continuity/blame carry, narrow `off_scope_containment` vs scene mismatch, weak-signal path, `build_evaluation_context_from_runtime_state` |
| [`ai_stack/semantic_planner_effect_surface.py`](../../ai_stack/semantic_planner_effect_surface.py) | `DramaticEffectEvaluator` protocol, `resolve_dramatic_effect_evaluator`, Non-GoC stub |
| [`ai_stack/goc_dramatic_alignment.py`](../../ai_stack/goc_dramatic_alignment.py) | `dramatic_alignment_legacy_fallback_only` (length/withhold/meta only); `dramatic_alignment_violation` retained as deprecated composite for old callers |
| [`ai_stack/goc_turn_seams.py`](../../ai_stack/goc_turn_seams.py) | `run_validation_seam(..., evaluation_context=...)` maps gate → `validation_outcome` |
| [`ai_stack/langgraph_runtime.py`](../../ai_stack/langgraph_runtime.py) | `RuntimeTurnState.dramatic_effect_outcome`, `_validate_seam` builds context; `dramatic_review` extensions |
| [`ai_stack/goc_gate_evaluation.py`](../../ai_stack/goc_gate_evaluation.py) | `gate_dramatic_quality` recognizes `dramatic_effect_*` rejection reasons |
| [`ai_stack/tests/test_dramatic_effect_contract.py`](../../ai_stack/tests/test_dramatic_effect_contract.py), [`test_dramatic_effect_gate.py`](../../ai_stack/tests/test_dramatic_effect_gate.py) | Contract, gate, legacy dominance, authority, Non-GoC |

## 3. Dramatic-effect contract truth

- **Serialization:** `DramaticEffectGateOutcome.to_runtime_dict()` / Pydantic `model_dump(mode="json")`.
- **`not_supported`:** Only for modules that are not full GoC evaluation (`resolve_dramatic_effect_evaluator` stub). On GoC paths, `evaluate_dramatic_effect_gate` never returns `not_supported` for `module_id == god_of_carnage`.
- **Weak signal:** `accepted_with_weak_signal` → validation **`approved`** with `dramatic_quality_gate: effect_gate_weak_signal` (no hard reject for “weak” alone).

## 4. Gate semantics and integration truth

- **Order:** (1) legacy structural/meta (`legacy_fallback_used` when this path fires), (2) narrow hard mismatch `off_scope_containment` vs non-pivot scene, (3) continuity blame carry when prior `blame_pressure` + selected reveal/redirect/escalate, (4) character repair-vs-attack rule for `repair_or_stabilize` + de-escalate mind, (5) boilerplate + missing tags → `rejected_empty_fluency`, (6) missing scene tags → `rejected_empty_fluency`, (7) borderline length + tags → `accepted_with_weak_signal`, else `accepted`.
- **Integration:** Single graph node `validate_seam` → `run_validation_seam` only; no parallel evaluator service.

## 5. Replacement posture for surface-only anti-seductive weakness

- Primary scene engagement uses **multi-cluster effect tags** per scene function (not `_FUNCTION_SUBSTRING_TOKENS` as the main pass/fail).
- **Legacy** remains only for **length / withhold / meta-commentary** bands via `dramatic_alignment_legacy_fallback_only`.

## 6. GoC-local planner hardening truth

- Gate outcome and codes appear on `validation_outcome`, state `dramatic_effect_outcome`, and `graph_diagnostics.dramatic_review` (`dramatic_effect_gate_outcome`, `dramatic_quality_gate`, `dramatic_effect_weak_signal`).

## 7. Controlled generalization boundaries

- **`semantic_planner_effect_surface`:** Protocol + resolver; Non-GoC returns **only** `not_supported` + rationale codes — no fake `accepted`.
- **`SemanticPlannerSupportLevel`:** metadata only; gate truth remains `DramaticEffectGateResult`.

## 8. Non-GoC fallback posture truth

- `resolve_dramatic_effect_evaluator("…")` for non-GoC module → evaluator returns `not_supported`.
- `run_validation_seam` for non-GoC modules unchanged: **`waived`** (validation authority unchanged).

## 9. Regression posture and golden-case coverage

- Existing GoC phase 2–5 scenarios and retrieval-heavy scenario updated where fixture narratives must satisfy `probe_motive` / tag expectations.
- New tests cover fluent-empty rejection, surface-variant stability, weak-signal approval, legacy-only path, golden non-legacy dominance, commit authority, off-scope mismatch.

## 10. Exact test commands run

```text
python -m pytest ai_stack/tests/test_dramatic_effect_contract.py ai_stack/tests/test_dramatic_effect_gate.py -v --tb=short
python -m pytest ai_stack/tests/ -q --tb=line
```

**Result:** All targeted tests passed; full `ai_stack/tests` run: **206 passed** (includes the new dramatic-effect tests).

## 11. Pass/fail outcome for acceptance criteria (summary)

| Criterion | Status |
|-----------|--------|
| Bounded contract exists and is serializable | **Pass** |
| Gate integrated in existing graph only | **Pass** |
| Validation/commit/visible authority unchanged | **Pass** |
| Outcomes in diagnostics and operator record | **Pass** |
| Minimal generalization + honest Non-GoC | **Pass** |
| Primary eval planner-aware (tags + move/continuity), legacy bounded | **Pass** |
| Weak signal = approved + diagnostics, hard reject only for four categories | **Pass** |
| Tests include legacy non-dominance on GoC goldens | **Pass** |

## 12. Explicit confirmation: no second runtime truth surface

The only turn orchestration graph remains `RuntimeTurnGraphExecutor` / `StateGraph(RuntimeTurnState)`. Dramatic effect output is **advisory** materialized in `validation_outcome` and **derived** diagnostics — it does not replace commit or invent committed world state.

## 13. Explicit confirmation: validation, commit, and visible-output authority seams remain intact

- **Validation:** Still `run_validation_seam` / `validation_outcome.status`.
- **Commit:** Still `run_commit_seam` — unchanged logic; rejects still yield no commit.
- **Visible:** Still `run_visible_render` from committed + approved path.

---

*Generated as part of ROADMAP MVP Semantic Dramatic Planner phases 5–6 closure.*
