# Frozen source manifest — `audit_run_id: g9_level_a_fullsix_20260410`

This manifest supports **correct assembly** of the **outgoing** Evaluator B package from the repository. Paths are **relative to repository root** unless noted.

## Normative scenario order and JSON files

Copy these **six** files from `tests/reports/evidence/g9_level_a_fullsix_20260410/` into the outgoing package’s `scenarios/` folder (or equivalent—see [06_PACKAGING_AND_ASSEMBLY.md](06_PACKAGING_AND_ASSEMBLY.md)):

| # | `scenario_id` | Filename |
|---|---------------|----------|
| 1 | `goc_roadmap_s1_direct_provocation` | `scenario_goc_roadmap_s1_direct_provocation.json` |
| 2 | `goc_roadmap_s2_deflection_brevity` | `scenario_goc_roadmap_s2_deflection_brevity.json` |
| 3 | `goc_roadmap_s3_pressure_escalation` | `scenario_goc_roadmap_s3_pressure_escalation.json` |
| 4 | `goc_roadmap_s4_misinterpretation_correction` | `scenario_goc_roadmap_s4_misinterpretation_correction.json` |
| 5 | `goc_roadmap_s5_primary_failure_fallback` | `scenario_goc_roadmap_s5_primary_failure_fallback.json` |
| 6 | `goc_roadmap_s6_retrieval_heavy` | `scenario_goc_roadmap_s6_retrieval_heavy.json` |

**Do not** rename scenario files inside the handoff if avoidable; Evaluator B rationales should cite the **bundled** filenames.

## Matrix flags (do not edit for handoff)

- **`failure_oriented`:** `true` **only** for `goc_roadmap_s5_primary_failure_fallback`; `false` for all others (matches `ai_stack/goc_g9_roadmap_scenarios.py`).

## God of Carnage source PDF (optional grounding)

If the package owner includes dramatic grounding, the PDF used in project declarations is:

- **`resources/Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf`** (Yasmina Reza, *God of Carnage*).

Including the PDF is **optional**; scoring must remain **anchored to the scenario JSON** fields.

## Allowed canonical repo references (for grounding **only if** explicitly authorized in handoff)

Typical allowlist (same spirit as `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`):

- `content/modules/god_of_carnage/` — module YAML / prompts / direction.  
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` — turn and field semantics.

**Not** an open-ended “clone the repo and browse” unless the engagement says so.

## Standard outgoing package — **excluded** for Evaluator A blindness

**Do not** include in the **default** external handoff:

| Artifact | Reason |
|----------|--------|
| `g9_experience_score_matrix.json` | Evaluator A matrix |
| Any Evaluator A `cell_rationale` excerpts copied standalone | Contamination risk |
| `g9b_raw_score_sheet.json` (Evaluator A pointer) | Points to A matrix |
| `g9b_score_delta_record.json` | A vs B delta — **after** B raw scoring only |
| `g9b_reconciliation_optional.*` | Reconciliation after raw |
| `g9b_evaluator_record.json`, `g9b_level_b_attempt_record.json` | Repo Task B / manifest; not part of B’s scoring inputs |
| Prior `g9_experience_score_matrix_evaluator_b.json` from repo | Prior pass; not default input for a **new** independent B |

**Evaluator A artifacts are excluded** from the standard external package **by default** to preserve **blind** scoring evidence. If the owner intentionally ships A for a **documented exception**, record that **before** scoring (see checklist).

## Optional technical witness files — **not** in default manifest

These live in the same evidence directory but are **out of scope** for the **default** outgoing scoring package:

- `run_metadata.json`  
- `pytest_g9_roadmap_bundle.txt`  

They may be added **only** if the package owner **opts in** and documents that choice (see [06_PACKAGING_AND_ASSEMBLY.md](06_PACKAGING_AND_ASSEMBLY.md)). When **not** included, they are **not** listed as required inputs in this manifest.

## Alignment note

Repository bundle `tests/reports/evidence/g9_level_a_fullsix_20260410/` may contain **historical** Evaluator B and delta files. This manifest describes what a **new** external Evaluator B should receive **by default**, not every file in that directory.
