# Gate G4 Baseline: Scene Direction Boundary

**Repository-truth note (2026-04-10):** Scenario coverage moved from `test_goc_phase2_scenarios.py` to `test_goc_runtime_breadth_continuity_diagnostics.py`. Archived transcripts may still mention the old module name.

## Gate

- Gate name: G4 Scene Direction Boundary
- Gate class: structural
- Audit subject: deterministic-first bounded scene-direction architecture and forbidden-behavior prevention

## Repository Inspection Targets

- `ai_stack/scene_director_goc.py`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/langgraph_runtime.py`
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`
- `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py`
- `ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py`

## Required Evidence

- mapped scene-direction subdecision matrix fields
- deterministic and bounded seams around model proposals
- anti-overwrite safeguards for director-selected fields
- scenario tests showing bounded behavior

## Audit Methods Used In This Baseline

- static scene-direction seam analysis
- contract-to-implementation comparison
- static scenario-test surface review (no test execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `python -m pytest ai_stack/tests/test_scene_direction_subdecision_matrix.py ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py -q --tb=short` | `repo-verified` | Canonical matrix + bounded scenario behavior path for G4 (renamed scenario module). | Archived: `tests/reports/evidence/all_gates_closure_20260409/g4_scene_direction_boundary.txt` |

## Baseline Findings

1. `scene_director_goc.py` contains deterministic selection helpers (`select_single_scene_function`) and frozen-vocab assertions for scene/pacing/silence decisions.
2. Runtime and seam code include validation and projection boundaries around model generation and commit seams.
3. Explicit subdecision matrix behavior is now covered by executed `test_scene_direction_subdecision_matrix.py` plus scenario behavior checks.
4. Executed scenario evidence is attached in the closure bundle and shows bounded behavior on the canonical path.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: deterministic-first bounded architecture is present and canonical matrix/scenario verification passed with archived evidence.

## Evidence Quality

- evidence_quality: `high`
- justification: static seam evidence plus executed canonical matrix/scenario transcript in `all_gates_closure_20260409`.

## Execution Risks Carried Forward

- Keep matrix/scenario command pair as required regression evidence for scene-direction changes.
