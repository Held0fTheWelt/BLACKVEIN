# Workstream: ai_stack

## In flight — DS-010 runtime executor split (session 20260521)

| Sub-wave | Outcome | Primary files / symbols | Evidence |
|----------|---------|--------------------------|----------|
| w01 | Physical runtime-executor split under 200 lines per file, with clear responsibility names and code-adjacent documentation. This is a transitional loader split; semantic promotion into ordinary modules remains open. | `ai_stack/langgraph/langgraph_runtime_executor.py`, `ai_stack/langgraph/runtime_executor/`; `_build_dramatic_generation_packet`, `_assemble_model_context`, `_director_select_dramatic_parameters`, `_interpret_input`, `_resolve_player_action` | Pre snapshot: `artifacts/workstreams/ai_stack/pre/session_20260521_DS-010_runtime_executor_split_snapshot.*`; post comparison: `artifacts/workstreams/ai_stack/post/session_20260521_DS-010_w01_runtime_executor_split_comparison.*` |

**Current structure:** `ai_stack/langgraph/langgraph_runtime_executor.py` is a compatibility facade. `ai_stack/langgraph/runtime_executor/public.py` assembles named source groups from `ai_stack/langgraph/runtime_executor/*.py`. `ai_stack/langgraph/runtime_executor/README.md` explains the loader, responsibility groups, and next extraction pass.

**Gates so far:**

- `python -m compileall -q ai_stack/langgraph/langgraph_runtime_executor.py ai_stack/langgraph/runtime_executor` — pass
- File-line check for facade + staging package — pass; max 186 lines, 0 files over 200, 0 numbered suffix names
- `pytest ai_stack/tests/test_responder_reconciliation.py ai_stack/tests/test_runtime_authority_aspects.py ai_stack/tests/test_phase1_live_wiring.py -q --tb=short` — 93 passed
- `pytest ai_stack/tests/test_phase_c_reaction_order_governance.py -q --tb=short` — 27 passed
- `pytest ai_stack/tests/test_wave3_multi_actor_vitality.py -q --tb=short` — 38 passed
- `PYTHONPATH="'fy'-suites" python "'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"` — pass; executor leaders no longer appear in top longest/nesting rankings
- `PYTHONPATH="'fy'-suites" python -m docify.tools audit --root ai_stack/langgraph/runtime_executor --json --out "'fy'-suites/docify/reports/ds010_runtime_executor_doc_audit.json" --exit-zero` — pass; 0 findings, 0 parse errors
- `PYTHONPATH="'fy'-suites" python -m docify.tools drift --paths-file /tmp/ds010_docify_paths.txt --json --out "'fy'-suites/docify/reports/ds010_runtime_executor_doc_drift.json"` — pass; report written
- `git diff --check` for touched executor/despaghettify report files — pass

**Caveat:** `check --with-metrics` writes `../reports/latest_check_with_metrics.json` but exits 1 because the existing DS-005 runtime import check cannot import `app.runtime.turn_executor` in the current tree. That is outside this executor split.

**Next DS-010 pass:** promote `SOURCE_LINES` chunks into ordinary Python modules by responsibility group, starting with semantic input, actor lanes, retrieval, dramatic packet, and director context. Keep the compatibility facade until direct imports move to stable module names.

## Closed — DS-008 (session 20260520)

| Sub-wave | Goal | Primary files / symbols | Gate |
|----------|------|--------------------------|------|
| 1 | Extract the LangGraph runtime aspect validation orchestration into a focused module while preserving the existing executor export and validation contract. | `ai_stack/langgraph/langgraph_runtime_executor.py`, `ai_stack/langgraph/langgraph_runtime_validation.py`; `_build_runtime_aspect_validation` | `python -m compileall -q ai_stack/langgraph`; `pytest ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short`; `python tests/run_tests.py --suite ai_stack_narrative ai_stack_quality --quick` |
| 2 | Thin the validation seam retry/context surface around the extracted validation module without changing graph node behavior. | `ai_stack/langgraph/langgraph_runtime_executor.py`; `_validate_seam` | `python -m compileall -q ai_stack/langgraph`; `pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short`; `python tests/run_tests.py --suite ai_stack_graph ai_stack_narrative ai_stack_quality --quick`; `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` |

**Plan mirror:** `artifacts/workstreams/ai_stack/pre/session_20260520_DS-008_wave_plan.json`

**Outcome:** `_build_runtime_aspect_validation` moved behind a stable executor wrapper into `ai_stack/langgraph/langgraph_runtime_validation.py`; `_validate_seam` now delegates validation seam execution, retry feedback assembly, retry attempt record assembly, and validation update copying. Formal scan no longer lists either DS-008 primary symbol in top longest/nesting rankings.

**Gates (final):**

- `python -m compileall -q ai_stack/langgraph` — pass
- `pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` — 51 passed
- `python tests/run_tests.py --suite ai_stack_graph ai_stack_narrative ai_stack_quality --quick` — pass
- `check --with-metrics` — pass, report `2026-05-20T19:32:19Z`

**Post artefacts:** `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w01_runtime_validation_comparison.*`, `artifacts/workstreams/ai_stack/post/session_20260520_DS-008_w02_validation_seam_comparison.*`

## Closed — DS-003, DS-005 (session 20260520)

RAG module split + shared GoC YAML cache fixture (C6). Validation seam extracted to `goc_turn_seams_validation.py` (C7).

**Gates (final):**

- `python tests/run_tests.py --suite ai_stack_goc ai_stack_retrieval_research --quick` — pass
- `pytest ai_stack/tests/test_w5_actor_situation_validation.py ai_stack/tests/test_goc_transcript_shell_validation.py ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py` — 27 passed

**Post artefacts:** `artifacts/workstreams/ai_stack/post/session_20260520_DS-003-005_*.json`
