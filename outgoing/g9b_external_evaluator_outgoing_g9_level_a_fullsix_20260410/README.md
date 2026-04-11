# External Evaluator B package — G9 frozen six scenarios

This directory is an **execution-ready handoff kit** for a **real independent Evaluator B** scoring pass against the **fixed** God of Carnage (GoC) Gate G9 scenario set for audit run `g9_level_a_fullsix_20260410`. It is **English** project-facing documentation.

## What this is

- Instructions, checklists, a frozen-source manifest, and **empty JSON return templates** aligned with `docs/goc_evidence_templates/schemas/`.
- **Not** gate evidence by itself. **Not** a Level B claim. **Not** a G9B upgrade, G10 upgrade, or MVP closure statement.

## What this is not

- No scores are supplied here. **You** (Evaluator B) produce scores and rationales.
- No delta between Evaluator A and B is computed in this package.
- The repository may already contain an **internal** second matrix under `tests/reports/evidence/g9_level_a_fullsix_20260410/` for historical context; **your** external run is a **new** submission unless your process says otherwise.

## Document map

| Document | Purpose |
|----------|---------|
| [documents/01_EVALUATOR_B_HANDOUT.md](documents/01_EVALUATOR_B_HANDOUT.md) | Compact briefing: task, rules, deliverables, non-claims |
| [documents/02_SCORING_INSTRUCTIONS_CRITERIA.md](documents/02_SCORING_INSTRUCTIONS_CRITERIA.md) | Detailed scoring guidance for all five G9 criteria |
| [documents/03_FROZEN_SOURCE_MANIFEST.md](documents/03_FROZEN_SOURCE_MANIFEST.md) | What to copy, IDs, allowed grounding, exclusions |
| [documents/04_BLINDNESS_CONTAMINATION_CHECKLIST.md](documents/04_BLINDNESS_CONTAMINATION_CHECKLIST.md) | Pre-scoring blindness / contamination checks |
| [documents/05_SUBMISSION_CHECKLIST.md](documents/05_SUBMISSION_CHECKLIST.md) | Return-package completeness |
| [documents/06_PACKAGING_AND_ASSEMBLY.md](documents/06_PACKAGING_AND_ASSEMBLY.md) | How to assemble the **outgoing** zip from the repo |
| [documents/INTERNAL_PACKAGE_OWNER_INSTRUCTIONS.md](documents/INTERNAL_PACKAGE_OWNER_INSTRUCTIONS.md) | **Internal:** for the person handing materials to Evaluator B |
| [documents/07_FILENAME_AND_RETURN_LAYOUT.md](documents/07_FILENAME_AND_RETURN_LAYOUT.md) | Return folder layout and filenames |

## JSON templates (fill and return)

| Template | Canonical return filename |
|----------|---------------------------|
| [templates/g9_experience_score_matrix_evaluator_b.json](templates/g9_experience_score_matrix_evaluator_b.json) | `g9_experience_score_matrix_evaluator_b.json` |
| [templates/g9b_raw_score_sheet_evaluator_b.json](templates/g9b_raw_score_sheet_evaluator_b.json) | `g9b_raw_score_sheet_evaluator_b.json` |
| [templates/g9b_evaluator_b_declaration.json](templates/g9b_evaluator_b_declaration.json) | `g9b_evaluator_b_declaration.json` |

Validate against schemas under `docs/goc_evidence_templates/schemas/` when possible (`g9_experience_score_matrix.schema.json`, `g9b_raw_score_sheet.schema.json`, `g9b_evaluator_b_declaration.schema.json`).

## Governing references

- Roadmap: `docs/ROADMAP_MVP_GoC.md` §6.9 (criteria and scenario set), §6.10 (independence discipline).
- Workflow plan: `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`.
- Baselines: `docs/audit/gate_G9_experience_acceptance_baseline.md`, `docs/audit/gate_G9B_evaluator_independence_baseline.md`.

## `audit_run_id`

Use **`g9_level_a_fullsix_20260410`** in all three JSON artifacts unless your organization explicitly creates a **new** evidence bundle and audit policy. This package assumes scoring the **same frozen six scenario JSON files** captured for that run.

## Schema note: `task_b_independence_class`

Do **not** set `task_b_independence_class` in your declaration JSON. That field is assigned **only** during repository **Task B** review (`strict_blind` / `documented_exception` / `contaminated` per the plan).

## Optional declaration key: `visibility_before_scoring`

You may add `visibility_before_scoring` with the **same factual content** as `pre_scoring_visibility_statement` if your tooling prefers that key; the schema treats it as an optional alias. Omit it if you only use `pre_scoring_visibility_statement`.
