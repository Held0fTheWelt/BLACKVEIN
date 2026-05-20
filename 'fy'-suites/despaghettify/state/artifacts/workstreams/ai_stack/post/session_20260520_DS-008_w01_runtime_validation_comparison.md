# DS-008 w01 post-comparison — runtime aspect validation extraction

Session: 20260520

Pre:

- `_build_runtime_aspect_validation` lived in `ai_stack/langgraph/langgraph_runtime_executor.py`.
- Baseline hotspot: 1569 AST lines, nesting depth 19.
- Latest full scan before the wave: 10677 functions, 858 functions over 50 lines, 236 functions over 100 lines, 27 functions at nesting depth >= 6.

Post:

- Added `ai_stack/langgraph/langgraph_runtime_validation.py` as the focused runtime aspect validation module.
- Kept `_build_runtime_aspect_validation(...)` exported from `langgraph_runtime_executor.py` as a stable wrapper.
- The extracted module receives executor-local hooks explicitly; it does not import the executor back.
- Local AST check after the wave: 10723 functions, 857 functions over 50 lines, 235 functions over 100 lines, 26 functions at nesting depth >= 6.
- `_build_runtime_aspect_validation` no longer appears in the top longest/nesting rankings. The new module's largest function is `_initial_context` at 50 source lines.

Gates:

- `python -m compileall -q ai_stack/langgraph` — passed.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli wave-plan-validate --file "'fy'-suites/despaghettify/state/artifacts/workstreams/ai_stack/pre/session_20260520_DS-008_wave_plan.json" --check-primary-paths` — passed after the new module existed.
- `pytest ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short` — 41 passed.
- `python tests/run_tests.py --suite ai_stack_narrative ai_stack_quality --quick` — ai_stack_narrative 880 passed; ai_stack_quality 502 passed, 1 skipped.

Remaining DS-008 work:

- Wave 2 owns `_validate_seam` and retry/context handling. The post-scan still shows `_validate_seam` at 500 AST lines / depth 16, plus context/action executor functions outside this wave.
