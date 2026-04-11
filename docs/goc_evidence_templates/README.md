# GoC human evidence templates (G9 / G9B)

These files are **empty shells** for auditable human scoring. Filling them does **not**
imply gate closure until scores are real, frozen, and attached to a baseline run.

## Sequencing

1. **G9 first:** complete and freeze the six-scenario matrix (`g9_experience_score_matrix`) for the audit run.
2. **G9B second:** archive **raw** per-evaluator artifacts, then (Level B only) delta records, then optional reconciliation. G9B must not use a different scenario set than G9 (`docs/ROADMAP_MVP_GoC.md` §11.2A).

**Level B bar (G9B `closure_level_status`):** `level_b_capable` is **not** automatic when two files exist. The evidence package must demonstrate **actual** independence in **process**, **authorship**, and **score generation** (separate creation of scores and rationales before reconciliation; no post-hoc alignment before deltas). If Evaluator B is present but the independence declaration is weak or contradictory, set `g9b_level_b_attempt_record.level_b_attempt_status` to `failed_insufficient_independence` (or `incomplete` when B is still missing) and keep G9B at **`level_a_capable`**. Use `g9b_level_b_attempt_record` + `g9b_evaluator_independence_declaration` to make status explicit.

**`g9b_evaluator_record.evaluator_mode_declared` (schema enum):** `level_a_single_evaluator` (only A); `level_b_attempt_insufficient_independence` (A and B matrices + delta ingested, independence below Level B); `level_b_independent_evaluators` (evidentiary independence satisfied). Optional mirror fields: `evaluator_b_present`, `closure_level_status_gate_g9b_reported`.

## Templates

| File | Purpose |
|------|---------|
| `g9_experience_score_matrix.template.json` | Six fixed roadmap scenarios × five rubric criteria (1–5), `failure_oriented` flags (§6.9 graceful-degradation rule applies only where `true`; typically scenario 5) |
| `g9b_evaluator_record.template.json` | **Manifest only:** pointers to raw sheets (A/B), delta, optional reconciliation, optional attempt record + independence declaration |
| `g9b_raw_score_sheet.template.json` | Immutable raw scores per evaluator (file ref and/or embedded matrix same shape as G9) |
| `g9b_score_delta_record.template.json` | Per-cell deltas between two evaluators; for **Level A** set `not_applicable_level_a` to `true` and leave deltas empty |
| `g9b_reconciliation_optional.template.json` | Optional summary; `must_not_replace_raw` must stay `true` |
| `g9b_level_b_attempt_record.template.json` | Machine-readable **incomplete / failed / complete** Level B attempt status on a fixed `audit_run_id` (no fabricated scores) |
| `g9b_evaluator_b_declaration.template.json` | Evaluator B declaration: identity, refs, grounding, **`pre_scoring_visibility_statement`** (mandatory for new packages per `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md` §5); optional **`task_b_independence_class`** after repo Task B review (`strict_blind` / `documented_exception` / `contaminated`, §11) |

**Level B file naming (convention on the authoritative bundle):** add `g9_experience_score_matrix_evaluator_b.json` and `g9b_raw_score_sheet_evaluator_b.json` in the **same** evidence directory as the frozen G9 scenario JSONs (same `audit_run_id`); do not replace `g9_experience_score_matrix.json` (Evaluator A).

## JSON Schemas

Machine-readable shapes live under `schemas/` (e.g. `schemas/g9_experience_score_matrix.schema.json`, `schemas/g9b_level_b_attempt_record.schema.json`, `schemas/g9b_evaluator_b_declaration.schema.json`). They mirror the roadmap vocabulary only — no parallel scoring system.

**Independent Evaluator B workflow (plan):** Process, blindness defaults, handoff split Task A / Task B, and independence-class framing are specified in `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`. That plan is not gate evidence by itself; templates and schemas here support later real submissions.

**External Evaluator B handoff package:** For a complete, English-language **outgoing** kit (handout, rubric, frozen-source manifest, blindness and submission checklists, packaging instructions, and empty return JSON templates aligned to the schemas above), use `docs/g9_evaluator_b_external_package/`. It does not replace these templates; it operationalizes real independent handoffs without changing gate status.

## `failure_oriented` (G9 matrix)

- `true` for scenarios where the run exercises primary-path failure and fallback (roadmap scenario 5).
- `scripts/g9_threshold_validator.py` applies the **graceful degradation ≥ 3.5** threshold only to rows with `failure_oriented: true`, matching §6.9 (“in failure scenarios”).

## Usage

1. Copy templates to `tests/reports/evidence/<run_id>/` (or your governed evidence folder).
2. Record real human scores; never commit fabricated numbers as if they were observed.
3. Run `python scripts/g9_threshold_validator.py <filled_g9_matrix.json>` to verify §6.9 threshold structure (arithmetic only when scores are complete).
4. When both Evaluator A and B matrices are frozen, compute `g9b_score_delta_record.json` with `python scripts/g9b_compute_score_delta.py <matrix_a> <matrix_b> -o <out> --raw-sheet-a-ref ... --raw-sheet-b-ref ...` (authoritative deltas from files; do not hand-invent per-cell values).

## Non-claim

Template presence in the repository is **scaffolding only**. It is **not** G9 or G9B pass evidence.

## Structural contracts (G1–G4, machine-verifiable)

For gate closure work on shared semantics, routing separation, dramatic turn records, and scene-direction boundaries, authoritative specs and code anchors are:

- `docs/CANONICAL_TURN_CONTRACT_GOC.md` (including §8.1 `goc_uninitialized_field_envelope_v1` for uninitialized G3 fields)
- `ai_stack/goc_roadmap_semantic_surface.py`, `ai_stack/goc_field_initialization_envelope.py`, `ai_stack/scene_direction_subdecision_matrix.py`
- `ai_stack/goc_g9_roadmap_scenarios.py` (frozen §6.9 scenario ids and `failure_oriented` defaults)
- `docs/audit/canonical_to_repo_mapping_table.md` (canonical-name → repo path)
