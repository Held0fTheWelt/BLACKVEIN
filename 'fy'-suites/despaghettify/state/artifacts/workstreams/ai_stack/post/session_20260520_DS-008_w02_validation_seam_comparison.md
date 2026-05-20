# DS-008 w02 post-comparison — validation seam retry/context split

Session: 20260520

Pre:

- Wave 1 had already extracted `_build_runtime_aspect_validation` from the LangGraph executor.
- `_validate_seam` still owned embedded validation execution, retry feedback assembly, and validation update copying.
- Local post-w01 measurement: `_validate_seam` 500 source lines / nesting depth 16.

Post:

- Added validation seam helpers to `ai_stack/langgraph/langgraph_runtime_validation.py`:
  - `run_runtime_validation_seam`
  - `build_validation_retry_feedback`
  - `build_retry_attempt_record_update`
  - `copy_validation_eval_to_update`
- `_validate_seam` now delegates those sections and retains graph-node orchestration only.
- Local post-w02 measurement: `_validate_seam` 231 source lines.
- Formal `check --with-metrics` no longer lists `_build_runtime_aspect_validation` or `_validate_seam` in top longest or top nesting rankings.
- Formal scan counts after DS-008: 10731 functions, 857 functions over 50 lines, 235 functions over 100 lines, 25 functions at nesting depth >= 6.

Gates:

- `python -m compileall -q ai_stack/langgraph` — passed.
- `pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` — 51 passed.
- `python tests/run_tests.py --suite ai_stack_graph ai_stack_narrative ai_stack_quality --quick` — ai_stack_graph 260 passed; ai_stack_narrative 880 passed; ai_stack_quality 502 passed, 1 skipped.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` — passed; report `2026-05-20T19:32:19Z`.

Residual follow-up:

- The executor still has large context/action functions (`_build_dramatic_generation_packet`, `_assemble_model_context`, `_interpret_input`, `_resolve_player_action`). These are no longer validation-seam blockers and are carried by the remaining LangGraph context/literal work in DS-010.
