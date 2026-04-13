# Gate G9 Baseline: User-Facing Experience Acceptance

## Gate

- Gate name: G9 User-Facing Experience Acceptance
- Gate class: evaluative
- Audit subject: scenario execution evidence, roadmap rubric readiness, threshold rules, transcript/trace linkage, and fallback/retrieval grounding for the fixed six-scenario set (`docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §6.9)

## Prerequisites Used

This baseline assumes the Task 3 dependency artifacts exist and were not re-audited here:

- `docs/audit/canonical_to_repo_mapping_table.md`
- `docs/audit/repo_evidence_index.md`
- `docs/audit/gate_G1_semantic_contract_baseline.md` through `docs/audit/gate_G6_admin_governance_baseline.md`
- `docs/audit/gate_G7_writers_room_operating_baseline.md`
- `docs/audit/gate_G8_improvement_operating_baseline.md`

## Repository Inspection and Evidence Surfaces

- `docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §6.9
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md` (rubric alignment only where consistent with roadmap numeric frame)
- `ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py`
- `ai_stack/tests/test_goc_multi_turn_experience_quality.py`
- `ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py`
- `ai_stack/goc_s4_misinterpretation_scenario.py`
- `ai_stack/tests/test_goc_retrieval_heavy_scenario.py`
- `ai_stack/goc_g9_roadmap_scenarios.py`
- `docs/goc_evidence_templates/g9_experience_score_matrix.template.json`
- `scripts/g9_threshold_validator.py`
- `scripts/g9_level_a_evidence_capture.py`
- **Authoritative Level A evaluative run — evidence bundle:** `tests/reports/evidence/g9_level_a_fullsix_20260410/`

**Authoritative vs historical (non-negotiable):** This run is the **current authoritative Level-A** G9 evaluative result on the repository. Earlier full or partial evidence bundles remain **historical context only** and must not be mixed into this threshold story without explicit `audit_run_id` boundaries.

## Required Scenario Set (Roadmap §6.9) — Mapping to Repo Anchors

**Anti-substitution rule:** The six roadmap scenarios are not substitutable, mergeable, or droppable. The table below binds each required scenario to concrete automated anchors. Gaps must be stated explicitly in audit text and score evidence.

| # | Roadmap scenario | Primary automated anchors | Transcript / trace pointers |
|---|------------------|---------------------------|-----------------------------|
| 1 | Direct provocation | `test_scenario_standard_escalation_non_preview` (`ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py`) | `trace-p2-escalate`; `visible_output_bundle`, `selected_scene_function`, `graph_diagnostics.dramatic_review` |
| 2 | Deflection / brevity | `test_scenario_thin_edge_silence_non_preview` | `trace-p2-thin`; `silence_brevity_decision`, pacing `thin_edge` |
| 3 | Pressure escalation | `test_scenario_multi_pressure_non_preview` | `trace-p2-multi`; `scene_assessment.multi_pressure_resolution` |
| 4 | Misinterpretation / correction | `test_roadmap_s4_misinterpretation_correction_chain` (`ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py`); canonical chain in `ai_stack/goc_s4_misinterpretation_scenario.py` | `trace-roadmap-s4-t1-misroute`, `trace-roadmap-s4-t2-correction`, `trace-roadmap-s4-t3-incorporation`; `roadmap_s4_evidence` in scenario JSON |
| 5 | Primary model failure + fallback | `test_experience_multiturn_primary_failure_fallback_and_degraded_explained` — primary `openai` path uses `ErrorAdapter`; graph `fallback_model` uses **`mock`** adapter wired to a succeeding fixture (`JsonAdapter`) so recovery is exercised | `trace-p3-c3`; `nodes_executed` includes `fallback_model`; `routing.fallback_stage_reached` (`graph_fallback_executed`); `generation.fallback_used`; after recovery: `validation_outcome` approved, `dramatic_review.run_classification` **pass** |
| 6 | Retrieval-heavy context | `test_roadmap_scenario_retrieval_heavy_governance_visible` (`ai_stack/tests/test_goc_retrieval_heavy_scenario.py`) | `trace-roadmap-s6-retrieval-heavy`; `retrieval_governance_summary`, dramatic turn `retrieval_record` |

## Historical runs (do not mix without `audit_run_id`)

- **`g9_level_a_20260408`:** Six pytest nodes executed, but S4 was mapped to `test_phase3_run_b_continuity_changes_later_behavior_more_than_once` (continuity re-staging, not misunderstanding/correction). Score matrix left S4 null; validator `complete: false`. See `tests/reports/evidence/g9_level_a_20260408/`.
- **`g9_s4_closure_20260409`:** Partial bundle only (`evidence_run_scope: s4_closure_partial`); not a full six-scenario G9 matrix. See `tests/reports/evidence/g9_s4_closure_20260409/`.
- **`g9_s5_targeted_20260409`:** Partial bundle only (`evidence_run_scope: s5_targeted_partial`); S5-targeted improvement witness. Does **not** replace the authoritative full-six matrix; see `tests/reports/evidence/g9_s5_targeted_20260409/`.
- **`g9_level_a_fullsix_20260409`:** Full six-scenario Level A bundle with complete 6×5 matrix; validator `complete: true`, `pass_all: false` (scenario-average rule failed on S5 row). **Historical** — superseded for the §6.9 threshold story by `g9_level_a_fullsix_20260410`. See `tests/reports/evidence/g9_level_a_fullsix_20260409/`.

## S5-targeted partial run (`g9_s5_targeted_20260409`) — historical input

**Purpose:** Documented stronger S5 primary-failure + mock fallback recovery **before** the post-S5 full six-scenario rerun; remains a partial bundle only.

- **Pytest anchor:** `ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained` (witness: `pytest_s5_anchor.txt` in that bundle).
- **Artifacts:** `run_metadata.json`, `scenario_goc_roadmap_s5_primary_failure_fallback.json`, `pytest_s5_anchor.txt`, `s5_evidence_notes.md`, `g9_s5_provisional_evaluator_row.json` (S5-only — **not** the 6×5 matrix).

## Level A evaluative evidence run (`g9_level_a_fullsix_20260410`)

### Executed scenarios (pytest technical witness)

Six roadmap-aligned tests were executed in one bundle (repository root, `PYTHONPATH` = repo root):

```text
ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_standard_escalation_non_preview
ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_thin_edge_silence_non_preview
ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py::test_scenario_multi_pressure_non_preview
ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py::test_roadmap_s4_misinterpretation_correction_chain
ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained
ai_stack/tests/test_goc_retrieval_heavy_scenario.py::test_roadmap_scenario_retrieval_heavy_governance_visible
```

**Result:** 6 passed. Log: `tests/reports/evidence/g9_level_a_fullsix_20260410/pytest_g9_roadmap_bundle.txt` (includes `exit_code` line).

### Structured capture (same graph shapes as tests)

- Script: `scripts/g9_level_a_evidence_capture.py`
- Command: `python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/g9_level_a_fullsix_20260410 --audit-run-id g9_level_a_fullsix_20260410 --evidence-run-note "Full six-scenario Level A G9 witness: pytest_g9_roadmap_bundle.txt in this directory (six nodes, same anchors as gate_G9 baseline)."`
- Outputs per scenario: `scenario_goc_roadmap_s_<n>_*.json` in `tests/reports/evidence/g9_level_a_fullsix_20260410/`
- Run metadata: `run_metadata.json` (`audit_run_id`, `timestamp_utc`, git commit + dirty flag, `python_version`, `active_environment_path`, `evaluator_id`, `evidence_run_scope: g9_level_a_capture_all_script_scenarios`)

### Score matrix (single evaluator)

- File: `tests/reports/evidence/g9_level_a_fullsix_20260410/g9_experience_score_matrix.json`
- **Scored rows:** S1–S6 — numeric 1–5 with `cell_rationale` tied to fields in the scenario JSON files in **this** bundle. S4 uses the canonical misinterpretation/correction chain; `roadmap_s4_status: meets_roadmap_s4_misinterpretation_correction_bar` in `scenario_goc_roadmap_s4_misinterpretation_correction.json`. S5 scores reflect post-fallback **committed** narration and `validation_outcome` / `dramatic_review` **pass** on the failure turn (`scenario_goc_roadmap_s5_primary_failure_fallback.json`).

### Threshold calculation (canonical validator)

- Command: `python scripts/g9_threshold_validator.py tests/reports/evidence/g9_level_a_fullsix_20260410/g9_experience_score_matrix.json`
- Archived output: `tests/reports/evidence/g9_level_a_fullsix_20260410/g9_threshold_validator_output.json`
- Process exit code: `0` (archived in `g9_threshold_validator_exitcode.txt`) because `pass_all` is true.

**Validator result:** `complete: true`, `pass_all: true`. All §6.9 rules in the validator are satisfied on this completed matrix (`min_scenario_average`: 4.4, `min_cell`: 4.0, `min_graceful_degradation_failure_scenarios`: 5.0).

**Roadmap §6.9 threshold pass:** **Satisfied** on authoritative run `g9_level_a_fullsix_20260410` — numeric closure computed and all threshold rules pass.

## Scoring Rubric (Roadmap §6.9)

Each acceptance scenario is scored **1–5** on: dramatic responsiveness; truth consistency; character credibility; conflict continuity; graceful degradation. Graceful degradation ≥ 3.5 applies to failure-oriented scenarios per validator mapping (`goc_roadmap_s5_primary_failure_fallback` has `failure_oriented: true`).

## Command Strategy (authoritative + closure rerun policy)

| command | status | execution evidence |
| --- | --- | --- |
| Six-test pytest bundle (authoritative run) | `repo-verified` | `tests/reports/evidence/g9_level_a_fullsix_20260410/pytest_g9_roadmap_bundle.txt` |
| `python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/g9_level_a_fullsix_20260410 --audit-run-id g9_level_a_fullsix_20260410` (+ note) | `repo-verified` | Scenario JSON files + `run_metadata.json` in same directory |
| `python scripts/g9_threshold_validator.py tests/reports/evidence/g9_level_a_fullsix_20260410/g9_experience_score_matrix.json` | `repo-verified` | `g9_threshold_validator_output.json`, `g9_threshold_validator_stdout.txt`, `g9_threshold_validator_stderr.txt`, `g9_threshold_validator_exitcode.txt` |
| Six-test pytest bundle rerun for all-gates closure adjudication | `repo-verified` | `tests/reports/evidence/all_gates_closure_20260409/g9_pytest_six_scenarios_rerun.txt` (6 passed) |
| Validator rerun on preserved authoritative matrix | `repo-verified` | `tests/reports/evidence/all_gates_closure_20260409/g9_validator_a_on_authoritative_matrix.json` (`pass_all: true`) |

## Status Baseline (updated for `g9_level_a_fullsix_20260410`)

- structural_status: `green`
- closure_level_status: `level_a_capable` *(§6.9 thresholds met on this authoritative run; does not, by itself, assert program-wide Level A closure — see G10 and `closure_level_classification_summary.md`.)*
- **g9_roadmap_threshold_pass (§6.9):** `true` (complete matrix; thresholds computed; `pass_all: true`)

**Rationale:** Full six-scenario pytest witness, structured capture, complete 6×5 score matrix with per-cell rationale grounded in this bundle, and validator `pass_all: true`. **No** MVP or program-wide Level A closure is asserted from G9 alone (G10 integrative chain and other gates still govern global closure).

**Preservation policy applied:** Existing authoritative G9 evidence (`g9_level_a_fullsix_20260410`) is preserved as authoritative in this closure pass because rerun validation remained consistent and no contradiction required matrix regeneration.

## Immediate follow-ups

1. Keep S4 anchored on `test_roadmap_s4_misinterpretation_correction_chain` + `goc_s4_misinterpretation_scenario.py` for future runs.
2. Re-run the six-node bundle under Python 3.10 (CI parity per `docs/testing-setup.md`) if regression or environment drift is a concern.

## Evidence Quality

- evidence_quality: `high` for **evaluative completeness** (six scenarios, six tests, full matrix, computed thresholds, §6.9 pass).

## Execution Risks Carried Forward

- Environment drift: capture metadata records host Python 3.13; CI merge bar is Python 3.10 per `docs/testing-setup.md` — re-run pytest in CI-parity env if regression is suspected.
- Scoring drift without locking rubric notes to concrete JSON fields in the evidence bundle.
