# DS-008 w01 pre-snapshot — LangGraph runtime aspect validation

Session: 20260520

Scope:

- DS-008 targets `ai_stack/langgraph/langgraph_runtime_executor.py`.
- This wave owns `_build_runtime_aspect_validation` and preserves the existing import/export surface used by tests.
- No changes are planned for `_assemble_model_context`, `_build_dramatic_generation_packet`, or world-engine paths in this wave.

Current hotspot evidence from the latest metrics scan (`2026-05-20T18:57:34Z`):

- `_build_runtime_aspect_validation`: 1569 AST lines, nesting depth 19.
- `_validate_seam`: 500 AST lines, nesting depth 16.
- `_build_dramatic_generation_packet`: 562 AST lines, nesting depth 2.
- `ai_stack/langgraph/langgraph_runtime_executor.py:_assemble_model_context` remains the DS-010 literal hotspot and is intentionally out of scope for this wave.

Planned change:

- Add a focused runtime validation module under `ai_stack/langgraph/`.
- Keep `_build_runtime_aspect_validation(...)` available from `langgraph_runtime_executor.py`.
- Pass executor-local validation hooks into the extracted module so the existing behavior remains unchanged and no reverse import from the new module to the executor is introduced.

Gates for this wave:

- `python -m compileall -q ai_stack/langgraph`
- `pytest ai_stack/tests/test_character_voice_runtime_enforcement.py ai_stack/tests/test_runtime_authority_aspects.py -q --tb=short`
- `python tests/run_tests.py --suite ai_stack_narrative ai_stack_quality --quick`
