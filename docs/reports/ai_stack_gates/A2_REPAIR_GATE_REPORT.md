# A2 Repair Gate Report — World-Engine Authoritative Narrative Commit

Date: 2026-04-04

## 1. Scope completed

- Added authoritative scene progression commit logic to World-Engine story runtime turns.
- Bound progression legality to runtime projection data (`scenes`, `transition_hints`) instead of diagnostics-only flow.
- Added explicit progression commit records to turn events and diagnostics.
- Exposed committed state snapshot in state/diagnostics responses.
- Added regression tests for legal commit, illegal rejection, diagnostics coherence, and multi-turn progression.

## 2. Files changed

- `world-engine/app/story_runtime/manager.py`
- `world-engine/tests/test_story_runtime_rag_runtime.py`
- `docs/architecture/world_engine_authoritative_narrative_commit.md`
- `docs/reports/ai_stack_gates/A2_REPAIR_GATE_REPORT.md`

## 3. What is truly wired

- `StoryRuntimeManager.execute_turn` now performs commit-time progression checks and mutates `session.current_scene_id` only on legal transitions.
- Commit legality uses runtime projection artifacts at execution time:
  - known scenes from `runtime_projection.scenes`
  - allowed edges from `runtime_projection.transition_hints`
- Turn events now include `progression_commit` with proposal, verdict, and committed result.
- `get_state` and `get_diagnostics` include committed state snapshots that are distinct from graph diagnostics.

## 4. What remains incomplete

- Commit semantics currently target scene progression authority; broader canonical world-state delta commits remain future work.
- Scene proposal extraction is intentionally conservative and currently strongest for explicit movement commands plus scene-id mentions.

## 5. Tests added/updated

- Added in `world-engine/tests/test_story_runtime_rag_runtime.py`:
  - `test_story_runtime_commits_legal_scene_progression`
  - `test_story_runtime_rejects_illegal_scene_progression`
  - `test_story_runtime_builds_multi_turn_committed_progression`
- Existing world-engine runtime tests (`test_story_runtime_api.py`, `test_trace_middleware.py`) re-run to ensure compatibility.
- Backend bridge regression tests re-run to verify A2 changes remain compatible with backend proxy path.

## 6. Exact test commands run

```powershell
cd world-engine
python -m pytest tests/test_story_runtime_rag_runtime.py -k "commits_legal_scene_progression or rejects_illegal_scene_progression or multi_turn_committed_progression"
python -m pytest tests/test_story_runtime_api.py tests/test_story_runtime_rag_runtime.py tests/test_trace_middleware.py
```

```powershell
cd ..\backend
python -m pytest tests/test_session_routes.py -k "execute_turn_proxies_to_world_engine or capability_audit_returns_world_engine_rows"
```

```powershell
cd ..
$env:PYTHONPATH='.'
python -m pytest story_runtime_core/tests/test_input_interpreter.py
```

## 7. Pass / Partial / Fail

Pass

## 8. Reason for the verdict

- Story turns now produce committed runtime progression when legal (`current_scene_id` mutation is real and persisted in session state).
- Illegal progression attempts are rejected safely and explicitly without corrupting committed state.
- Diagnostics now report progression commit outcomes and align with authoritative committed state.
- Multi-turn tests demonstrate real session progression across repeated turns.

## 9. Risks introduced or remaining

- Projects with sparse or inconsistent `transition_hints` can intentionally block progression commits (`transition_hints_missing`), which is safe but may require content updates.
- Scene proposal extraction is deterministic but simple; richer intent-to-scene inference can be added later without weakening current legality guardrails.
